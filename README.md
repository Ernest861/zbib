# zbib — YAML驱动的 NIBS 文献空白分析工具
# zh.dmtr@gmail.com
# 20260201

将 NSFC、NIH Reporter、PubMed 三库数据一站式抓取、分类、空白分析、出图。
用一个 YAML 配置文件定义研究课题，`run_all.py` 自动编排全流程，所有产出按标准化项目文件夹组织。

---

## 项目文件夹结构

每个课题在 `projects/` 下生成独立文件夹，包含 5 个子目录：

```
zbib/projects/{项目名}/
├── parameters/    ← 配置YAML副本 + manifest.json
├── data/          ← 所有下载/合并的数据文件
├── scripts/       ← run_info.json (调用命令、复现方式)
├── results/       ← 分析输出表格 (gap_counts, heatmap, ...)
└── figs/          ← 所有图表 (PNG + PDF)
```

**激活方式**：在 YAML 配置中设置 `project_dir` 字段：

```yaml
project_dir: 成瘾_TPJ_社交_20260201   # → projects/成瘾_TPJ_社交_20260201/
```

不设 `project_dir` 时，行为与旧版一致（所有文件写入 `data_dir`）。

**向后兼容**：`load_data()` 优先从 `projects/.../data/` 读取，找不到时自动回退到 `data_dir`（旧的扁平目录），无需迁移旧数据。

---

## 快速开始

```bash
# 0. 首次使用：安装环境
cd zbib
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 两个入口

| | `quick_search.py` | `run_all.py` |
|:---|:---|:---|
| 用途 | **新课题**：生成配置 YAML → 自动跑全流程 | **已有配置**：直接执行或按步骤重跑 |
| 输入 | `-i inputs/xxx.yaml`（简化参数）或交互问答 | `-c configs/xxx.yaml`（完整配置） |
| 适合 | 第一次探索一个新的疾病+靶点+症状组合 | 调参后重跑、只跑分析出图等 |

典型工作流：`quick_search.py` 生成配置 → 之后用 `run_all.py -c` 反复执行。

---

### Step 1: 新课题 — `quick_search.py`（推荐起点）

#### 方式一：YAML 文件模式（推荐）

准备输入参数文件（参考 `inputs/` 目录下的示例）：

```yaml
# inputs/成瘾_TPJ_复吸.yaml
letpub:
  email: "xxx@zjnu.edu.cn"
  password: "***"               # 留空则跳过 NSFC

disease:
  cn_keyword: "成瘾"
  cn_filter: "成瘾|药物依赖|物质滥用"
  en_query: '(addiction OR "substance use disorder")'

intervention:
  preset: "1"                   # 1=NIBS全部, 2=仅TMS

target:
  name: "TPJ"
  en: 'temporoparietal junction|\bTPJ\b'
  cn: "颞顶联合|颞顶交界"

symptom:
  name: "Relapse"
  en: 'relapse|relapsing|reinstatement'
  cn: "复吸|复发"
```

```bash
cd zbib
source venv/bin/activate
python quick_search.py -i inputs/成瘾_TPJ_复吸.yaml
```

#### 方式二：交互问答模式

```bash
python quick_search.py    # 不带 -i，逐步问答
```

### Step 2: 重跑/调参 — `run_all.py`

```bash
# 全流程（从抓取到出图）
python run_all.py -c configs/scz_ofc_rtms.yaml \
  --letpub-email "邮箱" --letpub-password "密码"

# 只跑分析+出图（改了 YAML 参数后快速迭代）
python run_all.py -c configs/scz_ofc_rtms.yaml --step 6

# 跳过爬虫，从合并开始
python run_all.py -c configs/scz_ofc_rtms.yaml --skip-fetch
```

### Step 3: 共现网络分析 — `run_cooccurrence.py`

```bash
# 独立运行（使用硬编码路径，适合 SCZ 旧项目）
python run_cooccurrence.py

