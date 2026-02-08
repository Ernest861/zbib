"""关键词/时序分析可视化 Mixin 模块

提供关键词分析和时序网络的可视化方法，包括：
- 共现网络演变 (plot_temporal_network)
- 关键词预测 (plot_keyword_prediction)
- 主题地图 (plot_thematic_map_temporal)
- 新兴关键词 (plot_emerging_keywords)
- 关键词轨迹 (plot_keyword_trajectories)
- 社区演变 (plot_community_evolution)
- 关键词地形图 (plot_keyword_landscape)
- 关键词热力图 (plot_keyword_heatmap)
- 共现矩阵 (plot_cooccurrence_matrix)
- 关键词流图 (plot_keyword_flow)
- 雷达对比 (plot_radar_comparison)
- 研究前沿 (plot_research_frontier)
- 词云演变 (plot_wordcloud_evolution)
- 演变摘要 (plot_evolution_summary)

使用方式 (Mixin 模式):
    class LandscapePlot(KeywordPlotMixin, ApplicantPlotMixin, BasePlot):
        pass

依赖:
    - self.C: 色板字典
    - matplotlib, numpy, networkx
    - 可选: community (python-louvain), wordcloud
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import pandas as pd


class KeywordPlotMixin:
    """
    关键词/时序分析可视化方法集 (Mixin 类).

    通过多重继承混入 LandscapePlot，提供关键词和时序分析相关的绑制方法。
    要求父类提供 self.C (色板字典)。

    公开方法:
        - plot_temporal_network(): 共现网络演变
        - plot_keyword_prediction(): 关键词预测
        - plot_thematic_map_temporal(): 主题地图演变
        - plot_emerging_keywords(): 新兴/衰退关键词
        - plot_keyword_trajectories(): 关键词增长轨迹
        - plot_community_evolution(): 社区演变
        - plot_keyword_landscape(): 关键词地形图
        - plot_keyword_heatmap(): 时序热力图
        - plot_cooccurrence_matrix(): 共现矩阵
        - plot_keyword_flow(): Sankey 流图
        - plot_radar_comparison(): 雷达对比
        - plot_research_frontier(): 研究前沿
        - plot_wordcloud_evolution(): 词云演变
        - plot_evolution_summary(): 演变摘要
    """

    # ═══════════════════════════════════════════════════════════════════
    # 共现网络与社区分析
    # ═══════════════════════════════════════════════════════════════════

    def plot_temporal_network(self, temporal: list, output: str,
                              title: str = '共现网络演变') -> None:
        """
        绑制每个时间窗口的共现网络子图.

        Args:
            temporal: 时间切片列表，每项含 {'period', 'graph', 'n_nodes', 'n_edges'}
            output: 输出文件路径 (不含扩展名)
            title: 图表标题

        Note:
            使用 spring_layout 布局，节点大小反映度数，
            颜色基于 Louvain 社区检测 (需安装 python-louvain)。
        """
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

            # 限制节点数
            top_n_nodes = min(35, len(G))
            if len(G) > top_n_nodes:
                top_nodes = sorted(G.nodes(), key=lambda nd: G.degree(nd),
                                   reverse=True)[:top_n_nodes]
                G = G.subgraph(top_nodes).copy()

            if len(G) == 0:
                ax.text(0.5, 0.5, '节点不足', ha='center', va='center',
                        transform=ax.transAxes)
                ax.set_title(snap['period'], fontsize=14, fontweight='bold')
                ax.axis('off')
                continue

            pos = nx.spring_layout(G, k=1.5 / max(len(G) ** 0.5, 1),
                                   iterations=50, seed=42)

            # 社区检测
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
                comm_ids = sorted(set(partition.values()))
                cmap = {cid: palette[i % len(palette)] for i, cid in enumerate(comm_ids)}
                colors = [cmap.get(partition.get(nd, 0), '#999') for nd in G.nodes()]
            except ImportError:
                colors = [C['INDIGO']] * len(G)

            # 边权重筛选
            edge_w = [G[u][v].get('weight', 1) for u, v in G.edges()]
            max_ew = max(edge_w) if edge_w else 1
            if len(edge_w) > 50:
                cutoff = sorted(edge_w)[int(len(edge_w) * 0.7)]
                edge_list = [(u, v) for u, v in G.edges()
                             if G[u][v].get('weight', 1) >= cutoff]
            else:
                edge_list = list(G.edges())
            filtered_w = [G[u][v].get('weight', 1) for u, v in edge_list]
            widths = [0.3 + 1.8 * w / max_ew for w in filtered_w]

            # 节点大小
            degrees = [G.degree(nd) for nd in G.nodes()]
            max_d = max(degrees) if degrees and max(degrees) > 0 else 1
            sizes = [80 + 350 * d / max_d for d in degrees]

            nx.draw_networkx_edges(G, pos, edgelist=edge_list, ax=ax, width=widths,
                                   alpha=0.15, edge_color='#999999')
            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes, node_color=colors,
                                   alpha=0.85, edgecolors='white', linewidths=0.5)

            # 标签
            n_labels = min(6, len(G))
            threshold = sorted(degrees, reverse=True)[n_labels - 1]
            labels = {nd: nd for nd in G.nodes() if G.degree(nd) >= threshold}
            labels = {nd: (lbl[:12] + '..' if len(lbl) > 14 else lbl)
                      for nd, lbl in labels.items()}
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

        self._save_keyword_figure(fig, output, C)

    def plot_community_evolution(self, temporal: list, output: str,
                                 title: str = '社区规模演变') -> None:
        """
        绘制社区规模随时间的堆叠面积图.

        Args:
            temporal: 时间切片列表
            output: 输出路径
            title: 标题
        """
        # 实现保留在 plot.py，此处为接口声明
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 关键词趋势分析
    # ═══════════════════════════════════════════════════════════════════

    def plot_keyword_prediction(self, predictions_nsfc: dict,
                                predictions_nih: dict,
                                output: str, top_k: int = 8) -> None:
        """
        双栏预测图: NSFC 左侧, NIH 右侧.

        Args:
            predictions_nsfc: NSFC 预测结果 {keyword: {'trend', 'growth', ...}}
            predictions_nih: NIH 预测结果
            output: 输出路径
            top_k: 显示前 K 个关键词
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_emerging_keywords(self, emerging_nsfc: 'pd.DataFrame',
                               emerging_nih: 'pd.DataFrame',
                               output: str) -> None:
        """
        双栏水平条形图显示新兴关键词.

        按 growth 排序，新词 (prior_count=0) 用强调色。

        Args:
            emerging_nsfc: NSFC 新兴词 DataFrame
            emerging_nih: NIH 新兴词 DataFrame
            output: 输出路径
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_keyword_trajectories(self, word_growth_nsfc: 'pd.DataFrame',
                                  word_growth_nih: 'pd.DataFrame',
                                  output: str, top_n: int = 8) -> None:
        """
        双栏折线图显示关键词增长轨迹.

        Args:
            word_growth_nsfc: NSFC 词频时序 DataFrame
            word_growth_nih: NIH 词频时序 DataFrame
            output: 输出路径
            top_n: 显示前 N 个关键词
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 主题地图与地形图
    # ═══════════════════════════════════════════════════════════════════

    def plot_thematic_map_temporal(self, temporal: list, output: str,
                                   title: str = '主题地图演变') -> None:
        """
        每个时间窗口的四象限主题地图.

        象限定义:
        - Motor (右上): 高中心性 + 高密度
        - Basic (左上): 低中心性 + 高密度
        - Niche (右下): 高中心性 + 低密度
        - Emerging/Declining (左下): 低中心性 + 低密度

        Args:
            temporal: 时间切片列表，每项含 'thematic_map' DataFrame
            output: 输出路径
            title: 标题
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_keyword_landscape(self, emerging: 'pd.DataFrame',
                               temporal: list, output: str) -> None:
        """
        关键词地形图 (3D 表面或等高线).

        Args:
            emerging: 新兴词 DataFrame
            temporal: 时间切片
            output: 输出路径
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 矩阵与热力图
    # ═══════════════════════════════════════════════════════════════════

    def plot_keyword_heatmap(self, word_growth: 'pd.DataFrame',
                             output: str, top_n: int = 20) -> None:
        """
        关键词-时间热力图.

        Args:
            word_growth: 词频时序 DataFrame (行=词, 列=年份)
            output: 输出路径
            top_n: 显示前 N 个关键词
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_cooccurrence_matrix(self, temporal: list, output: str,
                                 top_n: int = 15) -> None:
        """
        共现矩阵热力图 (每个时期一个子图).

        Args:
            temporal: 时间切片
            output: 输出路径
            top_n: 显示前 N 个词
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 流图与对比
    # ═══════════════════════════════════════════════════════════════════

    def plot_keyword_flow(self, temporal: list, output: str,
                          top_n: int = 10) -> None:
        """
        关键词流动 Sankey 图.

        展示关键词在不同时期之间的演变。

        Args:
            temporal: 时间切片
            output: 输出路径
            top_n: 每个时期显示前 N 个词
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_radar_comparison(self, nsfc_cats: dict, nih_cats: dict,
                              output: str, title: str = '研究方向对比') -> None:
        """
        雷达图对比 NSFC 和 NIH 的研究方向分布.

        Args:
            nsfc_cats: NSFC 类别计数
            nih_cats: NIH 类别计数
            output: 输出路径
            title: 标题
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 研究前沿与词云
    # ═══════════════════════════════════════════════════════════════════

    def plot_research_frontier(self, emerging: 'pd.DataFrame',
                               temporal: list, output: str) -> None:
        """
        研究前沿可视化 (气泡图).

        Args:
            emerging: 新兴词 DataFrame
            temporal: 时间切片
            output: 输出路径
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_wordcloud_evolution(self, word_growth: 'pd.DataFrame',
                                 output: str, periods: int = 4) -> None:
        """
        词云演变 (每个时期一个词云).

        需要安装 wordcloud 包。

        Args:
            word_growth: 词频时序 DataFrame
            output: 输出路径
            periods: 时期数
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    def plot_evolution_summary(self, evo_nsfc: 'pd.DataFrame',
                               evo_nih: 'pd.DataFrame',
                               output: str) -> None:
        """
        演变摘要图 (双栏).

        Args:
            evo_nsfc: NSFC 演变数据
            evo_nih: NIH 演变数据
            output: 输出路径
        """
        raise NotImplementedError("请使用 LandscapePlot 的完整实现")

    # ═══════════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════════

    def _save_keyword_figure(self, fig, output: str, C: dict) -> None:
        """保存关键词图表为 PNG 和 PDF"""
        out = Path(output)
        fig.savefig(str(out.with_suffix('.png')), dpi=200,
                    bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')),
                    bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        plt.close()
