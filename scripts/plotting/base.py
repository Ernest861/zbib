"""基础绑图工具 Mixin 模块

提供所有可视化类的共用工具方法，包括：
- 初始化和配置
- 图表保存
- 通用绑图组件 (Top-N 柱状图等)
- 中文字体配置

使用方式 (Mixin 模式):
    class LandscapePlot(BasePlotMixin, OtherMixin):
        pass

依赖:
    - self.C: 色板字典 (从 colors.py 导入)
    - matplotlib, numpy
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

# 无头环境优先使用 Agg，避免 GUI/显示导致崩溃 (SIGABRT 等)
import matplotlib
matplotlib.use('Agg')

import numpy as np
import matplotlib.pyplot as plt

from .colors import COLORS_GREEN_PURPLE, CAT_COLORS

if TYPE_CHECKING:
    import pandas as pd


class BasePlotMixin:
    """
    基础绑图工具 Mixin 类.

    提供初始化、保存和通用绑图方法。其他 Mixin 类应依赖此类提供的 self.C 色板。

    Attributes:
        figsize: 默认图表尺寸
        lang: 语言 ('zh' 或 'en')
        C: 色板字典

    公开方法:
        - plot_top_bar(): 通用 Top-N 柱状图
        - setup_chinese_fonts(): 配置中文字体
        - save_figure(): 保存图表为 PNG 和 PDF
    """

    def __init__(self, figsize: tuple[int, int] = (28, 16), lang: str = 'zh'):
        """
        初始化绑图配置.

        Args:
            figsize: 默认图表尺寸 (宽, 高)
            lang: 语言设置 ('zh' 中文, 'en' 英文)
        """
        self.figsize = figsize
        self.lang = lang
        self.C = COLORS_GREEN_PURPLE

    # ═══════════════════════════════════════════════════════════════════
    # 字体配置
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def setup_chinese_fonts() -> None:
        """配置 matplotlib 中文字体支持"""
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
        plt.rcParams['axes.unicode_minus'] = False

    # ═══════════════════════════════════════════════════════════════════
    # 图表保存
    # ═══════════════════════════════════════════════════════════════════

    def save_figure(self, fig, output: str, suffix: str = '',
                    dpi: int = 200, close: bool = True) -> Path:
        """
        保存图表为 PNG 和 PDF 格式.

        Args:
            fig: matplotlib Figure 对象
            output: 输出路径 (不含扩展名)
            suffix: 文件名后缀 (如 '_extended')
            dpi: PNG 分辨率
            close: 是否在保存后关闭图表

        Returns:
            保存的 PNG 文件路径
        """
        C = self.C
        out = Path(output + suffix)
        fig.savefig(str(out.with_suffix('.png')), dpi=dpi,
                    bbox_inches='tight', facecolor=C['BG'])
        fig.savefig(str(out.with_suffix('.pdf')),
                    bbox_inches='tight', facecolor=C['BG'])
        print(f"已保存: {out.with_suffix('.png')}")
        if close:
            plt.close(fig)
        return out.with_suffix('.png')

    def _save_fig(self, fig, output: str, suffix: str = '') -> None:
        """保存图表 (兼容旧接口)"""
        self.save_figure(fig, output, suffix)

    # ═══════════════════════════════════════════════════════════════════
    # 通用绘图组件
    # ═══════════════════════════════════════════════════════════════════

    def plot_top_bar(self, ax, data: 'pd.DataFrame', name_col: str, value_col: str,
                     n: int = 15, title: str = '', color: str = '#5C6DAF',
                     horizontal: bool = True) -> None:
        """
        通用 Top-N 柱状图.

        Args:
            ax: matplotlib Axes 对象
            data: 数据 DataFrame
            name_col: 名称列
            value_col: 数值列
            n: 显示前 N 项
            title: 标题
            color: 柱状图颜色
            horizontal: 是否水平显示

        Example:
            >>> plotter.plot_top_bar(ax, df, 'author', 'count', n=10, title='Top Authors')
        """
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

    # ═══════════════════════════════════════════════════════════════════
    # 样式工具
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def clean_spines(ax, keep: list[str] | None = None) -> None:
        """
        清理坐标轴边框.

        Args:
            ax: matplotlib Axes 对象
            keep: 保留的边框列表 (默认保留 'left' 和 'bottom')
        """
        keep = keep or ['left', 'bottom']
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(spine in keep)

    @staticmethod
    def add_panel_label(ax, label: str, x: float = -0.05, y: float = 1.05,
                        fontsize: int = 24) -> None:
        """
        添加面板标签 (如 A, B, C).

        Args:
            ax: matplotlib Axes 对象
            label: 标签文本
            x, y: 相对位置 (transform=ax.transAxes)
            fontsize: 字体大小
        """
        ax.text(x, y, label, transform=ax.transAxes, fontsize=fontsize,
                fontweight='bold', va='top', ha='left', color='#2C3E50')

    def get_category_color(self, category: str) -> str:
        """
        获取研究方向类别颜色.

        Args:
            category: 类别名称

        Returns:
            颜色代码 (十六进制)
        """
        return CAT_COLORS.get(category, '#D5D8DC')

    def create_figure(self, nrows: int = 1, ncols: int = 1,
                      figsize: tuple[int, int] | None = None,
                      **kwargs) -> tuple:
        """
        创建带预设样式的图表.

        Args:
            nrows: 行数
            ncols: 列数
            figsize: 图表尺寸 (默认使用 self.figsize)
            **kwargs: 传递给 plt.subplots 的其他参数

        Returns:
            (fig, axes) 元组
        """
        self.setup_chinese_fonts()
        figsize = figsize or self.figsize
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                                 facecolor=self.C['BG'], **kwargs)
        return fig, axes
