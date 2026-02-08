"""
预设色板和颜色常量

用于整个可视化系统的统一配色方案。

注意: CMAP_GP 需要 matplotlib，使用时才导入以避免模块级依赖问题。
"""

from __future__ import annotations

# ═══════════════════════════════════════════════
# 预设色板 — Green-Purple主题
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

# ═══════════════════════════════════════════════
# 研究方向分类颜色映射
# ═══════════════════════════════════════════════
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

# 申请人评估用色
APPLICANT_COLORS = {
    'fit': '#3498DB',        # 适配度 - 蓝色
    'competency': '#E74C3C', # 胜任力 - 红色
    'combined': '#9B59B6',   # 综合 - 紫色
    'highlight': '#F1C40F',  # 高亮 - 黄色
    'neutral': '#95A5A6',    # 中性 - 灰色
}

# 象限颜色
QUADRANT_COLORS = {
    '明星': '#2ECC71',      # 高适配高胜任 - 绿
    '潜力': '#3498DB',      # 高适配低胜任 - 蓝
    '实力': '#F39C12',      # 低适配高胜任 - 橙
    '发展': '#95A5A6',      # 低适配低胜任 - 灰
}


# ═══════════════════════════════════════════════
# 色带和渐变 (延迟加载)
# ═══════════════════════════════════════════════
_CMAP_GP = None


def get_cmap_gp():
    """获取 Green-Purple 色带 (延迟加载以避免 matplotlib 导入问题)"""
    global _CMAP_GP
    if _CMAP_GP is None:
        from matplotlib.colors import LinearSegmentedColormap
        _CMAP_GP = LinearSegmentedColormap.from_list(
            'gp', ['#FFFFFF', '#E0E0E0', '#A0A0A0', '#606060', '#303030'], N=256)
    return _CMAP_GP


# 后向兼容: CMAP_GP 作为模块属性
def __getattr__(name):
    if name == 'CMAP_GP':
        return get_cmap_gp()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
