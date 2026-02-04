"""TopicConfig — YAML驱动的研究空白分析配置"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ═══════════════════════════════════════════════
# NIBS 共享常量 (不进YAML, 所有课题通用)
# ═══════════════════════════════════════════════
NIBS_PATTERN_CN = r'经颅磁|TMS|rTMS|tDCS|经颅直流|经颅电|神经调控|脑刺激|磁刺激|电刺激|DBS|深部脑|theta.?burst|TBS|超声刺激|TUS'
NIBS_PATTERN_EN = r'transcranial magnetic|\bTMS\b|\brTMS\b|\btDCS\b|transcranial direct|brain stimulation|transcranial ultrasound|\bTUS\b|\bDBS\b|deep brain stimul|theta.?burst|\bECT\b|electroconvulsive'
NIBS_QUERY_EN = '(TMS OR rTMS OR tDCS OR "brain stimulation" OR TUS OR DBS OR "theta burst")'


# ═══════════════════════════════════════════════
# 申请人配置
# ═══════════════════════════════════════════════
@dataclass
class ApplicantConfig:
    """申请人信息配置，用于检索前期工作基础"""
    name_cn: str                                   # 中文姓名（显示用）
    name_en: str                                   # 英文姓名（PubMed检索）
    affiliation: str = ''                          # 机构（过滤同名）
    orcid: str = ''                                # ORCID（精准检索）
    keywords: list[str] = field(default_factory=list)   # 研究关键词
    aliases: list[str] = field(default_factory=list)    # 姓名变体 (e.g., ["M Wang", "Wang M"])

    @classmethod
    def from_dict(cls, d: dict) -> 'ApplicantConfig':
        """从字典构造，支持YAML解析"""
        return cls(
            name_cn=d.get('name_cn', ''),
            name_en=d.get('name_en', ''),
            affiliation=d.get('affiliation', ''),
            orcid=d.get('orcid', ''),
            keywords=d.get('keywords', []),
            aliases=d.get('aliases', []),
        )


@dataclass
class ProjectLayout:
    """标准化项目文件夹: parameters/ data/ results/ figs/ scripts_meta/"""
    root: Path

    @property
    def parameters(self) -> Path:
        return self.root / 'parameters'

    @property
    def data(self) -> Path:
        return self.root / 'data'

    @property
    def results(self) -> Path:
        return self.root / 'results'

    @property
    def figs(self) -> Path:
        return self.root / 'figs'

    @property
    def scripts_meta(self) -> Path:
        return self.root / 'scripts'

    def ensure_dirs(self):
        for d in [self.parameters, self.data, self.results, self.figs, self.scripts_meta]:
            d.mkdir(parents=True, exist_ok=True)


@dataclass
class TopicConfig:
    """一个研究课题的完整配置"""

    # ── 必填: 课题标识 ──
    name: str
    title_zh: str
    title_en: str

    # ── 必填: 数据源查询 ──
    disease_cn_keyword: str          # LetPub搜索词
    disease_cn_filter: str           # 后处理过滤正则
    disease_en_query: str            # PubMed/NIH查询

    # ── 必填: 维度定义 ──
    symptoms: dict[str, str]         # {名称: 正则}
    targets: dict[str, str]          # {名称: 正则}
    highlight_target: str            # 红色高亮的靶点

    # ── 必填: Gap分析 ──
    gap_patterns: dict[str, str]     # {模式名: 正则}
    gap_combinations: dict[str, list[str]]  # {组合名: [模式名...]}

    # ── 必填: Panel E 文献 ──
    key_papers: list[dict[str, str]]
    panel_e_title: str
    panel_e_summary: str

    # ── 有默认值 ──
    nsfc_merge_map: dict[str, str] = field(default_factory=lambda: {
        '神经递质': '环路/机制', '动物模型': '其他', '流行病/康复': '其他', '电生理': '其他',
    })
    nih_to_zh_map: dict[str, str] = field(default_factory=lambda: {
        'Neuromodulation': '神经调控', 'Clinical/Pharma': '临床/药物',
        'Neuroimaging': '神经影像', 'Electrophysiology': '其他',
        'Genetics/Omics': '遗传/组学', 'Immune/Metabolic': '免疫/代谢',
        'Circuit/Mechanism': '环路/机制', 'Neurotransmitter': '环路/机制',
        'Cognition/Behavior': '认知/行为', 'Animal Model': '其他',
        'Epidemiology/Rehab': '其他', 'Other': '其他',
    })
    display_cats: list[str] = field(default_factory=lambda: [
        '神经调控', '环路/机制', '免疫/代谢', '神经影像', '遗传/组学', '临床/药物', '认知/行为', '其他',
    ])
    period_labels: list[str] = field(default_factory=lambda: [
        '99-05', '06-08', '09-11', '12-14', '15-17', '18-20', '21-23',
    ])
    period_ranges: list[list[int]] = field(default_factory=lambda: [
        [1999, 2005], [2006, 2008], [2009, 2011], [2012, 2014],
        [2015, 2017], [2018, 2020], [2021, 2023],
    ])
    suptitle: str = ''
    panel_a_title: str = ''
    panel_b_title: str = ''
    panel_d_title: str = ''
    data_dir: str = '../nsfc_data'

    # ── 项目文件夹名 (为空则不创建子结构) ──
    project_dir: str = ''

    # ── 热力图维度 (可与symptoms/targets不同, 用于更紧凑的标签) ──
    heatmap_symptoms: dict[str, str] | None = None
    heatmap_targets: dict[str, str] | None = None

    # ── 高亮注释 ──
    highlight_annotation: str = ''

    # ── 自定义干预手段 (空则用模块级 NIBS_* 常量) ──
    intervention_query_en: str = ''
    intervention_pattern_cn: str = ''
    intervention_pattern_en: str = ''

    # ── 共现网络参数 ──
    cooccurrence_window: int = 5
    cooccurrence_step: int = 3            # <window = 重叠滑动窗口
    cooccurrence_min_freq_cn: int = 2
    cooccurrence_min_freq_en: int = 50
    cooccurrence_max_year: int = 2024
    extra_stopwords_cn: list[str] = field(default_factory=list)
    extra_stopwords_en: list[str] = field(default_factory=list)
    emerging_recent_years: int = 3

    # ── PubMed 高级检索 ──
    pubmed_query: str = ''           # 完整高级检索式（覆盖自动拼接）
    use_top_journals: bool = False   # 额外检索顶刊子集

    # ── 疾病负担检索 (Panel A 用，独立于 NIBS 检索) ──
    burden_query: str = ''           # e.g. 'schizophrenia AND negative symptoms'
    panel_h_title: str = ''          # Panel H 标题

    # ── 申请人前期基础 (Panel G) ──
    applicant: ApplicantConfig | dict | None = None   # 申请人配置
    panel_g_title: str = ''                           # Panel G 标题

    @property
    def layout(self) -> ProjectLayout | None:
        """返回ProjectLayout (仅当project_dir非空时), 位于 zbib/projects/{project_dir}/"""
        if not self.project_dir:
            return None
        # zbib/ 是 scripts/ 的父目录
        zbib_root = Path(__file__).resolve().parent.parent
        return ProjectLayout(zbib_root / 'projects' / self.project_dir)


def load_config(path: str | Path) -> TopicConfig:
    """从YAML文件加载配置"""
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)

    # 解析 applicant 字段为 ApplicantConfig
    if 'applicant' in raw and isinstance(raw['applicant'], dict):
        raw['applicant'] = ApplicantConfig.from_dict(raw['applicant'])

    # period_ranges: YAML里写 [[1999,2005],...] 直接映射
    return TopicConfig(**raw)
