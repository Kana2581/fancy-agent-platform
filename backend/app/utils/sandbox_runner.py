"""共享的 Python 软沙箱 runner —— **纯 stdlib，不依赖 app 包**。

backend 本地回退路径与独立 sandbox 容器服务两侧共用同一份逻辑，避免漂移。
（sandbox 镜像构建时把本文件 COPY 进去；见 sandbox/Dockerfile。）

软沙箱三层（沿用历史设计）：
1. 净化环境 —— 只透传无害环境变量，阻断凭证泄露
2. 白名单 __import__ —— 用户代码顶层只能 import _ALLOWED_MODULES
3. 沙箱化 open/io.open —— 限制在执行目录（cwd）内

与旧版的关键差异：runner 脚本与 user_code 落在**独立临时目录**，而执行 cwd
指向会话工作区，因此用户代码的相对文件读写、matplotlib 产物都落在工作区里，
且不会用 _runner.py / user_code.py 污染工作区。路径经环境变量传入，避免跨平台
转义问题。
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# 允许用户代码顶层导入的模块白名单（安全边界，不等于镜像已安装的集合）
ALLOWED_MODULES = {
    "math", "cmath", "random", "statistics", "decimal", "fractions", "numbers",
    "json", "csv", "datetime", "calendar", "time",
    "collections", "itertools", "functools", "operator", "copy", "pprint",
    "typing", "dataclasses", "enum", "abc", "contextlib", "warnings",
    "re", "string", "textwrap", "unicodedata", "difflib",
    "base64", "hashlib", "hmac", "struct", "binascii", "codecs",
    "urllib", "html", "xml",
    "numpy", "pandas", "matplotlib", "scipy", "sklearn", "seaborn",
    "PIL", "cv2", "skimage", "plotly", "bokeh", "altair",
}

# Layer 1: 仅保留无害的环境变量传入子进程
_SAFE_ENV_KEYS_COMMON = {
    "PATH", "HOME", "LANG", "LC_ALL", "TMP", "TEMP", "TMPDIR",
    "PYTHONDONTWRITEBYTECODE",
}
# Windows 子进程加载 DLL、解析系统路径需要这些变量
_SAFE_ENV_KEYS_WINDOWS = {"SYSTEMROOT", "SystemRoot", "WINDIR", "PATHEXT"}


def make_clean_env(meta_dir: str) -> dict:
    """构造净化后的子进程环境。meta_dir 作为 HOME/配置目录，避免触达真实用户目录。"""
    safe_keys = _SAFE_ENV_KEYS_COMMON | (_SAFE_ENV_KEYS_WINDOWS if sys.platform == "win32" else set())
    clean = {k: os.environ[k] for k in safe_keys if k in os.environ}

    clean["MPLCONFIGDIR"] = meta_dir  # matplotlib 配置目录，指向私有临时目录
    clean["PYTHONPATH"] = ""          # 不继承宿主的模块搜索路径

    if sys.platform == "win32":
        clean["USERPROFILE"] = meta_dir
        clean["APPDATA"] = meta_dir
        clean["LOCALAPPDATA"] = meta_dir
    else:
        clean["HOME"] = meta_dir

    return clean


# Layer 3: 子进程 runner 脚本模板。
# 路径通过环境变量传入：
#   SANDBOX_USER_CODE  —— 用户代码文件的绝对路径（位于私有临时目录，不在工作区）
#   SANDBOX_OUTPUT_DIR —— matplotlib 产物保存目录（= 执行 cwd = 会话工作区）
# open/io.open 的沙箱根 = 当前工作目录（cwd），即会话工作区。
_RUNNER_TEMPLATE = """\
import sys as _sys
import os as _os
import builtins as _builtins_mod

# ---------- matplotlib 图表保存设置 ----------
try:
    import matplotlib as _matplotlib
    _matplotlib.use('Agg')
    import matplotlib.pyplot as _plt
    _OUTPUT_DIR = _os.environ.get('SANDBOX_OUTPUT_DIR', '.')
    _plot_counter = [0]

    def _patched_show(*_a, **_kw):
        _plot_counter[0] += 1
        _path = _os.path.join(_OUTPUT_DIR, f'plot_{{_plot_counter[0]}}.png')
        _plt.savefig(_path, bbox_inches='tight', dpi=150)
        _plt.close()
        print(f'[图表已保存: plot_{{_plot_counter[0]}}.png]')

    _plt.show = _patched_show
except ImportError:
    pass

# ---------- 安全沙箱：白名单 __import__ + 屏蔽高危内置 ----------
# 原理：_safe_import 只限制用户代码顶层 import；
# 库内部的 import（使用各自模块 globals）不受影响，故 numpy/matplotlib 可正常运行。
_ALLOWED_MODULES = {allowed_modules!r}
_orig_import = _builtins_mod.__import__


def _safe_import(name, glob=None, loc=None, fromlist=(), level=0):
    if level == 0:  # 只检查绝对导入
        top = name.split('.')[0]
        if top not in _ALLOWED_MODULES:
            raise ImportError(f"不允许导入模块: {{name}}")
    return _orig_import(name, glob, loc, fromlist, level)


_safe_builtins = vars(_builtins_mod).copy()
_safe_builtins['__import__'] = _safe_import
for _k in ('exec', 'eval', 'compile', 'breakpoint'):
    _safe_builtins.pop(_k, None)

