"""关键词分析: 高频词、年趋势、Trend Topics、摘要分词、趋势预测"""

import re
from collections import Counter

import numpy as np
import pandas as pd


# 通用停用词 — 疾病名本身和无信息量的泛词
STOPWORDS_CN = {
    '精神分裂症', '精神分裂', '精神分裂症.', '精神分裂.', 'schizophrenia',
    # 英文碎片（从中文关键词字段混入）
    'resonance', 'imaging)', 'magnetic', 'imaging',
    'schizophrenia)', '精神分裂症(schizophrenia)', 'functional',
    # 摘要分词常见泛词（jieba提取的无信息量词）
    '研究', '分析', '方法', '结果', '患者', '临床', '治疗', '诊断',
    '基因', '遗传', '项目', '发病', '精神疾病', '机制', '实验',
    '目的', '结论', '背景', '对象', '材料', '讨论', '意义',
    '采用', '进行', '探讨', '观察', '检测', '比较', '评估',
    '影响', '作用', '相关', '水平', '表达', '变化', '功能',
    '正常', '对照', '统计', '差异', '显著', '提示', '可能',
    '发现', '报告', '资料', '信息', '技术', '应用', '系统',
    '目前', '近年来', '国内外', '国内', '国外', '本研究',
    '本项目', '课题', '申请', '经费', '基金', '国家',
}
STOPWORDS_EN = {
    # 疾病名
    'schizophrenia', 'schizophrenic disorders', 'schizophrenic',
    'dementia praecox',
    # 人口学
    'humans', 'human', 'male', 'female', 'adult', 'middle aged',
    'young adult', 'adolescent', 'aged', 'animals', 'child',
    # 无信息泛词 (NIH terms 常见)
    'brain', 'research', 'data', 'base', 'testing', 'disorder',
    'disease', 'disorders', 'role', 'goals', 'development',
    'developmental', 'encephalon', 'social role',
    'brain nervous system', 'neurons', 'neuronal', 'nerve cells',
    'nerve unit', 'neural cell', 'neurocyte',
    'novel', 'work', 'process', 'individual', 'model',
    'area', 'system', 'study', 'studies', 'outcome', 'outcomes',
    'patient', 'patients', 'treatment', 'clinical',
    'control', 'group', 'effect', 'effects', 'analysis',
    'result', 'results', 'method', 'methods', 'measure',
    'measures', 'performance', 'change', 'changes',
    'level', 'levels', 'state', 'states', 'sample',
    'response', 'responses', 'task', 'tasks', 'time',
    'intervention', 'condition', 'conditions',
    'function', 'associated', 'related', 'significant',
    'activity', 'evidence', 'risk', 'factor', 'factors',
    'age', 'cell', 'cells', 'gene', 'genes', 'protein',
    'receptor', 'receptors', 'trial', 'trials', 'dose',
    'design', 'support', 'evaluation', 'assessment',
    'approach', 'program', 'type', 'types',
    # NIH terms 特有泛词
    'modeling', 'modern man', 'mental disorders', 'affect',
    'mental health disorders', 'psychiatric disease',
    'psychiatric disorder', 'mental illness',
    'psychological disorder', 'address',
    'biological signal transduction', 'behavioral', 'behavior',
    'experiment', 'experimental research', 'signal transduction',
    'biological', 'mechanism', 'mechanisms', 'specific',
    'identify', 'understanding', 'develop', 'developing',
    'improved', 'improvement', 'new', 'normal',
    'potential', 'role of', 'basic', 'fundamental',
    'healthy', 'identify', 'identification',
    'disorder symptoms', 'symptoms', 'symptom',
    'psychotic', 'psychosis', 'psychiatric',
    'mental', 'health', 'illness',
    # 额外泛词 (从趋势图中发现)
    'experimental study', 'experimental studies',
    'cell communication and signaling', 'cell signaling',
    'intracellular communication and signaling',
    'signal transduction systems', 'signal transduction',
    'signaling', 'mediating', 'population',
    'experimental', 'communication', 'transduction',
    'cellular', 'molecular', 'genetic', 'genomic',
    'therapeutics', 'therapy', 'therapeutic',
    'diagnostic', 'diagnosis', 'prognosis',
    'prevalence', 'incidence', 'epidemiology',
    'randomized', 'controlled', 'randomized controlled trial',
    'laboratory', 'biomarker', 'biomarkers',
    'nerve', 'cortex', 'cortical',
    'structural', 'organization', 'regulation',
    'inhibition', 'activation', 'expression',
    'pathway', 'pathways', 'network', 'networks',
    'cognitive', 'memory', 'attention', 'learning',
    'imaging', 'neuroimaging', 'tomography',
    'pharmacology', 'pharmacological',
    # 第三轮补充 — 从趋势图再次发现的泛词
    'complex', 'link', 'insight', 'structure', 'structures',
    'disease/disorder', 'functional disorder', 'dysfunction',
    'neural', 'mice', 'mouse', 'rat', 'rats', 'animal',
    'autism', 'major', 'review', 'association', 'associations',
    'high', 'low', 'total', 'report', 'reports', 'score', 'scores',
    'detection', 'action', 'actions', 'target', 'targets',
    'region', 'regions', 'feature', 'features', 'test',
    'protocol', 'protocols', 'session', 'sessions',
    'hypothesis', 'theory', 'concept', 'framework',
    'participant', 'participants', 'subject', 'subjects',
    'criterion', 'criteria', 'index', 'ratio', 'rate',
    'phase', 'stages', 'stage', 'period', 'onset',
    'family', 'families', 'sibling', 'parent', 'offspring',
    'drug', 'drugs', 'medication', 'medications', 'agent', 'agents',
    'etiology', 'pathogenesis', 'pathology', 'morphology',
    # 第四轮 — NIH趋势图残留泛词
    'play', 'lead', 'pb element', 'heavy metal pb', 'heavy metal lead',
    'pattern', 'patterns', 'kanner\'s syndrome', 'kanner', 'autistic disorder',
    'physiopathology', 'pathophysiology',
    'ability', 'abilities', 'impact', 'event', 'events',
    'childhood', 'children', 'pediatric', 'infant', 'infants',
    'exposure', 'exposed', 'interaction', 'interactions',
    'deficiency', 'deficit', 'deficits', 'impairment', 'impairments',
    'susceptibility', 'vulnerability', 'predisposition',
    'chronic', 'acute', 'severe', 'mild', 'moderate',
    'variation', 'variations', 'variant', 'variants',
    'polymorphism', 'polymorphisms', 'allele', 'alleles',
    'comorbidity', 'comorbid', 'co-occurring',
    # 第五轮 — NIH残留
    'knowledge', 'designing', 'murine', 'mus',
    'early infantile autism', 'infantile autism', 'infantile',
    'mice mammals', 'relating to nervous system', 'nervous system',
    'relating', 'training', 'prevention', 'recovery',
    'validity', 'reliability', 'sensitivity', 'specificity',
    'dose response', 'signal', 'signals', 'processing',
    'screening', 'tool', 'tools', 'scale', 'scales',
    'survey', 'surveys', 'questionnaire', 'interview',
    # 第六轮 — 行政/方法学泛词
    'public health relevance', 'public health', 'relevance',
    'techniques', 'technique', 'investigators', 'investigator',
    'research personnel', 'researchers', 'researcher', 'personnel',
    'funding', 'grant', 'grants', 'budget', 'cost', 'costs',
    'in vivo', 'in vitro', 'ex vivo', 'vivo', 'vitro',
    'manuscript', 'publication', 'publications', 'paper', 'papers',
    'literature', 'database', 'databases', 'software',
    'recruitment', 'enrollment', 'consent', 'ethical',
    'longitudinal', 'cross-sectional', 'retrospective', 'prospective',
    'cohort', 'cohorts', 'regression', 'correlation',
    'significance', 'p-value', 'confidence interval',
    'limitation', 'limitations', 'strength', 'strengths',
    'future', 'aim', 'aims', 'objective', 'objectives', 'goal',
    'conclusion', 'conclusions', 'summary', 'abstract',
    'introduction', 'background', 'rationale',
    # 第七轮 — NIH人口统计/政策/行政术语
    'black', 'white', 'hispanic', 'latino', 'latina',
    'african american', 'african americans', 'caucasian',
    'racial', 'racial minority', 'racial minority population',
    'racial minority people', 'racial minority individual',
    'racial minority group', 'ethnic', 'ethnicity',
    'minority', 'minorities', 'disparity', 'disparities',
    'disparity population', 'underserved', 'underrepresented',
    'sex based differences', 'sex differences', 'gender',
    'gender differences', 'sex', 'race',
    'experiments', 'experiment', 'experimentation',
    'proctor', 'proctor framework', 'proctor evaluation model',
    'proctor multi-level outcomes framework',
    'proctor multilevel outcomes framework',
    'implementation science', 'implementation',
    'dissemination', 'stakeholder', 'stakeholders',
    'community', 'communities', 'engagement', 'equity',
    'social determinants', 'genetic propensity',
    '21+ years old', 'years old', 'young adult (21+)',
    # 第八轮 — 拨款写作套话 + COVID/DEI政策术语
    'innovative', 'innovation', 'innovations', 'innovate',
    'novel approach', 'cutting edge', 'state of the art',
    'reporting', 'report', 'reports', 'programs', 'program',
    'experience', 'experiences', 'experienced',
    'pharmaceutical preparations', 'pharmaceutic preparations',
    'drug/agent', 'drug agent', 'pharmaceutical',
    'social justice', 'health equity', 'health disparities',
    'socioeconomic', 'socio-economic', 'socioeconomic inequity',
    'socio-economic inequity', 'socioeconomic inequality',
    'and inclusion', 'and inclusiveness', 'inclusion',
    'inclusiveness', 'inclusive', 'diversity',
    'ethnic disadvantage', 'ethnically diverse',
    'post acute sequelae', 'post acute sequelae of covid19',
    'post acute sequelae of covid-19',
    'post acute sequelae of sars-cov-2', 'pasc',
    'adverse sequelae of covid-19', 'adverse sequelae',
    'covid-19', 'covid 19', 'covid19', 'coronavirus',
    'sars-cov-2', 'pandemic', 'covid-19 pandemic',
    'covid 19 pandemic', 'long covid',
    'dataset repository', 'data set repository',
    'repository', 'repositories',
    'adjuvant treatment', 'adjuvant',
    'peer recovery', 'long term recovery',
    'laboratory rat', 'laboratory mouse', 'laboratory animal',
    'biological assay', 'adult human', 'human adult',
    'transcriptional control', 'transcription',
    # 近义词/变体形式
    'interventional strategy', 'intervention strategies',
    'interventional strategies', 'intervention strategy',
    'addicted to cocaine', 'addicted to',
    'chemical class', 'alcohol chemical class',
    'proctor evaluation', 'proctor model',
    # 第九轮 — health disparities变体 + RCT设计术语 + 机构名
    'reduce health disparities', 'mitigate health disparities',
    'lower health disparities', 'decrease health disparities',
    'health disparity reduction', 'health disparity mitigation',
    'health disparity', 'health disparities',
    'unequal outcome', 'unequal outcomes',
    '2 arm randomized control trial', '2 arm randomized controlled trial',
    'two arm randomized control trial', 'two arm randomized controlled trial',
    'two arm rct', '2 arm rct', 'rct', 'randomized control trial',
    'randomized controlled trial', 'randomized clinical trial',
    'clinical trial', 'clinical trials',
    'ncats', 'nida', 'nimh', 'niaaa', 'ninds',
    'national center for advancing translational sciences',
    'national institute', 'national institutes',
    'latine', 'latinx',
    'sampling', 'sample size', 'power analysis',
    'data collection', 'data analysis', 'data sharing',
    'analyze gene expression', 'gene expression analysis',
    # 第十轮 — NIH年龄段模板术语 + 残留行政词
    'over 65 years', '65 and older', '65 or older',
    '65 years of age and older', '65 years of age or older',
    '65 years of age or more', '65+ years', 'aged 65+',
    'above age 65', 'after age 65', 'age 65 or older',
    '≥65 years', '>=65 years', 'older adults',
    'over 18 years', '18 and older', '18 or older',
    '18 years of age and older', '18 years of age or older',
    '18+ years', 'aged 18+', 'age 18 or older',
    'unequal impact', 'unequal impacts',
    'age associated', 'age-associated', 'age related', 'age-related',
    'ineuron', 'ipsc', 'ipscs',
    'drug usage', 'drug use',
    # 第十一轮 — minority stress变体 + 机构缩写 + 残留行政词
    'minority stress', 'stress to minorities', 'stress in minorities',
    'stress among minorities', 'minority health',
    'national institute on minority health and health disparities',
    'nimhd', 'samhsa', 'hrsa',
    'unequal effect', 'unequal effects', 'structural racism',
    'structural inequality', 'structural inequity',
    'process improvement', 'quality improvement',
    'translation', 'translational', 'translational research',
    'bench to bedside', 'site', 'sites', 'location', 'locations',
    'mris', 'mri', 'fmri', 'pet', 'ct scan', 'eeg',
    # 第十二轮 — SABV政策术语 + 人口统计模板 + 残留
    'sex as a biological factor', 'sex as a biological measure',
    'sex as a biological risk factor', 'sex as a biological variable',
    'sex as a biological variance',
    'sex as a biologically significant variable',
    'sex as a fundamental variable',
    'biological variable', 'biological factor',
    'american indian', 'american indian population',
    'american indian group', 'american indian individual',
    'alaska native', 'native american', 'native hawaiian',
    'pacific islander', 'asian american',
    'outcome inequity', 'outcome inequality',
    'gene modified', 'genetically modified',
    'induced neurons', 'induced pluripotent',
    'alcohol addiction treatment', 'alcohol dependence treatment',
    'tobacco disorder', 'tobacco use disorder',
    'digital platform', 'digital platforms', 'digital health',
    'telehealth', 'telemedicine',
    # 第十三轮 — 批量清理残留模式
    'outcome disparities', 'outcome disparity',
    'races', 'racial background', 'racial origin',
    'age months', 'age years', 'age weeks',
    'system integration', 'systems integration',
    'good manufacturing process', 'good manufacturing practice',
    'good manufacturing', 'manufacturing',
    'castration resistant', 'castration resistant cap',
    'alcohol associated hepatitis', 'alcohol hepatitis',
    'alcohol induced hepatitis', 'alcohol related hepatitis',
    'alcoholic hepatitis',
    'limited intellectual functioning', 'intellectual functioning',
    'shareable platform', 'shareable',
    'posttranscriptional', 'post-transcriptional',
    # 第十四轮 — 最后一批行政/DEI/人口术语
    'community advisory panel', 'community advisory',
    'advisory panel', 'advisory board',
    'histories', 'history', 'historical',
    'black group', 'black individual', 'black people', 'blacks',
    'white group', 'white individual', 'white people', 'whites',
    'remote assessment', 'remote evaluation', 'remote monitoring',
    'stressful experience', 'stressful experiences',
    'novel pharmaco-therapeutic', 'new pharmacological therapeutic',
    'pharmaco-therapeutic', 'pharmacological therapeutic',
    'prolonged abstinence', 'sustained abstinence',
    'hypertensive disorder', 'hypertension',
    'machine learning based algorithm', 'machine learning algorithm',
}


