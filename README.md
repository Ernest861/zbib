# zbib — NIBS 文献空白分析工具

**版本 2.3** — 新增知识图谱可视化 + 统一 CLI

> 用于国自然标书创新性论证的文献情报学分析

将 NSFC、NIH Reporter、PubMed 三库数据一站式抓取、分类、空白分析、出图。

---

## 2.3 新功能

### 统一命令行入口

```bash
python zbib.py new              # 创建新项目
python zbib.py run config.yaml  # 运行分析
python zbib.py diagnose project # 诊断项目状态
python zbib.py report project   # 生成 HTML 报告
python zbib.py kg project       # 生成知识图谱
```

### 交互式知识图谱

D3.js 力导向图可视化，支持：
- **双层网络**: 概念共现 + 作者合作 + 跨层链接
- **实时控制**: 节点数、边权重、间距、排斥力
- **视图模式**: 全部联动 / 仅概念 / 仅作者
- **中心性算法**: 度中心性 / 权重 / PageRank
- **交互功能**: 搜索、缩放、双击聚焦、PNG 导出

### 项目诊断

```bash
python zbib.py diagnose projects/xxx
```
自动检查数据完整性，0-100 评分，给出改进建议。

### 综合 HTML 报告

```bash
python zbib.py report projects/xxx
```
整合热力图、全景图、申请人评估、知识图谱、标书建议为单一报告。

---

## 极简模式 (推荐新用户)

只需 **4 个关键词**，自动完成全部分析：

```bash
./venv/bin/python quick_start.py
```

```
1. 疾病: 精神分裂症
2. 靶点: OFC
3. 症状: 阴性症状
4. 申请人: 胡强
   英文名: Qiang Hu
   单位: Shanghai Mental Health Center
```

自动完成：检索 → 分类 → 空白检测 → 申请人评估 → 出图 → 生成标书材料

### 已有项目直接运行

```bash
# OFC-rTMS 治疗精神分裂症阴性症状 (胡强)
./venv/bin/python run_scz_ofc.py

# 通用方式
./venv/bin/python run_all.py -c configs/xxx.yaml --step 6
```

### 输出文件

| 文件 | 说明 |
|------|------|
| `results/NSFC标书支撑材料.md` | **直接用于标书创新性论证** |
| `results/{name}_report.md` | 申请人完整分析报告 |
| `figs/*_landscape.pdf` | 主全景图 (8×6 in) |
| `figs/*_supplementary.pdf` | 补充分析图 (8×5.5 in) |
| `figs/*_applicant_p1.pdf` | 申请人图第1页 (8×6 in) |
| `figs/*_applicant_p2.pdf` | 申请人图第2页 (8×4 in) |
| `figs/knowledge_graph.html` | 交互式知识图谱 |
| `full_report.html` | 综合 HTML 报告 |

---

## 版本历史

### v2.3 (2026-02-09)
- 统一 CLI 入口 (`zbib.py`)
- 知识图谱可视化 (D3.js 交互式，概念+作者双层网络)
- 项目诊断工具 (`diagnose` 命令)
- 综合 HTML 报告生成器
- 可视化优化：白底配色、标签背景、权重渐变透明度

### v2.0 (2026-02-07)
- 申请人前期基础分析
- 适配度 + 胜任力双维度评分
- 象限定位：明星/潜力/跨界/边缘申请人
- 领域基准排名（百分位）
- 超图合作网络（Battiston 2025）
- 研究轨迹关键词演变

### v1.0
- 三库数据抓取（NSFC/NIH/PubMed）
- 研究空白热力图
- 全景图出图

---

## 三种使用方式

| 方式 | 命令 | 输入 | 适用 |
|------|------|------|------|
| **CLI** | `zbib.py` | 子命令 | 推荐 |
| **极简** | `quick_start.py` | 4个关键词 | 快速试探 |
| **向导** | `quick_search.py` | 交互问答 | 详细配置 |
| **配置** | `run_all.py -c` | YAML文件 | 精细调整 |

### 支持的关键词

<details>
<summary>点击展开</summary>

**疾病**: 精神分裂症、抑郁症、成瘾、焦虑、强迫症、帕金森、阿尔茨海默、癫痫、中风

