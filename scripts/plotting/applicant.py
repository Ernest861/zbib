"""申请人可视化 Mixin 模块

提供申请人前期工作基础的可视化方法，包括：
- 基础 4-panel 图 (时间线、雷达图、期刊分布、代表作)
- 扩展 6-panel 图 (+ 合作网络、研究轨迹)
- 评估总览图 (象限定位 + 六维度雷达)
- 多申请人对比图

使用方式 (Mixin 模式):
    class LandscapePlot(ApplicantPlotMixin, BasePlot):
        pass

依赖:
    - self.C: 色板字典 (来自 colors.py 的 COLORS_GREEN_PURPLE)
    - matplotlib, numpy
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from scripts.journals import TOP_JOURNAL_NAMES

if TYPE_CHECKING:
    from scripts.applicant import ApplicantProfile


class ApplicantPlotMixin:
    """
    申请人可视化方法集 (Mixin 类).

    通过多重继承混入 LandscapePlot，提供申请人相关的所有绑制方法。
    要求父类提供 self.C (色板字典)。

    公开方法:
        - create_applicant_panel(): 嵌入主图的 2×2 子面板
        - create_applicant_figure(): 独立 4-panel 图
        - create_applicant_extended_figure(): 扩展 6-panel 图
        - create_applicant_summary_figure(): 评估总览 (象限+雷达)
        - create_comparison_figure(): 多申请人对比图

    私有绑制方法 (以 _ 开头):
        - _plot_applicant_timeline(): 发文时间线
        - _plot_applicant_radar(): 维度雷达图
        - _plot_applicant_journals(): 期刊分布
        - _plot_applicant_papers(): 代表性论文
        - _plot_collaborator_network(): 合作者网络
        - _plot_research_trajectory(): 研究轨迹
        - _plot_fit_competency_quadrant(): 象限定位图
        - _plot_six_dimension_radar(): 六维度雷达
    """

    # ═══════════════════════════════════════════════════════════════════
    # 嵌入式面板 (用于主图的子网格)
    # ═══════════════════════════════════════════════════════════════════

    def create_applicant_panel(self, fig, gs_spec, profile: 'ApplicantProfile',
                               title: str = '') -> tuple:
        """
        创建申请人前期基础 Panel (2×2 子网格).

        用于嵌入主全景图的 Panel G 位置。

        布局:
        ┌─────────────────┬─────────────────┐
        │ 发文时间线       │ 维度雷达图       │
        ├─────────────────┼─────────────────┤
        │ 期刊分布        │ 代表性论文       │
        └─────────────────┴─────────────────┘

        Args:
            fig: matplotlib Figure 对象
            gs_spec: GridSpec 子区域
            profile: ApplicantProfile 数据对象
            title: Panel 标题 (可选)

        Returns:
            (ax_g1, ax_g2, ax_g3, ax_g4): 四个子图的 Axes 对象
        """
        C = self.C

        gs_g = gridspec.GridSpecFromSubplotSpec(
            2, 2, subplot_spec=gs_spec,
            hspace=0.35, wspace=0.25)

        # ─── G1: 发文时间线 ───
        ax_g1 = fig.add_subplot(gs_g[0, 0])
        ax_g1.set_facecolor(C['BG'])
        self._plot_applicant_timeline(ax_g1, profile)

        # ─── G2: 维度雷达图 ───
        ax_g2 = fig.add_subplot(gs_g[0, 1], polar=True)
        ax_g2.set_facecolor(C['BG'])
        self._plot_applicant_radar(ax_g2, profile)

        # ─── G3: 期刊分布 ───
        ax_g3 = fig.add_subplot(gs_g[1, 0])
        ax_g3.set_facecolor(C['BG'])
        self._plot_applicant_journals(ax_g3, profile)

        # ─── G4: 代表性论文 ───
        ax_g4 = fig.add_subplot(gs_g[1, 1])
        ax_g4.set_facecolor(C['BG'])
        self._plot_applicant_papers(ax_g4, profile)

        # Panel title (on first subplot)
        if title:
            ax_g1.set_title(title, fontsize=13, fontweight='bold',
                           loc='left', color='#2C3E50')

        return ax_g1, ax_g2, ax_g3, ax_g4

    # ═══════════════════════════════════════════════════════════════════
    # 独立图表生成
    # ═══════════════════════════════════════════════════════════════════

    def create_applicant_figure(self, profile: 'ApplicantProfile', output: str,
                                symptoms: dict | None = None,
                                targets: dict | None = None,
                                title: str = '申请人前期工作基础') -> None:
        """
        创建独立的申请人前期基础图 (4-panel).

        输出 PNG 和 PDF 两种格式。

        Args:
            profile: ApplicantProfile 对象
            output: 输出文件路径 (不含扩展名)
            symptoms: 症状维度定义 (保留参数，用于未来扩展)
            targets: 靶区维度定义 (保留参数)
            title: 图表标题
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(12, 8), facecolor=C['BG'])

        # 2×2 布局
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.25,
                               left=0.08, right=0.95, top=0.90, bottom=0.08)

        # ─── Panel 1: 发文时间线 ───
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor(C['BG'])
        self._plot_applicant_timeline(ax1, profile)
        ax1.set_title('发文时间线', fontsize=13, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── Panel 2: 维度雷达图 ───
        ax2 = fig.add_subplot(gs[0, 1], polar=True)
        ax2.set_facecolor(C['BG'])
        self._plot_applicant_radar(ax2, profile)
        ax2.set_title('维度覆盖', fontsize=13, fontweight='bold',
                      loc='left', color='#2C3E50', pad=15)

        # ─── Panel 3: 期刊分布 ───
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_facecolor(C['BG'])
        self._plot_applicant_journals(ax3, profile)
        ax3.set_title('期刊分布', fontsize=13, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── Panel 4: 代表性论文 ───
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_facecolor(C['BG'])
        self._plot_applicant_papers(ax4, profile)
        ax4.set_title('代表性论文', fontsize=13, fontweight='bold',
                      loc='left', color='#2C3E50')

        # Suptitle with applicant info
        h_index_str = ""
        if hasattr(profile, 'h_index_estimate') and profile.h_index_estimate > 0:
            h_index_str = f" | H-index≈{profile.h_index_estimate}"
        suptitle = f'{title}  {profile.name_cn} ({profile.name_en}){h_index_str}'
        fig.suptitle(suptitle, fontsize=16, fontweight='bold',
                     color='#2C3E50', y=0.97)

        # 统计摘要
        n_first_corr = getattr(profile, 'n_first_or_corresponding',
                               profile.n_first_author + profile.n_corresponding)
        n_recent = getattr(profile, 'recent_5yr_count', 0)
        summary_parts = [
            f'总发文: {profile.n_total}',
            f'近5年: {n_recent}' if n_recent > 0 else '',
            f'疾病相关: {profile.n_disease}',
            f'NIBS相关: {profile.n_nibs}',
            f'第一/通讯: {n_first_corr}',
        ]
        summary = ' | '.join([p for p in summary_parts if p])
        fig.text(0.5, 0.01, summary, ha='center', fontsize=10,
                 color='#666', style='italic')

        # Save
        self._save_applicant_figure(fig, output, C)

    def create_applicant_extended_figure(self, profile: 'ApplicantProfile',
                                         output: str,
                                         title: str = '申请人前期工作基础') -> None:
        """
        创建扩展版申请人前期基础图 (6-panel).

        相比基础版增加: 合作者网络、研究轨迹。

        布局 (3×2):
        ┌─────────────────┬─────────────────┐
        │ 发文时间线       │ 维度雷达图       │
        ├─────────────────┼─────────────────┤
        │ 期刊分布        │ 代表性论文       │
        ├─────────────────┼─────────────────┤
        │ 合作者网络      │ 研究轨迹        │
        └─────────────────┴─────────────────┘

        Args:
            profile: ApplicantProfile 对象
            output: 输出文件路径 (不含扩展名)
            title: 图表标题
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        # ═══════════════════════════════════════════════════════════════
        # Page 1: 基础 4-panel (8×6 英寸，符合出版标准)
        # ═══════════════════════════════════════════════════════════════
        fig1 = plt.figure(figsize=(8, 6), facecolor=C['BG'])

        gs1 = gridspec.GridSpec(2, 2, figure=fig1, hspace=0.35, wspace=0.30,
                                left=0.08, right=0.95, top=0.88, bottom=0.08)

        # ─── A: 发文时间线 ───
        ax1 = fig1.add_subplot(gs1[0, 0])
        ax1.set_facecolor(C['BG'])
        self._plot_applicant_timeline(ax1, profile)
        ax1.set_title('A  发文时间线', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── B: 维度雷达图 ───
        ax2 = fig1.add_subplot(gs1[0, 1], polar=True)
        ax2.set_facecolor(C['BG'])
        self._plot_applicant_radar(ax2, profile)
        ax2.set_title('B  维度覆盖', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50', pad=10)

        # ─── C: 期刊分布 ───
        ax3 = fig1.add_subplot(gs1[1, 0])
        ax3.set_facecolor(C['BG'])
        self._plot_applicant_journals(ax3, profile)
        ax3.set_title('C  期刊分布', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── D: 代表性论文 ───
        ax4 = fig1.add_subplot(gs1[1, 1])
        ax4.set_facecolor(C['BG'])
        self._plot_applicant_papers(ax4, profile)
        ax4.set_title('D  代表性论文', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50')

        # Suptitle
        h_str = f" H≈{profile.h_index_estimate}" if profile.h_index_estimate > 0 else ""
        suptitle = f'{profile.name_cn} ({profile.name_en}){h_str} | 评分: {profile.relevance_score:.0f}/100'
        fig1.suptitle(suptitle, fontsize=9, fontweight='bold',
                      color='#2C3E50', y=0.96)

        # 底部摘要
        tier1 = getattr(profile, 'tier1_count', profile.top_journal_count)
        summary = f'总: {profile.n_total} | 疾病: {profile.n_disease} | NIBS: {profile.n_nibs} | 独立: {profile.n_first_or_corresponding} | 顶刊: {tier1}'
        fig1.text(0.5, 0.02, summary, ha='center', fontsize=7, color='#666')

        # Save Page 1
        self._save_applicant_figure(fig1, output, C, suffix='_extended_p1')

        # ═══════════════════════════════════════════════════════════════
        # Page 2: 补充 2-panel (8×4 英寸)
        # ═══════════════════════════════════════════════════════════════
        fig2 = plt.figure(figsize=(8, 4), facecolor=C['BG'])

        gs2 = gridspec.GridSpec(1, 2, figure=fig2, wspace=0.25,
                                left=0.06, right=0.95, top=0.85, bottom=0.10)

        # ─── E: 合作网络 ───
        ax5 = fig2.add_subplot(gs2[0, 0])
        self._plot_collaborator_network(ax5, profile)
        ax5.set_title('E  合作网络', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── F: 研究轨迹 ───
        ax6 = fig2.add_subplot(gs2[0, 1])
        ax6.set_facecolor(C['BG'])
        self._plot_research_trajectory(ax6, profile)
        ax6.set_title('F  研究轨迹', fontsize=8, fontweight='bold',
                      loc='left', color='#2C3E50')

        fig2.suptitle(f'{profile.name_cn} — 合作与演进', fontsize=9,
                      fontweight='bold', color='#2C3E50', y=0.95)

        # Save Page 2
        self._save_applicant_figure(fig2, output, C, suffix='_extended_p2')

    def create_applicant_summary_figure(self, profile: 'ApplicantProfile',
                                        output: str,
                                        title: str = '申报者评估总览') -> None:
        """
        创建申报者评估总览图 (象限定位 + 六维度雷达).

        用于快速展示申请人的适配度×胜任力定位和各维度得分。

        布局 (1×2):
        ┌─────────────────┬─────────────────┐
        │ 象限定位图       │ 六维度雷达图     │
        └─────────────────┴─────────────────┘

        Args:
            profile: ApplicantProfile 对象
            output: 输出文件路径
            title: 图表标题
        """
        C = self.C
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(12, 5), facecolor=C['BG'])

        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.25,
                               left=0.08, right=0.95, top=0.85, bottom=0.12)

        # ─── 左: 象限图 ───
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor(C['BG'])
        self._plot_fit_competency_quadrant(ax1, profile)
        ax1.set_title('A  适配度 × 胜任力定位', fontsize=12, fontweight='bold',
                      loc='left', color='#2C3E50')

        # ─── 右: 六维度雷达 ───
        ax2 = fig.add_subplot(gs[0, 1], polar=True)
        ax2.set_facecolor(C['BG'])
        self._plot_six_dimension_radar(ax2, profile)
        ax2.set_title('B  六维度评分', fontsize=12, fontweight='bold',
                      loc='left', color='#2C3E50', pad=15)

        # Suptitle
        fit = getattr(profile, 'fit_score', 0)
        comp = getattr(profile, 'competency_score', 0)
        total = profile.relevance_score
        suptitle = f'{title}  {profile.name_cn} ({profile.name_en})'
        suptitle += f'  |  适配度: {fit:.0f}  胜任力: {comp:.0f}  综合: {total:.0f}'
        fig.suptitle(suptitle, fontsize=13, fontweight='bold',
                     color='#2C3E50', y=0.97)

        # Save
        self._save_applicant_figure(fig, output, C, suffix='_summary')

    # ═══════════════════════════════════════════════════════════════════
    # 多申请人对比
    # ═══════════════════════════════════════════════════════════════════

    def create_comparison_figure(self, profiles: list['ApplicantProfile'],
                                 output: str,
                                 title: str = '申请人对比分析') -> None:
        """
        生成多申请人对比图 (2×2 layout).

        四个面板分别展示:
        - A: 多人六维雷达叠加
        - B: 适配度×胜任力象限散点
        - C: 核心指标柱状对比
        - D: 百分位排名热力图

        Args:
            profiles: ApplicantProfile 对象列表
            output: 输出路径 (不含扩展名)
            title: 图表标题
        """
        C = self.C
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.97)

        self._plot_comparison_radar(axes[0, 0], profiles)
        self._plot_comparison_quadrant(axes[0, 1], profiles)
        self._plot_comparison_bars(axes[1, 0], profiles)
        self._plot_comparison_percentiles(axes[1, 1], profiles)

        plt.tight_layout(rect=[0, 0, 1, 0.94])

        for ext in ('png', 'pdf'):
            fig.savefig(f"{output}.{ext}", dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"[Plot] 对比图 → {output}.png/pdf")

    # ═══════════════════════════════════════════════════════════════════
    # 私有绑制方法: 基础面板
    # ═══════════════════════════════════════════════════════════════════

    def _plot_applicant_timeline(self, ax, profile: 'ApplicantProfile') -> None:
        """
        发文时间线: 年度发文柱状图 + 累计折线.

        双 Y 轴设计:
        - 左轴 (蓝色): 年度发文量柱状图
        - 右轴 (红色): 累计发文折线图

        Args:
            ax: matplotlib Axes 对象
            profile: ApplicantProfile 数据
        """
        C = self.C

        if profile.year_counts.empty:
            ax.text(0.5, 0.5, '无发表数据', ha='center', va='center',
                    fontsize=10, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        years = profile.year_counts.index.tolist()
        counts = profile.year_counts.values.tolist()

        # 柱状图
        ax.bar(years, counts, color=C['INDIGO'], alpha=0.7,
               width=0.8, edgecolor='white')

        # 累计折线 (右轴)
        ax2 = ax.twinx()
        cumsum = np.cumsum(counts)
        ax2.plot(years, cumsum, 'o-', color=C['ACCENT'],
                 linewidth=2, markersize=4)

        ax.set_xlabel('Year', fontsize=7)
        ax.set_ylabel('年发文量', fontsize=7, color=C['INDIGO'])
        ax2.set_ylabel('累计', fontsize=7, color=C['ACCENT'])

        ax.tick_params(axis='both', labelsize=6)
        ax2.tick_params(axis='y', labelsize=6, labelcolor=C['ACCENT'])
        ax.tick_params(axis='y', labelcolor=C['INDIGO'])

        ax.spines['top'].set_visible(False)
        ax2.spines['top'].set_visible(False)

        # 标注统计信息
        stats_text = f'N={profile.n_total}'
        if hasattr(profile, 'recent_5yr_count') and profile.recent_5yr_count > 0:
            stats_text += f' 近5年={profile.recent_5yr_count}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=6, va='top', fontweight='bold', color='#2C3E50')

    def _plot_applicant_radar(self, ax, profile: 'ApplicantProfile') -> None:
        """
        维度雷达图: 症状×靶区覆盖.

        自动合并 symptom_coverage 和 target_coverage，
        若维度不足 3 个则补充基础指标。

        Args:
            ax: 极坐标 Axes (polar=True)
            profile: ApplicantProfile 数据
        """
        C = self.C

        # 合并症状和靶区覆盖
        categories = []
        values = []
        for name, count in sorted(profile.symptom_coverage.items(),
                                  key=lambda x: -x[1]):
            categories.append(f'症:{name[:6]}')
            values.append(count)
        for name, count in sorted(profile.target_coverage.items(),
                                  key=lambda x: -x[1]):
            categories.append(f'靶:{name[:6]}')
            values.append(count)

        if len(categories) < 3:
            # 雷达图需要至少3个维度，添加基础指标
            categories.extend(['疾病相关', 'NIBS相关', '第一作者'])
            values.extend([profile.n_disease, profile.n_nibs, profile.n_first_author])

        # 截取前8个
        if len(categories) > 8:
            categories = categories[:8]
            values = values[:8]

        n = len(categories)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        values = values + [values[0]]  # 闭合
        angles = angles + [angles[0]]

        # 归一化
        max_val = max(values) if max(values) > 0 else 1
        values_norm = [v / max_val for v in values]

        ax.plot(angles, values_norm, 'o-', color=C['ACCENT'],
                linewidth=2, markersize=5)
        ax.fill(angles, values_norm, color=C['ACCENT'], alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=6)
        ax.set_ylim(0, 1.15)
        ax.tick_params(axis='y', labelsize=5)

        # 显示原始数值
        for ang, val, norm in zip(angles[:-1], values[:-1], values_norm[:-1]):
            ax.text(ang, norm + 0.12, str(val), ha='center', va='bottom',
                    fontsize=6, fontweight='bold', color='#2C3E50')

    def _plot_applicant_journals(self, ax, profile: 'ApplicantProfile',
                                 top_n: int = 8) -> None:
        """
        期刊分布: 水平柱状图.

        顶刊用强调色高亮。

        Args:
            ax: matplotlib Axes
            profile: ApplicantProfile 数据
            top_n: 显示前 N 个期刊
        """
        C = self.C

        if not profile.journal_counts:
            ax.text(0.5, 0.5, '无期刊数据', ha='center', va='center',
                    fontsize=10, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        # 取 top_n
        journals = list(profile.journal_counts.keys())[:top_n][::-1]
        counts = list(profile.journal_counts.values())[:top_n][::-1]

        y_pos = np.arange(len(journals))
        colors = [C['ACCENT'] if j in TOP_JOURNAL_NAMES else C['SLATE']
                  for j in journals]

        ax.barh(y_pos, counts, color=colors, edgecolor='white',
                height=0.7, alpha=0.85)

        max_cnt = max(counts) if counts else 1
        for i, (j, cnt) in enumerate(zip(journals, counts)):
            jname = j[:18] + '..' if len(j) > 18 else j
            ax.text(cnt + max_cnt * 0.02, i, str(cnt), va='center',
                    fontsize=6, fontweight='bold', color='#2C3E50')
            ax.text(-max_cnt * 0.02, i, jname, va='center', ha='right',
                    fontsize=6, color='#2C3E50')

        ax.set_yticks([])
        ax.set_xlim(0, max_cnt * 1.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='x', labelsize=6)
        ax.set_xlabel('N', fontsize=7)

        # 顶刊统计
        if profile.top_journal_count > 0:
            ax.text(0.98, 0.98, f'顶刊: {profile.top_journal_count}',
                    transform=ax.transAxes, fontsize=6, ha='right', va='top',
                    fontweight='bold', color=C['ACCENT'])

    def _plot_applicant_papers(self, ax, profile: 'ApplicantProfile') -> None:
        """
        代表性论文列表 + 统计摘要.

        显示 profile.key_papers 中的前 4 篇代表作，
        底部添加统计摘要和相关度评分。

        Args:
            ax: matplotlib Axes
            profile: ApplicantProfile 数据
        """
        C = self.C
        ax.axis('off')

        if not profile.key_papers:
            ax.text(0.5, 0.5, '无代表性论文', ha='center', va='center',
                    fontsize=10, color='#999', transform=ax.transAxes)
            return

        y_start = 0.92
        # 只显示3篇，增加间距避免遮挡
        for i, paper in enumerate(profile.key_papers[:3]):
            y = y_start - i * 0.24

            # 编号
            ax.text(0.02, y, f'{i+1}.', transform=ax.transAxes, fontsize=7,
                    fontweight='bold', color=C['ACCENT'], va='top')

            # 年份+期刊 (缩短)
            year = paper.get('year', '')
            journal = paper.get('journal', '')[:12]
            ax.text(0.06, y, f'[{year}] {journal}', transform=ax.transAxes,
                    fontsize=6, fontweight='bold', color=C['INDIGO'], va='top')

            # 标题 (截断更短)
            title = paper.get('title', '')[:35]
            if len(paper.get('title', '')) > 35:
                title += '...'
            ax.text(0.06, y - 0.08, title, transform=ax.transAxes,
                    fontsize=6, color='#2C3E50', va='top')

        # 相关度评分
        ax.text(0.50, 0.05, f'评分: {profile.relevance_score:.0f}/100',
                transform=ax.transAxes, fontsize=7, ha='center', va='bottom',
                fontweight='bold', color=C['ACCENT'],
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#FEF9E7',
                          edgecolor=C['WARN'], linewidth=0.5))

    # ═══════════════════════════════════════════════════════════════════
    # 私有绑制方法: 扩展面板
    # ═══════════════════════════════════════════════════════════════════

    def _plot_collaborator_network(self, ax, profile: 'ApplicantProfile') -> None:
        """
        合作者网络可视化 (圆形布局散点图).

        申请人居中 (星形标记)，合作者按合作频次排列。
        节点大小反映合作次数。

        Args:
            ax: matplotlib Axes
            profile: ApplicantProfile 数据
        """
        C = self.C
        ax.set_facecolor(C['BG'])

        if not profile.top_collaborators:
            ax.text(0.5, 0.5, '无合作者数据', ha='center', va='center',
                    fontsize=10, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        # 准备数据 (限制8人避免遮挡)
        collaborators = profile.top_collaborators[:8]
        # 仅显示姓氏 (取最后一个空格后的部分)
        names = [c[0].split()[-1][:10] if ' ' in c[0] else c[0][:10] for c in collaborators]
        counts = [c[1] for c in collaborators]

        # 圆形布局 (从顶部开始，顺时针)
        n = len(names)
        angles = np.linspace(np.pi/2, np.pi/2 - 2*np.pi, n, endpoint=False)
        x = np.cos(angles)
        y = np.sin(angles)

        # 节点大小按合作次数
        max_count = max(counts) if counts else 1
        sizes = [100 + 300 * (c / max_count) for c in counts]

        # 绘制边 (合作关系)
        collaborator_graph = getattr(profile, 'collaborator_graph', {})
        for i, name_i in enumerate(names):
            full_name_i = collaborators[i][0]
            if full_name_i in collaborator_graph:
                for j, name_j in enumerate(names):
                    full_name_j = collaborators[j][0]
                    if full_name_j in collaborator_graph.get(full_name_i, []):
                        ax.plot([x[i], x[j]], [y[i], y[j]],
                                color='#BDC3C7', alpha=0.4, linewidth=1, zorder=1)

        # 绘制节点
        ax.scatter(x, y, s=sizes, c=counts, cmap='Blues',
                   edgecolor='white', linewidth=1.5, alpha=0.85, zorder=2)

        # 标签 (单行显示避免遮挡)
        for i, (xi, yi, name, count) in enumerate(zip(x, y, names, counts)):
            offset = 0.22
            label_x = xi * (1 + offset)
            label_y = yi * (1 + offset)
            ha = 'left' if xi >= 0 else 'right'
            # 单行格式: 姓名(次数)
            ax.text(label_x, label_y, f'{name}({count})', fontsize=6,
                    ha=ha, va='center', color='#2C3E50')

        # 中心标注申请人
        ax.scatter([0], [0], s=150, c=[C['ACCENT']], edgecolor='white',
                   linewidth=1.5, zorder=3, marker='*')
        ax.text(0, 0.18, profile.name_en.split()[-1], fontsize=7, fontweight='bold',
                ha='center', va='bottom', color=C['ACCENT'])

        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis('off')

    def _plot_research_trajectory(self, ax, profile: 'ApplicantProfile') -> None:
        """
        研究轨迹可视化: 关键词流图.

        按时期展示研究方向的演变，从早期到近期用颜色渐变表示。

        Args:
            ax: matplotlib Axes
            profile: ApplicantProfile 数据
        """
        C = self.C
        ax.set_facecolor(C['BG'])

        trajectory = profile.research_trajectory
        if not trajectory:
            ax.text(0.5, 0.5, '无轨迹数据', ha='center', va='center',
                    fontsize=10, color='#999', transform=ax.transAxes)
            ax.axis('off')
            return

        periods = list(trajectory.keys())
        n_periods = len(periods)

        # 颜色渐变
        colors = plt.cm.Blues(np.linspace(0.3, 0.8, n_periods))

        y_offset = 0
        for i, (period, keywords) in enumerate(trajectory.items()):
            # 时期标签
            ax.text(0.02, 0.92 - y_offset, f'◆ {period}', transform=ax.transAxes,
                    fontsize=7, fontweight='bold', color=colors[i], va='top')

            # 关键词 (限制3个避免遮挡)
            kw_text = ' → '.join(keywords[:3])
            ax.text(0.02, 0.92 - y_offset - 0.10, kw_text, transform=ax.transAxes,
                    fontsize=6, color='#2C3E50', va='top', style='italic')

            y_offset += 0.30

        # 添加趋势箭头
        if n_periods > 1:
            ax.annotate('', xy=(0.95, 0.15), xytext=(0.95, 0.85),
                        xycoords='axes fraction',
                        arrowprops=dict(arrowstyle='->', color=C['ACCENT'],
                                        lw=1.5, mutation_scale=12))
            ax.text(0.98, 0.5, '演进', transform=ax.transAxes, fontsize=6,
                    rotation=-90, va='center', ha='left', color=C['ACCENT'])

        ax.axis('off')

    # ═══════════════════════════════════════════════════════════════════
    # 私有绘制方法: 评估可视化
    # ═══════════════════════════════════════════════════════════════════

    def _plot_fit_competency_quadrant(self, ax, profile: 'ApplicantProfile') -> None:
        """
        适配度×胜任力象限图.

        四象限:
        - 右上 (绿): 明星申请人 (fit≥60, comp≥60)
        - 左上 (蓝): 跨界申请人 (fit<60, comp≥60)
        - 右下 (黄): 潜力申请人 (fit≥60, comp<60)
        - 左下 (灰): 成长型申请人 (fit<60, comp<60)

        Args:
            ax: matplotlib Axes
            profile: ApplicantProfile 数据
        """
        C = self.C
        ax.set_facecolor(C['BG'])

        fit = getattr(profile, 'fit_score', 50)
        comp = getattr(profile, 'competency_score', 50)

        # 绘制象限背景
        ax.fill([60, 100, 100, 60], [60, 60, 100, 100], color='#E8F8E8', alpha=0.5)
        ax.fill([0, 60, 60, 0], [60, 60, 100, 100], color='#E8F0F8', alpha=0.5)
        ax.fill([60, 100, 100, 60], [0, 0, 60, 60], color='#FFF8E8', alpha=0.5)
        ax.fill([0, 60, 60, 0], [0, 0, 60, 60], color='#F5F5F5', alpha=0.5)

        # 绘制分界线
        ax.axhline(y=60, color='#BDC3C7', linestyle='--', linewidth=1)
        ax.axvline(x=60, color='#BDC3C7', linestyle='--', linewidth=1)

        # 象限标签
        ax.text(80, 85, '明星申请人', ha='center', va='center', fontsize=9,
                fontweight='bold', color='#27AE60', alpha=0.7)
        ax.text(30, 85, '跨界申请人', ha='center', va='center', fontsize=9,
                fontweight='bold', color='#3498DB', alpha=0.7)
        ax.text(80, 30, '潜力申请人', ha='center', va='center', fontsize=9,
                fontweight='bold', color='#F39C12', alpha=0.7)
        ax.text(30, 30, '成长型', ha='center', va='center', fontsize=9,
                fontweight='bold', color='#95A5A6', alpha=0.7)

        # 绘制申请人位置
        ax.scatter([fit], [comp], s=300, c=[C['ACCENT']], edgecolor='white',
                   linewidth=3, zorder=10, marker='*')

        # 标注分数
        name = profile.name_cn or profile.name_en.split()[-1]
        ax.annotate(f'{name}\n({fit:.0f}, {comp:.0f})',
                    xy=(fit, comp), xytext=(fit + 8, comp + 8),
                    fontsize=9, fontweight='bold', color='#2C3E50',
                    arrowprops=dict(arrowstyle='->', color='#2C3E50', lw=1),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor=C['ACCENT'], alpha=0.9))

        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_xlabel('适配度', fontsize=10, fontweight='bold')
        ax.set_ylabel('胜任力', fontsize=10, fontweight='bold')
        ax.tick_params(axis='both', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def _plot_six_dimension_radar(self, ax, profile: 'ApplicantProfile') -> None:
        """
        六维度雷达图 (适配度3维 + 胜任力3维).

        维度:
        - 适配度 (蓝线): 疾病领域、技术方法、交叉经验
        - 胜任力 (绿线): 学术独立、学术影响、研究活跃

        Args:
            ax: 极坐标 Axes (polar=True)
            profile: ApplicantProfile 数据
        """
        C = self.C
        breakdown = profile.get_score_breakdown()

        categories = ['疾病领域', '技术方法', '交叉经验',
                      '学术独立', '学术影响', '研究活跃']
        values = [
            breakdown.get('disease_raw', 0),
            breakdown.get('nibs_raw', 0),
            breakdown.get('crossover_raw', 0),
            breakdown.get('independence_raw', 0),
            breakdown.get('impact_raw', 0),
            breakdown.get('activity_raw', 0),
        ]

        n = len(categories)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        values = values + [values[0]]
        angles = angles + [angles[0]]

        values_norm = [v / 100 for v in values]

        ax.plot(angles, values_norm, 'o-', color=C['ACCENT'],
                linewidth=2, markersize=6)
        ax.fill(angles, values_norm, color=C['ACCENT'], alpha=0.25)

        # 适配度/胜任力分段线
        ax.plot(angles[:4], values_norm[:4], color='#3498DB',
                linewidth=3, alpha=0.7)
        ax.plot(angles[3:], values_norm[3:], color='#27AE60',
                linewidth=3, alpha=0.7)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=9)
        ax.set_ylim(0, 1.1)

        # 显示原始分值
        for ang, val in zip(angles[:-1], values[:-1]):
            val_norm = val / 100
            ax.text(ang, val_norm + 0.08, f'{val:.0f}', ha='center', va='bottom',
                    fontsize=8, fontweight='bold', color='#2C3E50')

        ax.text(0.5, -0.15, '蓝=适配度  绿=胜任力', transform=ax.transAxes,
                ha='center', fontsize=8, color='#666')

    # ═══════════════════════════════════════════════════════════════════
    # 私有绘制方法: 多申请人对比
    # ═══════════════════════════════════════════════════════════════════

    def _plot_comparison_radar(self, ax, profiles: list['ApplicantProfile']) -> None:
        """多人六维雷达叠加"""
        categories = ['疾病领域', '技术方法', '交叉经验',
                      '学术独立', '学术影响', '研究活跃']
        n = len(categories)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        angles += [angles[0]]

        colors = ['#3498DB', '#E74C3C', '#27AE60', '#F39C12', '#9B59B6']

        ax.remove()
        ax_polar = ax.figure.add_subplot(2, 2, 1, polar=True)

        for i, p in enumerate(profiles):
            breakdown = p.get_score_breakdown()
            values = [
                breakdown.get('disease_raw', 0),
                breakdown.get('nibs_raw', 0),
                breakdown.get('crossover_raw', 0),
                breakdown.get('independence_raw', 0),
                breakdown.get('impact_raw', 0),
                breakdown.get('activity_raw', 0),
            ]
            values_norm = [v / 100 for v in values] + [values[0] / 100]

            color = colors[i % len(colors)]
            name = p.name_cn or p.name_en
            ax_polar.plot(angles, values_norm, 'o-', color=color, linewidth=2,
                          markersize=5, label=name)
            ax_polar.fill(angles, values_norm, color=color, alpha=0.1)

        ax_polar.set_xticks(angles[:-1])
        ax_polar.set_xticklabels(categories, fontsize=9)
        ax_polar.set_ylim(0, 1.15)
        ax_polar.legend(loc='upper right', fontsize=8, bbox_to_anchor=(1.3, 1.1))
        ax_polar.set_title('六维能力对比', fontsize=12, pad=15)

    def _plot_comparison_quadrant(self, ax, profiles: list['ApplicantProfile']) -> None:
        """适配度×胜任力象限散点"""
        colors = ['#3498DB', '#E74C3C', '#27AE60', '#F39C12', '#9B59B6']

        ax.axhline(y=60, color='#BDC3C7', linestyle='--', alpha=0.7)
        ax.axvline(x=60, color='#BDC3C7', linestyle='--', alpha=0.7)

        ax.fill_between([60, 105], 60, 105, color='#27AE60', alpha=0.06)
        ax.fill_between([0, 60], 60, 105, color='#3498DB', alpha=0.06)
        ax.fill_between([60, 105], 0, 60, color='#F39C12', alpha=0.06)
        ax.fill_between([0, 60], 0, 60, color='#E74C3C', alpha=0.06)

        ax.text(82, 95, '明星', fontsize=10, ha='center', color='#27AE60', alpha=0.5)
        ax.text(30, 95, '跨界', fontsize=10, ha='center', color='#3498DB', alpha=0.5)
        ax.text(82, 15, '潜力', fontsize=10, ha='center', color='#F39C12', alpha=0.5)
        ax.text(30, 15, '成长', fontsize=10, ha='center', color='#E74C3C', alpha=0.5)

        for i, p in enumerate(profiles):
            fit = p.fit_score
            comp = p.competency_score
            name = p.name_cn or p.name_en
            color = colors[i % len(colors)]
            ax.scatter(fit, comp, s=200, c=color, zorder=5,
                       edgecolors='white', linewidths=2)
            ax.annotate(name, (fit, comp), textcoords="offset points",
                        xytext=(8, 8), fontsize=10, fontweight='bold', color=color)

        ax.set_xlabel('适配度', fontsize=11)
        ax.set_ylabel('胜任力', fontsize=11)
        ax.set_xlim(0, 105)
        ax.set_ylim(0, 105)
        ax.set_title('适配度 × 胜任力象限', fontsize=12)

    def _plot_comparison_bars(self, ax, profiles: list['ApplicantProfile']) -> None:
        """核心指标柱状对比"""
        metrics = ['总文献', '疾病相关', 'NIBS', '第一/通讯', '顶刊', '近5年']
        x = np.arange(len(metrics))
        width = 0.8 / max(len(profiles), 1)
        colors = ['#3498DB', '#E74C3C', '#27AE60', '#F39C12', '#9B59B6']

        for i, p in enumerate(profiles):
            values = [p.n_total, p.n_disease, p.n_nibs,
                      p.n_first_or_corresponding, p.tier1_count, p.recent_5yr_count]
            name = p.name_cn or p.name_en
            offset = (i - len(profiles) / 2 + 0.5) * width
            bars = ax.bar(x + offset, values, width * 0.9,
                          label=name, color=colors[i % len(colors)], alpha=0.8)
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                            str(val), ha='center', va='bottom', fontsize=7)

        ax.set_xticks(x)
        ax.set_xticklabels(metrics, fontsize=9)
        ax.legend(fontsize=8)
        ax.set_title('核心指标对比', fontsize=12)

    def _plot_comparison_percentiles(self, ax,
                                     profiles: list['ApplicantProfile']) -> None:
        """百分位排名热力图"""
        metrics = ['n_total', 'recent_5yr', 'h_index', 'independence',
                   'tier1', 'total_if', 'fit', 'competency', 'total_score']
        labels = ['发文量', '近5年', 'H-index', '独立性',
                  '顶刊', '累计IF', '适配度', '胜任力', '综合分']

        names = [p.name_cn or p.name_en for p in profiles]
        data = []
        for p in profiles:
            ranks = getattr(p, 'percentile_ranks', {})
            row = [ranks.get(m, 50) for m in metrics]
            data.append(row)

        if not data:
            ax.text(0.5, 0.5, '无基准数据', ha='center', va='center',
                    transform=ax.transAxes)
            return

        data_arr = np.array(data)
        im = ax.imshow(data_arr, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, fontsize=8, rotation=45, ha='right')
        ax.set_yticks(np.arange(len(names)))
        ax.set_yticklabels(names, fontsize=10)

        for i in range(len(names)):
            for j in range(len(labels)):
                val = data_arr[i, j]
                color = 'white' if val < 30 or val > 80 else 'black'
                ax.text(j, i, f'P{val:.0f}', ha='center', va='center',
                        fontsize=8, fontweight='bold', color=color)

        ax.set_title('领域基准百分位排名', fontsize=12)
        fig = ax.figure
        fig.colorbar(im, ax=ax, label='百分位', shrink=0.8)

    # ═══════════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════════

    def _save_applicant_figure(self, fig, output: str, C: dict,
                               suffix: str = '') -> None:
        """保存申请人图表为 PNG 和 PDF"""
        out = Path(output)
        base = out.with_suffix('')
        if suffix:
            base = Path(str(base) + suffix)

        fig.savefig(str(base.with_suffix('.png')), dpi=300,
                    bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(base.with_suffix('.pdf')),
                    bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {base.with_suffix('.png')}")
        print(f"已保存: {base.with_suffix('.pdf')}")
        plt.close()