# 配置模式（使用 Pipeline 集成，产出写入项目文件夹）
python run_cooccurrence.py -c configs/scz_ofc_rtms.yaml
```

---

## 流程步骤

| Step | 方法 | 数据源 | 产出文件 |
|:---|:---|:---|:---|
| 1 | `fetch_letpub()` | LetPub 逐年下载 | `data/nsfcfund_{keyword}_*.xls` → `_all.xlsx` |
| 2 | `fetch_kd()` | kd.nsfc.cn 详情 | `data/nsfc_kd_{name}.csv` |
| 3 | `fetch_pubmed()` | PubMed NIBS+疾病 | `data/pubmed_nibs_{name}.csv` |
| 3b | `fetch_pubmed_burden()` | PubMed 疾病负担 | `data/pubmed_burden_{name}.csv` |
| 4 | `fetch_nih()` | NIH Reporter 项目 | `data/nih_nibs_{name}.csv`, `data/nih_all_{name}.csv` |
| 4b | `fetch_nih_pubs()` | NIH 关联文献 | `data/nih_pubs_link_{name}.csv`, `data/nih_pubs_full_{name}.csv` |
| 4c | `fetch_intramural()` | NIH Intramural 年报 | `data/nih_intramural_{name}.csv` |
| 5 | `merge_nsfc()` | 合并 LetPub + KD | `data/nsfc_merged_{name}.xlsx` |
| 6 | `load → classify → analyze → plot` | 分析+出图 | `figs/{name}_landscape.png/.pdf` |
| 6+ | `analyze_supplementary → plot_supplementary` | 补充分析 | `figs/{name}_supplementary.png/.pdf` |
| — | `save_results()` | 结果存档 | `results/gap_counts.csv`, `heatmap.csv`, ... |
| — | `_save_manifest()` | 元信息 | `parameters/manifest.json`, `scripts/run_info.json` |

NSFC 数据为可选——没有 LetPub 账号也能先跑 PubMed + NIH 看初步结果。

---

## YAML 配置文件

每个课题一个 YAML（放在 `configs/` 下），核心字段：

```yaml
name: scz_ofc_rtms                   # 文件命名前缀
title_zh: OFC-rTMS治疗精神分裂症阴性症状
title_en: OFC-rTMS for Negative Symptoms of Schizophrenia

# 数据源查询
disease_cn_keyword: "精神分裂"        # LetPub 搜索词
disease_cn_filter: "精神分裂症"        # 后处理过滤正则
disease_en_query: "schizophrenia"     # PubMed/NIH 查询词
data_dir: ../nsfc_data                # 旧数据兼容路径

# 项目文件夹（设了此项才启用标准化结构）
project_dir: SCZ_OFC_rTMS_20260201   # → projects/SCZ_OFC_rTMS_20260201/

# 干预手段（空则用默认 NIBS 全家桶）
intervention_query_en: ""
intervention_pattern_cn: ""
intervention_pattern_en: ""

# 分析维度
symptoms: { Negative: "negative symptom...", Positive: "positive symptom..." }
targets: { DLPFC: "DLPFC|dorsolateral...", OFC: "OFC|orbitofrontal..." }
highlight_target: OFC

# 热力图维度（可选，标签可与 symptoms/targets 不同）
heatmap_symptoms: { Neg: "negative symptom...", Pos: "positive symptom..." }
heatmap_targets: { DLPFC: "dorsolateral...", OFC: "orbitofrontal..." }

# Gap 分析
gap_patterns: { ofc: "OFC|orbitofrontal...", neg: "negative symptom..." }
gap_combinations: { PubMed_OFC_Neg: [ofc, neg], ... }

# Panel E 关键文献
key_papers: [{ year: 2023, journal: "...", author: "...", desc: "..." }]
panel_e_title: "..."
panel_e_summary: "..."

# 疾病负担检索（Panel A）
burden_query: "schizophrenia AND negative symptoms"
```

完整字段参见 `scripts/config.py` 中的 `TopicConfig` 和 `ProjectLayout` 类定义。

---

## Python API（交互式使用）

```python
from scripts.pipeline import Pipeline

