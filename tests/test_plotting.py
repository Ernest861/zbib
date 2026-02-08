"""plotting 包单元测试

测试可视化模块的导入、Mixin 组合和基本功能。

注意: 需要 matplotlib 的测试会在 NumPy 2.x / matplotlib 不兼容时自动跳过。
"""

import sys
import pytest

# 绕过 scripts/__init__.py 的 matplotlib 导入问题
sys.modules['scripts'] = type(sys)('scripts')
sys.modules['scripts'].__path__ = ['scripts']

# 检测 matplotlib 是否可用
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except (ImportError, AttributeError):
    MATPLOTLIB_AVAILABLE = False

requires_matplotlib = pytest.mark.skipif(
    not MATPLOTLIB_AVAILABLE,
    reason="matplotlib 与 NumPy 2.x 不兼容"
)


class TestColorConstants:
    """测试色板常量 (无 matplotlib 依赖)"""

    def test_import_colors(self):
        """测试色板常量导入"""
        from scripts.plotting.colors import (
            COLORS_GREEN_PURPLE,
            CAT_COLORS,
            APPLICANT_COLORS,
            QUADRANT_COLORS,
        )
        assert 'ACCENT' in COLORS_GREEN_PURPLE
        assert 'BG' in COLORS_GREEN_PURPLE
        assert '神经调控' in CAT_COLORS
        assert 'fit' in APPLICANT_COLORS
        assert '明星' in QUADRANT_COLORS

    def test_colors_are_hex(self):
        """测试颜色值为有效十六进制"""
        from scripts.plotting.colors import COLORS_GREEN_PURPLE, CAT_COLORS

        for name, color in COLORS_GREEN_PURPLE.items():
            assert color.startswith('#'), f"{name} 不是十六进制颜色"
            assert len(color) == 7, f"{name} 长度不对"

        for name, color in CAT_COLORS.items():
            assert color.startswith('#'), f"{name} 不是十六进制颜色"

    def test_required_colors_exist(self):
        """测试必需的颜色存在"""
        from scripts.plotting.colors import COLORS_GREEN_PURPLE

        required = ['ACCENT', 'BG', 'INDIGO', 'VIOLET', 'WARN']
        for color in required:
            assert color in COLORS_GREEN_PURPLE, f"缺少必需颜色: {color}"

    def test_category_colors_complete(self):
        """测试研究方向分类颜色完整"""
        from scripts.plotting.colors import CAT_COLORS

        categories = ['神经调控', '环路/机制', '免疫/代谢', '神经影像',
                      '遗传/组学', '临床/药物', '认知/行为', '其他']
        for cat in categories:
            assert cat in CAT_COLORS, f"缺少类别颜色: {cat}"

    def test_applicant_colors_complete(self):
        """测试申请人评估用色完整"""
        from scripts.plotting.colors import APPLICANT_COLORS

        required = ['fit', 'competency', 'combined', 'highlight', 'neutral']
        for key in required:
            assert key in APPLICANT_COLORS, f"缺少申请人颜色: {key}"

    def test_quadrant_colors_complete(self):
        """测试象限颜色完整"""
        from scripts.plotting.colors import QUADRANT_COLORS

        quadrants = ['明星', '潜力', '实力', '发展']
        for q in quadrants:
            assert q in QUADRANT_COLORS, f"缺少象限颜色: {q}"


class TestPackageStructure:
    """测试包结构 (无 matplotlib 依赖)"""

    def test_package_init_exists(self):
        """测试 __init__.py 可导入"""
        import scripts.plotting
        assert hasattr(scripts.plotting, '__all__')

    def test_all_exports_defined(self):
        """测试 __all__ 定义完整"""
        from scripts.plotting import __all__

        expected = [
            'LandscapePlot',
            'BasePlotMixin', 'LandscapePlotMixin', 'KeywordPlotMixin',
            'BibliometricPlotMixin', 'NetworkPlotMixin', 'ApplicantPlotMixin',
            'COLORS_GREEN_PURPLE', 'CAT_COLORS', 'APPLICANT_COLORS',
            'QUADRANT_COLORS', 'get_cmap_gp',
        ]
        for name in expected:
            assert name in __all__, f"__all__ 缺少: {name}"

    def test_lazy_imports_defined(self):
        """测试延迟导入字典定义"""
        from scripts.plotting import _lazy_imports

        expected_keys = [
            'BasePlotMixin', 'LandscapePlotMixin', 'KeywordPlotMixin',
            'BibliometricPlotMixin', 'NetworkPlotMixin', 'ApplicantPlotMixin',
            'LandscapePlot', 'CMAP_GP',
        ]
        for key in expected_keys:
            assert key in _lazy_imports, f"_lazy_imports 缺少: {key}"


