# projects/ — 项目输出目录 (v2.3)

每个分析项目的数据和结果独立存储。

## 目录结构

```
projects/
└── {疾病_靶点_症状_申请人_日期}/
    ├── parameters/     # 配置
    │   ├── example.yaml       # YAML 配置副本
    │   └── manifest.json      # 运行元信息
    │
    ├── data/           # 原始数据 (12 文件)
    │   ├── pubmed_tms_scz.csv               # PubMed NIBS+疾病
    │   ├── pubmed_burden_scz_ofc_rtms.csv   # PubMed 疾病负担
    │   ├── nih_scz_all.csv                  # NIH 全部项目
    │   ├── nih_tms_scz.csv                  # NIH NIBS 项目
    │   ├── nsfc_精神分裂症_clean.xlsx         # NSFC 过滤后
    │   ├── nsfc_merged_精神分裂症.xlsx        # NSFC 合并数据
    │   ├── nsfc_kd_*.csv                    # NSFC KD 详情
    │   ├── nsfcfund_*_all.xlsx              # NSFC LetPub 原始
    │   ├── applicant_*_all.csv.gz           # 申请人全部文献
    │   ├── applicant_*_disease.csv.gz       # 申请人疾病相关
    │   ├── applicant_*_nibs.csv.gz          # 申请人 NIBS 相关
    │   └── applicant_*_disease_nibs.csv.gz  # 申请人疾病+NIBS
    │
    ├── results/        # 分析结果 (9 文件)
    │   ├── gap_counts.csv              # 空白统计
    │   ├── heatmap.csv                 # 靶区×症状交叉表
    │   ├── pubmed_symptoms.csv         # 症状分类
    │   ├── pubmed_targets.csv          # 靶点分类
    │   ├── applicant_summary.txt       # 申请人摘要
    │   ├── {Name}_report.md            # 申请人完整报告
    │   ├── NSFC标书支撑材料.md           # 标书创新性论证材料
    │   ├── nsfc_network_evolution.csv  # NSFC 共现演变
    │   └── nih_network_evolution.csv   # NIH 共现演变
    │
    ├── figs/           # 图表 (15 文件)
    │   ├── *_landscape.png/.pdf              # 主全景图 (8×6 in)
    │   ├── *_supplementary.png/.pdf          # 补充分析图 (8×5.5 in)
    │   ├── *_applicant_extended_p1.png/.pdf  # 申请人图第1页 (8×6 in)
    │   ├── *_applicant_extended_p2.png/.pdf  # 申请人图第2页 (8×4 in)
    │   ├── NSFC_共现网络演变.png/.pdf         # NSFC 共现演变
    │   ├── NIH_cooccurrence_evolution.png/.pdf
    │   ├── knowledge_graph.html              # 交互式知识图谱 (v2.3)
    │   └── knowledge_graph.json              # 知识图谱数据
    │
    ├── scripts/        # 复现信息
    │   └── run_info.json
    │
    └── full_report.html  # 综合 HTML 报告 (v2.3)
```

## 快速命令

```bash
# 创建新项目
python zbib.py new

# 运行完整分析
python zbib.py run configs/example.yaml

# 诊断项目完整性 (0-100 评分)
python zbib.py diagnose projects/xxx

# 生成知识图谱
python zbib.py kg projects/xxx

# 生成综合报告
python zbib.py report projects/xxx
```

## 输出文件说明

### data/ — 原始数据

| 文件模式 | 内容 | 来源 |
|----------|------|------|
| `pubmed*.csv` | PubMed 检索结果 | E-utilities API |
| `nih_*_all.csv` | NIH 全部相关项目 | NIH Reporter API |
| `nih_tms*.csv` | NIH NIBS 项目 | NIH Reporter API |
| `nsfc_*.xlsx` | NSFC 项目 | LetPub / kd.nsfc.cn |
| `applicant_*_all.csv.gz` | 申请人全部文献 | PubMed |
| `applicant_*_disease_nibs.csv.gz` | 申请人疾病+NIBS交集 | PubMed (本地过滤) |

### results/ — 分析结果

| 文件 | 内容 |
|------|------|
| `gap_counts.csv` | 各维度文献/项目数量统计 |
| `heatmap.csv` | 靶区×症状交叉表 |
| `applicant_summary.txt` | 申请人概况 (适配度/胜任力/象限) |
| `{Name}_report.md` | 完整申请人分析报告 |
| `NSFC标书支撑材料.md` | 标书创新性论证材料 |

### figs/ — 图表

| 文件 | 尺寸 | 内容 |
|------|------|------|
| `*_landscape.pdf` | 8×6 in | 主全景图 (6 panel) |
| `*_supplementary.pdf` | 8×5.5 in | 补充分析图 (资助趋势、新兴关键词等) |
| `*_applicant_*_p1.pdf` | 8×6 in | 申请人图 (时间线、雷达、期刊) |
| `*_applicant_*_p2.pdf` | 8×4 in | 申请人图 (合作网络、研究轨迹) |
| `knowledge_graph.html` | 交互式 | D3.js 知识图谱 (概念+作者双层网络) |
| `full_report.html` | 综合报告 | 整合所有分析结果 |

## 图表尺寸标准

符合学术期刊出版要求:
- 最大宽度: 8 英寸
- 最大高度: 6.5 英寸
- 字体: 6-8 pt
- 分辨率: 300 dpi

## 诊断评分规则

| 类别 | 必需文件 (15分/个) | 可选文件 (5分/个) |
|------|-------------------|-------------------|
| data | `pubmed*.csv`, `nih*.csv` | `nsfc*.csv`, `applicant_*.csv*` |
| results | `heatmap.csv`, `gap_counts.csv` | `NSFC标书支撑材料.md`, `applicant_summary.txt` |
| figs | `*landscape*.png`, `*landscape*.pdf` | `knowledge_graph.html`, `*applicant*.png`, `*supplementary*.pdf` |

满分 100，>= 70 为合格。

## 管理项目

```bash
# 诊断状态
python zbib.py diagnose projects/xxx

# 删除某个项目
rm -rf projects/xxx/

# 重新运行分析 (保留数据)
python run_all.py -c configs/example.yaml --step 6
```
