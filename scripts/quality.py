"""数据质量评估: 完整性矩阵、数据增益、摘要报告"""

import pandas as pd


class QualityReporter:
    """数据完整性评估

    评估各数据源字段的非空率，以及多源合并的增益效果。
    """

    # 每个数据源的关键字段（用于可视化，避免混杂无关列）
    KEY_FIELDS = {
        'NSFC': ['项目标题', '负责人', '单位', '金额（万）', '批准年份', '申请代码',
                 '中文关键词', '英文关键词', '项目参与人', '申请摘要', '英文摘要', '结题摘要'],
        'NIH': ['title', 'pi', 'org', 'award_amount', 'fiscal_year',
                'abstract', 'terms', 'project_start', 'project_end'],
        'PubMed': ['title', 'authors', 'year', 'journal', 'abstract',
                   'mesh', 'keywords', 'doi'],
    }

    def completeness_matrix(self, dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """每个字段的非空率，按数据源分列

        Parameters
        ----------
        dfs : {源名称: DataFrame}，如 {'NSFC': nsfc_df, 'NIH': nih_df}

        Returns
        -------
        DataFrame: 长格式 (source, field, rate) 用于分面可视化
        """
        rows = []
        for name, df in dfs.items():
            key_fields = self.KEY_FIELDS.get(name, list(df.columns))
            for col in key_fields:
                if col not in df.columns:
                    continue
                non_null = df[col].dropna().astype(str).str.strip()
                non_empty = (non_null.str.len() > 0) & (non_null != 'nan')
                rate = round(non_empty.sum() / max(len(df), 1), 3)
                rows.append({'source': name, 'field': col, 'rate': rate})

        return pd.DataFrame(rows)

    def enrichment_gain(self, base_df: pd.DataFrame, enriched_df: pd.DataFrame,
                        key_columns: list[str] | None = None) -> dict:
        """合并数据对基础数据的增益

        Parameters
        ----------
        base_df : 原始数据 (如 LetPub)
        enriched_df : 合并后数据 (如 LetPub + KD)
        key_columns : 关注的字段列表，默认检查所有共有字段

        Returns
        -------
        dict: {字段: {'before': float, 'after': float, 'gain': float}}
        """
        if key_columns is None:
            key_columns = [c for c in base_df.columns if c in enriched_df.columns]

        result = {}
        for col in key_columns:
            def _rate(df, c):
                s = df[c].dropna().astype(str).str.strip()
                return (s.str.len() > 0).sum() / max(len(df), 1)

            before = _rate(base_df, col)
            after = _rate(enriched_df, col)
            result[col] = {
                'before': round(before, 3),
                'after': round(after, 3),
                'gain': round(after - before, 3),
            }
        return result

    def summary(self, dfs: dict[str, pd.DataFrame]) -> str:
        """生成人类可读的数据质量摘要"""
        lines = []
        for name, df in dfs.items():
            n = len(df)
            lines.append(f"{'='*50}")
            lines.append(f"{name}: {n:,} 条记录")

            # Key fields coverage
            for col in df.columns:
                s = df[col].dropna().astype(str).str.strip()
                filled = ((s.str.len() > 0) & (s != 'nan')).sum()
                pct = filled * 100 / max(n, 1)
                if pct < 100:
                    lines.append(f"  {col}: {filled:,}/{n:,} ({pct:.0f}%)")

        lines.append(f"{'='*50}")
        return '\n'.join(lines)
