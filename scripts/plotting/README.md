# plotting/ — 可视化模块

采用 Mixin 模式组织的绑图代码，支持按需导入和独立测试。

## 模块结构

```
plotting/
├── __init__.py       # 延迟加载入口
├── colors.py         # 色板常量
├── base.py           # BasePlotMixin (200 行)
├── landscape.py      # LandscapePlotMixin (580 行)
├── keywords.py       # KeywordPlotMixin (390 行)
├── bibliometric.py   # BibliometricPlotMixin (450 行)
├── network.py        # NetworkPlotMixin (380 行)
└── applicant.py      # ApplicantPlotMixin (1015 行)
```

## Mixin 继承顺序

```python
class LandscapePlot(
    ApplicantPlotMixin,      # 申请人评估
    NetworkPlotMixin,        # 网络分析
    BibliometricPlotMixin,   # 文献计量
    KeywordPlotMixin,        # 关键词/时序
    LandscapePlotMixin,      # 全景图
    BasePlotMixin,           # 基础工具 (最后)
):
    pass
```

## 各 Mixin 功能

### BasePlotMixin (`base.py`)

基础工具方法:
- `_init_style()` — 设置全局样式
- `_save_figure()` — 保存 PNG + PDF
- `_add_title_box()` — 添加标题框
- `_setup_grid_style()` — 网格样式

### LandscapePlotMixin (`landscape.py`)

主全景图 (6-panel):
- `create_landscape_figure()` — 8×6 英寸主图
- `create_supplementary_figure()` — 8×5.5 英寸补充图
- `plot_gap_table()` — 空白统计表格
- `plot_paper_list()` — 论文列表

### KeywordPlotMixin (`keywords.py`)

关键词分析:
- `plot_keyword_cloud()` — 词云图
- `plot_keyword_trends()` — 关键词趋势
- `plot_emerging_keywords()` — 新兴关键词

### BibliometricPlotMixin (`bibliometric.py`)

文献计量:
- `plot_time_series()` — 时序趋势
- `plot_category_breakdown()` — 分类构成
- `plot_heatmap()` — 靶区×症状热力图

### NetworkPlotMixin (`network.py`)

共现网络:
- `plot_cooccurrence_network()` — 共现网络图
- `plot_network_evolution()` — 网络演变

### ApplicantPlotMixin (`applicant.py`)

申请人可视化:
- `create_applicant_figure()` — 独立 4-panel 图
- `create_applicant_extended_figure()` — 扩展 6-panel (分两页)
- `_plot_applicant_timeline()` — 发文时间线
- `_plot_applicant_radar()` — 维度雷达图
- `_plot_applicant_journals()` — 期刊分布
- `_plot_collaborator_network()` — 合作网络
- `_plot_research_trajectory()` — 研究轨迹

## 出版标准

所有核心图表遵循:
- 最大尺寸: 8 × 6.5 英寸
- 字体: 6-8 pt
- 超过尺寸限制的图自动分页

## 延迟加载

`__init__.py` 使用 `__getattr__` 延迟加载，避免 matplotlib 初始化开销:

```python
from scripts.plotting import LandscapePlot  # 按需导入
```

## 色板 (`colors.py`)

```python
from scripts.plotting.colors import COLORS_GREEN_PURPLE, CAT_COLORS, APPLICANT_COLORS

# 主色板 (绿紫渐变)
COLORS_GREEN_PURPLE = {
    'BG': '#FAFAFA',        # 背景
    'TEXT': '#2C3E50',      # 文字
    'ACCENT': '#8E44AD',    # 强调色 (紫)
    'GRID': '#ECF0F1',      # 网格
}

# 分类色板
CAT_COLORS = {
    'Clinical': '#3498DB',
    'Genetics': '#27AE60',
    'Neuroimaging': '#E74C3C',
    ...
}

# 申请人评估色板
APPLICANT_COLORS = {...}
```
