"""性能分析: PI/机构排名、资金分布、Bradford定律、新兴PI"""

import numpy as np
import pandas as pd


class PerformanceAnalyzer:
    """PI/机构产出排名、资金分布、Bradford定律

    Parameters
    ----------
    nsfc_df : DataFrame with columns: 负责人, 单位, 金额（万）, 批准年份, cat_merged
    nih_df : DataFrame with columns: pi, org, award_amount, fiscal_year, cat_merged
    """

    def __init__(self, nsfc_df: pd.DataFrame | None = None,
                 nih_df: pd.DataFrame | None = None):
        self.nsfc = nsfc_df
        self.nih = nih_df

    # ─── Top PIs ─────────────────────────────────
    def top_pis(self, n: int = 20) -> pd.DataFrame:
        """返回产出最高的PI，包含项目数和总金额"""
        frames = []

        if self.nsfc is not None:
            g = self.nsfc.groupby('负责人').agg(
                项目数=('负责人', 'size'),
                总金额_万=('金额（万）', 'sum'),
                首次年份=('批准年份', 'min'),
                末次年份=('批准年份', 'max'),
            ).sort_values('项目数', ascending=False)
            g['source'] = 'NSFC'
            g.index.name = 'pi'
            frames.append(g.head(n))

        if self.nih is not None:
            g = self.nih.groupby('pi').agg(
                项目数=('pi', 'size'),
                总金额_万=('award_amount', lambda x: round(x.sum() / 1e4, 1)),
                首次年份=('fiscal_year', 'min'),
                末次年份=('fiscal_year', 'max'),
            ).sort_values('项目数', ascending=False)
            g['source'] = 'NIH'
            frames.append(g.head(n))

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames)

    # ─── Top Institutions ────────────────────────
    def top_institutions(self, n: int = 20) -> pd.DataFrame:
        """返回产出最高的机构"""
        frames = []

        if self.nsfc is not None:
            g = self.nsfc.groupby('单位').agg(
                项目数=('单位', 'size'),
                总金额_万=('金额（万）', 'sum'),
                PI数=('负责人', 'nunique'),
            ).sort_values('项目数', ascending=False)
            g['source'] = 'NSFC'
            g.index.name = 'institution'
            frames.append(g.head(n))

        if self.nih is not None:
            g = self.nih.groupby('org').agg(
                项目数=('org', 'size'),
                总金额_万=('award_amount', lambda x: round(x.sum() / 1e4, 1)),
                PI数=('pi', 'nunique'),
            ).sort_values('项目数', ascending=False)
            g['source'] = 'NIH'
            g.index.name = 'institution'
            frames.append(g.head(n))

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames)

    # ─── Bradford Zones ──────────────────────────
    def bradford_zones(self, source: str = 'nsfc') -> dict:
        """机构集中度: Zone1(核心) / Zone2 / Zone3

        Bradford's Law: 将机构按产出排序，划分为三个等产出区域。
        Zone1 包含最少的核心机构，Zone3 包含最多的边缘机构。
        """
        if source == 'nsfc' and self.nsfc is not None:
            counts = self.nsfc.groupby('单位').size().sort_values(ascending=False)
        elif source == 'nih' and self.nih is not None:
            counts = self.nih.groupby('org').size().sort_values(ascending=False)
        else:
            return {}

        total = counts.sum()
        third = total / 3
        cumsum = counts.cumsum()

        zone1_mask = cumsum <= third
        # Include the first institution that crosses the boundary
        if zone1_mask.sum() == 0:
            zone1_mask.iloc[0] = True
        zone1 = counts[zone1_mask]

        zone2_mask = (cumsum > third) & (cumsum <= 2 * third)
        if zone2_mask.sum() == 0 and len(counts) > len(zone1):
            zone2_mask.iloc[len(zone1)] = True
        zone2 = counts[zone2_mask]

        zone3 = counts[(cumsum > 2 * third) & ~zone1_mask & ~zone2_mask]

        return {
            'zone1': {'institutions': zone1.index.tolist(), 'n_inst': len(zone1),
                       'n_projects': int(zone1.sum())},
            'zone2': {'institutions': zone2.index.tolist(), 'n_inst': len(zone2),
                       'n_projects': int(zone2.sum())},
            'zone3': {'n_inst': len(zone3), 'n_projects': int(zone3.sum())},
            'bradford_multiplier': round(len(zone2) / max(len(zone1), 1), 1),
            'total_institutions': len(counts),
            'total_projects': int(total),
        }

    # ─── Funding Trends ─────────────────────────
    def funding_trends(self) -> pd.DataFrame:
        """按年份+类别统计资助金额趋势"""
        frames = []

        if self.nsfc is not None:
            g = self.nsfc.groupby(['批准年份', 'cat_merged']).agg(
                项目数=('负责人', 'size'),
                总金额_万=('金额（万）', 'sum'),
            ).reset_index()
            g = g.rename(columns={'批准年份': 'year', 'cat_merged': 'category'})
            g['source'] = 'NSFC'
            frames.append(g)

        if self.nih is not None:
            g = self.nih.groupby(['fiscal_year', 'cat_merged']).agg(
                项目数=('pi', 'size'),
                总金额_万=('award_amount', lambda x: round(x.sum() / 1e4, 1)),
            ).reset_index()
            g = g.rename(columns={'fiscal_year': 'year', 'cat_merged': 'category'})
            g['source'] = 'NIH'
            frames.append(g)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    # ─── Emerging PIs ────────────────────────────
    def emerging_pis(self, recent_years: int = 3) -> pd.DataFrame:
        """近N年首次获资助的PI

        "新兴PI"定义: 首次出现在数据集中的年份在最近 recent_years 年内。
        """
        frames = []

        if self.nsfc is not None:
            max_year = int(self.nsfc['批准年份'].max())
            cutoff = max_year - recent_years + 1
            first_year = self.nsfc.groupby('负责人')['批准年份'].min()
            new_pis = first_year[first_year >= cutoff].index
            df_new = self.nsfc[self.nsfc['负责人'].isin(new_pis)].copy()
            g = df_new.groupby('负责人').agg(
                项目数=('负责人', 'size'),
                总金额_万=('金额（万）', 'sum'),
                首次年份=('批准年份', 'min'),
                方向=('cat_merged', 'first'),
            ).sort_values('总金额_万', ascending=False)
            g['source'] = 'NSFC'
            g.index.name = 'pi'
            frames.append(g)

        if self.nih is not None:
            max_year = int(self.nih['fiscal_year'].max())
            cutoff = max_year - recent_years + 1
            first_year = self.nih.groupby('pi')['fiscal_year'].min()
            new_pis = first_year[first_year >= cutoff].index
            df_new = self.nih[self.nih['pi'].isin(new_pis)].copy()
            g = df_new.groupby('pi').agg(
                项目数=('pi', 'size'),
                总金额_万=('award_amount', lambda x: round(x.sum() / 1e4, 1)),
                首次年份=('fiscal_year', 'min'),
                方向=('cat_merged', 'first'),
            ).sort_values('总金额_万', ascending=False)
            g['source'] = 'NIH'
            frames.append(g)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames)

    # ─── Lotka's Law ─────────────────────────────
    def lotka(self, source: str = 'nsfc') -> pd.DataFrame:
        """Lotka定律: PI产出分布

        返回 DataFrame: n_projects, n_authors, pct, cumulative_pct
        """
        if source == 'nsfc' and self.nsfc is not None:
            counts = self.nsfc.groupby('负责人').size()
        elif source == 'nih' and self.nih is not None:
            counts = self.nih.groupby('pi').size()
        else:
            return pd.DataFrame()

        dist = counts.value_counts().sort_index()
        total = dist.sum()
        result = pd.DataFrame({
            'n_projects': dist.index,
            'n_authors': dist.values,
            'pct': (dist.values / total * 100).round(1),
        })
        result['cumulative_pct'] = result['pct'].cumsum().round(1)
        return result

    # ─── PI Production Over Time ─────────────────
    def pi_timeline(self, n: int = 10, source: str = 'nsfc') -> pd.DataFrame:
        """Top-N PI 的逐年产出 (气泡图数据)

        返回长格式: pi, year, count, amount
        """
        if source == 'nsfc' and self.nsfc is not None:
            df = self.nsfc
            pi_col, year_col, amt_col = '负责人', '批准年份', '金额（万）'
        elif source == 'nih' and self.nih is not None:
            df = self.nih
            pi_col, year_col, amt_col = 'pi', 'fiscal_year', 'award_amount'
        else:
            return pd.DataFrame()

        top_pis = df.groupby(pi_col).size().nlargest(n).index
        subset = df[df[pi_col].isin(top_pis)]
        g = subset.groupby([pi_col, year_col]).agg(
            count=(pi_col, 'size'),
            amount=(amt_col, 'sum'),
        ).reset_index()
        g.columns = ['pi', 'year', 'count', 'amount']
        return g

    # ─── Institution × Direction Matrix ──────────
    def institution_direction_matrix(self, n: int = 15, source: str = 'nsfc') -> pd.DataFrame:
        """Top-N 机构 × 研究方向 交叉计数矩阵"""
        if source == 'nsfc' and self.nsfc is not None:
            df = self.nsfc
            inst_col, cat_col = '单位', 'cat_merged'
        elif source == 'nih' and self.nih is not None:
            df = self.nih
            inst_col, cat_col = 'org', 'cat_merged'
        else:
            return pd.DataFrame()

        top_inst = df.groupby(inst_col).size().nlargest(n).index
        subset = df[df[inst_col].isin(top_inst)]
        matrix = pd.crosstab(subset[inst_col], subset[cat_col])

        # Reorder rows by total
        matrix['_total'] = matrix.sum(axis=1)
        matrix = matrix.sort_values('_total', ascending=False).drop('_total', axis=1)
        return matrix
