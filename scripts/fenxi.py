#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage:
  # 使用默认输入文件
  python scripts/fenxi.py

  # 指定输入文件和输出目录
  python scripts/fenxi.py --input 数据文件.csv --output_dir 输出目录

Notes:
- 默认把 "", "无此条码", "无法识别", "搜条码" 这类当作空值（可自行增删）
- 统计口径：
  - "存在" = 非空（清洗后）
  - "唯一" = 同一 manu_no 下，非空去重值数量 == 1
  - "多种" = 同一 manu_no 下，非空去重值数量 > 1

输出文件（默认全部导出）：
- summary.csv：各场景汇总（row_count / manu_no_count）
- case1_details.csv ~ case6_details.csv：各场景明细
- other_details.csv：不属于上述场景的“剩余数据”明细

新增统计：
- case5：enterprise 有多种值（enterprise_nunique > 1）
- case6：enterprise、brand 都存在，但都不唯一（enterprise_nunique > 1 且 brand_nunique > 1）
- other：不属于 case1~case5 覆盖范围的剩余行（case6 属于 case5 子集，不重复覆盖）
"""

import argparse
import os
import pandas as pd

PLACEHOLDER_AS_NULL = {
    "", " ", "  ",
    "无此条码", "无法识别", "搜条码",
    "NULL", "null", "None", "none", "N/A", "n/a"
}

TARGET_COLS = ["manu_no", "enterprise", "brand", "mt_brand_name", "eb_brand_name"]


def normalize_nulls(df: pd.DataFrame, cols):
    """Trim strings and convert placeholders to NA."""
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
            continue
        s = df[c].astype("string").str.strip()
        s = s.where(~s.isin(list(PLACEHOLDER_AS_NULL)), pd.NA)
        df[c] = s
    return df


def nunique_nonnull(s: pd.Series) -> int:
    """Number of unique non-null values."""
    s2 = s.dropna()
    return 0 if s2.empty else int(s2.nunique())


def build_group_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-manu_no uniqueness stats for enterprise/brand and presence stats for mt/eb."""
    g = df.groupby("manu_no", dropna=False)

    stats = pd.DataFrame({
        "enterprise_nunique": g["enterprise"].apply(nunique_nonnull),
        "brand_nunique": g["brand"].apply(nunique_nonnull),

        "enterprise_nonnull_rows": g["enterprise"].apply(lambda x: int(x.notna().sum())),
        "brand_nonnull_rows": g["brand"].apply(lambda x: int(x.notna().sum())),

        "mt_brand_nonnull_rows": g["mt_brand_name"].apply(lambda x: int(x.notna().sum())),
        "eb_brand_nonnull_rows": g["eb_brand_name"].apply(lambda x: int(x.notna().sum())),
        "total_rows": g.size().astype(int),
    })

    # convenience flags
    stats["enterprise_unique_exists"] = (stats["enterprise_nunique"] == 1)
    stats["brand_unique_exists"] = (stats["brand_nunique"] == 1)
    stats["brand_multi_exists"] = (stats["brand_nunique"] > 1)

    stats["enterprise_all_null"] = (stats["enterprise_nonnull_rows"] == 0)
    stats["brand_all_null"] = (stats["brand_nonnull_rows"] == 0)

    stats["mt_or_eb_brand_exists"] = (stats["mt_brand_nonnull_rows"] > 0) | (stats["eb_brand_nonnull_rows"] > 0)
    stats["mt_and_eb_brand_all_null"] = (stats["mt_brand_nonnull_rows"] == 0) & (stats["eb_brand_nonnull_rows"] == 0)

    return stats.reset_index()


def summarize_case(df_case: pd.DataFrame, case_name: str) -> dict:
    return {
        "case": case_name,
        "row_count": int(len(df_case)),
        "manu_no_count": int(df_case["manu_no"].nunique(dropna=False)),
    }


