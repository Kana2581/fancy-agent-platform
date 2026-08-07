---
name: csv_profile
description: 对工作区里的 CSV 做字段概览（类型/缺失率/数值描述），含可直接运行的脚本
---

# CSV 概览技能

用 `profile.py` 对一份 CSV 输出字段类型、缺失率和数值列描述。

## 用法

1. 先把要分析的 CSV 放到工作区根目录并命名为 `input.csv`。
2. 用 Bash 读取本 Skill 的 `SKILL.md` 和 `profile.py`，路径分别是
   `/skills/system/csv_profile/SKILL.md` 和
   `/skills/system/csv_profile/profile.py`。
3. 用 Bash 在工作区执行脚本：
   `python /skills/system/csv_profile/profile.py`。

脚本只用预装的 pandas，不联网、不读工作区以外的文件。
