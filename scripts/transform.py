"""数据转换: 合并、拼接、过滤"""

import re
from pathlib import Path

import pandas as pd


def merge_nsfc_sources(letpub_path: str, kd_path: str, output_path: str):
    """合并LetPub下载数据与kd.nsfc.cn爬取数据"""
    letpub_path, kd_path, output_path = Path(letpub_path), Path(kd_path), Path(output_path)

    print(f"[1] 读取 LetPub: {letpub_path}")
    df_letpub = pd.read_excel(letpub_path)
    df_letpub["项目编号"] = df_letpub["项目编号"].astype(str).str.strip()
    print(f"    {len(df_letpub)} 条记录, {len(df_letpub.columns)} 列")

    print(f"[2] 读取 KD: {kd_path}")
    df_kd = pd.read_csv(kd_path)
    df_kd["项目批准号"] = df_kd["项目批准号"].astype(str).str.strip()
    df_kd = df_kd[df_kd["项目名称"] != "Not Found"]
    print(f"    {len(df_kd)} 条有效记录, {len(df_kd.columns)} 列")

    kd_cols_to_add = {
        "项目参与人": "项目参与人",
        "中文摘要": "中文摘要_kd",
        "英文摘要": "英文摘要_kd",
        "结题摘要": "结题摘要_kd",
        "原文链接": "原文链接",
        "申请代码": "申请代码",
    }
    df_kd_subset = df_kd[["项目批准号"] + list(kd_cols_to_add.keys())].copy()
    df_kd_subset = df_kd_subset.rename(columns=kd_cols_to_add)
    df_kd_subset = df_kd_subset.rename(columns={"项目批准号": "项目编号"})

    print(f"[3] 合并数据...")
    df = df_letpub.merge(df_kd_subset, on="项目编号", how="left")

    def pick_longer(row, col_a, col_b):
        a = str(row.get(col_a, "") or "")
        b = str(row.get(col_b, "") or "")
        if a in ("nan", "None", ""):
            a = ""
        if b in ("nan", "None", ""):
            b = ""
        return a if len(a) >= len(b) else b

    df["结题摘要_合并"] = df.apply(lambda r: pick_longer(r, "结题摘要_kd", "结题摘要"), axis=1)
    df["中文摘要_合并"] = df.apply(lambda r: pick_longer(r, "中文摘要_kd", "申请摘要"), axis=1)

    final_columns = [
        "项目编号", "项目标题", "负责人", "单位", "所属学部", "项目类型",
        "金额（万）", "批准年份", "执行起自", "执行截至",
        "申请代码", "一级学科", "一级代码", "二级学科", "二级代码",
        "三级学科", "三级代码", "中文关键词", "英文关键词",
        "项目参与人", "中文摘要_合并", "英文摘要_kd", "结题摘要_合并", "原文链接",
    ]
    final_columns = [c for c in final_columns if c in df.columns]
    df_final = df[final_columns].copy()
    df_final = df_final.rename(columns={
        "中文摘要_合并": "申请摘要", "英文摘要_kd": "英文摘要", "结题摘要_合并": "结题摘要",
    })

    print(f"[4] 保存: {output_path}")
    df_final.to_excel(output_path, index=False, engine="openpyxl")

    total = len(df_final)
    print(f"\n{'='*50}")
    print(f"合并完成: {total} 个项目")
    print(f"{'='*50}")
    for col in df_final.columns:
        filled = (df_final[col].astype(str).str.len() > 2).sum()
        pct = filled * 100 // total
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  {col:12s}  {bar} {filled:>3d}/{total} ({pct}%)")
    print(f"{'='*50}")
    return df_final


def create_search_text(df: pd.DataFrame, columns: list[str], output_col: str = "text") -> pd.DataFrame:
    """拼接多列为可搜索文本"""
    df = df.copy()
    df[output_col] = df[columns].fillna('').astype(str).agg(' '.join, axis=1)
    return df


def filter_by_pattern(df: pd.DataFrame, col: str, pattern: str, keep: bool = True) -> pd.DataFrame:
    """正则过滤行。keep=True保留匹配行，keep=False排除匹配行"""
    mask = df[col].astype(str).str.contains(pattern, flags=re.I, na=False)
    return df[mask] if keep else df[~mask]
