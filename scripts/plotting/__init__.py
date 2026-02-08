"""
可视化绑图包 (Plotting Package)

该包提供 zbib 的所有可视化功能，包括:
- 全景图 (Landscape)
- 关键词分析图
- 网络分析图
- 文献计量分析图
- 申请人评估图
- 多申请人对比图

模块结构:
    plotting/
    ├── __init__.py        ← 统一导出 (延迟加载)
    ├── colors.py          ← 色板常量 ✅
    ├── base.py            ← BasePlotMixin 基础工具 ✅
    ├── landscape.py       ← LandscapePlotMixin 全景图 ✅
    ├── keywords.py        ← KeywordPlotMixin 关键词/时序 ✅
    ├── bibliometric.py    ← BibliometricPlotMixin 文献计量 ✅
    ├── network.py         ← NetworkPlotMixin 网络分析 ✅
    └── applicant.py       ← ApplicantPlotMixin 申请人评估 ✅

用法:
    from scripts.plotting import LandscapePlot
    # 或
    from scripts.plot import LandscapePlot  # 后向兼容

    # 使用 Mixin (高级用法)
    from scripts.plotting import (
        BasePlotMixin,
        LandscapePlotMixin,
        KeywordPlotMixin,
        BibliometricPlotMixin,
        NetworkPlotMixin,
        ApplicantPlotMixin,
    )

Mixin 继承顺序 (MRO):
    class LandscapePlot(
        ApplicantPlotMixin,      # 申请人评估
        NetworkPlotMixin,        # 网络分析
        BibliometricPlotMixin,   # 文献计量
        KeywordPlotMixin,        # 关键词/时序
        LandscapePlotMixin,      # 全景图
        BasePlotMixin,           # 基础工具 (最后)
    ):
        pass

注意: 所有 Mixin 类使用延迟加载，避免模块级 matplotlib 导入问题。
"""

# ═══════════════════════════════════════════════
# 色板常量 (无 matplotlib 依赖，可直接导入)
# ═══════════════════════════════════════════════
from .colors import (
    COLORS_GREEN_PURPLE,
    CAT_COLORS,
    APPLICANT_COLORS,
    QUADRANT_COLORS,
    get_cmap_gp,
)

__all__ = [
    # 主类
    'LandscapePlot',
    # Mixin 类
    'BasePlotMixin',
    'LandscapePlotMixin',
    'KeywordPlotMixin',
    'BibliometricPlotMixin',
    'NetworkPlotMixin',
    'ApplicantPlotMixin',
    # 色板
    'COLORS_GREEN_PURPLE',
    'CAT_COLORS',
    'APPLICANT_COLORS',
    'QUADRANT_COLORS',
    'get_cmap_gp',
]

# ═══════════════════════════════════════════════
# 延迟加载 (避免模块级 matplotlib 导入)
# ═══════════════════════════════════════════════
_lazy_imports = {
    'BasePlotMixin': ('.base', 'BasePlotMixin'),
    'LandscapePlotMixin': ('.landscape', 'LandscapePlotMixin'),
    'KeywordPlotMixin': ('.keywords', 'KeywordPlotMixin'),
    'BibliometricPlotMixin': ('.bibliometric', 'BibliometricPlotMixin'),
    'NetworkPlotMixin': ('.network', 'NetworkPlotMixin'),
    'ApplicantPlotMixin': ('.applicant', 'ApplicantPlotMixin'),
    'LandscapePlot': ('scripts.plot', 'LandscapePlot'),
    'CMAP_GP': None,  # 特殊处理
}


def __getattr__(name):
    """延迟加载 Mixin 类和 CMAP_GP"""
    if name == 'CMAP_GP':
        return get_cmap_gp()

    if name in _lazy_imports:
        module_path, attr_name = _lazy_imports[name]
        if module_path.startswith('.'):
            # 相对导入
            from importlib import import_module
            module = import_module(module_path, __package__)
        else:
            # 绝对导入
            from importlib import import_module
            module = import_module(module_path)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