pipe = Pipeline.from_yaml('configs/scz_ofc_rtms.yaml')

# 单独执行某一步
pipe.fetch_pubmed()
pipe.fetch_nih()

# 分析+出图
pipe.load_data()
pipe.classify()
analysis = pipe.analyze_gaps()
pipe.save_results(analysis)              # → results/
data = pipe.build_plot_data(analysis)
pipe.plot(data)                          # → figs/

# 补充分析
supp = pipe.analyze_supplementary()
pipe.plot_supplementary(supp)            # → figs/

# 共现网络（集成模式）
pipe.run_cooccurrence()                  # → figs/ + results/

# 保存复现信息
pipe._save_manifest()                    # → parameters/ + scripts/
```

### 单独使用 fetch 客户端

```python
from scripts.fetch import PubMedClient, NIHClient

pm = PubMedClient()
df = pm.search('(rTMS OR TMS) AND schizophrenia')

nih = NIHClient()
df = nih.search('schizophrenia', fy_min=2015)

# NIH 项目 → 关联文献
link_df, full_df = nih.fetch_publications_full(
    ['R01MH112189', 'R01MH123456'], pubmed_client=pm)
```

---

## 文件结构

```
zbib/
├── run_all.py                  # 主入口
├── run_cooccurrence.py         # 共现网络分析入口
├── quick_search.py             # 新课题快速检索入口
├── requirements.txt
├── configs/                    # 完整 YAML 配置
│   ├── scz_ofc_rtms.yaml
│   └── tic_ofc_pu.yaml
├── inputs/                     # quick_search 简化输入
│   └── 成瘾_TPJ_复吸.yaml
├── scripts/                    # 核心代码库
│   ├── config.py               #   TopicConfig + ProjectLayout
│   ├── pipeline.py             #   全流程编排
│   ├── fetch.py                #   PubMedClient, NIHClient
│   ├── fetch_letpub.py         #   LetPub 浏览器爬虫
│   ├── fetch_kd.py             #   kd.nsfc.cn 爬虫
│   ├── fetch_intramural.py     #   NIH Intramural 爬虫
│   ├── transform.py            #   数据合并 & 清洗
│   ├── analyze.py              #   分类 & 空白分析
│   ├── keywords.py             #   关键词分析 & 趋势预测
│   ├── network.py              #   共现网络
│   ├── performance.py          #   PI/机构排名
│   ├── quality.py              #   数据质量评估
│   ├── journals.py             #   顶刊列表
│   └── plot.py                 #   出图
├── projects/                   # 项目产出（每个课题一个文件夹）
│   ├── 成瘾_TPJ_社交_20260201/
│   │   ├── parameters/         #   YAML副本 + manifest.json
│   │   ├── data/               #   PubMed/NIH/NSFC 数据文件
│   │   ├── scripts/            #   run_info.json (复现命令)
│   │   ├── results/            #   gap_counts.csv, heatmap.csv, ...
│   │   └── figs/               #   landscape + supplementary PNG/PDF
│   └── 肥胖_OFC_OE_20260131/
│       └── ...
└── venv/
```

---

## 技术备忘

- LetPub 下载的 `.xls` 是 OLE2 格式，需 `xlrd` + `ignore_workbook_corruption=True`
- LetPub 搜索"精神分裂"会模糊匹配"精神"和"分裂"，需后处理 `disease_cn_filter` 过滤
- LetPub 某些年份可能返回 404（网络问题），重试通常可恢复；确认 0 条时属正常
- NIH Reporter API `offset` 上限 14,999，大结果集自动按 `fiscal_year` 分批
- PubMed E-utilities 无 API key 限制 3 req/s
- LetPub 页面用 `wait_until="domcontentloaded"`（`"networkidle"` 会超时）
- NSFC 数据可选：无 LetPub 账号时仍可跑 PubMed + NIH 分析
- `heatmap_symptoms`/`heatmap_targets` 支持与 `symptoms`/`targets` 不同的短标签
