# projects/ — 项目输出目录

每个分析项目的数据和结果独立存储。

## 目录结构

```
projects/
└── {项目名称}/
    ├── data/           # 原始数据
    │   ├── pubmed.csv         # PubMed 文献
    │   ├── nih_all.csv        # NIH 全部项目
    │   ├── nih_nibs.csv       # NIH NIBS 项目
    │   ├── nsfc.csv           # NSFC 项目
    │   └── applicant.csv      # 申请人文献
    │
    ├── results/        # 分析结果
    │   ├── gap_counts.csv          # 空白统计
    │   ├── heatmap.csv             # 热力图数据
    │   ├── pubmed_symptoms.csv     # 症状分类
    │   ├── pubmed_targets.csv      # 靶点分类
    │   ├── applicant_summary.txt   # 申请人摘要
    │   ├── {name}_report.md        # 申请人报告
    │   ├── NSFC标书支撑材料.md      # NSFC 报告
    │   └── *_network_evolution.csv # 共现网络演变
    │
    └── figs/           # 图表
        ├── *_landscape.pdf              # 主全景图 (8×6 in)
        ├── *_supplementary.pdf          # 补充图 (8×5.5 in)
        ├── *_applicant_extended_p1.pdf  # 申请人图第1页
        ├── *_applicant_extended_p2.pdf  # 申请人图第2页
        ├── NSFC_共现网络演变.pdf         # NSFC 共现演变
        └── NIH_cooccurrence_evolution.pdf
```

## 输出文件说明

### data/ 目录

| 文件 | 内容 | 来源 |
|------|------|------|
| `pubmed.csv` | PubMed 检索结果 | E-utilities API |
| `nih_all.csv` | NIH 全部相关项目 | NIH Reporter API |
| `nih_nibs.csv` | NIH NIBS 项目 | NIH Reporter API |
| `nsfc.csv` | NSFC 项目 | LetPub / kd.nsfc.cn |
| `applicant.csv` | 申请人发表文献 | PubMed |

### results/ 目录

| 文件 | 内容 |
|------|------|
| `gap_counts.csv` | 各维度文献/项目数量统计 |
| `heatmap.csv` | 靶区×症状交叉表 |
| `applicant_summary.txt` | 申请人概况文本 |
| `{name}_report.md` | 完整申请人分析报告 |
| `NSFC标书支撑材料.md` | 标书创新性论证材料 |

### figs/ 目录

| 文件 | 尺寸 | 内容 |
|------|------|------|
| `*_landscape.pdf` | 8×6 in | 主全景图 (6 panel) |
| `*_supplementary.pdf` | 8×5.5 in | 补充分析图 |
| `*_applicant_extended_p1.pdf` | 8×6 in | 申请人图 (时间线、雷达、期刊、论文) |
| `*_applicant_extended_p2.pdf` | 8×4 in | 申请人图 (合作网络、研究轨迹) |

## 图表尺寸标准

符合学术期刊出版要求:
- 最大宽度: 8 英寸
- 最大高度: 6.5 英寸
- 字体: 6-8 pt
- 分辨率: 300 dpi

## 清理旧项目

```bash
# 删除某个项目
rm -rf projects/项目名称/

# 保留配置重新运行
python quick_search.py  # 或 pipeline.run()
```
