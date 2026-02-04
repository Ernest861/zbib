"""申请人前期基础分析

分析内容:
- 年度发表分布
- 期刊分布（标注顶刊）
- 症状/靶区维度覆盖
- 第一作者/通讯作者统计
- 代表性论文识别
- H-index 估算
- 合作者网络
- 研究轨迹演变
- Markdown报告生成
- JSON导出
- 多申请人对比
"""

import json
import re
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.journals import TOP_JOURNAL_NAMES, get_journal_if, estimate_citations, JOURNAL_IF


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

# 适配度和胜任力的子维度
FIT_DIMENSIONS = ['disease', 'nibs', 'crossover']
COMPETENCY_DIMENSIONS = ['independence', 'impact', 'activity']


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

    # 合作者网络
    top_collaborators: list[tuple[str, int]] = field(default_factory=list)  # [(name, count), ...]
    collaborator_graph: dict[str, list[str]] = field(default_factory=dict)  # {author: [co-authors]}

    # 研究轨迹 (按时期的主题词)
    research_trajectory: dict[str, list[str]] = field(default_factory=dict)  # {period: [keywords]}
    trajectory_years: list[int] = field(default_factory=list)  # 发表年份序列(用于可视化)

    @property
    def relevance_score(self) -> float:
        """综合评分 (0-100) = 适配度 + 胜任力"""
        return self.calculate_score(DEFAULT_SCORE_WEIGHTS)

    @property
    def fit_score(self) -> float:
        """适配度评分 (0-100): 前期工作与课题的契合程度"""
        breakdown = self.get_score_breakdown()
        # 适配度 = disease + nibs + crossover 的加权和，归一化到 100
        fit_weight = sum(DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in FIT_DIMENSIONS)
        if fit_weight == 0:
            return 0
        fit_sum = sum(breakdown.get(d, 0) for d in FIT_DIMENSIONS)
        return round(fit_sum / fit_weight * 100, 1) if fit_weight else 0

    @property
    def competency_score(self) -> float:
        """胜任力评分 (0-100): 独立完成课题的能力"""
        breakdown = self.get_score_breakdown()
        # 胜任力 = independence + impact + activity 的加权和，归一化到 100
        comp_weight = sum(DEFAULT_SCORE_WEIGHTS.get(d, 0) for d in COMPETENCY_DIMENSIONS)
        if comp_weight == 0:
            return 0
        comp_sum = sum(breakdown.get(d, 0) for d in COMPETENCY_DIMENSIONS)
        return round(comp_sum / comp_weight * 100, 1) if comp_weight else 0

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
        score = 0.0

        # ═══ 适配度维度 ═══

        # 1. 疾病领域深度
        disease_score = 0.0
        if self.n_total > 0:
            disease_ratio = self.n_disease / self.n_total
            disease_score = min(100, disease_ratio * 160)
        score += disease_score * w.get('disease', 0.20)

        # 2. 技术方法专长
        nibs_score = 0.0
        base = self.n_disease if self.n_disease > 0 else self.n_total
        if base > 0:
            nibs_ratio = self.n_nibs / base
            nibs_score = min(100, nibs_ratio * 160)
        score += nibs_score * w.get('nibs', 0.20)

        # 3. 交叉研究经验 (疾病+NIBS)
        crossover_score = 0.0
        if self.n_disease > 0:
            crossover_ratio = self.n_disease_nibs / self.n_disease
            crossover_score = min(100, crossover_ratio * 200)  # 满分需要 50% 交叉
        score += crossover_score * w.get('crossover', 0.10)

        # ═══ 胜任力维度 ═══

        # 4. 学术独立性
        independence_score = 0.0
        if self.n_total > 0:
            independence = self.n_first_or_corresponding / self.n_total
            independence_score = min(100, independence * 150)
        score += independence_score * w.get('independence', 0.20)

        # 5. 学术影响力
        impact_score = min(50, self.top_journal_count * 10) + min(50, self.h_index_estimate * 5)
        score += impact_score * w.get('impact', 0.15)

        # 6. 研究活跃度
        activity_score = 0.0
        if self.n_total > 0:
            recent_ratio = self.recent_5yr_count / self.n_total
            activity_score = min(100, recent_ratio * 133)
        score += activity_score * w.get('activity', 0.15)

        return round(score, 1)

    def get_score_breakdown(self, weights: dict[str, float] | None = None) -> dict[str, float]:
        """获取各维度评分明细"""
        w = weights or DEFAULT_SCORE_WEIGHTS
        breakdown = {}

        # ═══ 适配度维度原始分 ═══
        if self.n_total > 0:
            breakdown['disease_raw'] = min(100, (self.n_disease / self.n_total) * 160)
        else:
            breakdown['disease_raw'] = 0

        base = self.n_disease if self.n_disease > 0 else self.n_total
        if base > 0:
            breakdown['nibs_raw'] = min(100, (self.n_nibs / base) * 160)
        else:
            breakdown['nibs_raw'] = 0

        if self.n_disease > 0:
            breakdown['crossover_raw'] = min(100, (self.n_disease_nibs / self.n_disease) * 200)
        else:
            breakdown['crossover_raw'] = 0

        # ═══ 胜任力维度原始分 ═══
        if self.n_total > 0:
            breakdown['independence_raw'] = min(100, (self.n_first_or_corresponding / self.n_total) * 150)
        else:
            breakdown['independence_raw'] = 0

        breakdown['impact_raw'] = min(50, self.top_journal_count * 10) + min(50, self.h_index_estimate * 5)

        if self.n_total > 0:
            breakdown['activity_raw'] = min(100, (self.recent_5yr_count / self.n_total) * 133)
        else:
            breakdown['activity_raw'] = 0

        # 加权得分
        breakdown['disease'] = round(breakdown['disease_raw'] * w.get('disease', 0.20), 1)
        breakdown['nibs'] = round(breakdown['nibs_raw'] * w.get('nibs', 0.20), 1)
        breakdown['crossover'] = round(breakdown['crossover_raw'] * w.get('crossover', 0.10), 1)
        breakdown['independence'] = round(breakdown['independence_raw'] * w.get('independence', 0.20), 1)
        breakdown['impact'] = round(breakdown['impact_raw'] * w.get('impact', 0.15), 1)
        breakdown['activity'] = round(breakdown['activity_raw'] * w.get('activity', 0.15), 1)
        breakdown['total'] = self.calculate_score(w)

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
            'relevance_score': self.relevance_score,
            'score_breakdown': self.get_score_breakdown(),
            'top_collaborators': [{'name': n, 'count': c} for n, c in self.top_collaborators],
            'research_trajectory': self.research_trajectory,
            'key_papers': self.key_papers,
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

    def save_json(self, path: str | Path):
        """保存为 JSON 文件"""
        path = Path(path)
        path.write_text(self.to_json(), encoding='utf-8')
        print(f"[Profile] 已保存 JSON: {path}")


