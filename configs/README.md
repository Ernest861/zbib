# configs/ — 项目配置文件

YAML 格式的项目配置，定义检索主题和参数。

## 配置结构

```yaml
# 项目名称
name: "精神分裂症_OFC_Negative_胡强"

# 核心维度
disease: "schizophrenia"      # 疾病
disease_cn: "精神分裂症"       # 疾病中文名
target: "OFC"                  # 靶点
symptom: "Negative"            # 症状

# 检索式
search_queries:
  pubmed: "(TMS OR rTMS OR TBS OR TUS) AND schizophrenia"
  nih: "(TMS OR rTMS) AND schizophrenia"
  nsfc: "精神分裂 AND 磁刺激"

# 申请人信息
applicant:
  name_cn: "胡强"
  name_en: "Qiang Hu"
  affiliation: "Shanghai Mental Health Center"
  keywords: ["schizophrenia", "rTMS", "OFC"]
  aliases: ["Q Hu", "Hu Q"]

# 可选: 症状/靶点正则
symptom_patterns:
  Negative: "negative|avolition|anhedonia|alogia"
  Positive: "positive|hallucination|delusion"

target_patterns:
  OFC: "OFC|orbitofrontal"
  DLPFC: "DLPFC|dorsolateral"

# 输出设置
output:
  project_dir: "projects/精神分裂症_OFC_Negative_胡强"
  fig_format: ["png", "pdf"]
```

## 示例文件

| 文件 | 用途 |
|------|------|
| `example.yaml` | 完整配置示例 (OFC-rTMS 治疗精神分裂症阴性症状) |

## 关键字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✓ | 项目标识 |
| `disease` | ✓ | 疾病英文名 (用于检索) |
| `target` | ✓ | 靶点缩写 |
| `symptom` | ✓ | 症状维度 |
| `applicant.name_cn` | ✓ | 申请人中文名 |
| `applicant.name_en` | ✓ | 申请人英文名 (用于 PubMed 检索) |
| `applicant.affiliation` | | 单位 (提高检索精度) |
| `symptom_patterns` | | 自定义症状匹配正则 |
| `target_patterns` | | 自定义靶点匹配正则 |

## 快速生成

使用交互式向导自动生成配置:

```bash
python quick_search.py
```

向导流程:
1. 选择疾病类型
2. 输入靶点
3. 选择/输入症状
4. 输入申请人信息
5. 确认并生成 YAML
