"""文献计量学可视化 Mixin 模块

提供文献计量分析的可视化方法，包括：
- Lotka 定律 (plot_lotka)
- PI 产出时间线 (plot_pi_timeline)
- 机构×方向热力图 (plot_inst_direction_heatmap)
- 关键词年趋势 (plot_word_growth)
- Trend Topics 表格 (plot_trend_topics)
- Bradford 定律 (plot_bradford)
- 资金趋势 (plot_funding_trend)
- 数据完整性 (plot_completeness_matrix)
- 类别趋势 (plot_emerging_declining)
- 综合报告 (create_bibliometric_report, create_performance_report)

使用方式 (Mixin 模式):
    class LandscapePlot(BibliometricPlotMixin, BasePlotMixin):
        pass

依赖:
    - self.C: 色板字典
    - self.plot_top_bar(): 来自 BasePlotMixin
    - matplotlib, numpy, gridspec
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap

from .colors import CAT_COLORS

if TYPE_CHECKING:
    import pandas as pd


class BibliometricPlotMixin:
    """
    文献计量学可视化方法集 (Mixin 类).

    通过多重继承混入 LandscapePlot，提供文献计量分析相关的绑制方法。
    要求父类提供 self.C (色板字典) 和 self.plot_top_bar() 方法。

    公开方法:
        - plot_lotka(): Lotka 定律分布图
        - plot_pi_timeline(): PI 产出时间线
        - plot_inst_direction_heatmap(): 机构×研究方向热力图
        - plot_word_growth(): 关键词年趋势折线图
        - plot_trend_topics(): Trend Topics 表格
        - plot_bradford(): Bradford 定律三区饼图
        - plot_funding_trend(): 资金趋势堆叠面积图
        - plot_completeness_matrix(): 数据完整性条形图
        - plot_emerging_declining(): 类别趋势双向条形图
        - create_bibliometric_report(): 9-panel 文献计量综合报告
        - create_performance_report(): 6-panel 性能分析报告
    """

    # ═══════════════════════════════════════════════════════════════════
    # Lotka 定律
    # ═══════════════════════════════════════════════════════════════════

    def plot_lotka(self, ax, lotka_df: 'pd.DataFrame', title: str = "Lotka's Law") -> None:
        """
        Lotka 定律分布图: PI 产出分布条形图.

        Args:
            ax: matplotlib Axes 对象
            lotka_df: Lotka 数据 DataFrame (n_projects, n_authors, pct)
            title: 标题
        """
        C = self.C
        if lotka_df.empty:
            ax.axis('off')
            return

        df = lotka_df.head(8)
        ax.bar(df['n_projects'].astype(str), df['n_authors'], color=C['INDIGO'],
               edgecolor='white', width=0.6)
        for i, row in df.iterrows():
            ax.text(i, row['n_authors'] + df['n_authors'].max() * 0.02,
                    f"{row['pct']}%", ha='center', fontsize=11, fontweight='bold', color='#2C3E50')

        ax.set_xlabel('获资助项目数', fontsize=13)
        ax.set_ylabel('PI人数', fontsize=13)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=12)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # PI 产出时间线
    # ═══════════════════════════════════════════════════════════════════

    def plot_pi_timeline(self, ax, timeline_df: 'pd.DataFrame',
                         title: str = 'PI产出时间线') -> None:
        """
        Top PI 气泡图: x=year, y=PI, size=count.

        Args:
            ax: matplotlib Axes 对象
            timeline_df: 时间线数据 DataFrame (pi, year, count)
            title: 标题
        """
        C = self.C
        if timeline_df.empty:
            ax.axis('off')
            return

        pis = timeline_df.groupby('pi')['count'].sum().sort_values(ascending=False).index.tolist()
        pi_idx = {p: i for i, p in enumerate(pis)}

        y = [pi_idx[p] for p in timeline_df['pi']]
        sizes = timeline_df['count'].values * 80
        ax.scatter(timeline_df['year'], y, s=sizes, c=C['VIOLET'],
                   alpha=0.7, edgecolors='white', linewidth=0.5)

        ax.set_yticks(range(len(pis)))
        ax.set_yticklabels(pis, fontsize=11)
        ax.invert_yaxis()
        ax.set_xlabel('Year', fontsize=13)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', labelsize=11)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 机构×研究方向热力图
    # ═══════════════════════════════════════════════════════════════════

    def plot_inst_direction_heatmap(self, ax, matrix: 'pd.DataFrame',
                                    title: str = '机构×方向') -> None:
        """
        机构×研究方向热力图.

        Args:
            ax: matplotlib Axes 对象
            matrix: 交叉表 DataFrame (index=机构, columns=方向)
            title: 标题
        """
        C = self.C
        if matrix.empty:
            ax.axis('off')
            return

        data = matrix.values.astype(float)
        cmap = LinearSegmentedColormap.from_list('wp', ['#FFFFFF', C['INDIGO']], N=256)
        ax.imshow(data, cmap=cmap, aspect='auto')

        ax.set_xticks(range(len(matrix.columns)))
        ax.set_xticklabels(matrix.columns, fontsize=11, rotation=35, ha='right')
        ax.set_yticks(range(len(matrix.index)))
        ax.set_yticklabels(matrix.index, fontsize=11)

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                val = int(data[i, j])
                if val > 0:
                    color = 'white' if val > data.max() * 0.5 else '#2C3E50'
                    ax.text(j, i, str(val), ha='center', va='center',
                            fontsize=11, fontweight='bold', color=color)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 关键词年趋势
    # ═══════════════════════════════════════════════════════════════════

    def plot_word_growth(self, ax, growth_df: 'pd.DataFrame',
                         title: str = '关键词年趋势') -> None:
        """
        关键词频率年趋势折线图.

        Args:
            ax: matplotlib Axes 对象
            growth_df: 词频时序 DataFrame (index=年份, columns=关键词)
            title: 标题
        """
        C = self.C
        if growth_df.empty:
            ax.axis('off')
            return

        palette = [C['ACCENT'], C['INDIGO'], C['JADE'], C['VIOLET'], C['PLUM'],
                   C['SLATE'], C['ORCHID'], C['TEAL'], C['SAGE'], C['WARN']]
        for i, col in enumerate(growth_df.columns):
            ax.plot(growth_df.index, growth_df[col], '-o', color=palette[i % len(palette)],
                    linewidth=2, markersize=4, label=col)

        ax.legend(fontsize=10, ncol=2, loc='upper left', framealpha=0.9)
        ax.set_ylabel('频次', fontsize=13)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=11)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # Trend Topics 表格
    # ═══════════════════════════════════════════════════════════════════

    def plot_trend_topics(self, ax, topics: dict, title: str = 'Trend Topics') -> None:
        """
        每时期 Top 关键词表格.

        Args:
            ax: matplotlib Axes 对象
            topics: 时期→关键词列表 {'2015-2019': [('keyword', count), ...], ...}
            title: 标题
        """
        C = self.C
        ax.axis('off')

        if not topics:
            return

        periods = list(topics.keys())
        max_n = max(len(v) for v in topics.values())

        header = periods
        cell_text = []
        for i in range(max_n):
            row = []
            for p in periods:
                items = topics[p]
                if i < len(items):
                    kw, cnt = items[i]
                    row.append(f"{kw} ({cnt})")
                else:
                    row.append('')
            cell_text.append(row)

        table = ax.table(cellText=cell_text, colLabels=header,
                         cellLoc='center', loc='upper center',
                         bbox=[0.0, 0.0, 1.0, 0.92])
        table.auto_set_font_size(False)
        table.set_fontsize(11)

        for j in range(len(header)):
            cell = table[0, j]
            cell.set_facecolor(C['INDIGO'])
            cell.set_text_props(color='white', fontweight='bold', fontsize=12)
            cell.set_edgecolor('white')

        for i in range(1, max_n + 1):
            for j in range(len(header)):
                cell = table[i, j]
                cell.set_edgecolor('#E8E8E8')
                cell.set_facecolor('#F8F9FA' if i % 2 == 0 else 'white')

        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # Bradford 定律
    # ═══════════════════════════════════════════════════════════════════

    def plot_bradford(self, ax, bradford: dict, title: str = 'Bradford Zones') -> None:
        """
        Bradford 定律三区饼图.

        Args:
            ax: matplotlib Axes 对象
            bradford: Bradford 数据 {'zone1': {n_projects, n_inst}, ...}
            title: 标题
        """
        C = self.C
        z1 = bradford.get('zone1', {})
        z2 = bradford.get('zone2', {})
        z3 = bradford.get('zone3', {})

        sizes = [z1.get('n_projects', 0), z2.get('n_projects', 0), z3.get('n_projects', 0)]
        labels = [
            f"Zone1\n{z1.get('n_inst', 0)}机构",
            f"Zone2\n{z2.get('n_inst', 0)}机构",
            f"Zone3\n{z3.get('n_inst', 0)}机构",
        ]
        colors = [C['ACCENT'], C['SLATE'], '#D5D8DC']

        if sum(sizes) == 0:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.0f%%',
            startangle=90, textprops={'fontsize': 12})
        for t in autotexts:
            t.set_fontweight('bold')
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 资金趋势
    # ═══════════════════════════════════════════════════════════════════

    def plot_funding_trend(self, ax, funding_df: 'pd.DataFrame', source: str = 'NSFC',
                           display_cats: list[str] | None = None, title: str = '') -> None:
        """
        资金趋势堆叠面积图 — 按类别.

        Args:
            ax: matplotlib Axes 对象
            funding_df: 资金数据 DataFrame (source, year, category, 总金额_万)
            source: 数据源筛选
            display_cats: 显示的类别列表
            title: 标题
        """
        C = self.C
        df = funding_df[funding_df['source'] == source]
        if df.empty:
            return

        pivot = df.pivot_table(index='year', columns='category', values='总金额_万',
                               aggfunc='sum', fill_value=0)

        if display_cats:
            ordered = [c for c in display_cats if c in pivot.columns]
            rest = [c for c in pivot.columns if c not in ordered]
            if rest:
                pivot['其他'] = pivot[rest].sum(axis=1)
                if '其他' not in ordered:
                    ordered.append('其他')
            pivot = pivot[ordered]

        colors = [CAT_COLORS.get(c, '#D5D8DC') for c in pivot.columns]
        ax.stackplot(pivot.index, *[pivot[c] for c in pivot.columns],
                     labels=pivot.columns, colors=colors, alpha=0.8)

        ax.set_ylabel('资助金额(万)', fontsize=14)
        ax.set_xlabel('')
        ax.legend(fontsize=9, ncol=2, loc='upper left', framealpha=0.9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='both', labelsize=12)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 数据完整性
    # ═══════════════════════════════════════════════════════════════════

    def plot_completeness_matrix(self, ax, matrix: 'pd.DataFrame',
                                 title: str = '数据完整性') -> None:
        """
        数据完整性条形图 — 按数据源分组.

        Args:
            ax: matplotlib Axes 对象
            matrix: 长格式 DataFrame (source, field, rate)
            title: 标题
        """
        C = self.C
        if matrix.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)
            ax.axis('off')
            return

        display = matrix[matrix['rate'] < 1.0].copy()
        if display.empty:
            ax.text(0.5, 0.5, '所有字段100%覆盖', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return

        source_colors = {'NSFC': C['INDIGO'], 'NIH': C['JADE'], 'PubMed': C['VIOLET']}

        display['label'] = display['source'] + ': ' + display['field']
        display = display.sort_values(['source', 'rate'], ascending=[True, True])

        y_pos = range(len(display))
        colors = [source_colors.get(s, '#999') for s in display['source']]
        ax.barh(y_pos, display['rate'].values, color=colors, edgecolor='white', height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(display['label'].values, fontsize=10)
        ax.set_xlim(0, 1.15)
        ax.axvline(1.0, color='#CCCCCC', linewidth=0.8, linestyle='--')

        for i, v in enumerate(display['rate'].values):
            pct = f"{v*100:.0f}%"
            color = C['ACCENT'] if v < 0.6 else '#2C3E50'
            ax.text(v + 0.01, i, pct, va='center', fontsize=10, fontweight='bold', color=color)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 类别趋势
    # ═══════════════════════════════════════════════════════════════════

    def plot_emerging_declining(self, ax, trends: dict, title: str = '类别趋势',
                                exclude: list[str] | None = None) -> None:
        """
        上升/下降类别双向条形图.

        Args:
            ax: matplotlib Axes 对象
            trends: 趋势数据 {'emerging': [{category, change_pct}], 'declining': [...]}
            title: 标题
            exclude: 排除的类别列表
        """
        if exclude is None:
            exclude = ['其他', 'Other']

        emerging = [e for e in trends.get('emerging', []) if e['category'] not in exclude]
        declining = [d for d in trends.get('declining', []) if d['category'] not in exclude]

        cats = [e['category'] for e in emerging] + [d['category'] for d in declining]
        vals = [e['change_pct'] for e in emerging] + [d['change_pct'] for d in declining]

        if not cats:
            ax.text(0.5, 0.5, '无显著趋势', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return

        colors = [self.C['JADE'] if v > 0 else self.C['ACCENT'] for v in vals]
        y_pos = range(len(cats))
        ax.barh(y_pos, vals, color=colors, edgecolor='white', height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(cats, fontsize=12)
        ax.axvline(0, color='#2C3E50', linewidth=0.8)
        ax.set_xlabel('变化率 (%)', fontsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 综合报告
    # ═══════════════════════════════════════════════════════════════════

    def create_bibliometric_report(self, perf: dict, kw_data: dict, output: str) -> None:
        """
        生成文献计量学综合报告 (9-panel, 3×3).

        Args:
            perf: 性能分析数据 (lotka, pi_timeline, inst_direction_matrix)
            kw_data: 关键词数据 (top_kw_nsfc, top_kw_nih, word_growth, trend_topics)
            output: 输出路径 (不含扩展名)
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(34, 24), facecolor=C['BG'])
        gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.30, wspace=0.28,
                               left=0.05, right=0.97, top=0.94, bottom=0.03)

        # ── Row 1: 关键词 ──
        ax1 = fig.add_subplot(gs[0, 0])
        top_kw = kw_data.get('top_kw_nsfc')
        if top_kw is not None and not top_kw.empty:
            self.plot_top_bar(ax1, top_kw.head(20), 'keyword', 'count',
                              n=20, title='A  NSFC高频关键词 Top-20', color=C['JADE'])

        ax2 = fig.add_subplot(gs[0, 1])
        nih_codes = kw_data.get('nih_activity_codes')
        if nih_codes is not None and not nih_codes.empty:
            self.plot_top_bar(ax2, nih_codes.head(15), 'code', 'count',
                              n=15, title='B  NIH资助类型分布', color=C['TEAL'])
        else:
            top_kw_nih = kw_data.get('top_kw_nih')
            if top_kw_nih is not None and not top_kw_nih.empty:
                self.plot_top_bar(ax2, top_kw_nih.head(20), 'keyword', 'count',
                                  n=20, title='B  NIH高频Terms Top-20', color=C['TEAL'])

        ax3 = fig.add_subplot(gs[0, 2])
        growth = kw_data.get('word_growth')
        if growth is not None:
            self.plot_word_growth(ax3, growth, title='C  NSFC关键词年趋势')

        # ── Row 2: PI 深化 ──
        ax4 = fig.add_subplot(gs[1, 0])
        lotka_df = perf.get('lotka_nsfc')
        if lotka_df is not None:
            self.plot_lotka(ax4, lotka_df, title="D  Lotka定律 (NSFC)")

        ax5 = fig.add_subplot(gs[1, 1])
        timeline = perf.get('pi_timeline')
        if timeline is not None:
            self.plot_pi_timeline(ax5, timeline, title='E  Top PI产出时间线')

        ax6 = fig.add_subplot(gs[1, 2])
        topics = kw_data.get('trend_topics')
        if topics is not None:
            self.plot_trend_topics(ax6, topics, title='F  Trend Topics (NSFC)')

        # ── Row 3: 交叉分析 ──
        ax7 = fig.add_subplot(gs[2, 0:2])
        inst_matrix = perf.get('inst_direction_matrix')
        if inst_matrix is not None:
            self.plot_inst_direction_heatmap(ax7, inst_matrix,
                                             title='G  机构×研究方向 (NSFC Top-15)')

        ax8 = fig.add_subplot(gs[2, 2])
        top_kw_pm = kw_data.get('top_kw_pubmed')
        if top_kw_pm is not None and not top_kw_pm.empty:
            self.plot_top_bar(ax8, top_kw_pm.head(20), 'keyword', 'count',
                              n=20, title='H  PubMed高频MeSH Top-20', color=C['VIOLET'])

        fig.suptitle('文献计量学综合报告  Bibliometric Report',
                     fontsize=28, fontweight='bold', color='#2C3E50', y=0.97)

        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()

    def create_performance_report(self, perf: dict, quality: dict, trends: dict,
                                  output: str, display_cats: list[str] | None = None) -> None:
        """
        生成性能分析+数据质量综合图 (6-panel).

        Args:
            perf: 性能数据 (top_institutions, bradford_nsfc, funding_trends, top_pis)
            quality: 质量数据 (completeness)
            trends: 趋势数据 (nsfc_emerging)
            output: 输出路径 (不含扩展名)
            display_cats: 显示的类别列表
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(30, 18), facecolor=C['BG'])
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.32, wspace=0.28,
                               left=0.06, right=0.97, top=0.92, bottom=0.04)

        # Panel A: Top institutions (NSFC)
        ax_a = fig.add_subplot(gs[0, 0])
        top_inst = perf['top_institutions']
        nsfc_inst = top_inst[top_inst['source'] == 'NSFC'].reset_index()
        if not nsfc_inst.empty:
            self.plot_top_bar(ax_a, nsfc_inst, 'institution', '项目数',
                              n=15, title='A  NSFC Top机构', color=C['INDIGO'])

        # Panel B: Bradford zones (NSFC)
        ax_b = fig.add_subplot(gs[0, 1])
        self.plot_bradford(ax_b, perf.get('bradford_nsfc', {}),
                           title='B  NSFC Bradford定律')

        # Panel C: Funding trends (stacked area)
        ax_c = fig.add_subplot(gs[0, 2])
        funding = perf.get('funding_trends', None)
        if funding is not None and not funding.empty:
            self.plot_funding_trend(ax_c, funding, source='NSFC',
                                    display_cats=display_cats,
                                    title='C  NSFC资金趋势')

        # Panel D: Completeness (per-source bar chart)
        ax_d = fig.add_subplot(gs[1, 0])
        completeness = quality.get('completeness', None)
        if completeness is not None:
            self.plot_completeness_matrix(ax_d, completeness,
                                          title='D  数据完整性')

        # Panel E: Emerging/declining (NSFC)
        ax_e = fig.add_subplot(gs[1, 1])
        nsfc_trends = trends.get('nsfc_emerging', {})
        self.plot_emerging_declining(ax_e, nsfc_trends,
                                     title='E  NSFC类别变化趋势 (近5年 vs 前5年)')

        # Panel F: Top PIs (NSFC)
        ax_f = fig.add_subplot(gs[1, 2])
        top_pis = perf['top_pis']
        nsfc_pis = top_pis[top_pis['source'] == 'NSFC'].reset_index()
        if not nsfc_pis.empty:
            self.plot_top_bar(ax_f, nsfc_pis, 'pi', '项目数',
                              n=15, title='F  NSFC Top PI', color=C['VIOLET'])

        fig.suptitle('性能分析 + 数据质量报告', fontsize=26, fontweight='bold',
                     color='#2C3E50', y=0.96)

        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()