@requires_matplotlib
class TestPlottingImports:
    """测试 plotting 包导入 (需要 matplotlib)"""

    def test_import_base_mixin(self):
        """测试 BasePlotMixin 导入"""
        from scripts.plotting.base import BasePlotMixin
        assert hasattr(BasePlotMixin, '__init__')
        assert hasattr(BasePlotMixin, 'save_figure')
        assert hasattr(BasePlotMixin, 'plot_top_bar')
        assert hasattr(BasePlotMixin, 'setup_chinese_fonts')

    def test_import_landscape_mixin(self):
        """测试 LandscapePlotMixin 导入"""
        from scripts.plotting.landscape import LandscapePlotMixin
        assert hasattr(LandscapePlotMixin, 'plot_trend')
        assert hasattr(LandscapePlotMixin, 'plot_stacked_evolution')
        assert hasattr(LandscapePlotMixin, 'plot_heatmap_with_marginals')
        assert hasattr(LandscapePlotMixin, 'create_landscape')
        assert hasattr(LandscapePlotMixin, 'create_supplementary_figure')

    def test_import_keywords_mixin(self):
        """测试 KeywordPlotMixin 导入"""
        from scripts.plotting.keywords import KeywordPlotMixin
        assert hasattr(KeywordPlotMixin, 'plot_temporal_network')
        assert hasattr(KeywordPlotMixin, 'plot_keyword_prediction')
        assert hasattr(KeywordPlotMixin, 'plot_thematic_map_temporal')

    def test_import_bibliometric_mixin(self):
        """测试 BibliometricPlotMixin 导入"""
        from scripts.plotting.bibliometric import BibliometricPlotMixin
        assert hasattr(BibliometricPlotMixin, 'plot_lotka')
        assert hasattr(BibliometricPlotMixin, 'plot_bradford')
        assert hasattr(BibliometricPlotMixin, 'plot_funding_trend')
        assert hasattr(BibliometricPlotMixin, 'create_bibliometric_report')

    def test_import_network_mixin(self):
        """测试 NetworkPlotMixin 导入"""
        from scripts.plotting.network import NetworkPlotMixin
        assert hasattr(NetworkPlotMixin, 'plot_network')
        assert hasattr(NetworkPlotMixin, 'plot_thematic_map')
        assert hasattr(NetworkPlotMixin, 'plot_centrality_bar')
        assert hasattr(NetworkPlotMixin, 'create_network_report')

    def test_import_applicant_mixin(self):
        """测试 ApplicantPlotMixin 导入"""
        from scripts.plotting.applicant import ApplicantPlotMixin
        assert hasattr(ApplicantPlotMixin, 'create_applicant_figure')
        assert hasattr(ApplicantPlotMixin, 'create_applicant_extended_figure')
        assert hasattr(ApplicantPlotMixin, 'create_comparison_figure')


