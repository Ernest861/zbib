# zbib 使用说明

> NIBS 文献空白分析工具 — 用于国自然标书创新性论证

## 快速开始

### 方式一：YAML 配置驱动（推荐）

```bash
# 1. 复制并修改配置文件
cp configs/scz_ofc_huqiang.yaml configs/my_project.yaml

# 2. 运行全流程
python run_all.py -c configs/my_project.yaml

# 3. 跳过数据采集，只做分析和出图
python run_all.py -c configs/my_project.yaml --step 6
```

### 方式二：交互式向导

```bash
python quick_search.py
```

按提示输入疾病、靶点、症状等信息，自动生成配置并运行。

---

## 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        YAML 配置文件                             │
│  (疾病、靶点、症状、申请人信息)                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1-4: 数据采集                                              │
│  ├─ Step 1: LetPub → NSFC 项目                                  │
│  ├─ Step 2: KD → NSFC 项目详情                                  │
│  ├─ Step 3: PubMed → 文献检索                                   │
│  │   ├─ 3b: Burden 查询 (疾病负担)                              │
│  │   └─ 3c: Applicant 查询 (申请人论文)                         │
│  └─ Step 4: NIH Reporter → 美国基金项目                         │
│       ├─ 4b: NIH 资助论文                                       │
│       └─ 4c: NIH Intramural 报告                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: 数据合并 (NSFC LetPub + KD)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: 分析与可视化                                            │
│  ├─ load_data()      → 加载所有数据                             │
│  ├─ classify()       → 研究方向分类                             │
│  ├─ analyze_gaps()   → 空白检测                                 │
│  ├─ analyze_applicant() → 申请人评估                            │
│  ├─ plot()           → 主全景图                                 │
│  ├─ plot_applicant() → 申请人图 + Markdown 报告                 │
│  └─ plot_supplementary() → 补充分析图                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  输出文件                                                        │
│  projects/{项目名}/                                              │
│  ├─ data/         → 原始数据 (CSV/CSV.GZ)                       │
│  ├─ results/      → 分析结果 (gap_counts.csv, 报告.md)          │
│  └─ figs/         → 可视化图表 (PNG/PDF)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
zbib/
├── configs/                    # YAML 配置文件
│   ├── scz_ofc_huqiang.yaml   # 示例: 精神分裂症+OFC+胡强
│   └── addiction_tpj_wangmin.yaml  # 示例: 成瘾+TPJ+汪敏
│
├── scripts/                    # 核心模块
│   ├── config.py              # TopicConfig 配置解析
│   ├── pipeline.py            # Pipeline 流程编排 (核心)
│   ├── fetch.py               # PubMed/NIH API 客户端
│   ├── fetch_letpub.py        # LetPub 爬虫
│   ├── fetch_kd.py            # NSFC KD 爬虫
│   ├── fetch_applicant.py     # 申请人论文检索
│   ├── analyze.py             # 分类器、Gap 分析
│   ├── analyze_applicant.py   # 申请人评估 (薄层)
│   ├── plot.py                # 可视化入口
│   ├── journals.py            # 期刊 IF 数据
│   └── applicant/             # 申请人分析模块
│       ├── profile.py         # ApplicantProfile 数据类
│       ├── analyzer.py        # ApplicantAnalyzer 分析器
│       ├── assessment.py      # 评分与象限定位
│       ├── benchmark.py       # 领域基准排名
│       └── report.py          # Markdown 报告生成
│
├── projects/                   # 项目输出目录
│   └── {项目名}_{日期}/
│       ├── data/              # 原始数据
│       ├── results/           # 分析结果
│       └── figs/              # 图表
│
├── run_all.py                 # CLI 入口 (YAML 驱动)
└── quick_search.py            # 交互式向导
```

---

## YAML 配置说明

```yaml
# 基础信息
name: scz_ofc_huqiang           # 项目标识
title_zh: OFC-rTMS治疗精神分裂症阴性症状
project_dir: "../projects/SCZ_OFC_胡强_20260206"

# 疾病检索
disease_cn_keyword: "精神分裂"   # LetPub 中文检索
disease_cn_filter: "精神分裂症"  # 过滤正则
disease_en_query: "(schizophrenia OR psychosis)"  # PubMed/NIH 检索式

# 干预手段
intervention_query_en: '(TMS OR rTMS OR "brain stimulation")'
intervention_pattern_cn: '经颅磁|TMS|rTMS'
intervention_pattern_en: 'transcranial magnetic|\bTMS\b'

