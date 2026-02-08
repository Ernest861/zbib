"""出图: 全景图模板 + Mixin 组合

本模块通过多重继承组合所有可视化 Mixin，提供统一的 LandscapePlot 类。

Mixin 来源 (scripts/plotting/):
    - BasePlotMixin: 初始化、保存、工具方法
    - LandscapePlotMixin: 全景图 (趋势、热力图、空白表)
    - KeywordPlotMixin: 关键词/时序分析
    - BibliometricPlotMixin: 文献计量 (Lotka、Bradford)
    - NetworkPlotMixin: 网络分析 (力导向、主题地图)
    - ApplicantPlotMixin: 申请人评估

用法:
    from scripts.plot import LandscapePlot

    plotter = LandscapePlot()
    plotter.create_landscape(data_dict, 'output/figure')
    plotter.create_applicant_figure(profile, 'output/applicant')
"""

# ═══════════════════════════════════════════════
# 后向兼容: 导出色板常量
# ═══════════════════════════════════════════════
from scripts.plotting.colors import (
    COLORS_GREEN_PURPLE,
    CAT_COLORS,
    CMAP_GP,
    APPLICANT_COLORS,
    QUADRANT_COLORS,
)

# ═══════════════════════════════════════════════
# 导入所有 Mixin
# ═══════════════════════════════════════════════
from scripts.plotting.base import BasePlotMixin
from scripts.plotting.landscape import LandscapePlotMixin
from scripts.plotting.keywords import KeywordPlotMixin
from scripts.plotting.bibliometric import BibliometricPlotMixin
from scripts.plotting.network import NetworkPlotMixin
from scripts.plotting.applicant import ApplicantPlotMixin


# ═══════════════════════════════════════════════
# LandscapePlot: 组合所有 Mixin
# ═══════════════════════════════════════════════
class LandscapePlot(
    ApplicantPlotMixin,      # 申请人评估 (最高优先级)
    NetworkPlotMixin,        # 网络分析
    BibliometricPlotMixin,   # 文献计量
    KeywordPlotMixin,        # 关键词/时序
    LandscapePlotMixin,      # 全景图
    BasePlotMixin,           # 基础工具 (最低优先级，提供 __init__)
):
    """
    全景图模板 — 组合所有可视化功能.

    通过 Mixin 模式组合以下功能模块:
    - 基础工具: 初始化、保存、通用组件
    - 全景图: NIH/NSFC 趋势、热力图、研究空白
    - 关键词分析: 共现网络、主题演变、趋势预测
    - 文献计量: Lotka/Bradford 定律、PI 分析
    - 网络分析: 合作网络、主题地图、社区检测
    - 申请人评估: Profile 可视化、对比分析

    Attributes:
        figsize: 默认图表尺寸 (宽, 高)
        lang: 语言设置 ('zh' 中文, 'en' 英文)
        C: 色板字典

    Example:
        >>> plotter = LandscapePlot(figsize=(28, 16))
        >>> plotter.create_landscape(data_dict, 'output/landscape')
        >>> plotter.create_applicant_figure(profile, 'output/applicant')
        >>> plotter.create_network_report(net_data, 'output/network')
    """
    pass


# ═══════════════════════════════════════════════
# 后向兼容: 导出到模块级别
# ═══════════════════════════════════════════════
__all__ = [
    'LandscapePlot',
    # 色板常量
    'COLORS_GREEN_PURPLE',
    'CAT_COLORS',
    'CMAP_GP',
    'APPLICANT_COLORS',
    'QUADRANT_COLORS',
]