class KeywordAnalyzer:
    """关键词层面的文献计量分析

    支持中文关键词（;/；/、分隔）和英文关键词（;分隔）。
    所有方法支持 stopwords 参数，默认过滤疾病名和通用词。
    """

    def __init__(self, extra_stopwords_cn: set[str] | None = None,
                 extra_stopwords_en: set[str] | None = None):
        self._cn_sep = re.compile(r'[;；、,，]+')
        self._en_sep = re.compile(r'[;,]+')
        self._stop_cn = STOPWORDS_CN | (extra_stopwords_cn or set())
        self._stop_en = STOPWORDS_EN | (extra_stopwords_en or set())

    def _is_stopword(self, word: str, lang: str) -> bool:
        w = word.lower().strip().rstrip('.')
        if lang == 'cn':
            return w in self._stop_cn or w in self._stop_en
        return w in self._stop_en

    # ─── 基础: 拆分关键词 ────────────────────────
    def explode_keywords(self, df: pd.DataFrame, col: str, year_col: str | None = None,
                         lang: str = 'cn', filter_stopwords: bool = True) -> pd.DataFrame:
        """将关键词字段拆成长格式 (一行一个词)

        Returns DataFrame with columns: keyword, (year if year_col given)
        使用向量化 str.split + explode 替代 iterrows，大数据集快 50x+。
        """
        sep_pat = r'[;；、,，]+' if lang == 'cn' else r'[;,]+'

        # 向量化拆分
        sub = df[[col]].copy()
        if year_col:
            sub['year'] = df[year_col]
        sub[col] = sub[col].astype(str).replace({'nan': '', 'None': ''})
        sub = sub[sub[col].str.len() > 0]

        sub['keyword'] = sub[col].str.split(sep_pat)
        sub = sub.drop(columns=[col]).explode('keyword')
        sub['keyword'] = sub['keyword'].str.strip()
        if lang == 'en':
            sub['keyword'] = sub['keyword'].str.lower()

        # 过滤
        sub = sub[sub['keyword'].str.len() >= 2]
        if filter_stopwords:
            stop = self._stop_cn | self._stop_en if lang == 'cn' else self._stop_en
            lower_kw = sub['keyword'].str.lower().str.rstrip('.')
            sub = sub[~lower_kw.isin(stop)]

        if year_col:
            sub['year'] = sub['year'].astype(int)
            return sub[['keyword', 'year']].reset_index(drop=True)
        return sub[['keyword']].reset_index(drop=True)

    # ─── 高频词 Top-N ────────────────────────────
    def top_keywords(self, df: pd.DataFrame, col: str, n: int = 30,
                     lang: str = 'cn') -> pd.DataFrame:
        """返回频率最高的 N 个关键词 (已过滤停用词)"""
        exploded = self.explode_keywords(df, col, lang=lang)
        if exploded.empty:
            return pd.DataFrame(columns=['keyword', 'count'])
        counts = exploded['keyword'].value_counts().head(n).reset_index()
        counts.columns = ['keyword', 'count']
        return counts

    # ─── 关键词年趋势 ───────────────────────────
    def word_growth(self, df: pd.DataFrame, col: str, year_col: str,
                    keywords: list[str] | None = None, top_n: int = 10,
                    lang: str = 'cn') -> pd.DataFrame:
        """关键词的年度频率趋势 (已过滤停用词)

        Parameters
        ----------
        keywords : 指定追踪的词列表。若为 None，自动选 top_n 高频词。
        Returns pivot table: index=year, columns=keyword, values=count
        """
        exploded = self.explode_keywords(df, col, year_col=year_col, lang=lang)
        if exploded.empty:
            return pd.DataFrame()

        if keywords is None:
            top = exploded['keyword'].value_counts().head(top_n).index.tolist()
            keywords = top

        filtered = exploded[exploded['keyword'].isin(keywords)]
        if filtered.empty:
            return pd.DataFrame()

        pivot = filtered.groupby(['year', 'keyword']).size().unstack(fill_value=0)
        order = pivot.sum().sort_values(ascending=False).index
        return pivot[order]

    # ─── Trend Topics (每时期特征词) ─────────────
    def trend_topics(self, df: pd.DataFrame, col: str, year_col: str,
                     periods: list[tuple[int, int]], top_n: int = 5,
                     lang: str = 'cn') -> dict[str, list[tuple[str, int]]]:
        """每个时期的 Top-N 关键词 (已过滤停用词)

        Returns {period_label: [(keyword, count), ...]}
        """
        exploded = self.explode_keywords(df, col, year_col=year_col, lang=lang)
        if exploded.empty:
            return {}

        result = {}
        for start, end in periods:
            label = f"{start}-{end}"
            period_df = exploded[(exploded['year'] >= start) & (exploded['year'] <= end)]
            top = period_df['keyword'].value_counts().head(top_n)
            result[label] = list(zip(top.index, top.values))
        return result

    # ─── 新兴关键词检测 ──────────────────────────
    def emerging_keywords(self, df: pd.DataFrame, col: str, year_col: str,
                          recent_years: int = 3, min_count: int = 3,
                          lang: str = 'cn') -> pd.DataFrame:
        """近N年新出现或频率骤增的关键词

        Returns DataFrame: keyword, recent_count, prior_count, growth
        """
        exploded = self.explode_keywords(df, col, year_col=year_col, lang=lang)
        if exploded.empty:
            return pd.DataFrame()

        max_year = int(exploded['year'].max())
        cutoff = max_year - recent_years + 1

        recent = exploded[exploded['year'] >= cutoff]['keyword'].value_counts()
        prior = exploded[exploded['year'] < cutoff]['keyword'].value_counts()

        rows = []
        for kw, cnt in recent.items():
            if cnt < min_count:
                continue
            prior_cnt = prior.get(kw, 0)
            if prior_cnt == 0:
                growth = float('inf')
            else:
                growth = (cnt / recent_years) / (prior_cnt / max(cutoff - int(exploded['year'].min()), 1))
            rows.append({
                'keyword': kw,
                'recent_count': cnt,
                'prior_count': prior_cnt,
                'growth': round(growth, 2) if growth != float('inf') else 999,
            })

        result = pd.DataFrame(rows)
        if result.empty:
            return result
        return result.sort_values('growth', ascending=False)

    # ─── 摘要分词提取关键词 ─────────────────────────
    def extract_from_abstract(self, df: pd.DataFrame, abstract_col: str,
                              year_col: str | None = None,
                              lang: str = 'cn', top_n: int = 200) -> pd.DataFrame:
        """从摘要文本提取关键词，返回与 explode_keywords 相同格式的长表

        中文: jieba 分词 → 过滤停用词+单字
        英文: TF-IDF bigram/trigram → top_n
        """
        texts = []
        years = []
        for _, row in df.iterrows():
            txt = str(row.get(abstract_col, ''))
            if txt in ('nan', 'None', ''):
                continue
            texts.append(txt)
            years.append(int(row[year_col]) if year_col else None)

        if not texts:
            return pd.DataFrame(columns=['keyword'] + (['year'] if year_col else []))

        if lang == 'cn':
            import jieba
            rows = []
            for i, txt in enumerate(texts):
                words = jieba.lcut(txt)
                seen = set()
                for w in words:
                    w = w.strip()
                    if len(w) < 2 or self._is_stopword(w, 'cn') or w in seen:
                        continue
                    # 过滤纯数字、标点
                    if re.fullmatch(r'[\d.%+\-*/=<>()（）【】\s]+', w):
                        continue
                    seen.add(w)
                    entry = {'keyword': w}
                    if years[i] is not None:
                        entry['year'] = years[i]
                    rows.append(entry)
            return pd.DataFrame(rows)
        else:
            # 英文: TF-IDF bigram/trigram
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(ngram_range=(1, 3), max_features=top_n * 3,
                                  stop_words='english', max_df=0.8, min_df=2)
            try:
                tfidf = vec.fit_transform(texts)
            except ValueError:
                return pd.DataFrame(columns=['keyword'] + (['year'] if year_col else []))

            feature_names = vec.get_feature_names_out()
            # 每篇文档取 top-5 TF-IDF 词
            rows = []
            for i in range(tfidf.shape[0]):
                row_data = tfidf[i].toarray().ravel()
                top_idx = row_data.argsort()[-5:][::-1]
                for idx in top_idx:
                    if row_data[idx] <= 0:
                        continue
                    kw = feature_names[idx]
                    if self._is_stopword(kw, 'en'):
                        continue
                    entry = {'keyword': kw}
                    if years[i] is not None:
                        entry['year'] = years[i]
                    rows.append(entry)
            return pd.DataFrame(rows)

    # ─── 融合关键词(字段+摘要) ──────────────────────
    def fused_keywords(self, df: pd.DataFrame, kw_col: str, abstract_col: str,
                       year_col: str, lang: str = 'cn') -> pd.DataFrame:
        """合并关键词字段 + 摘要提取词，去重(优先保留原始关键词)

        Returns 长格式 DataFrame: keyword, year
        """
        kw_df = self.explode_keywords(df, kw_col, year_col=year_col, lang=lang)
        abs_df = self.extract_from_abstract(df, abstract_col, year_col=year_col, lang=lang)

        combined = pd.concat([kw_df, abs_df], ignore_index=True)
        # 同一年+同一关键词去重
        combined = combined.drop_duplicates(subset=['keyword', 'year'])
        return combined

    # ─── 关键词趋势预测 ─────────────────────────────
    def predict_trend(self, df_long: pd.DataFrame, keywords: list[str],
                      forecast_years: int = 5, min_yearly_avg: float = 2.0,
                      weighted: bool = True) -> dict[str, pd.DataFrame]:
        """对指定关键词的年度频率做线性回归 + 置信区间

        Parameters
        ----------
        df_long : 长格式 (keyword, year)
        keywords : 要预测的关键词列表
        forecast_years : 外推年数
        min_yearly_avg : 年均频率低于此值的词跳过
        weighted : 是否加权回归(近年权重更高)

        Returns {keyword: DataFrame(year, count, predicted, ci_lower, ci_upper)}
        """
        results = {}
        for kw in keywords:
            subset = df_long[df_long['keyword'] == kw]
            if subset.empty:
                continue

            yearly = subset.groupby('year').size()
            years = np.array(yearly.index, dtype=float)
            counts = np.array(yearly.values, dtype=float)

            if counts.mean() < min_yearly_avg:
                continue
            if len(years) < 3:
                continue

            # 加权: 近年权重递增
            if weighted:
                w = np.linspace(0.5, 1.5, len(years))
            else:
                w = np.ones(len(years))

            # 加权线性回归
            coeffs = np.polyfit(years, counts, 1, w=w)
            poly = np.poly1d(coeffs)

            # 残差标准误
            predicted_hist = poly(years)
            residuals = counts - predicted_hist
            se = np.sqrt(np.sum(residuals ** 2) / max(len(years) - 2, 1))

            # 外推
            max_year = int(years.max())
            future_years = np.arange(max_year + 1, max_year + forecast_years + 1, dtype=float)
            all_years = np.concatenate([years, future_years])
            all_pred = poly(all_years)
            all_pred = np.maximum(all_pred, 0)  # 不允许负值

            # 置信区间 (随外推距离增大)
            dist = np.abs(all_years - years.mean())
            ci = 1.96 * se * np.sqrt(1 + dist / max(dist.max(), 1))

            # 历史部分用实际值，预测部分用回归值
            all_counts = np.concatenate([counts, [np.nan] * len(future_years)])

            result_df = pd.DataFrame({
                'year': all_years.astype(int),
                'count': all_counts,
                'predicted': np.round(all_pred, 1),
                'ci_lower': np.round(np.maximum(all_pred - ci, 0), 1),
                'ci_upper': np.round(all_pred + ci, 1),
                'is_forecast': [False] * len(years) + [True] * len(future_years),
            })
            results[kw] = result_df

        return results
