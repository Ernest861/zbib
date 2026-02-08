# data/ — 预置数据

内置的症状数据库和其他参考数据。

## 症状数据库 (`symptom_db.yaml`)

10 种疾病 × 3-5 症状维度，支持双语正则匹配:

```yaml
schizophrenia:
  name_cn: "精神分裂症"
  symptoms:
    Negative:
      cn: "阴性症状"
      patterns:
        en: "negative|avolition|anhedonia|alogia|anergia"
        cn: "阴性|淡漠|意志|快感缺失"
    Positive:
      cn: "阳性症状"
      patterns:
        en: "positive|hallucination|delusion|thought disorder"
        cn: "阳性|幻觉|妄想|思维障碍"
    Cognitive:
      cn: "认知功能"
      patterns:
        en: "cogniti|memory|attention|executive"
        cn: "认知|记忆|注意|执行功能"
```

## 已收录疾病

| 疾病 | 中文名 | 症状维度数 |
|------|--------|-----------|
| schizophrenia | 精神分裂症 | 5 |
| depression | 抑郁症 | 4 |
| anxiety | 焦虑症 | 3 |
| addiction | 成瘾 | 4 |
| OCD | 强迫症 | 3 |
| PTSD | 创伤后应激障碍 | 4 |
| bipolar | 双相障碍 | 4 |
| ADHD | 注意缺陷多动障碍 | 3 |
| autism | 自闭症 | 3 |
| pain | 慢性疼痛 | 3 |

## 使用方式

```python
import yaml

with open('data/symptom_db.yaml', 'r') as f:
    db = yaml.safe_load(f)

# 获取精神分裂症的阴性症状正则
pattern = db['schizophrenia']['symptoms']['Negative']['patterns']['en']
```

## 扩展

添加新疾病或症状:

```yaml
# 在 symptom_db.yaml 中添加
my_disease:
  name_cn: "我的疾病"
  symptoms:
    Symptom1:
      cn: "症状1中文"
      patterns:
        en: "english|regex|pattern"
        cn: "中文|正则|模式"
```
