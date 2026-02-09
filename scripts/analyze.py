"""数据分析: 分类、维度计数、空白检测"""

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CategorySet:
    """可配置的分类体系: (名称, 正则) 列表，按优先级排序"""
    categories: list[tuple[str, str]]
    default_label: str = "其他"


class TextClassifier:
    """互斥正则分类器 — 按优先级匹配第一个命中的类别"""

    def __init__(self, category_set: CategorySet):
        self.categories = [
            (name, re.compile(pattern, re.I))
            for name, pattern in category_set.categories
        ]
        self.default_label = category_set.default_label

    def classify(self, texts) -> pd.Series:
        result = []
        for text in texts:
            assigned = self.default_label
            t = str(text)
            for name, pat in self.categories:
                if pat.search(t):
                    assigned = name
                    break
            result.append(assigned)
        return pd.Series(result)

    @staticmethod
    def merge_categories(series: pd.Series, merge_map: dict) -> pd.Series:
        return series.map(lambda x: merge_map.get(x, x))


class AspectClassifier:
    """维度分类器 — 统计每个维度的匹配数（非互斥）"""

    def __init__(self, aspects: dict[str, str]):
        """aspects: {名称: 正则模式}"""
        self.aspects = {
            name: re.compile(pattern, re.I)
            for name, pattern in aspects.items()
        }

    def count(self, texts) -> dict[str, int]:
        result = {k: 0 for k in self.aspects}
        for text in texts:
            t = str(text)
            for name, pat in self.aspects.items():
                if pat.search(t):
                    result[name] += 1
        return result

    def build_matrix(self, texts, row_aspects: 'AspectClassifier', col_aspects: 'AspectClassifier',
                      include_other: bool = True) -> pd.DataFrame:
        """构建交叉计数矩阵 (row_aspects × col_aspects)

        Args:
            texts: 文本序列
            row_aspects: 行维度分类器（如症状）
            col_aspects: 列维度分类器（如靶点）
            include_other: 是否添加 "Other" 行（不属于任何行维度的文献）

        Returns:
            DataFrame，行=症状，列=靶点，值=交集文献数
        """
        import numpy as np
        rows = list(row_aspects.aspects.keys())
        cols = list(col_aspects.aspects.keys())

        # 如果需要 Other 行，添加到末尾
        if include_other:
            rows_with_other = rows + ['Other']
            matrix = np.zeros((len(rows) + 1, len(cols)))
        else:
            rows_with_other = rows
            matrix = np.zeros((len(rows), len(cols)))

        for text in texts:
            t = str(text)
            # 检查每个列（靶点）
            for ci, ck in enumerate(cols):
                if col_aspects.aspects[ck].search(t):
                    # 检查行（症状），记录是否匹配到任何症状
                    matched_any_row = False
                    for ri, rk in enumerate(rows):
                        if row_aspects.aspects[rk].search(t):
                            matrix[ri, ci] += 1
                            matched_any_row = True
                    # 如果没有匹配任何症状，计入 Other
                    if include_other and not matched_any_row:
                        matrix[len(rows), ci] += 1

        return pd.DataFrame(matrix, index=rows_with_other, columns=cols)


class GapAnalyzer:
    """空白检测: 计算模式组合在文本中的命中数"""

    def __init__(self, patterns: dict[str, str]):
        """patterns: {名称: 正则模式}"""
        self.patterns = {
            name: re.compile(pat, re.I)
            for name, pat in patterns.items()
        }

    def count_combinations(self, texts, combinations: dict[str, list[str]]) -> dict[str, int]:
        """计算指定的模式组合。
        combinations: {组合名: [模式名1, 模式名2, ...]}
        返回每个组合名命中的文本数。
        """
        result = {}
        for combo_name, pat_names in combinations.items():
            pats = [self.patterns[n] for n in pat_names]
            count = 0
            for text in texts:
                t = str(text)
                if all(p.search(t) for p in pats):
                    count += 1
            result[combo_name] = count
        return result

    def identify_gaps(self, counts: dict[str, int], threshold: int = 0) -> list[str]:
        """返回命中数 <= threshold 的组合名列表"""
        return [name for name, cnt in counts.items() if cnt <= threshold]


# ═══════════════════════════════════════════════
# 预置分类体系
# ═══════════════════════════════════════════════