# ---------- 沙箱文件访问：open / io.open 限制在 cwd（会话工作区）内 ----------
_SANDBOX_DIR = _os.path.realpath(_os.path.abspath('.'))
_real_open = _builtins_mod.open

def _safe_open(file, mode='r', *_a, **_kw):
    if isinstance(file, (str, bytes)):
        _abs = _os.path.realpath(_os.path.abspath(str(file)))
        if not _abs.startswith(_SANDBOX_DIR):
            raise PermissionError(f"沙箱限制：不允许访问工作区外路径: {{file}}")
    return _real_open(file, mode, *_a, **_kw)

_safe_builtins['open'] = _safe_open

try:
    import io as _io_mod
    _real_io_open = _io_mod.open
    def _safe_io_open(file, mode='r', *_a, **_kw):
        if isinstance(file, (str, bytes)):
            _abs = _os.path.realpath(_os.path.abspath(str(file)))
            if not _abs.startswith(_SANDBOX_DIR):
                raise PermissionError(f"沙箱限制：不允许访问工作区外路径: {{file}}")
        return _real_io_open(file, mode, *_a, **_kw)
    _io_mod.open = _safe_io_open
except Exception:
    pass

# ---------- 读取并执行用户代码 ----------
with _real_open(_os.environ['SANDBOX_USER_CODE'], 'r', encoding='utf-8') as _f:
    _user_code = _f.read()

try:
    _code_obj = compile(_user_code, '<user_code>', 'exec')
except SyntaxError as _e:
    print(f'语法错误: {{_e}}', file=_sys.stderr)
    _sys.exit(1)

_glb = {{'__builtins__': _safe_builtins, '__name__': '__main__'}}
try:
    exec(_code_obj, _glb)
except ImportError as _e:
    _msg = str(_e)
    if '不允许导入模块' in _msg:
        _mod = _msg.replace('不允许导入模块: ', '').strip()
        print(f"【安全拦截】导入 '{{_mod}}' 已被安全策略禁止，请改用允许的数据/计算类模块。", file=_sys.stderr)
    else:
        import traceback as _tb
        _tb.print_exc()
    _sys.exit(1)
except Exception:
    import traceback as _tb
    _tb.print_exc()
    _sys.exit(1)
"""


def _snapshot(workdir: Path) -> Dict[str, Tuple[int, int]]:
    """记录工作区内每个文件的 (size, mtime_ns)，用于执行前后 diff 出新增/改动文件。"""
    snap: Dict[str, Tuple[int, int]] = {}
    if not workdir.exists():
        return snap
    for entry in workdir.rglob("*"):
        try:
            if entry.is_file():
                st = entry.stat()
                snap[entry.relative_to(workdir).as_posix()] = (st.st_size, st.st_mtime_ns)
        except OSError:
            continue
    return snap


def _diff_produced(
    before: Dict[str, Tuple[int, int]],
    after: Dict[str, Tuple[int, int]],
) -> List[str]:
    """返回新增或被修改的文件相对路径（已存在且未变的不算产物）。"""
    return sorted(rel for rel, meta in after.items() if before.get(rel) != meta)


def execute(
    code: Optional[str] = None,
    workdir: str = ".",
    timeout: int = 30,
    script_path: Optional[str] = None,
) -> dict:
    """在 workdir（会话工作区）内执行用户代码，返回结构化结果。

    两种入口（二选一）：
    - code：内联代码字符串，写入私有临时目录后作为入口。
    - script_path：工作区内已有脚本的绝对路径，**直接以该文件为入口用户代码**
      （用于运行 use_skill 物化出来的 .skills/... 脚本）。受同一套白名单/open 限制。

    返回 {stdout, stderr, exit_code, produced}；produced 为本次执行新增/改动的文件相对路径。
    runner 落在独立临时目录，不污染工作区。
    """
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    before = _snapshot(work)

    meta_dir = tempfile.mkdtemp(prefix="sandbox_meta_")
    try:
        if script_path is not None:
            entry = Path(script_path)
            if not entry.is_file():
                return {"error": f"脚本不存在: {script_path}", "stdout": "", "stderr": "",
                        "exit_code": -1, "produced": []}
            user_code_path = entry
        else:
            user_code_path = Path(meta_dir) / "user_code.py"
            user_code_path.write_text(code or "", encoding="utf-8")
        runner_path = Path(meta_dir) / "_runner.py"
        runner_path.write_text(
            _RUNNER_TEMPLATE.format(allowed_modules=ALLOWED_MODULES),
            encoding="utf-8",
        )

        env = make_clean_env(meta_dir)
        env["SANDBOX_USER_CODE"] = str(user_code_path)
        env["SANDBOX_OUTPUT_DIR"] = str(work)

        try:
            result = subprocess.run(
                [sys.executable, str(runner_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(work),
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {
                "error": f"执行超时（超过 {timeout} 秒）",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "produced": [],
            }

        after = _snapshot(work)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "produced": _diff_produced(before, after),
        }
    except Exception as e:
        return {
            "error": f"执行失败: {e}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "produced": [],
        }
    finally:
        shutil.rmtree(meta_dir, ignore_errors=True)
