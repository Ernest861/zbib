"""申请人前期工作分析 - Profile数据类

定义 ApplicantProfile 数据类及其评分体系。
"""

import json
import re
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.journals import TOP_JOURNAL_NAMES


# ═══════════════════════════════════════════════
# 申报者评估体系: 适配度 + 胜任力
# ═══════════════════════════════════════════════
#
# 适配度 (Fit): 申请人前期工作与本课题的契合程度
#   - 疾病领域: 在该疾病方向的研究积累
#   - 技术方法: 对 NIBS 技术的掌握程度
#   - 交叉深度: 疾病+NIBS 结合的工作
#
# 胜任力 (Competency): 申请人独立完成课题的能力
#   - 学术独立性: 第一/通讯作者占比
#   - 学术影响力: 顶刊发表、H-index
#   - 研究活跃度: 近5年持续产出
#   - 团队协作: 合作网络广度
#
# ═══════════════════════════════════════════════

# ═══════════════════════════════════════════════
# 评分参数常量
# ═══════════════════════════════════════════════

# 默认评分权重 (适配度 50% + 胜任力 50%)
DEFAULT_SCORE_WEIGHTS = {
    # 适配度维度 (50%)
    'disease': 0.20,      # 疾病领域深度
    'nibs': 0.20,         # 技术方法专长
    'crossover': 0.10,    # 交叉研究经验
    # 胜任力维度 (50%)
    'independence': 0.20, # 学术独立性
    'impact': 0.15,       # 学术影响力
    'activity': 0.15,     # 研究活跃度
}

# 验证权重总和为 1.0
assert abs(sum(DEFAULT_SCORE_WEIGHTS.values()) - 1.0) < 0.001, \
    f"评分权重总和必须为1.0, 当前为 {sum(DEFAULT_SCORE_WEIGHTS.values())}"

# 适配度和胜任力的子维度
FIT_DIMENSIONS = ['disease', 'nibs', 'crossover']
COMPETENCY_DIMENSIONS = ['independence', 'impact', 'activity']

# 维度得分换算系数 (将比例转换为0-100分)
SCORE_MULTIPLIERS = {
    'disease': 160,      # 疾病覆盖率 × 160 → 0~100分 (假设60%覆盖为满分)
    'nibs': 160,         # NIBS覆盖率 × 160 → 0~100分
    'crossover': 200,    # 交叉覆盖率 × 200 → 0~100分 (因为交叉本身较难)
    'independence': 150, # 独立作者比 × 150 → 0~100分 (假设65%为满分)
    'impact': 3.0,       # 顶刊数量 × 3.0 → 封顶100分
    'activity': 4.0,     # 近5年发文量 × 4.0 → 封顶100分 (假设25篇为满分)
}

# H-index 年增长率上限 (合理的学术成长速度)
H_INDEX_GROWTH_RATE = 2


# 期刊影响力分级 (基于常见分类)
JOURNAL_TIERS = {
    'tier1': TOP_JOURNAL_NAMES,  # 顶刊
    'tier2': {  # 高质量期刊
        'Neuroimage', 'Hum Brain Mapp', 'Cereb Cortex', 'J Neurosci',
        'Neuropsychopharmacology', 'Transl Psychiatry', 'Brain Stimul',
        'Cortex', 'Addiction', 'Drug Alcohol Depend', 'Psychol Med',
    },
}


