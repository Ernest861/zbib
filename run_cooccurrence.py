#!/usr/bin/env python3
"""共现网络演变 + 关键词趋势预测 — 独立运行脚本

用法:
    zbib/venv/bin/python zbib/run_cooccurrence.py

输出:
    nsfc_data/NSFC_共现网络演变.png/pdf
    nsfc_data/NIH_cooccurrence_evolution.png/pdf
    nsfc_data/keyword_trend_prediction.png/pdf
    nsfc_data/network_evolution_summary.png/pdf
"""

import sys
from pathlib import Path

# 确保项目根目录和 zbib/scripts 在 path 中
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'zbib'))

import pandas as pd
from scripts.keywords import KeywordAnalyzer, STOPWORDS_CN, STOPWORDS_EN
from scripts.network import ConceptNetwork
from scripts.plot import LandscapePlot

OUT_DIR = ROOT / 'nsfc_data'


def load_data():
    """加载 NSFC clean + NIH all"""
    nsfc_path = OUT_DIR / 'nsfc_精神分裂症_clean.xlsx'
    nih_path = OUT_DIR / 'nih_scz_all.csv'

    print(f"加载 NSFC: {nsfc_path}")
    nsfc = pd.read_excel(nsfc_path)
    nsfc['批准年份'] = pd.to_numeric(nsfc['批准年份'], errors='coerce')
    nsfc = nsfc.dropna(subset=['批准年份'])
    nsfc['批准年份'] = nsfc['批准年份'].astype(int)
    print(f"  NSFC: {len(nsfc)} 项, 年份 {nsfc['批准年份'].min()}-{nsfc['批准年份'].max()}")

    print(f"加载 NIH: {nih_path}")
    nih = pd.read_csv(nih_path)
    nih['fiscal_year'] = pd.to_numeric(nih['fiscal_year'], errors='coerce')
    nih = nih.dropna(subset=['fiscal_year'])
    nih['fiscal_year'] = nih['fiscal_year'].astype(int)
    print(f"  NIH: {len(nih)} 项, 年份 {nih['fiscal_year'].min()}-{nih['fiscal_year'].max()}")

    return nsfc, nih


