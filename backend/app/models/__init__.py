
import pkgutil
import importlib
import inspect
from sqlalchemy.orm import DeclarativeMeta


# 遍历当前包下的所有模块
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f".{module_name}", package=__name__)

    # 遍历模块里的所有类
    for name, obj in inspect.getmembers(module):
        # 如果是SQLAlchemy Base子类（模型）
        if isinstance(obj, DeclarativeMeta):
            globals()[name] = obj  # 导入到__init__的全局空间