@requires_matplotlib
class TestMixinComposition:
    """测试 Mixin 组合 (需要 matplotlib)"""

    def test_landscape_plot_inherits_all_mixins(self):
        """测试 LandscapePlot 继承所有 Mixin"""
        from scripts.plotting.base import BasePlotMixin
        from scripts.plotting.landscape import LandscapePlotMixin
        from scripts.plotting.keywords import KeywordPlotMixin
        from scripts.plotting.bibliometric import BibliometricPlotMixin
        from scripts.plotting.network import NetworkPlotMixin
        from scripts.plotting.applicant import ApplicantPlotMixin

        # 创建组合类 (模拟 LandscapePlot)
        class TestPlot(
            ApplicantPlotMixin,
            NetworkPlotMixin,
            BibliometricPlotMixin,
            KeywordPlotMixin,
            LandscapePlotMixin,
            BasePlotMixin,
        ):
            pass

        # 验证 MRO
        mro_names = [cls.__name__ for cls in TestPlot.__mro__]
        assert 'ApplicantPlotMixin' in mro_names
        assert 'NetworkPlotMixin' in mro_names
        assert 'BibliometricPlotMixin' in mro_names
        assert 'KeywordPlotMixin' in mro_names
        assert 'LandscapePlotMixin' in mro_names
        assert 'BasePlotMixin' in mro_names

    def test_landscape_plot_has_all_methods(self):
        """测试 LandscapePlot 拥有所有方法"""
        from scripts.plotting.base import BasePlotMixin
        from scripts.plotting.landscape import LandscapePlotMixin
        from scripts.plotting.keywords import KeywordPlotMixin
        from scripts.plotting.bibliometric import BibliometricPlotMixin
        from scripts.plotting.network import NetworkPlotMixin
        from scripts.plotting.applicant import ApplicantPlotMixin

        class TestPlot(
            ApplicantPlotMixin,
            NetworkPlotMixin,
            BibliometricPlotMixin,
            KeywordPlotMixin,
            LandscapePlotMixin,
            BasePlotMixin,
        ):
            pass

        # 关键方法检查
        key_methods = [
            # Base
            'save_figure', 'plot_top_bar',
            # Landscape
            'create_landscape', 'plot_trend', 'plot_gap_table',
            # Keywords
            'plot_temporal_network',
            # Bibliometric
            'plot_lotka', 'plot_bradford',
            # Network
            'plot_network', 'create_network_report',
            # Applicant
            'create_applicant_figure', 'create_comparison_figure',
        ]

        for method in key_methods:
            assert hasattr(TestPlot, method), f"Missing method: {method}"


@requires_matplotlib
class TestBasePlotMixin:
    """测试 BasePlotMixin 功能 (需要 matplotlib)"""

    def test_init_sets_attributes(self):
        """测试初始化设置属性"""
        from scripts.plotting.base import BasePlotMixin

        mixin = BasePlotMixin(figsize=(20, 10), lang='en')
        assert mixin.figsize == (20, 10)
        assert mixin.lang == 'en'
        assert 'ACCENT' in mixin.C
        assert 'BG' in mixin.C

    def test_default_init(self):
        """测试默认初始化"""
        from scripts.plotting.base import BasePlotMixin

        mixin = BasePlotMixin()
        assert mixin.figsize == (28, 16)
        assert mixin.lang == 'zh'

    def test_get_category_color(self):
        """测试类别颜色获取"""
        from scripts.plotting.base import BasePlotMixin

        mixin = BasePlotMixin()
        color = mixin.get_category_color('神经调控')
        assert color.startswith('#')
        assert len(color) == 7

        # 未知类别返回默认色
        default_color = mixin.get_category_color('未知类别')
        assert default_color == '#D5D8DC'


@requires_matplotlib
class TestBackwardCompatibility:
    """测试后向兼容性 (需要 matplotlib)"""

    def test_import_from_plot_module(self):
        """测试从 scripts.plot 导入"""
        from scripts.plot import (
            LandscapePlot,
            COLORS_GREEN_PURPLE,
            CAT_COLORS,
        )
        assert LandscapePlot is not None
        assert 'ACCENT' in COLORS_GREEN_PURPLE
        assert '神经调控' in CAT_COLORS

    def test_landscape_plot_can_instantiate(self):
        """测试 LandscapePlot 可以实例化"""
        from scripts.plot import LandscapePlot

        plotter = LandscapePlot()
        assert plotter.figsize == (28, 16)
        assert plotter.lang == 'zh'
        assert hasattr(plotter, 'C')

    def test_landscape_plot_has_create_methods(self):
        """测试 LandscapePlot 有所有 create 方法"""
        from scripts.plot import LandscapePlot

        create_methods = [
            'create_landscape',
            'create_supplementary_figure',
            'create_bibliometric_report',
            'create_performance_report',
            'create_network_report',
            'create_applicant_figure',
            'create_applicant_extended_figure',
            'create_comparison_figure',
        ]

        for method in create_methods:
            assert hasattr(LandscapePlot, method), f"Missing: {method}"
