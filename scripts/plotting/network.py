"""网络分析可视化 Mixin 模块

提供网络分析的可视化方法，包括：
- 力导向网络图 (plot_network)
- 主题地图 (plot_thematic_map)
- 中心性条形图 (plot_centrality_bar)
- 社区摘要表 (plot_community_summary)
- 网络统计表 (_plot_network_stats)
- 网络分析报告 (create_network_report)

使用方式 (Mixin 模式):
    class LandscapePlot(NetworkPlotMixin, BasePlotMixin):
        pass

依赖:
    - self.C: 色板字典
    - self._save_fig(): 来自 BasePlotMixin
    - matplotlib, networkx, gridspec
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

if TYPE_CHECKING:
    import pandas as pd
    import networkx as nx


class NetworkPlotMixin:
    """
    网络分析可视化方法集 (Mixin 类).

    通过多重继承混入 LandscapePlot，提供网络分析相关的绑制方法。
    要求父类提供 self.C (色板字典) 和 self._save_fig() 方法。

    公开方法:
        - plot_network(): 力导向布局网络图
        - plot_thematic_map(): 四象限主题地图
        - plot_centrality_bar(): 中心性排名条形图
        - plot_community_summary(): 社区摘要表格
        - create_network_report(): 两页网络分析报告
    """

    # ═══════════════════════════════════════════════════════════════════
    # 力导向网络图
    # ═══════════════════════════════════════════════════════════════════

    def plot_network(self, ax, G: 'nx.Graph', title: str = '',
                     community_map: dict | None = None, top_n: int = 60) -> None:
        """
        力导向布局网络图.

        Args:
            ax: matplotlib Axes 对象
            G: networkx Graph 对象
            title: 标题
            community_map: 节点→社区ID 映射，用于着色
            top_n: 只显示 degree 最高的 N 个节点
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

    # ═══════════════════════════════════════════════════════════════════
    # 主题地图
    # ═══════════════════════════════════════════════════════════════════

    def plot_thematic_map(self, ax, thematic_df: 'pd.DataFrame',
                          title: str = '主题地图 Thematic Map') -> None:
        """
        四象限主题地图 (Callon's centrality × density).

        象限定义:
        - Motor (右上): 高中心性 + 高密度
        - Niche (左上): 低中心性 + 高密度
        - Basic (右下): 高中心性 + 低密度
        - Emerging/Declining (左下): 低中心性 + 低密度

        Args:
            ax: matplotlib Axes 对象
            thematic_df: 主题数据 DataFrame (centrality, density, size, label, quadrant)
            title: 标题
        """
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

    # ═══════════════════════════════════════════════════════════════════
    # 中心性条形图
    # ═══════════════════════════════════════════════════════════════════

    def plot_centrality_bar(self, ax, centrality_df: 'pd.DataFrame',
                            title: str = '节点中心性 Top-15') -> None:
        """
        中心性排名条形图.

        Args:
            ax: matplotlib Axes 对象
            centrality_df: 中心性数据 DataFrame (name, degree, betweenness)
            title: 标题
        """
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

    # ═══════════════════════════════════════════════════════════════════
    # 社区摘要表
    # ═══════════════════════════════════════════════════════════════════

    def plot_community_summary(self, ax, communities: dict, G: 'nx.Graph',
                               title: str = '社区结构') -> None:
        """
        社区摘要表格.

        Args:
            ax: matplotlib Axes 对象
            communities: 社区数据 {community_id: [members]}
            G: networkx Graph 对象 (用于获取节点 degree)
            title: 标题
        """
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

    # ═══════════════════════════════════════════════════════════════════
    # 网络统计表
    # ═══════════════════════════════════════════════════════════════════

    def _plot_network_stats(self, ax, stats: dict, title: str = '') -> None:
        """
        网络结构统计摘要表.

        Args:
            ax: matplotlib Axes 对象
            stats: 统计数据字典
            title: 标题
        """
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

    # ═══════════════════════════════════════════════════════════════════
    # 网络分析报告
    # ═══════════════════════════════════════════════════════════════════

    def create_network_report(self, net_data: dict, output: str) -> None:
        """
        生成网络分析报告 (两页).

        Page 1: 社会结构 — PI合作网络 + 机构合作网络
        Page 2: 概念结构 — NSFC关键词网络 + PubMed MeSH网络 + 主题地图

        Args:
            net_data: 网络数据字典，包含:
                - collab_graph, collab_partition, collab_centrality, collab_communities
                - inst_graph
                - network_stats
                - concept_graph, concept_partition, concept_communities
                - mesh_graph, mesh_partition
                - thematic_map, thematic_map_pubmed
            output: 输出路径 (不含扩展名)
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