def main():
    import argparse
    parser = argparse.ArgumentParser(description='共现网络分析')
    parser.add_argument('-c', '--config', help='YAML配置文件 (使用Pipeline集成模式)')
    args = parser.parse_args()

    # Config mode: delegate to Pipeline.run_cooccurrence()
    if args.config:
        sys.path.insert(0, str(ROOT / 'zbib'))
        from scripts.pipeline import Pipeline
        pipe = Pipeline.from_yaml(args.config)
        pipe.load_data()
        pipe.classify()
        pipe.run_cooccurrence()
        return

    nsfc, nih = load_data()

    ka = KeywordAnalyzer()
    cn = ConceptNetwork()
    plotter = LandscapePlot()

    # ── 1. 融合分词 ──
    print("\n[1/5] NSFC 融合分词 (关键词 + 摘要)...")
    if '中文关键词' in nsfc.columns and '申请摘要' in nsfc.columns:
        nsfc_fused = ka.fused_keywords(nsfc, '中文关键词', '申请摘要', '批准年份', lang='cn')
    elif '中文关键词' in nsfc.columns:
        nsfc_fused = ka.explode_keywords(nsfc, '中文关键词', year_col='批准年份', lang='cn')
    else:
        print("  [WARN] 无关键词列，跳过NSFC")
        nsfc_fused = pd.DataFrame(columns=['keyword', 'year'])
    print(f"  NSFC融合词: {len(nsfc_fused)} 条")

    print("[1/5] NIH 关键词展开 (terms字段，跳过摘要TF-IDF以加速)...")
    if 'terms' in nih.columns:
        nih_fused = ka.explode_keywords(nih, 'terms', year_col='fiscal_year', lang='en')
    else:
        print("  [WARN] 无terms列，跳过NIH")
        nih_fused = pd.DataFrame(columns=['keyword', 'year'])
    print(f"  NIH融合词: {len(nih_fused)} 条")

    # ── 2. 时间窗口共现网络 ──
    print("\n[2/5] NSFC 时间窗口共现网络...")
    nsfc_temporal = cn.temporal_networks(
        nsfc, '中文关键词', '批准年份', window=5, step=5,
        lang='cn', min_freq=2, stopwords=STOPWORDS_CN)
    print(f"  {len(nsfc_temporal)} 个时期")

    print("[2/5] NIH 时间窗口共现网络...")
    # 仅取完整窗口(<=2024)，提高min_freq控制网络密度
    nih_complete = nih[nih['fiscal_year'] <= 2024]
    nih_temporal = cn.temporal_networks(
        nih_complete, 'terms', 'fiscal_year', window=5, step=5,
        lang='en', min_freq=50, stopwords=STOPWORDS_EN)
    print(f"  {len(nih_temporal)} 个时期")

    # ── 3. 网络演变指标 ──
    print("\n[3/5] 网络演变摘要...")
    evo_nsfc = cn.network_evolution_summary(nsfc_temporal)
    evo_nih = cn.network_evolution_summary(nih_temporal)
    if not evo_nsfc.empty:
        print(f"  NSFC演变:\n{evo_nsfc[['period','n_nodes','n_edges','n_clusters','modularity']].to_string(index=False)}")
    if not evo_nih.empty:
        print(f"  NIH演变:\n{evo_nih[['period','n_nodes','n_edges','n_clusters','modularity']].to_string(index=False)}")

    # ── 4. 关键词趋势预测 ──
    print("\n[4/5] 关键词趋势预测...")

    # 排除不完整年份(2025+)以避免回归失真
    max_complete_year = 2024

    # NSFC: 用关键词字段(非融合)做预测，避免jieba泛词稀释
    nsfc_kw_only = ka.explode_keywords(nsfc, '中文关键词', year_col='批准年份', lang='cn') \
        if '中文关键词' in nsfc.columns else pd.DataFrame(columns=['keyword', 'year'])
    nsfc_for_pred = nsfc_kw_only[nsfc_kw_only['year'] <= max_complete_year] if not nsfc_kw_only.empty else nsfc_kw_only
    nih_for_pred = nih_fused[nih_fused['year'] <= max_complete_year] if not nih_fused.empty else nih_fused

    # NSFC: top-30 高频词
    nsfc_top = nsfc_for_pred['keyword'].value_counts().head(30).index.tolist() if not nsfc_for_pred.empty else []
    pred_nsfc = ka.predict_trend(nsfc_for_pred, nsfc_top, forecast_years=5, min_yearly_avg=0.5)
    print(f"  NSFC 可预测词: {len(pred_nsfc)}")
    if pred_nsfc:
        print(f"    词: {', '.join(list(pred_nsfc.keys())[:10])}")

    # NIH: top-30 高频词
    nih_top = nih_for_pred['keyword'].value_counts().head(30).index.tolist() if not nih_for_pred.empty else []
    pred_nih = ka.predict_trend(nih_for_pred, nih_top, forecast_years=5, min_yearly_avg=5)
    print(f"  NIH 可预测词: {len(pred_nih)}")
    if pred_nih:
        print(f"    词: {', '.join(list(pred_nih.keys())[:10])}")

    # ── 5. 生成图表 ──
    print("\n[5/5] 生成图表...")

    plotter.plot_temporal_network(
        nsfc_temporal, str(OUT_DIR / 'NSFC_共现网络演变'),
        title='NSFC 关键词共现网络演变 (5年窗口)')

    plotter.plot_temporal_network(
        nih_temporal, str(OUT_DIR / 'NIH_cooccurrence_evolution'),
        title='NIH Keyword Co-occurrence Network Evolution (5-year windows)')

    plotter.plot_keyword_prediction(
        pred_nsfc, pred_nih,
        str(OUT_DIR / 'keyword_trend_prediction'))

    plotter.plot_evolution_summary(
        evo_nsfc, evo_nih,
        str(OUT_DIR / 'network_evolution_summary'))

    print("\n完成!")


if __name__ == '__main__':
    main()