NSFC_SCZ_CATEGORIES = CategorySet([
    ('神经调控', r'经颅磁|TMS|rTMS|tDCS|经颅直流|经颅电|神经调控|脑刺激|磁刺激|电刺激|DBS|深部脑|theta.?burst|TBS|超声刺激|TUS'),
    ('临床/药物', r'临床试验|随机对照|RCT|疗效|药物治疗|抗精神病|氯氮平|利培酮|奥氮平|阿立哌唑|长效针剂|联合治疗|增效|音乐治疗|干预[效模]|用药体验|共享决策|难治性.*治疗|精准识别.*治疗'),
    ('神经影像', r'fMRI|功能磁共振|静息态|PET|SPECT|DTI|脑结构|灰质|白质|MRI|磁共振成像|脑影像|皮层厚度|神经影像|多模态影像|脑萎缩|影像分型|影像.*模型|脑老化'),
    ('电生理', r'EEG|脑电|ERP|事件相关|MEG|脑磁图|近红外|fNIRS|MMN|P50|P300|gamma振荡'),
    ('遗传/组学', r'基因|SNP|多态|GWAS|全基因组|表观遗传|甲基化|miRNA|lncRNA|circRNA|转录|遗传|易感|COMT|DISC1|NRG1|多组学|外泌体|外囊泡|类器官|剪接|突变|变异.*机制|HERV|神经发育.*机制'),
    ('免疫/代谢', r'免疫|炎症|细胞因子|IL-|TNF|补体|小胶质|星形胶质|代谢|氧化应激|肠脑|肠道菌|肠道.*菌|口腔.*菌|PM2\.?5|环境暴露|饥荒|内质网|焦亡|NLRP'),
    ('环路/机制', r'环路|通路|前额叶|纹状体|伏隔核|杏仁核|海马|丘脑|前扣带|突触可塑|功能连接|脑网络|默认网络|神经振荡|眶额|OFC|小脑|基底[节神]|突触.*蛋白|D2R'),
    ('神经递质', r'多巴胺|5-HT|5-羟色胺|谷氨酸|GABA|NMDA|dopamin|serotonin|受体(?!器)|神经递质|乙酰胆碱|GluN'),
    ('认知/行为', r'认知功能|工作记忆|执行功能|社会认知|心理理论|情绪识别|认知训练|认知矫正|神经心理|注意缺|快感缺失|自我缺损|表情识别|疼痛感知|感知缺损|听觉感知|反应抑制|人际互动|计算精神病学|类脑|序列预测'),
    ('动物模型', r'动物模型|小鼠|大鼠|模型鼠|造模|MK-801|PCP|转基因小鼠|行为学|前脉冲抑制|PPI|树鼩'),
    ('流行病/康复', r'流行病|患病率|发病率|社会功能|生活质量|康复|社区|家属|病耻感|照顾者|服务参与|气温.*精神|时空演变'),
])

# 通用别名 (兼容新pipeline)
NSFC_NEURO_CATEGORIES = NSFC_SCZ_CATEGORIES

NIH_SCZ_CATEGORIES = CategorySet(
    categories=[
        ('Neuromodulation', r'transcranial magnetic|\bTMS\b|\brTMS\b|\btDCS\b|transcranial direct|brain stimulation|transcranial ultrasound|\bTUS\b|\bDBS\b|deep brain stimul|theta.?burst|\bECT\b|electroconvulsive'),
        ('Clinical/Pharma', r'clinical trial|randomized|\bRCT\b|efficacy|drug therapy|antipsychotic|clozapine|risperidone|olanzapine|aripiprazole|haloperidol|pharmacother|treatment.?resistan|medication|drug.?develop|side effect|tardive|metabolic syndrome'),
        ('Neuroimaging', r'\bfMRI\b|functional magnetic|resting.?state|\bPET\b|\bSPECT\b|\bDTI\b|diffusion tensor|gray matter|white matter|cortical thick|brain imag|neuroimag|structural MRI|brain morpho|voxel'),
        ('Electrophysiology', r'\bEEG\b|electroencephalog|\bERP\b|event.?related potential|\bMEG\b|magnetoencephalog|\bfNIRS\b|mismatch negativity|\bMMN\b|P50|P300|gamma oscillat|neural oscillat'),
        ('Genetics/Omics', r'\bgene\b|\bSNP\b|polymorphism|\bGWAS\b|genome.?wide|epigenetic|methylation|\bmiRNA\b|transcript|genetic|susceptib|\bCOMT\b|\bDISC1\b|\bNRG1\b|copy number|exome|sequencing|polygenic|heritab|chromatin|\bRNA.?seq'),
        ('Immune/Metabolic', r'immun|inflammat|cytokine|interleukin|\bTNF\b|complement|microglia|astrocyte|metaboli[sc]|oxidative stress|gut.?brain|microbiom|neuroinflam'),
        ('Circuit/Mechanism', r'circuit|pathway|prefrontal|striatum|striatal|nucleus accumbens|amygdala|hippocamp|thalam|anterior cingulate|synaptic plasticity|functional connectiv|brain network|default mode|neural circuit|orbitofrontal|\bOFC\b|cerebellum|basal ganglia|reward circuit|dopamine circuit'),
        ('Neurotransmitter', r'\bdopamine\b|\bserotonin\b|\b5-HT\b|\bglutamate\b|\bGABA\b|\bNMDA\b|receptor binding|neurotransmit|acetylcholine|cholinergic|D[12] receptor|glycine'),
        ('Cognition/Behavior', r'cogniti[vo]|working memory|executive function|social cognition|theory of mind|emotion recognit|cognitive train|cognitive remed|neuropsycholog|attention deficit|anhedonia|self.?referenc|computational psychiatry'),
        ('Animal Model', r'animal model|\bmice\b|\bmouse\b|\brat[s]?\b|\brodent|transgenic|knockout|prepulse inhibition|\bPPI\b|preclinical'),
        ('Epidemiology/Rehab', r'epidemiolog|prevalence|incidence|risk factor|social function|quality of life|rehab|community|caregiver|stigma|psychosocial|vocational|supported employ|first.?episode.*outcome'),
    ],
    default_label="Other",
)

