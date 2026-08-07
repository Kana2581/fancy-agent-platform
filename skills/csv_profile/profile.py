import pandas as pd

# 把要分析的 CSV 命名为 input.csv 放到工作区根目录
TARGET = "input.csv"

try:
    df = pd.read_csv(TARGET)
except FileNotFoundError:
    print(f"未找到 {TARGET}，请先把目标 CSV 命名为 input.csv 放到工作区根目录。")
    raise SystemExit(0)

print(f"形状: {df.shape[0]} 行 x {df.shape[1]} 列\n")
print("=== 字段类型 ===")
print(df.dtypes.to_string())
print("\n=== 缺失率(%) ===")
print((df.isna().mean() * 100).round(2).to_string())
num = df.describe(include="number")
print("\n=== 数值列描述 ===")
print(num.to_string() if not num.empty else "（无数值列）")