# 症状维度 (用于热力图)
symptoms:
  Negative: 'negative symptom|anhedonia|avolition|alogia'
  Cognitive: 'cogniti|memory|attention|executive'
  Positive: 'positive symptom|hallucin|delusion'

# 脑区靶点
targets:
  OFC: 'orbitofrontal|\bOFC\b|眶额'
  DLPFC: 'DLPFC|dorsolateral prefrontal'
  TPJ: 'temporoparietal|\bTPJ\b'

highlight_target: OFC  # 热力图高亮

# Gap 检测
gap_patterns:
  ofc: 'orbitofrontal|\bOFC\b'
  neg: 'negative symptom|anhedonia'
  tms_cn: '经颅磁|TMS'

gap_combinations:
  PubMed_OFC_Neg: [ofc, neg]
  NIH_OFC_Neg: [ofc, neg]

# Panel E 关键文献
key_papers:
  - year: "2024"
    journal: "Brain Stimul"
    author: "Author et al."
    desc: "OFC-rTMS 治疗阴性症状的首个 RCT"

# 申请人配置 (可选)
applicant:
  name_cn: "胡强"
  name_en: "Qiang Hu"
  affiliations:
    - "Shanghai Mental Health Center"
    - "Zhenjiang Fourth Hospital"
  aliases:
    - "Hu Q"
    - "Q Hu"
  keywords:
    - "schizophrenia"
    - "TMS"
    - "OFC"
```

---

## 常用命令

### 完整流程（含 NSFC 爬虫）

```bash
# 需要 LetPub 账号
python run_all.py -c configs/my_project.yaml \
    --letpub-email your@email.com \
    --letpub-password yourpassword
```

### 仅 PubMed + NIH（跳过 NSFC）

```bash
python run_all.py -c configs/my_project.yaml --skip-fetch
# 或直接只做分析
python run_all.py -c configs/my_project.yaml --step 6
```

### Python API 调用

```python
from scripts.pipeline import Pipeline

# 从 YAML 加载
pipe = Pipeline.from_yaml('configs/my_project.yaml')

# 分步执行
pipe.fetch_pubmed()          # Step 3
pipe.fetch_nih()             # Step 4
pipe.load_data()             # 加载数据
pipe.classify()              # 分类
analysis = pipe.analyze_gaps()  # Gap 分析
pipe.analyze_applicant()     # 申请人分析
pipe.plot_applicant()        # 生成申请人图表
```

---

## 输出文件说明

| 文件 | 说明 |
|------|------|
| `data/pubmed_nibs_*.csv.gz` | PubMed 检索结果 |
| `data/nih_nibs_*.csv.gz` | NIH NIBS 项目 |
| `data/nih_all_*.csv.gz` | NIH 全部项目 |
| `data/applicant_*.csv.gz` | 申请人论文 |
| `results/gap_counts.csv` | 空白统计 |
| `results/applicant_summary.txt` | 申请人摘要 |
| `results/*_report.md` | 详细 Markdown 报告 |
| `figs/*_landscape.png/pdf` | 主全景图 |
| `figs/*_applicant.png/pdf` | 申请人可视化 |

---

## 申请人评估指标

| 维度 | 说明 | 权重 |
|------|------|------|
| 疾病相关度 | 论文中疾病关键词占比 | 25% |
| NIBS专业度 | 论文中 TMS/tDCS 等关键词占比 | 25% |
| 学术独立性 | 第一/通讯作者论文比例 | 20% |
| 学术影响力 | H-index、顶刊论文数 | 15% |
| 研究活跃度 | 近5年发文量 | 15% |

**象限定位**:
- **明星申请人**: 高适配 + 高胜任
- **潜力申请人**: 高适配 + 低胜任
- **跨界申请人**: 低适配 + 高胜任
- **新手申请人**: 低适配 + 低胜任

---

## 常见问题

### Q: LetPub 登录失败？
A: 确保账号密码正确。可用 `--skip-fetch` 跳过 NSFC 步骤。

### Q: PubMed 检索结果为空？
A: 检查 `disease_en_query` 语法，确保使用标准 PubMed 布尔检索式。

### Q: 申请人检索结果过多/过少？
A: 调整 `affiliations` 和 `aliases`，添加更多机构变体或姓名写法。

### Q: 图表生成报错？
A: 确保安装 matplotlib 3.10+，与 NumPy 2.x 兼容。

---

*zbib v2 — 2026-02*