NIH_NEURO_CATEGORIES = NIH_SCZ_CATEGORIES


# ═══════════════════════════════════════════════
# 时间趋势检测
# ═══════════════════════════════════════════════

class TrendDetector:
    """时间趋势检测: 拐点、CAGR、上升/下降类别"""

    def detect_inflections(self, year_counts: pd.Series, threshold: float = 0.5) -> list[dict]:
        """拐点检测 — 同比增长率突变点

        Parameters
        ----------
        year_counts : Series indexed by year, values = count
        threshold : 增长率变化(Δgrowth)超过此阈值视为拐点

        Returns
        -------
        list of {'year': int, 'growth_before': float, 'growth_after': float, 'delta': float}
        """
        years = sorted(year_counts.index)
        if len(years) < 3:
            return []

        # Compute year-over-year growth rates
        growths = {}
        for i in range(1, len(years)):
            prev = year_counts[years[i - 1]]
            curr = year_counts[years[i]]
            if prev > 0:
                growths[years[i]] = (curr - prev) / prev
            else:
                growths[years[i]] = 0.0

        # Detect inflections: large change in growth rate
        inflections = []
        growth_years = sorted(growths.keys())
        for i in range(1, len(growth_years)):
            y = growth_years[i]
            delta = growths[y] - growths[growth_years[i - 1]]
            if abs(delta) >= threshold:
                inflections.append({
                    'year': y,
                    'growth_before': round(growths[growth_years[i - 1]], 3),
                    'growth_after': round(growths[y], 3),
                    'delta': round(delta, 3),
                })

        return inflections

    def growth_rates(self, year_cat_df: pd.DataFrame, year_col: str = 'year',
                     cat_col: str = 'category') -> pd.DataFrame:
        """每个类别的CAGR(复合年增长率)

        Parameters
        ----------
        year_cat_df : 长格式 DataFrame，包含 year 和 category 列
        """
        counts = year_cat_df.groupby([year_col, cat_col]).size().unstack(fill_value=0)

        results = []
        for cat in counts.columns:
            series = counts[cat]
            years = sorted(series.index)
            if len(years) < 2:
                continue
            first_val = series[years[0]]
            last_val = series[years[-1]]
            n_years = years[-1] - years[0]
            if first_val > 0 and n_years > 0:
                cagr = (last_val / first_val) ** (1 / n_years) - 1
            else:
                cagr = 0.0
            results.append({
                'category': cat,
                'first_year': years[0],
                'last_year': years[-1],
                'first_count': int(first_val),
                'last_count': int(last_val),
                'cagr': round(cagr, 4),
            })

        return pd.DataFrame(results).sort_values('cagr', ascending=False)

    def emerging_declining(self, year_cat_df: pd.DataFrame, recent: int = 5,
                           year_col: str = 'year', cat_col: str = 'category') -> dict:
        """近N年上升/下降类别

        比较最近 recent 年与之前同样长度时期的均值。
        返回 {'emerging': [...], 'declining': [...]}
        """
        counts = year_cat_df.groupby([year_col, cat_col]).size().unstack(fill_value=0)
        years = sorted(counts.index)
        if len(years) < recent * 2:
            recent = len(years) // 2

        recent_years = years[-recent:]
        prior_years = years[-(2 * recent):-recent]

        emerging = []
        declining = []

        for cat in counts.columns:
            recent_mean = counts.loc[recent_years, cat].mean()
            prior_mean = counts.loc[prior_years, cat].mean() if prior_years else 0

            if prior_mean > 0:
                change = (recent_mean - prior_mean) / prior_mean
            elif recent_mean > 0:
                change = 1.0
            else:
                change = 0.0

            entry = {
                'category': cat,
                'prior_mean': round(prior_mean, 1),
                'recent_mean': round(recent_mean, 1),
                'change_pct': round(change * 100, 1),
            }

            if change > 0.1:
                emerging.append(entry)
            elif change < -0.1:
                declining.append(entry)

        emerging.sort(key=lambda x: x['change_pct'], reverse=True)
        declining.sort(key=lambda x: x['change_pct'])

        return {'emerging': emerging, 'declining': declining}