**靶点**: OFC、DLPFC、TPJ、mPFC、ACC、M1、SMA、Insula、Cerebellum

**症状**: 阴性症状、阳性症状、认知、情绪、运动、疼痛、睡眠、焦虑、抑郁、冲动、渴求

</details>

---

## 项目文件夹结构

每个课题在 `projects/` 下生成独立文件夹：

```
zbib/projects/{项目名}/
├── parameters/    ← 配置YAML副本 + manifest.json
├── data/          ← 所有下载/合并的数据文件
├── scripts/       ← run_info.json (调用命令、复现方式)
├── results/       ← 分析输出 (gap_counts, heatmap, 标书材料)
├── figs/          ← 所有图表 (PNG + PDF + HTML)
└── full_report.html ← 综合报告
```

**激活方式**：在 YAML 配置中设置 `project_dir` 字段：

```yaml
project_dir: 成瘾_TPJ_社交_20260201   # → projects/成瘾_TPJ_社交_20260201/
```

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

### CLI 命令 (推荐)

```bash
# 创建新项目
python zbib.py new

# 运行分析
python zbib.py run configs/my_project.yaml

# 诊断项目状态
python zbib.py diagnose projects/xxx

# 生成知识图谱
python zbib.py kg projects/xxx

# 生成综合报告
python zbib.py report projects/xxx
```

### 传统入口

```bash
# 全流程（从抓取到出图）
python run_all.py -c configs/scz_ofc_rtms.yaml \
  --letpub-email "邮箱" --letpub-password "密码"

# 只跑分析+出图
python run_all.py -c configs/scz_ofc_rtms.yaml --step 6

# 跳过爬虫，从合并开始
python run_all.py -c configs/scz_ofc_rtms.yaml --skip-fetch
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
| — | `kg` | 知识图谱 | `figs/knowledge_graph.html/.json` |
| — | `report` | 综合报告 | `full_report.html` |

NSFC 数据为可选——没有 LetPub 账号也能先跑 PubMed + NIH 看初步结果。

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

# 知识图谱
from scripts.knowledge_graph import KnowledgeGraph
kg = KnowledgeGraph()
kg.build_from_papers(df, concept_col=['keywords', 'mesh'])
kg.export_interactive('figs/knowledge_graph.html')

# 项目诊断
from scripts.diagnostic import diagnose_project, print_diagnostic
result = diagnose_project('projects/xxx')
print_diagnostic(result)

# 综合报告
from scripts.report_generator import generate_full_report
generate_full_report('projects/xxx')
```

---

## 文件结构

```
zbib/
├── zbib.py                     # 统一 CLI 入口 (v2.3)
├── run_all.py                  # 传统入口
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
│   ├── knowledge_graph.py      #   知识图谱可视化 (v2.3)
│   ├── diagnostic.py           #   项目诊断 (v2.3)
│   ├── report_generator.py     #   综合报告生成 (v2.3)
│   ├── progress.py             #   进度显示 (v2.3)
│   ├── performance.py          #   PI/机构排名
│   ├── quality.py              #   数据质量评估
│   ├── journals.py             #   顶刊列表
│   └── plot.py                 #   出图
├── projects/                   # 项目产出（每个课题一个文件夹）
│   └── {项目名}/
│       ├── parameters/         #   YAML副本 + manifest.json
│       ├── data/               #   PubMed/NIH/NSFC 数据文件
│       ├── scripts/            #   run_info.json (复现命令)
│       ├── results/            #   gap_counts.csv, heatmap.csv, ...
│       ├── figs/               #   landscape + KG + supplementary
│       └── full_report.html    #   综合 HTML 报告
└── venv/
```

---

## 技术备忘

- LetPub 下载的 `.xls` 是 OLE2 格式，需 `xlrd` + `ignore_workbook_corruption=True`
- LetPub 搜索"精神分裂"会模糊匹配"精神"和"分裂"，需后处理 `disease_cn_filter` 过滤
- NIH Reporter API `offset` 上限 14,999，大结果集自动按 `fiscal_year` 分批
- PubMed E-utilities 无 API key 限制 3 req/s
- NSFC 数据可选：无 LetPub 账号时仍可跑 PubMed + NIH 分析
- NumPy 2.x 与旧版 matplotlib 不兼容，使用 `sys.modules` 补丁绕过