def save_details(df_case: pd.DataFrame, keep_cols: list, out_path: str) -> int:
    """Always write details file; even if empty, still write header for visibility."""
    cols = [c for c in keep_cols if c in df_case.columns]
    if not cols:
        cols = ["manu_no"] if "manu_no" in df_case.columns else list(df_case.columns[:1])
    df_case[cols].to_csv(out_path, index=False, encoding="utf-8-sig")
    return len(df_case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./data/ner_key_product_info_top95.csv",
                        help="Input CSV path (default: ./data/ner_key_product_info_top95.csv)")
    parser.add_argument("--output_dir", default="out", help="Output directory")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default utf-8)")
    parser.add_argument("--sep", default=",", help="CSV delimiter (default ,)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Validate input file
    if not os.path.exists(args.input):
        print(f"错误: 输入文件 '{args.input}' 不存在！")
        print("请确保输入文件存在，或使用 --input 参数指定正确的文件路径。")
        print("例如: python scripts/fenxi.py --input 你的数据文件.csv")
        return

    # Read CSV
    df = pd.read_csv(args.input, encoding=args.encoding, sep=args.sep, dtype="string", keep_default_na=False)

    # Ensure needed columns exist
    for c in TARGET_COLS:
        if c not in df.columns:
            df[c] = pd.NA

    df = normalize_nulls(df, TARGET_COLS)

    # Group stats by manu_no
    stats = build_group_stats(df)

    # Join group stats back to rows
    df2 = df.merge(stats, on="manu_no", how="left")

    # ---------- Case 1 ----------
    # 同一 manu_no 下 enterprise 唯一且存在、brand 唯一且存在；统计 enterprise 或 brand 为空 的记录数
    case1_manu = df2["enterprise_unique_exists"] & df2["brand_unique_exists"]
    case1_rows = case1_manu & (df2["enterprise"].isna() | df2["brand"].isna())
    df_case1 = df2.loc[case1_rows].copy()

    # ---------- Case 2 ----------
    # 同一 manu_no 下 enterprise 唯一且存在；brand 多种；统计 enterprise 或 brand 为空 的记录数
    case2_manu = df2["enterprise_unique_exists"] & df2["brand_multi_exists"]
    case2_rows = case2_manu & (df2["enterprise"].isna() | df2["brand"].isna())
    df_case2 = df2.loc[case2_rows].copy()

    # ---------- Case 3 ----------
    # 同一 manu_no 下 enterprise 全空、brand 全空；但 mt_brand_name 或 eb_brand_name 存在 的记录数
    case3_manu = df2["enterprise_all_null"] & df2["brand_all_null"]
    case3_rows = case3_manu & (df2["mt_brand_name"].notna() | df2["eb_brand_name"].notna())
    df_case3 = df2.loc[case3_rows].copy()

    # ---------- Case 4 ----------
    # 同一 manu_no 下 enterprise、brand、mt_brand_name、eb_brand_name 全空 的记录数
    case4_manu = (
        df2["enterprise_all_null"] &
        df2["brand_all_null"] &
        df2["mt_and_eb_brand_all_null"]
    )
    df_case4 = df2.loc[case4_manu].copy()

    # ---------- Case 5 ----------
    # enterprise 有多种值（按 manu_no 整组取出）
    case5_manu = df2["enterprise_nunique"] > 1
    df_case5 = df2.loc[case5_manu].copy()

    # ---------- Case 6 ----------
    # enterprise、brand 都存在，但都不唯一（按 manu_no 整组取出；case6 是 case5 子集）
    case6_manu = (df2["enterprise_nunique"] > 1) & (df2["brand_nunique"] > 1)
    df_case6 = df2.loc[case6_manu].copy()

    # ---- “剩余数据” other ----
    # 覆盖范围：case1_rows、case2_rows、case3_rows、case4_manu、case5_manu
    # 注意：case6 属于 case5 子集，不单独参与覆盖，避免重复覆盖
    covered_mask = case1_rows | case2_rows | case3_rows | case4_manu | case5_manu
    df_other = df2.loc[~covered_mask].copy()

    # Summary
    df_summary = pd.DataFrame([
        summarize_case(df_case1, "case1_unique_enterprise_and_brand_but_some_null_rows"),
        summarize_case(df_case2, "case2_unique_enterprise_brand_multi_but_some_null_rows"),
        summarize_case(df_case3, "case3_enterprise_brand_all_null_but_mt_or_eb_brand_exists"),
        summarize_case(df_case4, "case4_all_brand_fields_all_null"),
        summarize_case(df_case5, "case5_enterprise_multi_values"),
        summarize_case(df_case6, "case6_enterprise_and_brand_both_multi_values"),
        summarize_case(df_other, "other_unclassified_rows"),
    ])

    # Save summary
    summary_path = os.path.join(args.output_dir, "summary.csv")
    df_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    # ---- Always export details (默认导出) ----
    base_cols = ["manu_no", "enterprise", "brand", "mt_brand_name", "eb_brand_name"]
    optional_cols = ["id", "barcode", "item_name", "product_name", "manu_name"]
    keep_cols = base_cols + [c for c in optional_cols if c in df2.columns]

    case_files = {
        "case1_details.csv": df_case1,
        "case2_details.csv": df_case2,
        "case3_details.csv": df_case3,
        "case4_details.csv": df_case4,
        "case5_details.csv": df_case5,
        "case6_details.csv": df_case6,
        "other_details.csv": df_other,
    }

    print("Exporting details (默认开启)...")
    for fname, dfx in case_files.items():
        out_path = os.path.join(args.output_dir, fname)
        n = save_details(dfx, keep_cols, out_path)
        print(f"  - {fname}: {n} rows -> {out_path}")

    # 完整性检查：covered + other 是否等于总行数
    total_rows = len(df2)
    covered_rows = int(covered_mask.sum())
    other_rows = len(df_other)
    print("\nIntegrity check:")
    print(f"  Total rows:   {total_rows}")
    print(f"  Covered rows: {covered_rows}")
    print(f"  Other rows:   {other_rows}")
    print(f"  Covered + Other == Total ? {covered_rows + other_rows == total_rows}")

    print("\nDone.")
    print(df_summary.to_string(index=False))
    print(f"\nSaved summary: {summary_path}")
    print(f"Details saved under: {args.output_dir}")


if __name__ == "__main__":
    main()
