"""全景图可视化 Mixin 模块

提供研究全景图的可视化方法，包括：
- 趋势图 (plot_trend)
- 堆叠演变图 (plot_stacked_evolution)
- 热力图 + 边际图 (plot_heatmap_with_marginals)
- 空白表格 (plot_gap_table)
- 文献列表 (plot_paper_list)
- 靶点时间线 (plot_target_timeline)
- 期刊分布图 (plot_journal_landscape)
- 一键出图 (create_landscape)

使用方式 (Mixin 模式):
    class LandscapePlot(LandscapePlotMixin, BasePlotMixin):
        pass

依赖:
    - self.C: 色板字典
    - matplotlib, numpy, gridspec
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .colors import CAT_COLORS, get_cmap_gp

if TYPE_CHECKING:
    import pandas as pd


class LandscapePlotMixin:
    """
    全景图可视化方法集 (Mixin 类).

    通过多重继承混入 LandscapePlot，提供研究全景图相关的绑制方法。
    要求父类提供 self.C (色板字典)。

    公开方法:
        - plot_trend(): NIH+NSFC 双轴趋势图
        - plot_stacked_evolution(): 堆叠百分比演变图
        - plot_heatmap_with_marginals(): 热力图+边际柱状图
        - plot_gap_table(): 研究空白汇总表
        - plot_paper_list(): 关键文献列表
        - plot_target_timeline(): 靶点文献时间线
        - plot_journal_landscape(): 期刊分布图
        - create_landscape(): 一键生成完整全景图
    """

    # ═══════════════════════════════════════════════════════════════════
    # Panel A: 趋势图
    # ═══════════════════════════════════════════════════════════════════

    def plot_trend(self, ax, nih_year_cat: 'pd.DataFrame', nsfc_yearly: 'pd.Series',
                   display_cats: list[str], years_range: tuple[int, int] = (1990, 2025)):
        """
        NIH 堆叠柱状 + NSFC 折线双轴图.

        Args:
            ax: matplotlib Axes 对象
            nih_year_cat: NIH 年份×类别 交叉表
            nsfc_yearly: NSFC 年度计数 Series
            display_cats: 显示的类别列表
            years_range: 年份范围

        Returns:
            ax2: 右侧 Y 轴 (NSFC)
        """
        C = self.C
        years_nih = sorted([y for y in nih_year_cat.index
                           if years_range[0] <= y <= years_range[1]])

        bottom = np.zeros(len(years_nih))
        for cat in display_cats:
            if cat in nih_year_cat.columns:
                vals = [nih_year_cat.loc[y, cat] if y in nih_year_cat.index else 0
                        for y in years_nih]
            else:
                vals = [0] * len(years_nih)
            ax.bar(years_nih, vals, bottom=bottom, color=CAT_COLORS.get(cat, '#D5D8DC'),
                   width=0.8, edgecolor='none', alpha=0.75)
            bottom += np.array(vals)

        ax.set_ylabel('NIH项目数/年', color='#2C3E50', fontsize=18)
        ax.set_xlabel('Year', fontsize=18)
        ax.tick_params(axis='both', labelsize=14, labelcolor='#2C3E50')

        ax2 = ax.twinx()
        years_nsfc = sorted(nsfc_yearly.index)
        vals_nsfc = [nsfc_yearly.get(y, 0) for y in years_nsfc]
        ax2.plot(years_nsfc, vals_nsfc, 'o-', color=C['ACCENT'], linewidth=2.5, markersize=5)
        ax2.set_ylabel('NSFC项目数/年', color=C['ACCENT'], fontsize=18)
        ax2.tick_params(axis='y', labelsize=14, labelcolor=C['ACCENT'])

        legend_items = [
            Line2D([0], [0], color=C['ACCENT'], linewidth=2.5, marker='o',
                   markersize=5, label='NSFC (右轴)'),
        ]
        for cat in display_cats:
            legend_items.append(Patch(facecolor=CAT_COLORS.get(cat, '#D5D8DC'),
                                      alpha=0.75, label=cat))
        ax.legend(handles=legend_items, loc='upper left', fontsize=13, ncol=3,
                  framealpha=0.9, edgecolor='#CCCCCC')
        ax.set_xlim(years_range[0] - 1, years_range[1] + 1)
        ax.spines['top'].set_visible(False)
        return ax2

    # ═══════════════════════════════════════════════════════════════════
    # Panel B: 堆叠演变图
    # ═══════════════════════════════════════════════════════════════════

    def plot_stacked_evolution(self, ax, nsfc: 'pd.DataFrame', cat_col: str,
                               display_cats: list[str], period_labels: list[str],
                               period_ranges: list[tuple[int, int]],
                               year_col: str = '批准年份') -> None:
        """
        堆叠百分比柱状图.

        Args:
            ax: matplotlib Axes 对象
            nsfc: NSFC 数据 DataFrame
            cat_col: 类别列名
            display_cats: 显示的类别列表
            period_labels: 时期标签
            period_ranges: 时期范围列表 [(start, end), ...]
            year_col: 年份列名
        """
        stacked_data = {}
        for cat in display_cats:
            counts = []
            for s, e in period_ranges:
                c = ((nsfc[cat_col] == cat) & (nsfc[year_col] >= s) & (nsfc[year_col] <= e)).sum()
                counts.append(c)
            stacked_data[cat] = counts

        totals = [sum(stacked_data[c][i] for c in display_cats)
                  for i in range(len(period_labels))]
        x = np.arange(len(period_labels))
        bottom = np.zeros(len(period_labels))

        for cat in display_cats:
            vals = [stacked_data[cat][i] / totals[i] * 100 if totals[i] > 0 else 0
                    for i in range(len(period_labels))]
            ax.bar(x, vals, bottom=bottom, label=cat, color=CAT_COLORS.get(cat, '#D5D8DC'),
                   width=0.72, edgecolor='white', linewidth=0.5)
            bottom += vals

        ax.set_xticks(x)
        ax.set_xticklabels(period_labels, fontsize=14)
        ax.set_ylabel('占比 (%)', fontsize=18)
        ax.set_ylim(0, 108)
        ax.tick_params(axis='y', labelsize=14)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # ═══════════════════════════════════════════════════════════════════
    # Panel C: 热力图 + 边际图
    # ═══════════════════════════════════════════════════════════════════

    def plot_heatmap_with_marginals(self, fig, gs_spec, heatmap: np.ndarray,
                                    row_labels: list[str], col_labels: list[str],
                                    row_totals: list[int], col_totals: list[int],
                                    highlight_col: int = -1, title: str = '',
                                    highlight_annotation: str = '',
                                    font_scale: float = 1.0) -> tuple:
        """
        热力图 + 上方/右侧边际柱状图.

        Args:
            fig: matplotlib Figure 对象
            gs_spec: GridSpec 规格
            heatmap: 热力图数据矩阵
            row_labels: 行标签
            col_labels: 列标签
            row_totals: 行合计
            col_totals: 列合计
            highlight_col: 高亮列索引 (-1 表示不高亮)
            title: 标题
            highlight_annotation: 高亮注释模板 (如 'OFC\\n仅{n}篇')
            font_scale: 字体缩放比例 (<1 用于紧凑布局)

        Returns:
            (ax_top, ax_center, ax_right) 三个 Axes 对象
        """
        C = self.C
        s = font_scale
        n_rows, n_cols = heatmap.shape

        gs_c = gridspec.GridSpecFromSubplotSpec(
            2, 2, subplot_spec=gs_spec,
            height_ratios=[1, 2.5], width_ratios=[3, 1],
            hspace=0.05, wspace=0.05)

        bar_colors_c = ['#909090'] * n_cols
        if 0 <= highlight_col < n_cols:
            bar_colors_c[highlight_col] = C['ACCENT']
        bar_colors_r = ['#909090'] * n_rows

        # Top bar
        ax_ct = fig.add_subplot(gs_c[0, 0])
        ax_ct.set_facecolor(C['BG'])
        ax_ct.bar(range(n_cols), col_totals, color=bar_colors_c, edgecolor='white', width=0.7)
        for i, v in enumerate(col_totals):
            ax_ct.text(i, v + 3, str(v), ha='center', fontsize=int(16*s),
                       fontweight='bold', color='#2C3E50')
        ax_ct.set_xlim(-0.5, n_cols - 0.5)
        ax_ct.set_xticks([])
        ax_ct.set_ylabel('N', fontsize=int(14*s))
        for sp in ['top', 'right', 'bottom']:
            ax_ct.spines[sp].set_visible(False)
        ax_ct.tick_params(axis='y', labelsize=int(12*s))
        if title:
            ax_ct.set_title(title, fontsize=int(22*s), fontweight='bold',
                            loc='left', color='#2C3E50')

        if 0 <= highlight_col < n_cols:
            if highlight_annotation:
                hl_text = highlight_annotation.format(n=col_totals[highlight_col])
            else:
                hl_text = f'OFC\n仅{col_totals[highlight_col]}篇'
            ax_ct.annotate(hl_text,
                           xy=(highlight_col, col_totals[highlight_col]),
                           xytext=(highlight_col - 1.0, max(col_totals) * 0.65),
                           fontsize=int(16*s), color=C['ACCENT'], fontweight='bold',
                           arrowprops=dict(arrowstyle='->', color=C['ACCENT'], lw=max(1, 2*s)))

        # Center heatmap
        ax_ch = fig.add_subplot(gs_c[1, 0])
        ax_ch.set_facecolor(C['BG'])
        ax_ch.imshow(heatmap, cmap=get_cmap_gp(), aspect='auto', vmin=0)
        ax_ch.set_xticks(range(n_cols))
        ax_ch.set_xticklabels(col_labels, fontsize=int(16*s), rotation=30, ha='right')
        ax_ch.set_yticks(range(n_rows))
        ax_ch.set_yticklabels(row_labels, fontsize=int(16*s))

        for si in range(n_rows):
            for ti in range(n_cols):
                val = int(heatmap[si, ti])
                if ti == highlight_col:
                    color = C['ACCENT']
                elif val > heatmap.max() * 0.5:
                    color = 'white'
                else:
                    color = '#2C3E50'
                ax_ch.text(ti, si, str(val), ha='center', va='center',
                           fontsize=int(18*s), fontweight='bold', color=color)

        if 0 <= highlight_col < n_cols:
            rect = plt.Rectangle((highlight_col - 0.5, -0.5), 1, n_rows,
                                  linewidth=max(1.5, 2.5*s), edgecolor=C['ACCENT'],
                                  facecolor='none', linestyle='--')
            ax_ch.add_patch(rect)

        # Right bar
        ax_cr = fig.add_subplot(gs_c[1, 1])
        ax_cr.set_facecolor(C['BG'])
        ax_cr.barh(range(n_rows), row_totals, color=bar_colors_r, edgecolor='white', height=0.6)
        for i, v in enumerate(row_totals):
            ax_cr.text(v + 5, i, str(v), va='center', fontsize=int(16*s),
                       fontweight='bold', color='#2C3E50')
        ax_cr.set_ylim(-0.5, n_rows - 0.5)
        ax_cr.set_yticks([])
        ax_cr.set_xlabel('N', fontsize=int(14*s))
        ax_cr.invert_yaxis()
        for sp in ['top', 'right', 'left']:
            ax_cr.spines[sp].set_visible(False)
        ax_cr.tick_params(axis='x', labelsize=int(12*s))

        ax_corner = fig.add_subplot(gs_c[0, 1])
        ax_corner.axis('off')
        ax_corner.text(0.5, 0.3, 'N papers\n(all targets)', fontsize=int(14*s),
                       ha='center', va='center', color='#888888', style='italic')

        # 尾注：说明单元格可重叠
        ax_ch.text(0.5, -0.12, '* 单元格为交集计数，一篇文献可涉及多个维度；条形图为各维度真实总数',
                   transform=ax_ch.transAxes, fontsize=int(10*s), color='#666666',
                   ha='center', va='top', style='italic')

        return ax_ct, ax_ch, ax_cr

    # ═══════════════════════════════════════════════════════════════════
    # Panel D: 空白表格
    # ═══════════════════════════════════════════════════════════════════

    def plot_gap_table(self, ax, table_data: list[list], header_color: str | None = None,
                        font_scale: float = 1.0):
        """
        研究空白汇总表.

        Args:
            ax: matplotlib Axes 对象
            table_data: 表格数据 [[header], [row1], [row2], ...]
            header_color: 表头颜色
            font_scale: 字体缩放比例 (默认1.0，0.6适合8×6英寸图)

        Returns:
            table: matplotlib Table 对象
        """
        C = self.C
        if header_color is None:
            header_color = C['INDIGO']

        fs_main = int(15 * font_scale)
        fs_header = int(15 * font_scale)
        fs_cell = int(14 * font_scale)

        ax.axis('off')
        table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                         cellLoc='center', loc='upper center',
                         bbox=[0.02, 0.02, 0.96, 0.90])
        table.auto_set_font_size(False)
        table.set_fontsize(fs_main)

        n_cols = len(table_data[0])
        for j in range(n_cols):
            cell = table[0, j]
            cell.set_facecolor(header_color)
            cell.set_text_props(color='white', fontweight='bold', fontsize=fs_header)
            cell.set_edgecolor('white')

        for i in range(1, len(table_data)):
            for j in range(n_cols):
                cell = table[i, j]
                cell.set_edgecolor('#E8E8E8')
                if j == 0:
                    cell.set_facecolor('#F0F3F5')
                    cell.get_text().set_fontweight('bold')
                    cell.get_text().set_fontsize(fs_cell)
                txt = cell.get_text().get_text()
                if txt == '0':
                    cell.set_facecolor(C['WARN'])
                    cell.get_text().set_fontweight('bold')
                    cell.get_text().set_color(C['ACCENT'])
        return table

    # ═══════════════════════════════════════════════════════════════════
    # Panel E: 文献列表
    # ═══════════════════════════════════════════════════════════════════

    def plot_paper_list(self, ax, papers: list[tuple], title: str = '',
                         font_scale: float = 1.0) -> None:
        """
        关键文献列表.

        Args:
            ax: matplotlib Axes 对象
            papers: 文献列表 [(year, journal, author, desc), ...]
            title: 标题
            font_scale: 字体缩放比例 (默认1.0，0.6适合8×6英寸图)
        """
        C = self.C
        ax.axis('off')

        fs_title = int(22 * font_scale)
        fs_num = int(18 * font_scale)
        fs_journal = int(15 * font_scale)
        fs_auth = int(14 * font_scale)

        if title:
            ax.set_title(title, fontsize=int(8 if font_scale < 1 else fs_title),
                         fontweight='bold', loc='left', color='#2C3E50')

        y_start = 0.88
        y_step = 0.18 if font_scale >= 1 else 0.22
        for i, (yr, journal, auth, desc) in enumerate(papers[:5 if font_scale < 1 else len(papers)]):
            y = y_start - i * y_step
            ax.text(0.02, y, f'{i+1}.', transform=ax.transAxes, fontsize=fs_num,
                    fontweight='bold', color=C['ACCENT'], va='top')
            # 截断期刊名和作者描述
            journal_short = journal[:15] if font_scale < 1 else journal
            auth_short = (auth[:20] + '..') if font_scale < 1 and len(auth) > 20 else auth
            desc_short = (desc[:15] + '..') if font_scale < 1 and len(desc) > 15 else desc
            ax.text(0.07, y, f'[{yr}] {journal_short}', transform=ax.transAxes,
                    fontsize=fs_journal, fontweight='bold', color=C['INDIGO'], va='top')
            ax.text(0.07, y - 0.08, f'{auth_short} — {desc_short}', transform=ax.transAxes,
                    fontsize=fs_auth, color='#2C3E50', va='top')

    # ═══════════════════════════════════════════════════════════════════
    # Panel F: 靶点时间线
    # ═══════════════════════════════════════════════════════════════════

    def plot_target_timeline(self, ax, ofc_yearly: 'pd.Series', milestones: list[dict],
                             title: str = '', fs_title: int = 11, fs_label: int = 9,
                             fs_tick: int = 8, fs_annot: int = 7) -> None:
        """
        OFC 文献柱状图 + 里程碑编号标注.

        Args:
            ax: matplotlib Axes 对象
            ofc_yearly: OFC 年度文献计数 Series
            milestones: 里程碑文献列表 [{year, author, journal}, ...]
            title: 标题
            fs_*: 各部分字体大小
        """
        C = self.C
        if ofc_yearly is None or ofc_yearly.empty:
            ax.text(0.5, 0.5, '无 OFC 相关文献', ha='center', va='center',
                    fontsize=fs_label, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        years = sorted(ofc_yearly.index)
        vals = [ofc_yearly.get(y, 0) for y in years]

        ax.bar(years, vals, color=C['ACCENT'], alpha=0.65, width=0.8, edgecolor='white')
        y_max = max(vals) if vals else 1
        ax.set_ylim(0, y_max * 1.55)

        ax.set_ylabel('OFC 文献数', fontsize=fs_label)
        ax.tick_params(axis='both', labelsize=fs_tick)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        total = sum(vals)
        ax.text(0.02, 0.97, f'N = {total}', transform=ax.transAxes,
                fontsize=fs_label, va='top', fontweight='bold', color='#2C3E50')

        if milestones:
            for i, p in enumerate(milestones[:5]):
                yr = int(p['year'])
                y_val = ofc_yearly.get(yr, 0)
                offset = y_max * (0.20 + 0.18 * (i % 2))
                ax.annotate(
                    f'[{i+1}]', xy=(yr, y_val), xytext=(yr, y_val + offset),
                    fontsize=fs_annot + 1, ha='center', va='bottom',
                    color=C['ACCENT'], fontweight='bold',
                    arrowprops=dict(arrowstyle='-', color=C['ACCENT'], lw=0.8, alpha=0.5))

            legend_lines = []
            for i, p in enumerate(milestones[:5]):
                author_short = p['author'].split(' et')[0]
                legend_lines.append(f"[{i+1}] {p['year']} {author_short} — {p['journal']}")
            ax.text(0.02, -0.15, '\n'.join(legend_lines),
                    transform=ax.transAxes, fontsize=fs_annot, va='top', color='#444',
                    linespacing=1.3)

        if title:
            ax.set_title(title, fontsize=fs_title, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # Panel G: 期刊分布
    # ═══════════════════════════════════════════════════════════════════

    def plot_journal_landscape(self, ax, pubmed_df: 'pd.DataFrame' = None, title: str = '',
                               n_top: int = 12, fs_title: int = 11, fs_label: int = 8,
                               fs_tick: int = 7) -> None:
        """
        发文期刊分布 — Top-N 水平柱状图 + 顶刊标记.

        Args:
            ax: matplotlib Axes 对象
            pubmed_df: PubMed 数据 DataFrame (需含 'journal' 列)
            title: 标题
            n_top: 显示前 N 个期刊
            fs_*: 各部分字体大小
        """
        C = self.C
        if pubmed_df is None or 'journal' not in pubmed_df.columns:
            ax.text(0.5, 0.5, '无期刊数据', ha='center', va='center',
                    fontsize=fs_label, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        top_n = pubmed_df['journal'].value_counts().head(n_top)
        journals = top_n.index.tolist()[::-1]
        counts = top_n.values.tolist()[::-1]

        has_top_col = 'top_journal' in pubmed_df.columns
        top_set = set()
        if has_top_col:
            top_set = set(pubmed_df[pubmed_df['top_journal'] == True]['journal'].unique())  # noqa: E712

        colors = [C['INDIGO'] if j in top_set else C['SLATE'] for j in journals]

        y_pos = np.arange(len(journals))
        ax.barh(y_pos, counts, color=colors, edgecolor='white', height=0.7, alpha=0.85)

        max_cnt = max(counts) if counts else 1
        for i, (j, cnt) in enumerate(zip(journals, counts)):
            jname = j[:25] + '..' if len(j) > 27 else j
            ax.text(cnt + max_cnt * 0.02, i, str(cnt), va='center',
                    fontsize=fs_tick, fontweight='bold', color='#2C3E50')
            ax.text(-max_cnt * 0.02, i, jname, va='center', ha='right',
                    fontsize=fs_tick, color='#2C3E50')

        ax.set_yticks([])
        ax.set_xlim(0, max_cnt * 1.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='x', labelsize=fs_tick)
        ax.set_xlabel('N articles', fontsize=fs_label)

        if top_set:
            leg = [Patch(facecolor=C['INDIGO'], alpha=0.85, label='顶刊'),
                   Patch(facecolor=C['SLATE'], alpha=0.85, label='其他')]
            ax.legend(handles=leg, loc='lower right', fontsize=fs_tick, framealpha=0.9)

        if title:
            ax.set_title(title, fontsize=fs_title, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════════════════════════
    # 一键出图
    # ═══════════════════════════════════════════════════════════════════

    def create_landscape(self, data_dict: dict, output: str) -> None:
        """
        一键生成完整全景图 — 2×3 或 3×3 布局.

        Args:
            data_dict: 数据字典，必须包含:
                - display_cats: 显示类别列表
                - nih_year_cat: NIH 年份×类别 DataFrame
                - nsfc_yearly: NSFC 年度 Series
                - nsfc: NSFC 数据 DataFrame
                - cat_col: 类别列名
                - period_labels, period_ranges: 时期配置
                - heatmap, row_labels, col_labels, row_totals, col_totals: 热力图数据
                - gap_table: 空白表格数据
                - papers: 文献列表
                可选:
                - burden_yearly, ofc_yearly: 触发新布局
                - panel_*_title: 各面板标题
                - suptitle: 总标题

            output: 输出路径 (不含扩展名)
        """
        C = self.C

        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        d = data_dict
        display_cats = d['display_cats']
        has_new_panels = d.get('burden_yearly') is not None or d.get('ofc_yearly') is not None

        if has_new_panels:
            # ═══ 2×3 layout — 出版标准 (8×6 in, 6-8pt fonts) ═══
            fig = plt.figure(figsize=(8, 6), facecolor=C['BG'])
            gs_main = gridspec.GridSpec(
                2, 3, figure=fig,
                height_ratios=[1, 1],
                width_ratios=[1, 1, 1.1],
                hspace=0.35, wspace=0.28,
                left=0.07, right=0.96, top=0.90, bottom=0.08)

            # ── Row 1: A=全景 → B=方向演变 → C=热力图 ──
            ax_a = fig.add_subplot(gs_main[0, 0])
            ax_a.set_facecolor(C['BG'])
            ax_a.set_title('A  NSFC vs NIH',
                           fontsize=8, fontweight='bold', loc='left', color='#2C3E50')
            ax_a2 = self.plot_trend(ax_a, d['nih_year_cat'], d['nsfc_yearly'], display_cats)
            nih_total = d.get('nih_total', 0)
            nsfc_total = d.get('nsfc_total', 0)
            ax_a.text(0.97, 0.95, f'NIH:{nih_total:,}', transform=ax_a.transAxes,
                      fontsize=6, ha='right', va='top', fontweight='bold', color='#2C3E50')
            ax_a2.text(0.03, 0.95, f'NSFC:{nsfc_total}', transform=ax_a2.transAxes,
                       fontsize=6, ha='left', va='top', fontweight='bold', color=C['ACCENT'])
            ax_a.tick_params(axis='both', labelsize=6)
            ax_a.yaxis.label.set_size(7)
            ax_a.xaxis.label.set_size(7)
            ax_a2.tick_params(axis='y', labelsize=6)
            ax_a2.yaxis.label.set_size(7)
            leg = ax_a.get_legend()
            if leg:
                for t in leg.get_texts():
                    t.set_fontsize(5)

            ax_b = fig.add_subplot(gs_main[0, 1])
            ax_b.set_facecolor(C['BG'])
            ax_b.set_title('B  研究方向演变',
                           fontsize=8, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_stacked_evolution(ax_b, d['nsfc'], d['cat_col'], display_cats,
                                        d['period_labels'], d['period_ranges'])
            ax_b.annotate('神经调控↑', xy=(6, 18), fontsize=6,
                          color=C['ACCENT'], fontweight='bold')
            ax_b.tick_params(axis='both', labelsize=6)
            ax_b.yaxis.label.set_size(7)

            self.plot_heatmap_with_marginals(
                fig, gs_main[0, 2], d['heatmap'], d['row_labels'], d['col_labels'],
                d['row_totals'], d['col_totals'],
                highlight_col=d.get('highlight_col', -1),
                title=d.get('panel_c_title', ''),
                highlight_annotation=d.get('highlight_annotation', ''),
                font_scale=0.6)

            # ── Row 2: D=空白表 → E=文献列表 → F=假说图 ──
            ax_d = fig.add_subplot(gs_main[1, 0])
            ax_d.set_title('D  研究空白',
                           fontsize=8, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_gap_table(ax_d, d['gap_table'], font_scale=0.6)

            ax_e = fig.add_subplot(gs_main[1, 1])
            self.plot_paper_list(ax_e, d['papers'],
                                 title=d.get('panel_e_title', '').replace('E ', 'E '),
                                 font_scale=0.6)
            if 'panel_e_summary' in d:
                ax_e.text(0.50, 0.02, d['panel_e_summary'],
                          transform=ax_e.transAxes, fontsize=6, ha='center', va='bottom',
                          fontweight='bold', color=C['ACCENT'],
                          bbox=dict(boxstyle='round,pad=0.2', facecolor='#FEF9E7',
                                    edgecolor=C['WARN'], linewidth=0.5))

            ax_f = fig.add_subplot(gs_main[1, 2])
            ax_f.set_facecolor('#F5F0FA')
            ax_f.set_title('F  假说图', fontsize=8, fontweight='bold',
                           loc='left', color='#2C3E50')
            for spine in ax_f.spines.values():
                spine.set_linestyle('--')
                spine.set_color(C['VIOLET'])
                spine.set_linewidth(1)
            ax_f.set_xticks([])
            ax_f.set_yticks([])
            ax_f.text(0.5, 0.5, '假说图\n(待插入)',
                      transform=ax_f.transAxes, fontsize=8, ha='center', va='center',
                      color=C['VIOLET'], alpha=0.4, fontweight='bold')

        else:
            # Legacy 2×3 layout
            fig = plt.figure(figsize=self.figsize, facecolor=C['BG'])
            gs_main = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.32,
                                        left=0.04, right=0.97, top=0.92, bottom=0.03)
            gs_top = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs_main[0],
                                                      wspace=0.26, width_ratios=[1, 1, 1.2])
            gs_bot = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs_main[1],
                                                      wspace=0.12, width_ratios=[0.7, 0.9, 1])

            # Panel A
            ax_a = fig.add_subplot(gs_top[0])
            ax_a.set_facecolor(C['BG'])
            ax_a.set_title(d.get('panel_a_title', 'A  精神分裂症研究全景：NSFC vs NIH'),
                           fontsize=22, fontweight='bold', loc='left', color='#2C3E50')
            ax_a2 = self.plot_trend(ax_a, d['nih_year_cat'], d['nsfc_yearly'], display_cats)
            nih_total = d.get('nih_total', 0)
            nsfc_total = d.get('nsfc_total', 0)
            ax_a.annotate(f'NIH: {nih_total:,}项', xy=(2018, ax_a.get_ylim()[1]*0.75),
                          fontsize=18, color='#2C3E50', fontweight='bold')
            ax_a2.annotate(f'NSFC: {nsfc_total}项', xy=(2002, ax_a2.get_ylim()[1]*0.75),
                           fontsize=18, color=C['ACCENT'], fontweight='bold')

            # Panel B
            ax_b = fig.add_subplot(gs_top[1])
            ax_b.set_facecolor(C['BG'])
            ax_b.set_title(d.get('panel_b_title', 'B  NSFC研究方向构成演变'),
                           fontsize=22, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_stacked_evolution(ax_b, d['nsfc'], d['cat_col'], display_cats,
                                        d['period_labels'], d['period_ranges'])
            ax_b.annotate('神经调控 ↑', xy=(6, 18), fontsize=16, color=C['ACCENT'], fontweight='bold')
            ax_b.annotate('环路/机制 ↑', xy=(5.5, 30), fontsize=15, color=C['PLUM'], fontweight='bold')

            # Panel C
            self.plot_heatmap_with_marginals(
                fig, gs_top[2], d['heatmap'], d['row_labels'], d['col_labels'],
                d['row_totals'], d['col_totals'],
                highlight_col=d.get('highlight_col', -1),
                title=d.get('panel_c_title', ''),
                highlight_annotation=d.get('highlight_annotation', ''))

            # Panel D
            ax_d = fig.add_subplot(gs_bot[0])
            ax_d.set_title(d.get('panel_d_title', 'D  研究空白'),
                           fontsize=22, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_gap_table(ax_d, d['gap_table'])

            # Panel E
            ax_e = fig.add_subplot(gs_bot[1])
            self.plot_paper_list(ax_e, d['papers'], title=d.get('panel_e_title', ''))
            if 'panel_e_summary' in d:
                ax_e.text(0.50, 0.03, d['panel_e_summary'],
                          transform=ax_e.transAxes, fontsize=16, ha='center', va='bottom',
                          fontweight='bold', color=C['ACCENT'],
                          bbox=dict(boxstyle='round,pad=0.4', facecolor='#FEF9E7',
                                    edgecolor=C['WARN'], linewidth=1.5))

            # Panel F
            ax_f = fig.add_subplot(gs_bot[2])
            ax_f.set_facecolor('#F5F0FA')
            ax_f.set_title('F  假说图（待插入）', fontsize=22, fontweight='bold',
                           loc='left', color='#2C3E50')
            for spine in ax_f.spines.values():
                spine.set_linestyle('--')
                spine.set_color(C['VIOLET'])
                spine.set_linewidth(1.5)
            ax_f.set_xticks([])
            ax_f.set_yticks([])
            ax_f.text(0.5, 0.5, '假说图\nHypothesis Figure\n\n（手动插入）',
                      transform=ax_f.transAxes, fontsize=22, ha='center', va='center',
                      color=C['VIOLET'], alpha=0.4, fontweight='bold')

        # Title
        sup_fs = 14 if has_new_panels else 24
        sup_y = 0.97 if has_new_panels else 0.96
        fig.suptitle(d.get('suptitle', ''), fontsize=sup_fs, fontweight='bold',
                     color='#2C3E50', y=sup_y)

        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=300, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # 补充数据图
    # ═══════════════════════════════════════════════════════════════════

    def create_supplementary_figure(self, data: dict, output: str,
                                    display_cats: list[str] | None = None,
                                    highlight_target: str = '') -> None:
        """
        生成补充数据图 (2×2, 14×9 inches).

        Args:
            data: 数据字典，包含:
                - nih_funding: NIH 资金数据
                - emerging_kw: 新兴关键词数据
                - inst_target_matrix: 机构×靶区矩阵
                - thematic_map: 主题地图数据
            output: 输出路径 (不含扩展名)
            display_cats: 类别显示顺序
            highlight_target: 高亮的靶区名称
        """
        from matplotlib.colors import LinearSegmentedColormap
        C = self.C

        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        # 出版标准尺寸 (8×5.5 英寸)
        fig = plt.figure(figsize=(8, 5.5), facecolor=C['BG'])
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.30,
                               left=0.08, right=0.96, top=0.90, bottom=0.10)

        # ─── Panel A: NIH经费趋势 ───
        ax_a = fig.add_subplot(gs[0, 0])
        ax_a.set_facecolor(C['BG'])
        funding_df = data.get('nih_funding')
        if funding_df is not None and not funding_df.empty:
            pivot = funding_df.pivot_table(
                index='year', columns='category', values='总金额_万',
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
            ax_a.stackplot(pivot.index, *[pivot[c] for c in pivot.columns],
                           labels=pivot.columns, colors=colors, alpha=0.75)

            if '神经调控' in pivot.columns:
                max_year = pivot.index.max()
                cat_idx = list(pivot.columns).index('神经调控')
                cum_y = pivot.loc[max_year][:cat_idx+1].sum()
                ax_a.annotate('神经调控↑', xy=(max_year, cum_y * 0.9),
                              fontsize=6, color=C['ACCENT'], fontweight='bold')

            ax_a.set_ylabel('NIH金额(万)', fontsize=7)
            ax_a.set_xlabel('Year', fontsize=7)
            ax_a.tick_params(axis='both', labelsize=6)
            ax_a.legend(fontsize=5, ncol=2, loc='upper left', framealpha=0.9)
            ax_a.spines['top'].set_visible(False)
            ax_a.spines['right'].set_visible(False)
        ax_a.set_title('A  NIH资助趋势', fontsize=8, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel B: 新兴关键词 ───
        ax_b = fig.add_subplot(gs[0, 1])
        ax_b.set_facecolor(C['BG'])
        emerging = data.get('emerging_kw')
        if emerging is not None and not emerging.empty:
            filtered = emerging[emerging['growth'] < 999] if len(emerging[emerging['growth'] < 999]) >= 10 else emerging
            top15 = filtered.nlargest(15, 'growth')

            y_pos = range(len(top15))
            max_growth = top15['growth'].max()
            colors = [plt.cm.Reds(0.3 + 0.6 * g / max_growth) for g in top15['growth']]

            ax_b.barh(y_pos, top15['recent_count'].values, color=colors,
                      edgecolor='white', height=0.7)
            ax_b.set_yticks(y_pos)
            ax_b.set_yticklabels(top15['keyword'].values, fontsize=7)
            ax_b.invert_yaxis()

            for i, (cnt, gr) in enumerate(zip(top15['recent_count'], top15['growth'])):
                label = f"{gr:.1f}×" if gr < 100 else "new"
                ax_b.text(cnt + 1, i, label, va='center', fontsize=7,
                          color=C['ACCENT'], fontweight='bold')

            ax_b.set_xlabel('Count (3y)', fontsize=7)
            ax_b.tick_params(axis='both', labelsize=5)
            ax_b.spines['top'].set_visible(False)
            ax_b.spines['right'].set_visible(False)
        ax_b.set_title('B  新兴关键词', fontsize=8, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel C: 机构×靶区矩阵 ───
        ax_c = fig.add_subplot(gs[1, 0])
        ax_c.set_facecolor(C['BG'])
        matrix = data.get('inst_target_matrix')
        if matrix is not None and not matrix.empty:
            data_c = matrix.values.astype(float)
            cmap_c = LinearSegmentedColormap.from_list('wp', ['#FFFFFF', C['INDIGO']], N=256)
            ax_c.imshow(data_c, cmap=cmap_c, aspect='auto', vmin=0)

            ax_c.set_xticks(range(len(matrix.columns)))
            ax_c.set_xticklabels(matrix.columns, fontsize=5, rotation=30, ha='right')
            ax_c.set_yticks(range(len(matrix.index)))
            labels_c = [inst[:20] + '..' if len(inst) > 20 else inst for inst in matrix.index]
            ax_c.set_yticklabels(labels_c, fontsize=5)

            for i in range(data_c.shape[0]):
                for j in range(data_c.shape[1]):
                    val = int(data_c[i, j])
                    color = 'white' if val > data_c.max() * 0.5 else '#2C3E50'
                    ax_c.text(j, i, str(val), ha='center', va='center',
                              fontsize=5, fontweight='bold', color=color)

            if highlight_target and highlight_target in matrix.columns:
                hl_col = list(matrix.columns).index(highlight_target)
                rect = plt.Rectangle((hl_col - 0.5, -0.5), 1, len(matrix),
                                      linewidth=1.5, edgecolor=C['ACCENT'],
                                      facecolor='none', linestyle='--')
                ax_c.add_patch(rect)
                if matrix[highlight_target].sum() == 0:
                    ax_c.text(hl_col, len(matrix) * 0.5, '0', fontsize=10,
                              color=C['ACCENT'], fontweight='bold', ha='center', va='center',
                              bbox=dict(boxstyle='round,pad=0.2', facecolor='#FEF9E7',
                                        edgecolor=C['ACCENT'], linewidth=1))

            for spine in ax_c.spines.values():
                spine.set_visible(False)
        ax_c.set_title('C  机构×靶区', fontsize=8, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel D: 主题象限图 ───
        ax_d = fig.add_subplot(gs[1, 1])
        ax_d.set_facecolor(C['BG'])
        thematic = data.get('thematic_map')
        if thematic is not None and not thematic.empty:
            quadrant_colors = {
                'Motor': C['ACCENT'],
                'Basic': C['INDIGO'],
                'Niche': C['VIOLET'],
                'Emerging/Declining': C['SAGE'],
            }

            for _, row in thematic.iterrows():
                color = quadrant_colors.get(row['quadrant'], '#999')
                ax_d.scatter(row['centrality'], row['density'], s=row['size'] * 25,
                             c=color, alpha=0.7, edgecolors='white', linewidth=0.5)
                ax_d.annotate(row['label'], (row['centrality'], row['density']),
                              fontsize=5, fontweight='bold', color='#2C3E50',
                              textcoords='offset points', xytext=(3, 3))

            med_c = thematic['centrality'].median()
            med_d = thematic['density'].median()
            ax_d.axvline(med_c, color='#CCCCCC', linewidth=0.8, linestyle='--')
            ax_d.axhline(med_d, color='#CCCCCC', linewidth=0.8, linestyle='--')

            xlim = ax_d.get_xlim()
            ylim = ax_d.get_ylim()
            label_props = dict(fontsize=6, alpha=0.4, fontweight='bold', ha='center')
            ax_d.text((xlim[1] + med_c) / 2, (ylim[1] + med_d) / 2, 'Motor',
                      color=C['ACCENT'], **label_props)
            ax_d.text((xlim[0] + med_c) / 2, (ylim[1] + med_d) / 2, 'Niche',
                      color=C['VIOLET'], **label_props)
            ax_d.text((xlim[1] + med_c) / 2, (ylim[0] + med_d) / 2, 'Basic',
                      color=C['INDIGO'], **label_props)
            ax_d.text((xlim[0] + med_c) / 2, (ylim[0] + med_d) / 2, 'Emerging',
                      color=C['SAGE'], **label_props)

            ax_d.set_xlabel('Centrality', fontsize=7)
            ax_d.set_ylabel('Density', fontsize=7)
            ax_d.tick_params(labelsize=6)
            ax_d.spines['top'].set_visible(False)
            ax_d.spines['right'].set_visible(False)
        ax_d.set_title('D  主题定位', fontsize=8, fontweight='bold',
                       loc='left', color='#2C3E50')

        fig.suptitle('附图  文献计量补充数据',
                     fontsize=9, fontweight='bold', color='#2C3E50', y=0.96)

        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=300, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()