@dataclass
class ApplicantProfile:
    """申请人前期工作分析结果"""

    # 基础统计
    name_cn: str
    name_en: str
    n_total: int = 0                  # 全部文献数
    n_disease: int = 0                # 疾病相关文献数
    n_nibs: int = 0                   # NIBS相关文献数
    n_disease_nibs: int = 0           # 疾病+NIBS交集
    n_first_author: int = 0           # 第一作者文献数
    n_corresponding: int = 0          # 通讯作者文献数
    n_first_or_corresponding: int = 0 # 第一或通讯作者（去重）

    # 时间分布
    year_counts: pd.Series = field(default_factory=lambda: pd.Series(dtype=int))
    year_range: tuple[int, int] = (0, 0)
    recent_5yr_count: int = 0         # 近5年发文数

    # 期刊分布
    journal_counts: dict[str, int] = field(default_factory=dict)
    top_journal_count: int = 0
    top_journal_list: list[str] = field(default_factory=list)  # 顶刊论文标题
    tier1_count: int = 0              # 顶刊(CNS等)数量
    tier2_count: int = 0              # 高质量期刊数量
    journal_tier_papers: dict[str, list[dict]] = field(default_factory=dict)  # {tier: [{pmid, title, journal}]}

    # IF 统计 (基于期刊影响因子)
    if_stats: dict[str, float] = field(default_factory=dict)  # {total_if, avg_if, max_if, median_if}

    # 维度覆盖
    symptom_coverage: dict[str, int] = field(default_factory=dict)
    target_coverage: dict[str, int] = field(default_factory=dict)

    # 代表性论文 (top 5 by relevance)
    key_papers: list[dict[str, Any]] = field(default_factory=list)

    # H-index (基于PubMed数据估算)
    h_index_estimate: int = 0

    # 合作者网络 (二元)
    top_collaborators: list[tuple[str, int]] = field(default_factory=list)  # [(name, count), ...]
    collaborator_graph: dict[str, list[str]] = field(default_factory=dict)  # {author: [co-authors]}

    # 合作超图 (高阶结构)
    # Reference: Battiston et al. (2025) Higher-order interactions. Nature Human Behaviour.
    stable_teams: list[dict] = field(default_factory=list)  # [{members, papers, size}, ...]
    team_stability_index: float = 0.0   # 团队稳定性 (0-1)
    avg_team_size: float = 0.0          # 平均团队规模
    max_team_size: int = 0              # 最大团队规模
    solo_ratio: float = 0.0             # 独立发表比例

    # 研究轨迹 (按时期的主题词)
    research_trajectory: dict[str, list[str]] = field(default_factory=dict)  # {period: [keywords]}
    trajectory_years: list[int] = field(default_factory=list)  # 发表年份序列(用于可视化)

    # ORCID 交叉验证
    orcid_verified: bool = False                    # 是否已通过 ORCID 验证
    orcid_id: str = ''                              # ORCID ID
    orcid_match_count: int = 0                      # ORCID 确认的论文数
    orcid_only_count: int = 0                       # 仅在 ORCID 中出现 (PubMed 未检到)
    pubmed_only_count: int = 0                      # 仅在 PubMed 中出现 (ORCID 未记录)
    verification_confidence: str = ''               # 'high', 'medium', 'low'

    # 领域基准排名
    percentile_ranks: dict[str, float] = field(default_factory=dict)  # {metric: percentile}

    @property
    def relevance_score(self) -> float:
        """综合评分 (0-100) = 适配度 + 胜任力"""
        return self.calculate_score(DEFAULT_SCORE_WEIGHTS)

    def _raw_dimension_scores(self, weights: dict[str, float] | None = None) -> dict[str, float]:
        """计算各维度原始分 (0-100)，不触发循环调用"""
        w = weights or DEFAULT_SCORE_WEIGHTS
        raw = {}

        # 适配度维度
        raw['disease'] = min(100, (self.n_disease / self.n_total) * 160) if self.n_total > 0 else 0
        base = self.n_disease if self.n_disease > 0 else self.n_total
        raw['nibs'] = min(100, (self.n_nibs / base) * 160) if base > 0 else 0
        raw['crossover'] = min(100, (self.n_disease_nibs / self.n_disease) * 200) if self.n_disease > 0 else 0

        # 胜任力维度
        raw['independence'] = min(100, (self.n_first_or_corresponding / self.n_total) * 150) if self.n_total > 0 else 0
        raw['impact'] = min(50, self.top_journal_count * 10) + min(50, self.h_index_estimate * 5)
        raw['activity'] = min(100, (self.recent_5yr_count / self.n_total) * 133) if self.n_total > 0 else 0

        return raw

    @property
    def fit_score(self) -> float:
        """适配度评分 (0-100): 前期工作与课题的契合程度"""
        raw = self._raw_dimension_scores()
        fit_weight = sum(DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in FIT_DIMENSIONS)
        if fit_weight == 0:
            return 0
        fit_sum = sum(raw[d] * DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in FIT_DIMENSIONS)
        return round(fit_sum / fit_weight, 1)

    @property
    def competency_score(self) -> float:
        """胜任力评分 (0-100): 独立完成课题的能力"""
        raw = self._raw_dimension_scores()
        comp_weight = sum(DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in COMPETENCY_DIMENSIONS)
        if comp_weight == 0:
            return 0
        comp_sum = sum(raw[d] * DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in COMPETENCY_DIMENSIONS)
        return round(comp_sum / comp_weight, 1)

    def calculate_score(self, weights: dict[str, float] | None = None) -> float:
        """
        计算申请人综合评分 (0-100)

        Args:
            weights: 各维度权重，权重之和应为 1.0

        评分体系:
        【适配度】前期工作与课题的契合程度
        - disease: 疾病领域深度 (n_disease / n_total)
        - nibs: 技术方法专长 (n_nibs / base)
        - crossover: 交叉研究经验 (n_disease_nibs / n_disease)

        【胜任力】独立完成课题的能力
        - independence: 学术独立性 (第一/通讯作者占比)
        - impact: 学术影响力 (顶刊 + H-index)
        - activity: 研究活跃度 (近5年产出)
        """
        w = weights or DEFAULT_SCORE_WEIGHTS
        raw = self._raw_dimension_scores(w)
        score = sum(raw[dim] * w.get(dim, 0) for dim in raw)
        return round(score, 1)

    def get_score_breakdown(self, weights: dict[str, float] | None = None) -> dict[str, float]:
        """获取各维度评分明细"""
        w = weights or DEFAULT_SCORE_WEIGHTS
        raw = self._raw_dimension_scores(w)
        breakdown = {}

        # 原始分
        for dim in ['disease', 'nibs', 'crossover', 'independence', 'impact', 'activity']:
            breakdown[f'{dim}_raw'] = raw[dim]

        # 加权得分
        for dim in ['disease', 'nibs', 'crossover', 'independence', 'impact', 'activity']:
            breakdown[dim] = round(raw[dim] * w.get(dim, 0), 1)

        # 汇总分数
        breakdown['total'] = self.calculate_score(w)
        breakdown['fit'] = self.fit_score
        breakdown['competency'] = self.competency_score

        return breakdown

    @property
    def experience_years(self) -> int:
        """研究经验年数"""
        if self.year_range[0] > 0 and self.year_range[1] > 0:
            return self.year_range[1] - self.year_range[0] + 1
        return 0

    def to_dict(self) -> dict:
        """转换为字典 (用于 JSON 导出)"""
        data = {
            'name_cn': self.name_cn,
            'name_en': self.name_en,
            'n_total': self.n_total,
            'n_disease': self.n_disease,
            'n_nibs': self.n_nibs,
            'n_disease_nibs': self.n_disease_nibs,
            'n_first_author': self.n_first_author,
            'n_corresponding': self.n_corresponding,
            'n_first_or_corresponding': self.n_first_or_corresponding,
            'year_range': list(self.year_range),
            'experience_years': self.experience_years,
            'recent_5yr_count': self.recent_5yr_count,
            'journal_counts': self.journal_counts,
            'top_journal_count': self.top_journal_count,
            'top_journal_list': self.top_journal_list,
            'tier1_count': self.tier1_count,
            'tier2_count': self.tier2_count,
            'symptom_coverage': self.symptom_coverage,
            'target_coverage': self.target_coverage,
            'h_index_estimate': self.h_index_estimate,
            'if_stats': self.if_stats,
            'fit_score': self.fit_score,
            'competency_score': self.competency_score,
            'total_score': self.relevance_score,
            'score_breakdown': self.get_score_breakdown(),
            'top_collaborators': [{'name': n, 'count': c} for n, c in self.top_collaborators],
            # 合作超图 (高阶结构)
            'stable_teams': self.stable_teams,
            'team_stability_index': self.team_stability_index,
            'avg_team_size': self.avg_team_size,
            'max_team_size': self.max_team_size,
            'solo_ratio': self.solo_ratio,
            'research_trajectory': self.research_trajectory,
            'key_papers': self.key_papers,
            # ORCID 验证
            'orcid_verified': self.orcid_verified,
            'orcid_id': self.orcid_id,
            'orcid_match_count': self.orcid_match_count,
            'orcid_only_count': self.orcid_only_count,
            'pubmed_only_count': self.pubmed_only_count,
            'verification_confidence': self.verification_confidence,
            # 领域基准排名
            'percentile_ranks': self.percentile_ranks,
        }
        # year_counts 转为普通 dict
        if hasattr(self.year_counts, 'to_dict'):
            data['year_counts'] = {int(k): int(v) for k, v in self.year_counts.to_dict().items()}
        else:
            data['year_counts'] = dict(self.year_counts) if self.year_counts else {}
        return data

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_json(self, path: str | Path) -> None:
        """保存为 JSON 文件"""
        path = Path(path)
        path.write_text(self.to_json(), encoding='utf-8')
        print(f"[Profile] 已保存 JSON: {path}")
