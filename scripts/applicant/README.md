# applicant/ — 申请人分析模块

分析 NSFC 申请人的前期工作基础，生成评估报告。

## 模块结构

```
applicant/
├── __init__.py      # 包入口 + 导出
├── profile.py       # ApplicantProfile 数据类 (295 行)
├── analyzer.py      # ApplicantAnalyzer 主分析类 (622 行)
├── assessment.py    # 叙事评估 + 象限定位
├── benchmark.py     # 领域基准排名
├── report.py        # Markdown 报告生成 (1003 行)
└── orcid.py         # ORCID 交叉验证
```

## 核心类

### ApplicantProfile (`profile.py`)

申请人画像数据类:

```python
@dataclass
class ApplicantProfile:
    # 基本信息
    name_cn: str
    name_en: str

    # 发表统计
    n_total: int           # 总发文
    n_disease: int         # 疾病相关
    n_nibs: int            # NIBS 相关
    n_disease_nibs: int    # 交叉研究

    # 作者身份
    n_first_author: int
    n_corresponding: int
    n_first_or_corresponding: int

    # 期刊影响力
    top_journal_count: int      # 顶刊数量
    high_quality_count: int     # 高质量期刊
    if_stats: IFStats           # IF 统计

    # 评分
    fit_score: float          # 适配度 (0-100)
    competency_score: float   # 胜任力 (0-100)
    relevance_score: float    # 综合评分 (0-100)
    percentile_ranks: dict    # 领域基准百分位

    # 合作网络
    top_collaborators: list
    stable_teams: list
    team_stability_index: float
```

### ApplicantAnalyzer (`analyzer.py`)

主分析类:

```python
from scripts.applicant import ApplicantAnalyzer

analyzer = ApplicantAnalyzer(config, applicant_df)
profile = analyzer.analyze()
```

关键方法:
- `analyze()` — 完整分析流程
- `_count_authorship()` — 第一/通讯作者统计
- `_estimate_h_index()` — IF 加权 H-index 估算
- `_extract_collaborators()` — 合作者提取
- `_detect_stable_teams()` — 稳定团队检测
- `_analyze_trajectory()` — 研究轨迹分析

## 评分体系

### 适配度 (Fit Score, 50%)

| 维度 | 权重 | 含义 |
|------|------|------|
| 疾病领域 | 20% | 疾病相关发文占比 |
| 技术方法 | 20% | NIBS 技术积累 |
| 交叉经验 | 10% | 疾病+NIBS 交叉 |

### 胜任力 (Competence Score, 50%)

| 维度 | 权重 | 含义 |
|------|------|------|
| 学术独立 | 20% | 第一/通讯作者占比 |
| 学术影响 | 15% | 顶刊 + H-index |
| 研究活跃 | 15% | 近5年产出 |

### 象限定位

```
            胜任力高
               │
     潜力申请人 │ 明星申请人
               │
 ──────────────┼────────────── 适配度
               │
     边缘申请人 │ 跨界申请人
               │
            胜任力低
```

## 领域基准排名 (`benchmark.py`)

基于 NIBS-Psychiatry 领域活跃研究者建立基准:

```python
from scripts.applicant.benchmark import FieldBenchmark

benchmark = FieldBenchmark()
percentiles = benchmark.get_percentile_ranks(profile)
# {'total_pubs': 51, 'h_index': 42, 'fit_score': 75, ...}
```

## 报告生成 (`report.py`)

生成完整 Markdown 报告:

```python
from scripts.applicant.report import create_markdown_report, save_markdown_report

report = create_markdown_report(profile, topic_name="OFC-rTMS")
# 返回 Markdown 字符串，包含 11 个章节

# 或直接保存
save_markdown_report(profile, output_dir, topic_name="OFC-rTMS")
```

报告章节:
1. 申请人信息
2. 发表统计
3. 研究维度覆盖
4. 合作网络
5. 研究轨迹
6. 代表性论文
7. 顶刊论文详情
8. 适配度与胜任力评估
9. 叙事性评估
10. 薄弱维度分析
11. 领域基准排名

## 超图合作网络

基于 Battiston et al. 2025 高阶网络理论:

- `stable_teams` — 稳定合作团队 (≥3 次共同发表)
- `team_stability_index` — 团队稳定性指数 (0-1)
- `avg_team_size` / `max_team_size` — 团队规模
- `solo_ratio` — 独立发表比例