class ApplicantAnalyzer:
    """申请人前期工作分析器"""

    # 常见中国姓氏（需要更精确匹配）
    COMMON_SURNAMES = {
        'wang', 'li', 'zhang', 'liu', 'chen', 'yang', 'huang', 'zhao',
        'wu', 'zhou', 'xu', 'sun', 'ma', 'zhu', 'hu', 'guo', 'he', 'lin',
        'luo', 'gao', 'zheng', 'liang', 'xie', 'tang', 'han', 'cao', 'deng',
    }

    def __init__(
        self,
        symptoms: dict[str, str] | None = None,
        targets: dict[str, str] | None = None,
        aliases: list[str] | None = None,
    ):
        """
        Args:
            symptoms: {症状名: 正则} 用于维度覆盖分析
            targets: {靶区名: 正则} 用于维度覆盖分析
            aliases: 作者姓名变体列表
        """
        self.symptoms = symptoms or {}
        self.targets = targets or {}
        self.aliases = aliases or []

    def analyze(
        self,
        name_cn: str,
        name_en: str,
        df_all: pd.DataFrame,
        df_disease: pd.DataFrame | None = None,
        df_nibs: pd.DataFrame | None = None,
    ) -> ApplicantProfile:
        """
        分析申请人前期工作基础。

        Args:
            name_cn: 中文姓名
            name_en: 英文姓名
            df_all: 全部文献
            df_disease: 疾病相关文献
            df_nibs: NIBS相关文献

        Returns:
            ApplicantProfile
        """
        if df_disease is None:
            df_disease = pd.DataFrame()
        if df_nibs is None:
            df_nibs = pd.DataFrame()

        # 计算 disease + NIBS 交集
        n_disease_nibs = 0
        if not df_disease.empty and not df_nibs.empty and 'pmid' in df_disease.columns:
            disease_pmids = set(df_disease['pmid'].dropna().astype(str))
            nibs_pmids = set(df_nibs['pmid'].dropna().astype(str))
            n_disease_nibs = len(disease_pmids & nibs_pmids)

        profile = ApplicantProfile(
            name_cn=name_cn,
            name_en=name_en,
            n_total=len(df_all),
            n_disease=len(df_disease),
            n_nibs=len(df_nibs),
            n_disease_nibs=n_disease_nibs,
        )

        if df_all.empty:
            return profile

        # 构建姓名匹配模式
        name_patterns = self._build_name_patterns(name_en)

        # 年度分布
        if 'year' in df_all.columns:
            df_all = df_all.copy()
            df_all['year'] = pd.to_numeric(df_all['year'], errors='coerce')
            year_counts = df_all['year'].dropna().astype(int).value_counts().sort_index()
            profile.year_counts = year_counts
            if not year_counts.empty:
                profile.year_range = (int(year_counts.index.min()), int(year_counts.index.max()))
                # 近5年发文数
                current_year = pd.Timestamp.now().year
                recent_mask = df_all['year'] >= (current_year - 4)
                profile.recent_5yr_count = recent_mask.sum()

        # 期刊分布
        if 'journal' in df_all.columns:
            journal_counts = df_all['journal'].value_counts().head(15).to_dict()
            profile.journal_counts = journal_counts

            # 期刊分级统计
            tier1_mask = df_all['journal'].apply(
                lambda j: j in JOURNAL_TIERS['tier1'] if pd.notna(j) else False
            )
            tier2_mask = df_all['journal'].apply(
                lambda j: j in JOURNAL_TIERS['tier2'] if pd.notna(j) else False
            )
            profile.tier1_count = tier1_mask.sum()
            profile.tier2_count = tier2_mask.sum()
            profile.top_journal_count = profile.tier1_count  # 向后兼容

            # 分级论文列表
            tier_papers = {'tier1': [], 'tier2': []}
            for tier_name, mask in [('tier1', tier1_mask), ('tier2', tier2_mask)]:
                if mask.any():
                    for _, row in df_all.loc[mask].head(5).iterrows():
                        tier_papers[tier_name].append({
                            'pmid': row.get('pmid', ''),
                            'title': row.get('title', ''),
                            'journal': row.get('journal', ''),
                            'year': row.get('year', ''),
                        })
            profile.journal_tier_papers = tier_papers

            # 顶刊论文标题列表 (向后兼容)
            if tier1_mask.any() and 'title' in df_all.columns:
                profile.top_journal_list = df_all.loc[tier1_mask, 'title'].head(5).tolist()

        # 第一作者/通讯作者统计
        first_set, corr_set = self._count_authorship(df_all, name_patterns)
        profile.n_first_author = len(first_set)
        profile.n_corresponding = len(corr_set)
        profile.n_first_or_corresponding = len(first_set | corr_set)

        # H-index 估算 (基于 IF 加权)
        profile.h_index_estimate = self._estimate_h_index(df_all)

        # IF 统计
        profile.if_stats = self._calculate_if_stats(df_all)

        # 合作者网络
        profile.top_collaborators = self._extract_collaborators(df_all, name_patterns, top_n=10)
        profile.collaborator_graph = self._build_collaborator_graph(df_all, name_patterns, top_n=15)

        # 研究轨迹
        profile.research_trajectory = self._analyze_trajectory(df_all)
        if 'year' in df_all.columns:
            profile.trajectory_years = sorted(df_all['year'].dropna().astype(int).unique().tolist())

        # 维度覆盖分析 (基于疾病相关文献)
        analysis_df = df_disease if not df_disease.empty else df_all
        text_col = self._get_text_column(analysis_df)

        if text_col and self.symptoms:
            profile.symptom_coverage = self._count_dimension(analysis_df[text_col], self.symptoms)
        if text_col and self.targets:
            profile.target_coverage = self._count_dimension(analysis_df[text_col], self.targets)

        # 代表性论文 (从 NIBS 相关优先，否则疾病相关，否则全部)
        key_source = df_nibs if not df_nibs.empty else (df_disease if not df_disease.empty else df_all)
        profile.key_papers = self._extract_key_papers(key_source, name_patterns, top_n=5)

        return profile

    def _build_name_patterns(self, name_en: str) -> list[str]:
        """构建姓名匹配模式列表"""
        patterns = []

        # 原始名字 (e.g., "Ming Wang")
        patterns.append(name_en.lower())

        # 分解姓名
        parts = name_en.split()
        if len(parts) >= 2:
            # 假设格式: FirstName LastName 或 LastName FirstName
            # 尝试两种顺序
            first, last = parts[0], parts[-1]

            # 完整名字变体
            patterns.append(f"{last} {first}".lower())  # Wang Ming
            patterns.append(f"{last}, {first}".lower())  # Wang, Ming
            patterns.append(f"{first[0]} {last}".lower())  # M Wang
            patterns.append(f"{last} {first[0]}".lower())  # Wang M

            # 如果是常见姓，需要更严格匹配
            if last.lower() in self.COMMON_SURNAMES or first.lower() in self.COMMON_SURNAMES:
                # 只用完整名或首字母缩写
                pass
            else:
                # 非常见姓可以只用姓
                patterns.append(last.lower())

        # 添加用户提供的别名
        for alias in self.aliases:
            patterns.append(alias.lower())

        return list(set(patterns))

    def _match_author(self, author: str, patterns: list[str]) -> bool:
        """检查作者是否匹配任一模式"""
        author_lower = author.lower().strip()
        for pattern in patterns:
            if pattern in author_lower or author_lower in pattern:
                return True
        return False

    def _count_authorship(self, df: pd.DataFrame, name_patterns: list[str]) -> tuple[set, set]:
        """统计第一作者和通讯作者文献，返回PMID集合"""
        first_pmids = set()
        corr_pmids = set()

        if 'authors' not in df.columns:
            return first_pmids, corr_pmids

        for idx, row in df.iterrows():
            authors = row.get('authors', '')
            if pd.isna(authors):
                continue

            author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
            if not author_list:
                continue

            pmid = str(row.get('pmid', idx))

            # 第一作者
            if self._match_author(author_list[0], name_patterns):
                first_pmids.add(pmid)

            # 通讯作者（最后一位）
            if self._match_author(author_list[-1], name_patterns):
                corr_pmids.add(pmid)

        return first_pmids, corr_pmids

    def _estimate_h_index(self, df: pd.DataFrame) -> int:
        """
        基于期刊 IF 和发表年限估算 H-index。

        方法:
        1. 为每篇论文估算引用数: citations ≈ IF × √years × 0.8
        2. 按估算引用数排序
        3. 找到最大的 h 使得至少有 h 篇论文引用数 ≥ h

        这比简单的 √n 公式更准确，因为考虑了期刊影响力。
        """
        n = len(df)
        if n == 0:
            return 0

        current_year = pd.Timestamp.now().year

        # 计算每篇论文的估算引用数
        estimated_citations = []
        for _, row in df.iterrows():
            journal = row.get('journal', '')
            year = row.get('year', current_year)
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = current_year

            years_since = max(1, current_year - year + 1)
            citations = estimate_citations(journal, years_since)
            estimated_citations.append(citations)

        # 按引用数降序排序
        estimated_citations.sort(reverse=True)

        # 计算 H-index
        h = 0
        for i, citations in enumerate(estimated_citations):
            if citations >= i + 1:
                h = i + 1
            else:
                break

        # 应用上限: 职业年限 × 2 (合理的 H-index 增长率)
        if 'year' in df.columns:
            years = df['year'].dropna()
            if len(years) > 0:
                career_years = current_year - int(years.min()) + 1
                h = min(h, career_years * 2)

        return max(1, h)

    def _calculate_if_stats(self, df: pd.DataFrame) -> dict:
        """计算 IF 相关统计指标"""
        if df.empty or 'journal' not in df.columns:
            return {'total_if': 0, 'avg_if': 0, 'max_if': 0, 'median_if': 0}

        ifs = [get_journal_if(j) for j in df['journal'].dropna()]
        if not ifs:
            return {'total_if': 0, 'avg_if': 0, 'max_if': 0, 'median_if': 0}

        ifs_sorted = sorted(ifs)
        median_idx = len(ifs_sorted) // 2
        median_if = ifs_sorted[median_idx] if ifs_sorted else 0

        return {
            'total_if': round(sum(ifs), 1),
            'avg_if': round(sum(ifs) / len(ifs), 2),
            'max_if': round(max(ifs), 1),
            'median_if': round(median_if, 1),
        }

    def _extract_collaborators(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
        top_n: int = 10,
    ) -> list[tuple[str, int]]:
        """提取主要合作者"""
        if 'authors' not in df.columns:
            return []

        collaborator_counts = Counter()

        for authors in df['authors'].dropna():
            author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
            for author in author_list:
                # 排除申请人自己
                if not self._match_author(author, name_patterns):
                    # 标准化作者名
                    collaborator_counts[author] += 1

        return collaborator_counts.most_common(top_n)

    def _build_collaborator_graph(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
        top_n: int = 15,
    ) -> dict[str, list[str]]:
        """
        构建合作者网络图 (用于可视化).

        返回: {核心作者: [共同发文的合作者列表]}
        """
        if 'authors' not in df.columns:
            return {}

        # 获取主要合作者
        top_collabs = set()
        collaborator_counts = Counter()

        for authors in df['authors'].dropna():
            author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
            for author in author_list:
                if not self._match_author(author, name_patterns):
                    collaborator_counts[author] += 1

        for name, _ in collaborator_counts.most_common(top_n):
            top_collabs.add(name)

        # 构建合作关系图
        graph = defaultdict(set)
        for authors in df['authors'].dropna():
            author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
            # 只关注top合作者之间的关系
            relevant = [a for a in author_list if a in top_collabs]
            for i, a1 in enumerate(relevant):
                for a2 in relevant[i+1:]:
                    graph[a1].add(a2)
                    graph[a2].add(a1)

        return {k: list(v) for k, v in graph.items()}

    def _analyze_trajectory(self, df: pd.DataFrame) -> dict[str, list[str]]:
        """分析研究轨迹 (按时期提取高频关键词)"""
        trajectory = {}

        if 'year' not in df.columns:
            return trajectory

        df = df.copy()
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df.dropna(subset=['year'])

        if df.empty:
            return trajectory

        # 定义时期
        min_year = int(df['year'].min())
        max_year = int(df['year'].max())

        periods = []
        if max_year - min_year <= 5:
            periods = [(min_year, max_year)]
        elif max_year - min_year <= 10:
            mid = (min_year + max_year) // 2
            periods = [(min_year, mid), (mid + 1, max_year)]
        else:
            # 分三个时期
            span = (max_year - min_year) // 3
            periods = [
                (min_year, min_year + span),
                (min_year + span + 1, min_year + 2 * span),
                (min_year + 2 * span + 1, max_year),
            ]

        # 提取关键词的列
        kw_cols = ['keywords', 'mesh']
        kw_col = None
        for col in kw_cols:
            if col in df.columns:
                kw_col = col
                break

        if kw_col is None:
            return trajectory

        for start, end in periods:
            period_df = df[(df['year'] >= start) & (df['year'] <= end)]
            if period_df.empty:
                continue

            # 统计关键词
            all_kw = []
            for kws in period_df[kw_col].dropna():
                # 关键词通常用 "; " 分隔
                all_kw.extend([k.strip().lower() for k in str(kws).split(';') if k.strip()])

            if all_kw:
                top_kw = [kw for kw, _ in Counter(all_kw).most_common(5)]
                trajectory[f"{start}-{end}"] = top_kw

        return trajectory

    def _get_text_column(self, df: pd.DataFrame) -> str | None:
        """获取用于文本分析的列"""
        # 优先使用已合并的 text 列
        if 'text' in df.columns:
            return 'text'
        # 否则拼接 title + abstract
        if 'title' in df.columns and 'abstract' in df.columns:
            df['_text'] = df['title'].fillna('') + ' ' + df['abstract'].fillna('')
            return '_text'
        if 'title' in df.columns:
            return 'title'
        return None

    def _count_dimension(self, texts: pd.Series, patterns: dict[str, str]) -> dict[str, int]:
        """统计各维度覆盖数量"""
        result = {}
        for name, pattern in patterns.items():
            count = texts.str.contains(pattern, flags=re.I, na=False).sum()
            if count > 0:
                result[name] = count
        return result

    def _extract_key_papers(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        """提取代表性论文"""
        if df.empty:
            return []

        current_year = pd.Timestamp.now().year
        papers = []

        for _, row in df.iterrows():
            paper = {
                'pmid': row.get('pmid', ''),
                'year': row.get('year', ''),
                'title': row.get('title', ''),
                'journal': row.get('journal', ''),
                'authors': row.get('authors', ''),
            }

            # 计算评分
            score = 0

            # 顶刊 +5
            journal = paper.get('journal', '')
            if journal and journal in TOP_JOURNAL_NAMES:
                score += 5

            # 第一作者 +4
            authors = paper.get('authors', '')
            if authors:
                author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
                if author_list and self._match_author(author_list[0], name_patterns):
                    score += 4
                # 通讯作者 +3
                elif author_list and self._match_author(author_list[-1], name_patterns):
                    score += 3

            # 近5年 +2, 近3年 +3
            try:
                year = int(paper.get('year', 0))
                if year >= current_year - 2:
                    score += 3
                elif year >= current_year - 4:
                    score += 2
            except (ValueError, TypeError):
                pass

            paper['_score'] = score
            papers.append(paper)

        # 按评分排序，取 top_n
        papers.sort(key=lambda p: (-p['_score'], -int(p.get('year', 0) or 0)))
        for p in papers:
            p.pop('_score', None)
        return papers[:top_n]


def create_profile_summary(profile: ApplicantProfile) -> str:
    """生成申请人前期工作摘要文本"""
    lines = [
        f"═══════════════════════════════════════════════",
        f"申请人前期工作基础报告",
        f"═══════════════════════════════════════════════",
        f"",
        f"姓名: {profile.name_cn} ({profile.name_en})",
        f"发表年限: {profile.year_range[0]}-{profile.year_range[1]} ({profile.experience_years}年)",
        f"H-index (估算): {profile.h_index_estimate}",
        f"",
        f"───────────────────────────────────────────────",
        f"文献统计",
        f"───────────────────────────────────────────────",
        f"  全部文献: {profile.n_total} 篇",
        f"  近5年发文: {profile.recent_5yr_count} 篇",
        f"  疾病相关: {profile.n_disease} 篇",
        f"  NIBS相关: {profile.n_nibs} 篇",
        f"  疾病+NIBS: {profile.n_disease_nibs} 篇",
        f"",
        f"  第一作者: {profile.n_first_author} 篇",
        f"  通讯作者: {profile.n_corresponding} 篇",
        f"  第一或通讯: {profile.n_first_or_corresponding} 篇",
        f"  顶刊发表: {profile.top_journal_count} 篇",
        f"",
        f"───────────────────────────────────────────────",
        f"相关度评分: {profile.relevance_score}/100",
        f"───────────────────────────────────────────────",
    ]

    if profile.symptom_coverage:
        lines.append(f"\n症状维度覆盖:")
        for name, count in sorted(profile.symptom_coverage.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count} 篇")

    if profile.target_coverage:
        lines.append(f"\n靶区维度覆盖:")
        for name, count in sorted(profile.target_coverage.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count} 篇")

    if profile.top_journal_list:
        lines.append(f"\n顶刊论文:")
        for i, title in enumerate(profile.top_journal_list[:5], 1):
            title_short = title[:55] + '...' if len(title) > 55 else title
            lines.append(f"  [{i}] {title_short}")

    if profile.top_collaborators:
        lines.append(f"\n主要合作者 (共{len(profile.top_collaborators)}人):")
        for name, count in profile.top_collaborators[:5]:
            lines.append(f"  {name}: {count}次")

    if profile.research_trajectory:
        lines.append(f"\n研究轨迹:")
        for period, keywords in profile.research_trajectory.items():
            kw_str = ', '.join(keywords[:4])
            lines.append(f"  {period}: {kw_str}")

    if profile.key_papers:
        lines.append(f"\n代表性论文:")
        for i, p in enumerate(profile.key_papers[:5], 1):
            title = p.get('title', '')[:55]
            if len(p.get('title', '')) > 55:
                title += '...'
            lines.append(f"  [{i}] {p.get('year', '')} {p.get('journal', '')}")
            lines.append(f"      {title}")

    lines.append(f"\n═══════════════════════════════════════════════")
    return '\n'.join(lines)


def create_markdown_report(profile: ApplicantProfile, topic_name: str = '') -> str:
    """
    生成申请人前期工作基础 Markdown 报告.

    Args:
        profile: ApplicantProfile 对象
        topic_name: 研究主题名称 (可选)

    Returns:
        Markdown 格式的报告文本
    """
    lines = []

    # 标题
    title = f"# 申请人前期工作基础报告"
    if topic_name:
        title += f" — {topic_name}"
    lines.append(title)
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # 基本信息
    lines.append("## 1. 申请人信息")
    lines.append("")
    lines.append(f"| 项目 | 内容 |")
    lines.append(f"|:-----|:-----|")
    lines.append(f"| **姓名** | {profile.name_cn} ({profile.name_en}) |")
    lines.append(f"| **发表年限** | {profile.year_range[0]}-{profile.year_range[1]} ({profile.experience_years}年) |")
    lines.append(f"| **H-index (估算)** | {profile.h_index_estimate} |")
    lines.append(f"| **相关度评分** | **{profile.relevance_score}/100** |")
    lines.append("")

    # 发表统计
    lines.append("## 2. 发表统计")
    lines.append("")
    lines.append("### 2.1 文献数量")
    lines.append("")
    lines.append(f"| 类别 | 数量 | 占比 |")
    lines.append(f"|:-----|-----:|-----:|")
    total = profile.n_total or 1
    lines.append(f"| 全部文献 | {profile.n_total} | 100% |")
    lines.append(f"| 近5年发文 | {profile.recent_5yr_count} | {profile.recent_5yr_count*100//total}% |")
    lines.append(f"| 疾病相关 | {profile.n_disease} | {profile.n_disease*100//total}% |")
    lines.append(f"| NIBS相关 | {profile.n_nibs} | {profile.n_nibs*100//total}% |")
    lines.append(f"| 疾病+NIBS | {profile.n_disease_nibs} | {profile.n_disease_nibs*100//total}% |")
    lines.append("")

    lines.append("### 2.2 作者身份")
    lines.append("")
    lines.append(f"| 身份 | 数量 | 占比 |")
    lines.append(f"|:-----|-----:|-----:|")
    lines.append(f"| 第一作者 | {profile.n_first_author} | {profile.n_first_author*100//total}% |")
    lines.append(f"| 通讯作者 | {profile.n_corresponding} | {profile.n_corresponding*100//total}% |")
    lines.append(f"| 第一或通讯 | {profile.n_first_or_corresponding} | {profile.n_first_or_corresponding*100//total}% |")
    lines.append("")

    # 期刊分布
    lines.append("### 2.3 期刊影响力")
    lines.append("")
    tier1 = getattr(profile, 'tier1_count', profile.top_journal_count)
    tier2 = getattr(profile, 'tier2_count', 0)
    lines.append(f"- **顶刊 (IF≥10)**: {tier1} 篇")
    lines.append(f"- **高质量期刊 (IF≥4)**: {tier2} 篇")

    # IF 统计
    if_stats = getattr(profile, 'if_stats', {})
    if if_stats:
        lines.append("")
        lines.append("**影响因子统计:**")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|:-----|-----:|")
        lines.append(f"| 累计 IF | {if_stats.get('total_if', 0)} |")
        lines.append(f"| 平均 IF | {if_stats.get('avg_if', 0)} |")
        lines.append(f"| 最高 IF | {if_stats.get('max_if', 0)} |")
        lines.append(f"| 中位 IF | {if_stats.get('median_if', 0)} |")
    lines.append("")

    if profile.journal_counts:
        lines.append("**主要发表期刊:**")
        lines.append("")
        lines.append(f"| 期刊 | 篇数 |")
        lines.append(f"|:-----|-----:|")
        for journal, count in list(profile.journal_counts.items())[:10]:
            tier_mark = ""
            if journal in JOURNAL_TIERS['tier1']:
                tier_mark = " ⭐"
            elif journal in JOURNAL_TIERS['tier2']:
                tier_mark = " ★"
            lines.append(f"| {journal}{tier_mark} | {count} |")
        lines.append("")

    # 维度覆盖
    if profile.symptom_coverage or profile.target_coverage:
        lines.append("## 3. 研究维度覆盖")
        lines.append("")

        if profile.symptom_coverage:
            lines.append("### 3.1 症状维度")
            lines.append("")
            for name, count in sorted(profile.symptom_coverage.items(), key=lambda x: -x[1]):
                lines.append(f"- **{name}**: {count} 篇")
            lines.append("")

        if profile.target_coverage:
            lines.append("### 3.2 靶区维度")
            lines.append("")
            for name, count in sorted(profile.target_coverage.items(), key=lambda x: -x[1]):
                lines.append(f"- **{name}**: {count} 篇")
            lines.append("")

    # 合作网络
    if profile.top_collaborators:
        lines.append("## 4. 合作网络")
        lines.append("")
        lines.append("### 主要合作者")
        lines.append("")
        lines.append(f"| 合作者 | 合作次数 |")
        lines.append(f"|:-------|--------:|")
        for name, count in profile.top_collaborators[:10]:
            lines.append(f"| {name} | {count} |")
        lines.append("")

    # 研究轨迹
    if profile.research_trajectory:
        lines.append("## 5. 研究轨迹")
        lines.append("")
        lines.append("研究主题随时间的演变:")
        lines.append("")
        for period, keywords in profile.research_trajectory.items():
            kw_str = ', '.join(keywords)
            lines.append(f"- **{period}**: {kw_str}")
        lines.append("")

    # 代表性论文
    if profile.key_papers:
        lines.append("## 6. 代表性论文")
        lines.append("")
        for i, paper in enumerate(profile.key_papers[:5], 1):
            title = paper.get('title', '')
            year = paper.get('year', '')
            journal = paper.get('journal', '')
            pmid = paper.get('pmid', '')
            lines.append(f"**{i}. [{year}] {journal}**")
            lines.append(f"")
            lines.append(f"> {title}")
            if pmid:
                lines.append(f"> PMID: [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
            lines.append("")

    # 顶刊论文 (如果有)
    tier_papers = getattr(profile, 'journal_tier_papers', {})
    if tier_papers.get('tier1'):
        lines.append("## 7. 顶刊论文详情")
        lines.append("")
        for paper in tier_papers['tier1']:
            lines.append(f"- **[{paper.get('year', '')}] {paper.get('journal', '')}**")
            lines.append(f"  {paper.get('title', '')}")
        lines.append("")

    # 评分解读
    lines.append("## 8. 相关度评分解读")
    lines.append("")
    score = profile.relevance_score
    if score >= 80:
        assessment = "**极高相关度** - 申请人在该领域有深厚的前期工作基础"
    elif score >= 60:
        assessment = "**高相关度** - 申请人在该领域有较好的前期积累"
    elif score >= 40:
        assessment = "**中等相关度** - 申请人有一定的相关工作基础"
    elif score >= 20:
        assessment = "**低相关度** - 申请人在该领域的前期工作较少"
    else:
        assessment = "**相关度较低** - 建议加强前期工作积累"

    lines.append(f"- 综合评分: **{score}/100**")
    lines.append(f"- 评估: {assessment}")
    lines.append("")

    lines.append("### 评分维度说明")
    lines.append("")
    lines.append("| 维度 | 权重 | 说明 |")
    lines.append("|:-----|:----:|:-----|")
    lines.append("| 疾病相关度 | 25% | 疾病相关文献占比 |")
    lines.append("| NIBS专业度 | 25% | NIBS相关文献占比 |")
    lines.append("| 学术独立性 | 20% | 第一/通讯作者占比 |")
    lines.append("| 学术影响力 | 15% | 顶刊发表 + H-index |")
    lines.append("| 研究活跃度 | 15% | 近5年发文占比 |")
    lines.append("")

    lines.append("---")
    lines.append("*报告由 zbib 自动生成*")

    return '\n'.join(lines)


def save_markdown_report(profile: ApplicantProfile, output_path: str, topic_name: str = ''):
    """保存 Markdown 报告到文件"""
    from pathlib import Path
    content = create_markdown_report(profile, topic_name)
    path = Path(output_path)
    path.write_text(content, encoding='utf-8')
    print(f"[Report] 已保存 Markdown 报告: {path}")
