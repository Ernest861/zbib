"""出图: 全景图模板 + 预设色板"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# ═══════════════════════════════════════════════
# 预设色板
# ═══════════════════════════════════════════════
COLORS_GREEN_PURPLE = {
    'TEAL':   '#0D9B76',
    'JADE':   '#3AAF85',
    'SAGE':   '#6BBF96',
    'SLATE':  '#5E8CA5',
    'INDIGO': '#5C6DAF',
    'VIOLET': '#7B5EA7',
    'PLUM':   '#9B59B6',
    'ORCHID': '#C39BD3',
    'ACCENT': '#E74C3C',
    'WARN':   '#F39C12',
    'BG':     '#FAFAFA',
}

# Category → color mapping
CAT_COLORS = {
    '神经调控': '#E74C3C',
    '环路/机制': '#9B59B6',
    '免疫/代谢': '#7B5EA7',
    '神经影像': '#5C6DAF',
    '遗传/组学': '#5E8CA5',
    '临床/药物': '#3AAF85',
    '认知/行为': '#C39BD3',
    '其他':     '#D5D8DC',
}

CMAP_GP = LinearSegmentedColormap.from_list(
    'gp', ['#FFFFFF', '#E0E0E0', '#A0A0A0', '#606060', '#303030'], N=256)


class LandscapePlot:
    """全景图模板"""

    def __init__(self, figsize=(28, 16), lang='zh'):
        self.figsize = figsize
        self.lang = lang
        self.C = COLORS_GREEN_PURPLE

    def plot_trend(self, ax, nih_year_cat, nsfc_yearly, display_cats, years_range=(1990, 2025)):
        """Panel A: NIH堆叠柱状 + NSFC折线双轴图"""
        C = self.C
        years_nih = sorted([y for y in nih_year_cat.index if years_range[0] <= y <= years_range[1]])

        bottom = np.zeros(len(years_nih))
        for cat in display_cats:
            if cat in nih_year_cat.columns:
                vals = [nih_year_cat.loc[y, cat] if y in nih_year_cat.index else 0 for y in years_nih]
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
            Line2D([0], [0], color=C['ACCENT'], linewidth=2.5, marker='o', markersize=5, label='NSFC (右轴)'),
        ]
        for cat in display_cats:
            legend_items.append(Patch(facecolor=CAT_COLORS.get(cat, '#D5D8DC'), alpha=0.75, label=cat))
        ax.legend(handles=legend_items, loc='upper left', fontsize=13, ncol=3,
                  framealpha=0.9, edgecolor='#CCCCCC')
        ax.set_xlim(years_range[0] - 1, years_range[1] + 1)
        ax.spines['top'].set_visible(False)
        return ax2

    def plot_stacked_evolution(self, ax, nsfc, cat_col, display_cats, period_labels, period_ranges, year_col='批准年份'):
        """Panel B: 堆叠百分比柱状图"""
        stacked_data = {}
        for cat in display_cats:
            counts = []
            for s, e in period_ranges:
                c = ((nsfc[cat_col] == cat) & (nsfc[year_col] >= s) & (nsfc[year_col] <= e)).sum()
                counts.append(c)
            stacked_data[cat] = counts

        totals = [sum(stacked_data[c][i] for c in display_cats) for i in range(len(period_labels))]
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

    def plot_heatmap_with_marginals(self, fig, gs_spec, heatmap, row_labels, col_labels,
                                    row_totals, col_totals, highlight_col=-1, title='',
                                    highlight_annotation='', font_scale=1.0):
        """Panel C: 热力图 + 上方/右侧边际柱状图. font_scale<1 for compact layouts."""
        C = self.C
        s = font_scale  # shorthand
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
        ax_ch.imshow(heatmap, cmap=CMAP_GP, aspect='auto', vmin=0)
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

        return ax_ct, ax_ch, ax_cr

    def plot_gap_table(self, ax, table_data, header_color=None):
        """Panel D: 空白汇总表"""
        C = self.C
        if header_color is None:
            header_color = C['INDIGO']

        ax.axis('off')
        table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                         cellLoc='center', loc='upper center',
                         bbox=[0.02, 0.02, 0.96, 0.90])
        table.auto_set_font_size(False)
        table.set_fontsize(15)

        n_cols = len(table_data[0])
        for j in range(n_cols):
            cell = table[0, j]
            cell.set_facecolor(header_color)
            cell.set_text_props(color='white', fontweight='bold', fontsize=15)
            cell.set_edgecolor('white')

        for i in range(1, len(table_data)):
            for j in range(n_cols):
                cell = table[i, j]
                cell.set_edgecolor('#E8E8E8')
                if j == 0:
                    cell.set_facecolor('#F0F3F5')
                    cell.get_text().set_fontweight('bold')
                    cell.get_text().set_fontsize(14)
                txt = cell.get_text().get_text()
                if txt == '0':
                    cell.set_facecolor(C['WARN'])
                    cell.get_text().set_fontweight('bold')
                    cell.get_text().set_color(C['ACCENT'])
        return table

    def plot_paper_list(self, ax, papers, title=''):
        """Panel E: 文献列表"""
        C = self.C
        ax.axis('off')
        if title:
            ax.set_title(title, fontsize=22, fontweight='bold', loc='left', color='#2C3E50')

        y_start = 0.88
        for i, (yr, journal, auth, desc) in enumerate(papers):
            y = y_start - i * 0.18
            ax.text(0.02, y, f'{i+1}.', transform=ax.transAxes, fontsize=18,
                    fontweight='bold', color=C['ACCENT'], va='top')
            ax.text(0.07, y, f'[{yr}] {journal}', transform=ax.transAxes, fontsize=15,
                    fontweight='bold', color=C['INDIGO'], va='top')
            ax.text(0.07, y - 0.06, f'{auth} — {desc}', transform=ax.transAxes, fontsize=14,
                    color='#2C3E50', va='top')

    def plot_target_timeline(self, ax, ofc_yearly, milestones, title='',
                            fs_title=11, fs_label=9, fs_tick=8, fs_annot=7):
        """OFC 文献柱状图 + 里程碑编号标注"""
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

    def plot_journal_landscape(self, ax, pubmed_df=None, title='',
                               n_top=12, fs_title=11, fs_label=8, fs_tick=7):
        """发文期刊分布 — Top-N 水平柱状图 + 顶刊标记"""
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

    def create_landscape(self, data_dict: dict, output: str):
        """一键出完整图 — 3×3 布局，8 panel + 1 placeholder"""
        C = self.C

        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        d = data_dict
        display_cats = d['display_cats']
        has_new_panels = d.get('burden_yearly') is not None or d.get('ofc_yearly') is not None

        if has_new_panels:
            # ═══ 2×3 layout — A4 嵌入 (14×9 in) ═══
            # 从大到小: 全景 → 演变 → 热力图聚焦 → 空白 → 文献 → 假说
            fig = plt.figure(figsize=(14, 9), facecolor=C['BG'])
            gs_main = gridspec.GridSpec(
                2, 3, figure=fig,
                height_ratios=[1, 1],
                width_ratios=[1, 1, 1.2],
                hspace=0.30, wspace=0.22,
                left=0.05, right=0.97, top=0.92, bottom=0.05)

            # ── Row 1: A=全景 → B=方向演变 → C=热力图 ──
            ax_a = fig.add_subplot(gs_main[0, 0])
            ax_a.set_facecolor(C['BG'])
            ax_a.set_title('A  研究全景：NSFC vs NIH',
                            fontsize=13, fontweight='bold', loc='left', color='#2C3E50')
            ax_a2 = self.plot_trend(ax_a, d['nih_year_cat'], d['nsfc_yearly'], display_cats)
            nih_total = d.get('nih_total', 0)
            nsfc_total = d.get('nsfc_total', 0)
            ax_a.text(0.97, 0.95, f'NIH: {nih_total:,}项', transform=ax_a.transAxes,
                      fontsize=10, ha='right', va='top', fontweight='bold', color='#2C3E50')
            ax_a2.text(0.03, 0.95, f'NSFC: {nsfc_total}项', transform=ax_a2.transAxes,
                       fontsize=10, ha='left', va='top', fontweight='bold', color=C['ACCENT'])
            # Downscale shared method fonts
            ax_a.tick_params(axis='both', labelsize=8)
            ax_a.yaxis.label.set_size(9)
            ax_a.xaxis.label.set_size(9)
            ax_a2.tick_params(axis='y', labelsize=8)
            ax_a2.yaxis.label.set_size(9)
            leg = ax_a.get_legend()
            if leg:
                for t in leg.get_texts():
                    t.set_fontsize(7)

            ax_b = fig.add_subplot(gs_main[0, 1])
            ax_b.set_facecolor(C['BG'])
            ax_b.set_title('B  NSFC研究方向构成演变',
                            fontsize=13, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_stacked_evolution(ax_b, d['nsfc'], d['cat_col'], display_cats,
                                        d['period_labels'], d['period_ranges'])
            ax_b.annotate('神经调控 ↑', xy=(6, 18), fontsize=10,
                          color=C['ACCENT'], fontweight='bold')
            ax_b.tick_params(axis='both', labelsize=8)
            ax_b.yaxis.label.set_size(9)

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
                            fontsize=13, fontweight='bold', loc='left', color='#2C3E50')
            self.plot_gap_table(ax_d, d['gap_table'])

            ax_e = fig.add_subplot(gs_main[1, 1])
            self.plot_paper_list(ax_e, d['papers'],
                                 title=d.get('panel_e_title', '').replace('E ', 'E '))
            if 'panel_e_summary' in d:
                ax_e.text(0.50, 0.02, d['panel_e_summary'],
                          transform=ax_e.transAxes, fontsize=9, ha='center', va='bottom',
                          fontweight='bold', color=C['ACCENT'],
                          bbox=dict(boxstyle='round,pad=0.3', facecolor='#FEF9E7',
                                    edgecolor=C['WARN'], linewidth=1))

            ax_f = fig.add_subplot(gs_main[1, 2])
            ax_f.set_facecolor('#F5F0FA')
            ax_f.set_title('F  假说图（待插入）', fontsize=13, fontweight='bold',
                            loc='left', color='#2C3E50')
            for spine in ax_f.spines.values():
                spine.set_linestyle('--')
                spine.set_color(C['VIOLET'])
                spine.set_linewidth(1.5)
            ax_f.set_xticks([])
            ax_f.set_yticks([])
            ax_f.text(0.5, 0.5, '假说图\nHypothesis Figure\n\n（手动插入）',
                      transform=ax_f.transAxes, fontsize=14, ha='center', va='center',
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

        # Title — scale for figure size
        sup_fs = 14 if has_new_panels else 24
        sup_y = 0.97 if has_new_panels else 0.96
        fig.suptitle(d.get('suptitle', ''), fontsize=sup_fs, fontweight='bold',
                     color='#2C3E50', y=sup_y)

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=300, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()

    # ═══════════════════════════════════════════════
    # 共现网络演变 + 趋势预测
    # ═══════════════════════════════════════════════

    def plot_temporal_network(self, temporal: list, output: str,
                              title: str = '共现网络演变'):
        """每个时间窗口一个子图的网络演变图"""
        import networkx as nx
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        n = len(temporal)
        if n == 0:
            print(f"[WARN] 无网络数据，跳过 {output}")
            return

        ncols = min(n, 3)
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(8 * ncols, 7 * nrows),
                                 facecolor=C['BG'])
        if n == 1:
            axes = np.array([axes])
        axes = np.atleast_2d(axes)

        palette = [C['ACCENT'], C['INDIGO'], C['JADE'], C['VIOLET'], C['PLUM'],
                   C['SLATE'], C['TEAL'], C['ORCHID'], C['SAGE'], C['WARN']]

        for idx, snap in enumerate(temporal):
            r, c = divmod(idx, ncols)
            ax = axes[r, c]
            ax.set_facecolor(C['BG'])
            G = snap['graph']

            top_n_nodes = min(35, len(G))
            if len(G) > top_n_nodes:
                top_nodes = sorted(G.nodes(), key=lambda nd: G.degree(nd), reverse=True)[:top_n_nodes]
                G = G.subgraph(top_nodes).copy()

            if len(G) == 0:
                ax.text(0.5, 0.5, '节点不足', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(snap['period'], fontsize=14, fontweight='bold')
                ax.axis('off')
                continue

            pos = nx.spring_layout(G, k=1.5 / max(len(G) ** 0.5, 1), iterations=50, seed=42)

            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
                comm_ids = sorted(set(partition.values()))
                cmap = {cid: palette[i % len(palette)] for i, cid in enumerate(comm_ids)}
                colors = [cmap.get(partition.get(nd, 0), '#999') for nd in G.nodes()]
            except ImportError:
                colors = [C['INDIGO']] * len(G)

            edge_w = [G[u][v].get('weight', 1) for u, v in G.edges()]
            max_ew = max(edge_w) if edge_w else 1
            # 只显示权重前30%的边以减少视觉噪声但保留结构
            if len(edge_w) > 50:
                cutoff = sorted(edge_w)[int(len(edge_w) * 0.7)]
                edge_list = [(u, v) for u, v in G.edges() if G[u][v].get('weight', 1) >= cutoff]
            else:
                edge_list = list(G.edges())
            filtered_w = [G[u][v].get('weight', 1) for u, v in edge_list]
            widths = [0.3 + 1.8 * w / max_ew for w in filtered_w]

            degrees = [G.degree(nd) for nd in G.nodes()]
            max_d = max(degrees) if degrees and max(degrees) > 0 else 1
            sizes = [80 + 350 * d / max_d for d in degrees]

            nx.draw_networkx_edges(G, pos, edgelist=edge_list, ax=ax, width=widths,
                                   alpha=0.15, edge_color='#999999')
            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes, node_color=colors,
                                   alpha=0.85, edgecolors='white', linewidths=0.5)

            n_labels = min(6, len(G))
            threshold = sorted(degrees, reverse=True)[n_labels - 1]
            labels = {nd: nd for nd in G.nodes() if G.degree(nd) >= threshold}
            # 截断长标签
            labels = {nd: (lbl[:12] + '..' if len(lbl) > 14 else lbl) for nd, lbl in labels.items()}
            nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=8,
                                    font_color='#2C3E50', font_weight='bold')

            ax.set_title(f"{snap['period']}  (n={snap['n_nodes']}, e={snap['n_edges']})",
                         fontsize=13, fontweight='bold', color='#2C3E50')
            ax.axis('off')

        for idx in range(n, nrows * ncols):
            r, c = divmod(idx, ncols)
            axes[r, c].axis('off')

        fig.suptitle(title, fontsize=18, fontweight='bold', color='#2C3E50', y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.95])

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    def plot_keyword_prediction(self, predictions_nsfc: dict, predictions_nih: dict,
                                output: str, top_k: int = 8):
        """双栏预测图: NSFC左, NIH右"""
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        palette = [C['ACCENT'], C['INDIGO'], C['JADE'], C['VIOLET'], C['PLUM'],
                   C['SLATE'], C['TEAL'], C['ORCHID'], C['SAGE'], C['WARN']]

        fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(16, 7), facecolor=C['BG'])

        def _plot_panel(ax, preds, panel_title):
            ax.set_facecolor(C['BG'])
            if not preds:
                ax.text(0.5, 0.5, '数据不足', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(panel_title, fontsize=14, fontweight='bold', color='#2C3E50')
                return

            items = list(preds.items())[:top_k]
            for i, (kw, pdf) in enumerate(items):
                color = palette[i % len(palette)]
                hist = pdf[~pdf['is_forecast']]
                fore = pdf[pdf['is_forecast']]

                ax.plot(hist['year'], hist['count'], '-o', color=color,
                        linewidth=1.8, markersize=4, label=kw)
                if not fore.empty:
                    conn = pd.concat([hist.tail(1), fore])
                    ax.plot(conn['year'], conn['predicted'], '--', color=color,
                            linewidth=1.2, alpha=0.7)
                    ax.fill_between(fore['year'], fore['ci_lower'], fore['ci_upper'],
                                    color=color, alpha=0.1)

            ax.legend(fontsize=8, ncol=2, loc='upper left', framealpha=0.9)
            ax.set_xlabel('Year', fontsize=10)
            ax.set_ylabel('频次', fontsize=10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(labelsize=9)
            ax.set_title(panel_title, fontsize=14, fontweight='bold', loc='left', color='#2C3E50')

        _plot_panel(ax_l, predictions_nsfc, 'NSFC 关键词趋势预测')
        _plot_panel(ax_r, predictions_nih, 'NIH Keyword Trend Prediction')

        fig.suptitle('关键词趋势预测  Keyword Trend Prediction',
                     fontsize=16, fontweight='bold', color='#2C3E50', y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.94])

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    def plot_thematic_map_temporal(self, temporal: list, output: str,
                                   title: str = '主题地图演变'):
        """每个时间窗口一个子图的四象限主题地图"""
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        n = len(temporal)
        if n == 0:
            print(f"[WARN] 无网络数据，跳过 thematic map {output}")
            return

        ncols = min(n, 3)
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 6 * nrows),
                                 facecolor=C['BG'])
        if n == 1:
            axes = np.array([axes])
        axes = np.atleast_2d(axes)

        quadrant_colors = {
            'Motor': C['ACCENT'], 'Basic': C['INDIGO'],
            'Niche': C['JADE'], 'Emerging/Declining': '#999999',
        }

        for idx, snap in enumerate(temporal):
            r, c = divmod(idx, ncols)
            ax = axes[r, c]
            ax.set_facecolor(C['BG'])

            tm = snap.get('thematic_map')
            if tm is None or (hasattr(tm, 'empty') and tm.empty):
                ax.text(0.5, 0.5, '数据不足', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(snap['period'], fontsize=13, fontweight='bold')
                ax.axis('off')
                continue

            # Median lines for quadrant separation
            med_c = tm['centrality'].median()
            med_d = tm['density'].median()
            ax.axvline(med_c, ls='--', color='#CCCCCC', lw=1, zorder=0)
            ax.axhline(med_d, ls='--', color='#CCCCCC', lw=1, zorder=0)

            for _, row in tm.iterrows():
                q = row.get('quadrant', 'Emerging/Declining')
                color = quadrant_colors.get(q, '#999999')
                size = max(row['size'] * 40, 60)
                ax.scatter(row['centrality'], row['density'], s=size,
                           c=color, alpha=0.7, edgecolors='white', linewidth=0.5, zorder=2)
                ax.annotate(row['label'], (row['centrality'], row['density']),
                            fontsize=7, ha='center', va='bottom',
                            textcoords='offset points', xytext=(0, 5))

            ax.set_xlabel('Centrality', fontsize=9)
            ax.set_ylabel('Density', fontsize=9)
            ax.set_title(snap['period'], fontsize=13, fontweight='bold', color='#2C3E50')

        # Hide empty axes
        for idx in range(n, nrows * ncols):
            r, c = divmod(idx, ncols)
            axes[r, c].axis('off')

        # Legend
        from matplotlib.lines import Line2D
        legend_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=v,
                                 markersize=8, label=k) for k, v in quadrant_colors.items()]
        fig.legend(handles=legend_handles, loc='lower center', ncol=4, fontsize=9,
                   frameon=False, bbox_to_anchor=(0.5, -0.02))

        fig.suptitle(title, fontsize=16, fontweight='bold', color='#2C3E50', y=1.01)
        fig.tight_layout()
        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    def plot_emerging_keywords(self, emerging_nsfc: 'pd.DataFrame',
                               emerging_nih: 'pd.DataFrame', output: str):
        """双栏水平条形图: NSFC左, NIH右, 按growth排序top-15"""
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 7), facecolor=C['BG'])

        def _bar(ax, df, panel_title, top_n=15):
            ax.set_facecolor(C['BG'])
            if df is None or df.empty:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(panel_title, fontsize=13, fontweight='bold', color='#2C3E50')
                return
            sub = df.head(top_n).iloc[::-1]  # reverse for bottom-up
            colors = [C['ACCENT'] if row['prior_count'] == 0 else C['INDIGO']
                      for _, row in sub.iterrows()]
            ax.barh(range(len(sub)), sub['growth'].clip(upper=100), color=colors, alpha=0.85)
            ax.set_yticks(range(len(sub)))
            ax.set_yticklabels(sub['keyword'], fontsize=9)
            ax.set_xlabel('Growth ratio', fontsize=10)
            ax.set_title(panel_title, fontsize=13, fontweight='bold', color='#2C3E50')
            # Annotate counts
            for i, (_, row) in enumerate(sub.iterrows()):
                g = row['growth'] if row['growth'] < 100 else 100
                label = '★ NEW' if row['prior_count'] == 0 else f"{row['growth']:.1f}x"
                ax.text(g + 0.5, i, label, va='center', fontsize=7, color='#555')

        _bar(ax_l, emerging_nsfc, 'NSFC 新兴关键词')
        _bar(ax_r, emerging_nih, 'NIH Emerging Keywords')

        # Legend
        from matplotlib.patches import Patch
        legend_handles = [
            Patch(facecolor=C['ACCENT'], label='全新词 (prior=0)'),
            Patch(facecolor=C['INDIGO'], label='增长词'),
        ]
        fig.legend(handles=legend_handles, loc='lower center', ncol=2, fontsize=9,
                   frameon=False, bbox_to_anchor=(0.5, -0.02))

        fig.suptitle('新兴关键词检测 (Emerging Keywords)', fontsize=15, fontweight='bold',
                     color='#2C3E50', y=1.01)
        fig.tight_layout()
        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    def plot_evolution_summary(self, evo_nsfc: 'pd.DataFrame', evo_nih: 'pd.DataFrame',
                               output: str):
        """网络演变摘要: 双行 heatmap (节点/边/模块性变化)"""
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), facecolor=C['BG'])

        def _plot_evo(ax, evo_df, panel_title):
            ax.set_facecolor(C['BG'])
            if evo_df is None or evo_df.empty:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(panel_title, fontsize=13, fontweight='bold', color='#2C3E50')
                ax.axis('off')
                return

            periods = evo_df['period'].tolist()
            metrics = ['n_nodes', 'n_edges', 'n_clusters', 'modularity']
            labels_m = ['Nodes', 'Edges', 'Clusters', 'Modularity']

            data = evo_df[metrics].values.T.astype(float)
            for row_i in range(data.shape[0]):
                rmax = data[row_i].max()
                if rmax > 0:
                    data[row_i] = data[row_i] / rmax

            ax.imshow(data, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
            ax.set_xticks(range(len(periods)))
            ax.set_xticklabels(periods, fontsize=9, rotation=15)
            ax.set_yticks(range(len(labels_m)))
            ax.set_yticklabels(labels_m, fontsize=10)

            raw = evo_df[metrics].values.T
            for ri in range(raw.shape[0]):
                for ci in range(raw.shape[1]):
                    val = raw[ri, ci]
                    txt = f"{val:.2f}" if isinstance(val, float) and val < 10 else str(int(val))
                    ax.text(ci, ri, txt, ha='center', va='center', fontsize=9,
                            color='white' if data[ri, ci] > 0.5 else '#2C3E50', fontweight='bold')

            ax.set_title(panel_title, fontsize=13, fontweight='bold', loc='left', color='#2C3E50')

        _plot_evo(axes[0], evo_nsfc, 'NSFC 网络演变指标')
        _plot_evo(axes[1], evo_nih, 'NIH Network Evolution Metrics')

        fig.suptitle('共现网络演变摘要', fontsize=16, fontweight='bold', color='#2C3E50', y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.94])

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    # ═══════════════════════════════════════════════
    # Phase 1b: 关键词 + PI深化 + 机构交叉
    # ═══════════════════════════════════════════════

    def plot_lotka(self, ax, lotka_df: 'pd.DataFrame', title: str = "Lotka's Law"):
        """Lotka定律: PI产出分布条形图"""
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

    def plot_pi_timeline(self, ax, timeline_df: 'pd.DataFrame', title: str = 'PI产出时间线'):
        """Top PI 气泡图: x=year, y=PI, size=count"""
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

    def plot_inst_direction_heatmap(self, ax, matrix: 'pd.DataFrame',
                                    title: str = '机构×方向'):
        """机构×研究方向热力图"""
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

    def plot_word_growth(self, ax, growth_df: 'pd.DataFrame', title: str = '关键词年趋势'):
        """关键词频率年趋势折线图"""
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

    def plot_trend_topics(self, ax, topics: dict, title: str = 'Trend Topics'):
        """每时期 Top 关键词表格"""
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

    def create_bibliometric_report(self, perf: dict, kw_data: dict,
                                    output: str):
        """生成文献计量学综合报告 (9-panel, 3×3)

        Parameters
        ----------
        perf : from PerformanceAnalyzer (lotka, pi_timeline, inst_direction_matrix)
        kw_data : from KeywordAnalyzer (top_kw_nsfc, top_kw_nih, word_growth, trend_topics)
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

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()

    # ═══════════════════════════════════════════════
    # Phase 1: 性能分析 + 数据质量面板
    # ═══════════════════════════════════════════════

    def plot_top_bar(self, ax, data: 'pd.DataFrame', name_col: str, value_col: str,
                     n: int = 15, title: str = '', color: str = '#5C6DAF',
                     horizontal: bool = True):
        """通用Top-N柱状图"""
        df = data.nlargest(n, value_col)
        if horizontal:
            y_pos = range(len(df))
            ax.barh(y_pos, df[value_col].values, color=color, edgecolor='white', height=0.7)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df[name_col].values, fontsize=12)
            ax.invert_yaxis()
            for i, v in enumerate(df[value_col].values):
                ax.text(v + df[value_col].max() * 0.01, i, str(int(v)),
                        va='center', fontsize=11, color='#2C3E50')
        else:
            x_pos = range(len(df))
            ax.bar(x_pos, df[value_col].values, color=color, edgecolor='white', width=0.7)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(df[name_col].values, fontsize=10, rotation=45, ha='right')

        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def plot_bradford(self, ax, bradford: dict, title: str = 'Bradford Zones'):
        """Bradford定律三区饼图"""
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

    def plot_funding_trend(self, ax, funding_df: 'pd.DataFrame', source: str = 'NSFC',
                           display_cats: list[str] | None = None, title: str = ''):
        """资金趋势堆叠面积图 — 按类别"""
        C = self.C
        df = funding_df[funding_df['source'] == source]
        if df.empty:
            return

        pivot = df.pivot_table(index='year', columns='category', values='总金额_万',
                               aggfunc='sum', fill_value=0)

        # Only show display_cats (in order), collapse the rest into "其他"
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

    def plot_completeness_matrix(self, ax, matrix: 'pd.DataFrame', title: str = '数据完整性'):
        """完整性矩阵 — 按数据源分组的水平条形图

        matrix: 长格式 DataFrame (source, field, rate)
        """
        C = self.C
        if matrix.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)
            ax.axis('off')
            return

        # Filter to fields with < 100% coverage (interesting ones)
        display = matrix[matrix['rate'] < 1.0].copy()
        if display.empty:
            ax.text(0.5, 0.5, '所有字段100%覆盖', ha='center', va='center',
                    fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return

        source_colors = {'NSFC': C['INDIGO'], 'NIH': C['JADE'], 'PubMed': C['VIOLET']}

        # Build labels: "NSFC: 中文关键词" format
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

    def plot_emerging_declining(self, ax, trends: dict, title: str = '类别趋势',
                               exclude: list[str] | None = None):
        """上升/下降类别双向条形图"""
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

    def create_performance_report(self, perf: dict, quality: dict, trends: dict,
                                  output: str, display_cats: list[str] | None = None):
        """生成性能分析+数据质量综合图 (6-panel)"""
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

        # Panel E: Emerging/declining (NSFC), exclude "其他"
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

        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()

    # ═══════════════════════════════════════════════
    # Phase 2: 网络分析可视化
    # ═══════════════════════════════════════════════

    def plot_network(self, ax, G, title: str = '', community_map: dict | None = None,
                     top_n: int = 60):
        """力导向布局网络图

        Parameters
        ----------
        G : networkx.Graph
        community_map : {node: community_id}，用于着色
        top_n : 只显示 degree 最高的 N 个节点
        """
        import networkx as nx
        C = self.C

        if len(G) == 0:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)
            ax.axis('off')
            return

        # Subgraph: top nodes by degree
        if len(G) > top_n:
            top_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:top_n]
            G = G.subgraph(top_nodes).copy()

        # Layout
        pos = nx.spring_layout(G, k=1.5 / max(len(G) ** 0.5, 1), iterations=50, seed=42)

        # Edge drawing
        edge_weights = [G[u][v].get('weight', 1) for u, v in G.edges()]
        max_w = max(edge_weights) if edge_weights else 1
        edge_widths = [0.3 + 2.0 * w / max_w for w in edge_weights]
        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths,
                               alpha=0.25, edge_color='#999999')

        # Node colors by community
        palette = [C['ACCENT'], C['INDIGO'], C['JADE'], C['VIOLET'], C['PLUM'],
                   C['SLATE'], C['TEAL'], C['ORCHID'], C['SAGE'], C['WARN']]
        if community_map:
            comm_ids = sorted(set(community_map.values()))
            color_map = {cid: palette[i % len(palette)] for i, cid in enumerate(comm_ids)}
            node_colors = [color_map.get(community_map.get(n, 0), '#999') for n in G.nodes()]
        else:
            node_colors = [C['INDIGO']] * len(G)

        # Node sizes by degree
        degrees = [G.degree(n) for n in G.nodes()]
        max_deg = max(degrees) if degrees else 1
        node_sizes = [80 + 400 * d / max_deg for d in degrees]

        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes,
                               node_color=node_colors, alpha=0.85, edgecolors='white',
                               linewidths=0.5)

        # Labels for high-degree nodes
        n_labels = min(20, len(degrees))
        label_threshold = sorted(degrees, reverse=True)[min(n_labels - 1, len(degrees) - 1)]
        labels = {n: n for n in G.nodes() if G.degree(n) >= label_threshold}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=11,
                                font_color='#2C3E50', font_weight='bold')

        ax.axis('off')
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    def plot_thematic_map(self, ax, thematic_df: 'pd.DataFrame',
                          title: str = '主题地图 Thematic Map'):
        """四象限主题地图 (Callon's centrality × density)"""
        C = self.C

        if thematic_df.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)
            ax.axis('off')
            return

        quadrant_colors = {
            'Motor': C['ACCENT'],
            'Basic': C['INDIGO'],
            'Niche': C['VIOLET'],
            'Emerging/Declining': C['SAGE'],
        }

        for _, row in thematic_df.iterrows():
            color = quadrant_colors.get(row['quadrant'], '#999')
            ax.scatter(row['centrality'], row['density'], s=row['size'] * 50,
                       c=color, alpha=0.7, edgecolors='white', linewidth=1)
            ax.annotate(row['label'], (row['centrality'], row['density']),
                        fontsize=10, fontweight='bold', color='#2C3E50',
                        textcoords='offset points', xytext=(5, 5))

        # Draw quadrant lines at median
        med_c = thematic_df['centrality'].median()
        med_d = thematic_df['density'].median()
        ax.axvline(med_c, color='#CCCCCC', linewidth=1, linestyle='--')
        ax.axhline(med_d, color='#CCCCCC', linewidth=1, linestyle='--')

        # Quadrant labels
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        label_props = dict(fontsize=11, alpha=0.4, fontweight='bold', ha='center')
        ax.text((xlim[1] + med_c) / 2, (ylim[1] + med_d) / 2, 'Motor\nThemes',
                color=C['ACCENT'], **label_props)
        ax.text((xlim[0] + med_c) / 2, (ylim[1] + med_d) / 2, 'Niche\nThemes',
                color=C['VIOLET'], **label_props)
        ax.text((xlim[1] + med_c) / 2, (ylim[0] + med_d) / 2, 'Basic\nThemes',
                color=C['INDIGO'], **label_props)
        ax.text((xlim[0] + med_c) / 2, (ylim[0] + med_d) / 2, 'Emerging/\nDeclining',
                color=C['SAGE'], **label_props)

        ax.set_xlabel('Centrality (外部连接)', fontsize=13)
        ax.set_ylabel('Density (内部紧密度)', fontsize=13)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=11)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    def plot_centrality_bar(self, ax, centrality_df: 'pd.DataFrame',
                            title: str = '节点中心性 Top-15'):
        """中心性排名条形图"""
        C = self.C
        if centrality_df.empty:
            ax.axis('off')
            return

        df = centrality_df.head(15)
        y = range(len(df))
        ax.barh(y, df['degree'].values, color=C['VIOLET'], edgecolor='white', height=0.6,
                label='Degree')
        ax.set_yticks(y)
        ax.set_yticklabels(df['name'].values, fontsize=11)
        ax.invert_yaxis()

        for i, row in enumerate(df.itertuples()):
            ax.text(row.degree + 0.3, i, f"btw={row.betweenness:.3f}",
                    va='center', fontsize=9, color='#888888')

        ax.set_xlabel('Degree (合作人数)', fontsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=11)
        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    def plot_community_summary(self, ax, communities: dict, G,
                               title: str = '社区结构'):
        """社区摘要表格"""
        C = self.C
        ax.axis('off')

        if not communities:
            return

        header = ['社区', '人数', '核心成员']
        rows = []
        for i, (cid, members) in enumerate(list(communities.items())[:8]):
            # Sort by degree in this community
            members_sorted = sorted(members, key=lambda n: G.degree(n), reverse=True)
            core = ', '.join(members_sorted[:4])
            if len(members_sorted) > 4:
                core += f' +{len(members_sorted)-4}'
            rows.append([f'C{i+1}', str(len(members)), core])

        table = ax.table(cellText=rows, colLabels=header,
                         cellLoc='center', loc='upper center',
                         bbox=[0.0, 0.0, 1.0, 0.92])
        table.auto_set_font_size(False)
        table.set_fontsize(11)

        for j in range(len(header)):
            cell = table[0, j]
            cell.set_facecolor(C['VIOLET'])
            cell.set_text_props(color='white', fontweight='bold', fontsize=12)
            cell.set_edgecolor('white')

        for i in range(1, len(rows) + 1):
            for j in range(len(header)):
                table[i, j].set_edgecolor('#E8E8E8')
                table[i, j].set_facecolor('#F8F9FA' if i % 2 == 0 else 'white')

        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    def _save_fig(self, fig, output: str, suffix: str = ''):
        """保存图片的通用方法"""
        from pathlib import Path
        C = self.C
        out = Path(output + suffix)
        fig.savefig(str(out.with_suffix('.png')), dpi=200, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()

    def create_network_report(self, net_data: dict, output: str):
        """生成网络分析报告 (两页)

        Page 1: 社会结构 — PI合作网络 + 机构合作网络
        Page 2: 概念结构 — NSFC关键词网络 + PubMed MeSH网络 + 主题地图
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        # ═══════════════════════════════════════════
        # Page 1: 社会结构
        # ═══════════════════════════════════════════
        fig1 = plt.figure(figsize=(36, 18), facecolor=C['BG'])
        gs1 = gridspec.GridSpec(2, 3, figure=fig1, hspace=0.25, wspace=0.22,
                                left=0.04, right=0.97, top=0.92, bottom=0.03,
                                width_ratios=[1.3, 0.7, 1])

        # A: PI合作网络（最大连通分量）
        ax1a = fig1.add_subplot(gs1[0, 0])
        collab_G = net_data.get('collab_graph')
        collab_part = net_data.get('collab_partition', {})
        if collab_G is not None:
            self.plot_network(ax1a, collab_G, title='A  PI合作网络 (最大连通分量)',
                              community_map=collab_part, top_n=80)

        # B: 中心性排名
        ax1b = fig1.add_subplot(gs1[0, 1])
        centrality = net_data.get('collab_centrality')
        if centrality is not None:
            self.plot_centrality_bar(ax1b, centrality, title='B  合作中心性 Top-15')

        # C: 社区结构
        ax1c = fig1.add_subplot(gs1[0, 2])
        comms = net_data.get('collab_communities', {})
        if comms and collab_G is not None:
            self.plot_community_summary(ax1c, comms, collab_G,
                                         title='C  合作社区结构')

        # D: 机构合作网络
        ax1d = fig1.add_subplot(gs1[1, 0])
        inst_G = net_data.get('inst_graph')
        if inst_G is not None:
            self.plot_network(ax1d, inst_G, title='D  机构合作网络', top_n=40)

        # E: 网络统计摘要
        ax1e = fig1.add_subplot(gs1[1, 1:])
        stats = net_data.get('network_stats', {})
        self._plot_network_stats(ax1e, stats, title='E  网络结构统计')

        fig1.suptitle('社会结构分析  Social Structure',
                      fontsize=28, fontweight='bold', color='#2C3E50', y=0.96)
        self._save_fig(fig1, output, '_social')

        # ═══════════════════════════════════════════
        # Page 2: 概念结构
        # ═══════════════════════════════════════════
        fig2 = plt.figure(figsize=(36, 18), facecolor=C['BG'])
        gs2 = gridspec.GridSpec(2, 3, figure=fig2, hspace=0.25, wspace=0.22,
                                left=0.04, right=0.97, top=0.92, bottom=0.03,
                                width_ratios=[1.2, 0.8, 1])

        # A: NSFC关键词共现
        ax2a = fig2.add_subplot(gs2[0, 0])
        concept_G = net_data.get('concept_graph')
        concept_part = net_data.get('concept_partition', {})
        if concept_G is not None:
            self.plot_network(ax2a, concept_G, title='A  NSFC关键词共现网络',
                              community_map=concept_part, top_n=60)

        # B: NSFC概念聚类
        ax2b = fig2.add_subplot(gs2[0, 1:])
        concept_comms = net_data.get('concept_communities', {})
        if concept_comms and concept_G is not None:
            self.plot_community_summary(ax2b, concept_comms, concept_G,
                                         title='B  NSFC概念聚类')

        # C: PubMed MeSH共现
        ax2c = fig2.add_subplot(gs2[1, 0])
        mesh_G = net_data.get('mesh_graph')
        mesh_part = net_data.get('mesh_partition', {})
        if mesh_G is not None:
            self.plot_network(ax2c, mesh_G, title='C  PubMed MeSH共现网络',
                              community_map=mesh_part, top_n=60)

        # D: 主题地图（NSFC）
        ax2d = fig2.add_subplot(gs2[1, 1])
        thematic = net_data.get('thematic_map')
        if thematic is not None:
            self.plot_thematic_map(ax2d, thematic, title='D  NSFC主题地图')

        # E: 主题地图（PubMed）
        ax2e = fig2.add_subplot(gs2[1, 2])
        thematic_pm = net_data.get('thematic_map_pubmed')
        if thematic_pm is not None:
            self.plot_thematic_map(ax2e, thematic_pm, title='E  PubMed主题地图')

        fig2.suptitle('概念结构分析  Conceptual Structure',
                      fontsize=28, fontweight='bold', color='#2C3E50', y=0.96)
        self._save_fig(fig2, output, '_conceptual')

    def _plot_network_stats(self, ax, stats: dict, title: str = ''):
        """网络结构统计摘要表"""
        C = self.C
        ax.axis('off')

        if not stats:
            return

        header = ['指标', 'PI合作网络', '机构合作网络']
        rows = [
            ['节点数', str(stats.get('collab_nodes', '')), str(stats.get('inst_nodes', ''))],
            ['边数', str(stats.get('collab_edges', '')), str(stats.get('inst_edges', ''))],
            ['连通分量', str(stats.get('collab_components', '')), str(stats.get('inst_components', ''))],
            ['平均度', str(stats.get('collab_avg_degree', '')), str(stats.get('inst_avg_degree', ''))],
            ['网络密度', str(stats.get('collab_density', '')), str(stats.get('inst_density', ''))],
            ['跨机构合作率', str(stats.get('cross_inst_rate', '')), '—'],
            ['社区数', str(stats.get('collab_n_communities', '')), str(stats.get('inst_n_communities', ''))],
        ]

        table = ax.table(cellText=rows, colLabels=header,
                         cellLoc='center', loc='upper center',
                         bbox=[0.05, 0.05, 0.9, 0.85])
        table.auto_set_font_size(False)
        table.set_fontsize(14)

        for j in range(len(header)):
            cell = table[0, j]
            cell.set_facecolor(C['INDIGO'])
            cell.set_text_props(color='white', fontweight='bold', fontsize=15)
            cell.set_edgecolor('white')
            cell.set_height(0.08)

        for i in range(1, len(rows) + 1):
            for j in range(len(header)):
                cell = table[i, j]
                cell.set_edgecolor('#E8E8E8')
                cell.set_facecolor('#F8F9FA' if i % 2 == 0 else 'white')
                cell.set_height(0.08)
                if j == 0:
                    cell.get_text().set_fontweight('bold')

        if title:
            ax.set_title(title, fontsize=18, fontweight='bold', loc='left', color='#2C3E50')

    # ═══════════════════════════════════════════════
    # Supplementary Figure (Figure 2)
    # ═══════════════════════════════════════════════

    def create_supplementary_figure(self, data: dict, output: str,
                                     display_cats=None, highlight_target=''):
        """生成补充数据图 (2×2, 14×9 inches)

        Parameters
        ----------
        data : dict with keys 'nih_funding', 'emerging_kw', 'inst_target_matrix', 'thematic_map'
        display_cats : category order for panel A
        highlight_target : target name to highlight in panel C
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(14, 9), facecolor=C['BG'])
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.28, wspace=0.25,
                               left=0.07, right=0.97, top=0.92, bottom=0.07)

        # ─── Panel A: NIH经费趋势 (stacked area by category) ───
        ax_a = fig.add_subplot(gs[0, 0])
        ax_a.set_facecolor(C['BG'])
        funding_df = data.get('nih_funding')
        if funding_df is not None and not funding_df.empty:
            pivot = funding_df.pivot_table(
                index='year', columns='category', values='总金额_万',
                aggfunc='sum', fill_value=0)

            # Collapse non-display_cats into "其他"
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

            # Annotate neuromodulation growth
            if '神经调控' in pivot.columns:
                max_year = pivot.index.max()
                # Find cumulative position for annotation
                cat_idx = list(pivot.columns).index('神经调控')
                cum_y = pivot.loc[max_year][:cat_idx+1].sum()
                ax_a.annotate('神经调控 ↑', xy=(max_year, cum_y * 0.9),
                              fontsize=10, color=C['ACCENT'], fontweight='bold')

            ax_a.set_ylabel('NIH资助金额(万)', fontsize=9)
            ax_a.set_xlabel('Year', fontsize=9)
            ax_a.tick_params(axis='both', labelsize=8)
            ax_a.legend(fontsize=7, ncol=2, loc='upper left', framealpha=0.9)
            ax_a.spines['top'].set_visible(False)
            ax_a.spines['right'].set_visible(False)
        ax_a.set_title('A  NIH资助金额趋势 (按方向)', fontsize=13, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel B: 新兴关键词 (horizontal bar) ───
        ax_b = fig.add_subplot(gs[0, 1])
        ax_b.set_facecolor(C['BG'])
        emerging = data.get('emerging_kw')
        if emerging is not None and not emerging.empty:
            # Filter out brand-new terms (growth=999) if >15 remain
            filtered = emerging[emerging['growth'] < 999] if len(emerging[emerging['growth'] < 999]) >= 10 else emerging
            top15 = filtered.nlargest(15, 'growth')

            y_pos = range(len(top15))
            # Color gradient by growth
            max_growth = top15['growth'].max()
            colors = [plt.cm.Reds(0.3 + 0.6 * g / max_growth) for g in top15['growth']]

            ax_b.barh(y_pos, top15['recent_count'].values, color=colors,
                      edgecolor='white', height=0.7)
            ax_b.set_yticks(y_pos)
            ax_b.set_yticklabels(top15['keyword'].values, fontsize=7)
            ax_b.invert_yaxis()

            # Annotate growth rate
            for i, (cnt, gr) in enumerate(zip(top15['recent_count'], top15['growth'])):
                label = f"{gr:.1f}×" if gr < 100 else "new"
                ax_b.text(cnt + 1, i, label, va='center', fontsize=7,
                          color=C['ACCENT'], fontweight='bold')

            ax_b.set_xlabel('Recent count (3y)', fontsize=9)
            ax_b.tick_params(axis='both', labelsize=7)
            ax_b.spines['top'].set_visible(False)
            ax_b.spines['right'].set_visible(False)
        ax_b.set_title('B  PubMed新兴MeSH关键词 (近3年)', fontsize=13, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel C: 机构×靶区矩阵 (heatmap) ───
        ax_c = fig.add_subplot(gs[1, 0])
        ax_c.set_facecolor(C['BG'])
        matrix = data.get('inst_target_matrix')
        if matrix is not None and not matrix.empty:
            data_c = matrix.values.astype(float)
            cmap_c = LinearSegmentedColormap.from_list('wp', ['#FFFFFF', C['INDIGO']], N=256)
            ax_c.imshow(data_c, cmap=cmap_c, aspect='auto', vmin=0)

            ax_c.set_xticks(range(len(matrix.columns)))
            ax_c.set_xticklabels(matrix.columns, fontsize=8, rotation=30, ha='right')
            ax_c.set_yticks(range(len(matrix.index)))
            # Truncate institution names
            labels_c = [inst[:30] + '..' if len(inst) > 32 else inst for inst in matrix.index]
            ax_c.set_yticklabels(labels_c, fontsize=7)

            # Annotate cell values
            for i in range(data_c.shape[0]):
                for j in range(data_c.shape[1]):
                    val = int(data_c[i, j])
                    color = 'white' if val > data_c.max() * 0.5 else '#2C3E50'
                    ax_c.text(j, i, str(val), ha='center', va='center',
                              fontsize=8, fontweight='bold', color=color)

            # Highlight target column
            if highlight_target and highlight_target in matrix.columns:
                hl_col = list(matrix.columns).index(highlight_target)
                rect = plt.Rectangle((hl_col - 0.5, -0.5), 1, len(matrix),
                                      linewidth=2, edgecolor=C['ACCENT'],
                                      facecolor='none', linestyle='--')
                ax_c.add_patch(rect)
                # If OFC column is all zeros, annotate
                if matrix[highlight_target].sum() == 0:
                    ax_c.text(hl_col, len(matrix) * 0.5, '0', fontsize=18,
                              color=C['ACCENT'], fontweight='bold', ha='center', va='center',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='#FEF9E7',
                                        edgecolor=C['ACCENT'], linewidth=1.5))

            ax_c.spines['top'].set_visible(False)
            ax_c.spines['right'].set_visible(False)
            ax_c.spines['bottom'].set_visible(False)
            ax_c.spines['left'].set_visible(False)
        ax_c.set_title('C  NIH机构×刺激靶区 (TMS+SCZ)', fontsize=13, fontweight='bold',
                       loc='left', color='#2C3E50')

        # ─── Panel D: 主题象限图 (scatter, compact version) ───
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
                ax_d.scatter(row['centrality'], row['density'], s=row['size'] * 40,
                             c=color, alpha=0.7, edgecolors='white', linewidth=1)
                ax_d.annotate(row['label'], (row['centrality'], row['density']),
                              fontsize=8, fontweight='bold', color='#2C3E50',
                              textcoords='offset points', xytext=(4, 4))

            # Quadrant lines
            med_c = thematic['centrality'].median()
            med_d = thematic['density'].median()
            ax_d.axvline(med_c, color='#CCCCCC', linewidth=1, linestyle='--')
            ax_d.axhline(med_d, color='#CCCCCC', linewidth=1, linestyle='--')

            # Quadrant labels
            xlim = ax_d.get_xlim()
            ylim = ax_d.get_ylim()
            label_props = dict(fontsize=8, alpha=0.4, fontweight='bold', ha='center')
            ax_d.text((xlim[1] + med_c) / 2, (ylim[1] + med_d) / 2, 'Motor',
                      color=C['ACCENT'], **label_props)
            ax_d.text((xlim[0] + med_c) / 2, (ylim[1] + med_d) / 2, 'Niche',
                      color=C['VIOLET'], **label_props)
            ax_d.text((xlim[1] + med_c) / 2, (ylim[0] + med_d) / 2, 'Basic',
                      color=C['INDIGO'], **label_props)
            ax_d.text((xlim[0] + med_c) / 2, (ylim[0] + med_d) / 2, 'Emerging',
                      color=C['SAGE'], **label_props)

            ax_d.set_xlabel('Centrality (外部连接)', fontsize=9)
            ax_d.set_ylabel('Density (内部紧密度)', fontsize=9)
            ax_d.tick_params(labelsize=8)
            ax_d.spines['top'].set_visible(False)
            ax_d.spines['right'].set_visible(False)
        ax_d.set_title('D  PubMed研究主题战略定位', fontsize=13, fontweight='bold',
                       loc='left', color='#2C3E50')

        # Suptitle
        fig.suptitle('附图  文献计量学补充数据  Supplementary Bibliometric Data',
                     fontsize=14, fontweight='bold', color='#2C3E50', y=0.96)

        # Save
        from pathlib import Path
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=300, bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')), bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        print(f"已保存: {out.with_suffix('.pdf')}")
        plt.close()
