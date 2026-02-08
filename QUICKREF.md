# zbib 快速参考

## 一键运行

```bash
# 新项目 (交互式)
python quick_search.py

# 已有配置
python run_all.py -c configs/your_config.yaml --step 6
```

## 调用链路

```
run_all.py / quick_search.py
        │
        ▼
    Pipeline (scripts/pipeline.py)
        │
        ├── fetch_pubmed()    → PubMedClient (fetch.py)
        ├── fetch_nih()       → NIHClient (fetch.py)
        ├── fetch_applicant() → ApplicantClient (fetch_applicant.py)
        ├── fetch_letpub()    → LetPubClient (fetch_letpub.py)
        │
        ├── load_data()       → 加载 CSV 到 DataFrame
        ├── classify()        → TextClassifier (analyze.py)
        ├── analyze_gaps()    → GapAnalyzer (analyze.py)
        │
        ├── analyze_applicant() → ApplicantAnalyzer (applicant/analyzer.py)
        │                            → ApplicantProfile (applicant/profile.py)
        │                            → 评分/象限 (applicant/assessment.py)
        │
        ├── plot()            → LandscapePlot (plot.py → plotting/*.py)
        └── plot_applicant()  → ApplicantPlotMixin (plotting/applicant.py)
```

## 模块职责

| 模块 | 职责 |
|------|------|
| `pipeline.py` | 流程编排，串联所有步骤 |
| `fetch.py` | PubMed/NIH API 封装 |
| `fetch_applicant.py` | 申请人论文检索 |
| `analyze.py` | 分类器、Gap 分析器 |
| `applicant/` | 申请人评估 (profile, analyzer, assessment, benchmark, report) |
| `plotting/` | 可视化 Mixin (base, landscape, keywords, bibliometric, network, applicant) |

## 配置文件模板

```yaml
name: my_project
project_dir: "../projects/我的项目_20260207"

# 检索式
disease_cn_keyword: "疾病名"
disease_en_query: "(disease name OR synonym)"
intervention_query_en: '(TMS OR rTMS)'

# 维度
symptoms:
  Symptom1: 'regex1|regex2'
targets:
  Target1: 'regex1|regex2'

highlight_target: Target1

# Gap 模式
gap_patterns:
  target: 'target_regex'
  symptom: 'symptom_regex'

gap_combinations:
  PubMed_combo: [target, symptom]

# 申请人
applicant:
  name_cn: "中文名"
  name_en: "English Name"
  affiliations: ["Affiliation 1", "Affiliation 2"]
```

## 输出结构

```
projects/{项目名}/
├── data/
│   ├── pubmed_nibs_*.csv.gz     # PubMed 文献
│   ├── nih_nibs_*.csv.gz        # NIH NIBS 项目
│   ├── nih_all_*.csv.gz         # NIH 全部项目
│   └── applicant_*.csv.gz       # 申请人论文
├── results/
│   ├── gap_counts.csv           # 空白计数
│   ├── applicant_summary.txt    # 申请人摘要
│   └── 优化分析报告.md          # 完整报告
└── figs/
    ├── *_landscape.png/pdf      # 主图
    └── *_applicant.png/pdf      # 申请人图
```

## 常用 API

```python
from scripts.pipeline import Pipeline

pipe = Pipeline.from_yaml('configs/xxx.yaml')

# 单步执行
pipe.fetch_pubmed()
pipe.fetch_nih()
pipe.fetch_applicant()
pipe.load_data()
pipe.classify()
analysis = pipe.analyze_gaps()
profile = pipe.analyze_applicant()
pipe.plot_applicant()

# 一键执行
pipe.run(step=6)  # 只做分析+出图
pipe.run()        # 全流程
```
