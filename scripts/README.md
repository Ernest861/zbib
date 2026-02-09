# scripts/ — 核心代码模块

zbib 的所有核心功能代码。

## 模块结构

```
scripts/
├── __init__.py          # 包初始化
├── config.py            # 配置数据类 (TopicConfig, ApplicantConfig)
├── pipeline.py          # 主流程编排 (Pipeline 类)
├── domain_knowledge.py  # 疾病领域知识库 ★ 新增
├── fetch.py             # PubMed + NIH 检索
├── fetch_applicant.py   # 申请人文献检索
├── analyze.py           # 分类与空白分析
├── journals.py          # 期刊分级 + IF 数据
├── keywords.py          # 关键词提取与分析
├── network.py           # 共现网络分析
├── plot.py              # 绑图入口 (LandscapePlot)
├── plotting/            # 绑图模块包 (6 个 Mixin)
├── applicant/           # 申请人分析包
└── ...
```

## 领域知识库 (`domain_knowledge.py`)

基于 PubMed 文献综合分析，自动扩展热力图分析维度：

```python
from scripts.domain_knowledge import expand_config_dimensions, list_dimensions

# 查看精神分裂症的所有维度
dims = list_dimensions('schizophrenia')
# 症状: Negative, Positive, Cognitive, AVH, Disorganization
# 靶点: DLPFC, OFC, TPJ, mPFC, ACC, Cerebellum, STS

# 扩展用户配置
expanded = expand_config_dimensions(
    disease='schizophrenia',
    user_symptoms={'Negative': 'negative.*'},  # 用户只配置了1个
    highlight_target='OFC',
)
# 自动扩展为5个症状 × 7个靶点
```

**已收录疾病**:

| 疾病 | 症状维度 | 靶点维度 |
|------|---------|---------|
| schizophrenia | 5 | 7 |
| depression | 6 | 6 |
| addiction | 5 | 6 |
| ocd | 4 | 5 |

## 核心类

### Pipeline (`pipeline.py`)

主流程编排，一站式完成所有分析:

```python
from scripts.pipeline import Pipeline

p = Pipeline.from_yaml('configs/xxx.yaml')
p.run()  # 自动执行全部流程
```

关键方法:
- `load_data()` — 加载 PubMed/NIH/NSFC/申请人数据
- `classify()` — 按研究方向分类
- `analyze_gaps()` — 空白分析
- `analyze_applicant()` — 申请人分析
- `plot()` — 生成主图
- `generate_nsfc_report()` — 生成 NSFC 标书支撑报告

### TopicConfig (`config.py`)

配置数据类:

```python
@dataclass
class TopicConfig:
    name: str               # 项目名称
    disease: str            # 疾病 (如 "schizophrenia")
    target: str             # 靶点 (如 "OFC")
    symptom: str            # 症状 (如 "Negative")
    applicant: ApplicantConfig  # 申请人信息
    ...
```

## 绑图模块 (`plotting/`)

采用 Mixin 模式拆分:

| Mixin | 功能 |
|-------|------|
| `BasePlotMixin` | 初始化、保存、工具方法 |
| `LandscapePlotMixin` | 主全景图 |
| `KeywordPlotMixin` | 关键词/时序分析 |
| `BibliometricPlotMixin` | 文献计量分析 |
| `NetworkPlotMixin` | 共现网络 |
| `ApplicantPlotMixin` | 申请人可视化 |

## 申请人分析包 (`applicant/`)

| 模块 | 功能 |
|------|------|
| `profile.py` | ApplicantProfile 数据类 + 评分计算 |
| `analyzer.py` | ApplicantAnalyzer 主分析类 |
| `assessment.py` | 叙事评估 + 象限定位 |
| `benchmark.py` | 领域基准排名 |
| `report.py` | Markdown 报告生成 |
| `orcid.py` | ORCID 交叉验证 |

## 数据检索

| 模块 | 数据源 |
|------|--------|
| `fetch.py` | PubMed E-utilities + NIH Reporter API |
| `fetch_applicant.py` | 申请人文献 (PubMed) |
| `fetch_letpub.py` | LetPub NSFC 数据 |
| `fetch_kd.py` | 科学基金共享服务网详情 |

## 依赖关系

```
pipeline.py
    ├── config.py
    ├── fetch.py / fetch_applicant.py
    ├── analyze.py
    ├── applicant/analyzer.py
    └── plot.py → plotting/*
```
