"""
ApplicantAnalyzer: 申请人前期工作分析器

负责分析申请人的文献数据,生成完整的学术画像。
"""

import re
import math
from collections import Counter, defaultdict
from typing import Any

import pandas as pd

from scripts.journals import TOP_JOURNAL_NAMES, get_journal_if, estimate_citations
from scripts.applicant.profile import ApplicantProfile, JOURNAL_TIERS


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

        # 数据质量检查与清洗
        df_all, quality = self._check_data_quality(df_all)
        if df_disease is not None and not df_disease.empty:
            df_disease, _ = self._check_data_quality(df_disease, label='disease')
        if df_nibs is not None and not df_nibs.empty:
            df_nibs, _ = self._check_data_quality(df_nibs, label='nibs')

        # 更新总数 (去重后可能变化)
        profile.n_total = len(df_all)
        profile.n_disease = len(df_disease) if df_disease is not None else 0
        profile.n_nibs = len(df_nibs) if df_nibs is not None else 0

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

        # 合作者网络 (二元)
        profile.top_collaborators = self._extract_collaborators(df_all, name_patterns, top_n=10)
        profile.collaborator_graph = self._build_collaborator_graph(df_all, name_patterns, top_n=15)

        # 合作超图分析 (高阶结构)
        collab_structure = self._analyze_collaboration_structure(df_all, name_patterns)
        profile.stable_teams = collab_structure['stable_teams']
        profile.team_stability_index = collab_structure['stability_index']
        profile.avg_team_size = collab_structure['avg_team_size']
        profile.max_team_size = collab_structure['max_team_size']
        profile.solo_ratio = collab_structure['solo_ratio']

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
        """
        检查作者是否匹配任一模式。

        使用词边界匹配避免误匹配 (如 "Wang" 误匹配 "Wang Li")
        """
        author_lower = author.lower().strip()
        author_parts = set(re.split(r'[\s,\-]+', author_lower))

        for pattern in patterns:
            pattern_parts = set(re.split(r'[\s,\-]+', pattern.lower()))
            # 要求模式中所有部分都在作者名中出现
            if pattern_parts and pattern_parts <= author_parts:
                return True
            # 或完全包含 (用于处理 "zhang san" 匹配 "san zhang")
            if pattern in author_lower or author_lower in pattern:
                # 额外检查: 对于常见姓氏，要求更多匹配信息
                if pattern.split()[0] if ' ' in pattern else pattern in self.COMMON_SURNAMES:
                    # 常见姓氏需要匹配完整模式，不能只匹配姓
                    if len(pattern_parts) == 1 and len(author_parts) > 1:
                        continue  # 跳过仅姓氏匹配
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

        # 向量化计算每篇论文的估算引用数
        journals = df['journal'].fillna('')
        years = pd.to_numeric(df.get('year', current_year), errors='coerce').fillna(current_year)
        years_since = (current_year - years + 1).clip(lower=1)

        # 向量化 estimate_citations
        estimated_citations = [
            estimate_citations(j, int(y))
            for j, y in zip(journals, years_since)
        ]
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

    # ═══════════════════════════════════════════════════════════════════
    # 超图分析: 高阶合作模式
    # ═══════════════════════════════════════════════════════════════════

    def _extract_collaboration_hyperedges(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
    ) -> list[tuple[frozenset[str], int]]:
        """
        提取合作超边 (Collaboration Hyperedges).

        每篇论文的共同作者构成一条超边 (hyperedge)。
        统计每种作者组合出现的频次。

        Args:
            df: 文献 DataFrame (需含 'authors' 列)
            name_patterns: 申请人姓名匹配模式

        Returns:
            [(frozenset{coauthors}, count), ...] 按频次降序排列
            仅返回出现 2 次及以上的稳定团队

        Reference:
            Battiston et al. (2025) Higher-order interactions shape collective
            human behaviour. Nature Human Behaviour.
        """
        if 'authors' not in df.columns:
            return []

        hyperedge_counts: Counter[frozenset[str]] = Counter()

        for authors in df['authors'].dropna():
            author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
            # 移除申请人本人，保留合作者
            coauthors = frozenset(
                a for a in author_list
                if not self._match_author(a, name_patterns)
            )
            # 只统计有合作者的论文
            if len(coauthors) >= 1:
                hyperedge_counts[coauthors] += 1

        # 返回出现多次的稳定团队 (recurring hyperedges)
        recurring = [
            (edge, count) for edge, count in hyperedge_counts.items()
            if count >= 2
        ]
        return sorted(recurring, key=lambda x: -x[1])

    def _detect_stable_teams(
        self,
        hyperedges: list[tuple[frozenset[str], int]],
        min_size: int = 2,
        max_size: int = 6,
    ) -> list[dict[str, Any]]:
        """
        检测稳定合作团队.

        从超边中筛选出规模适中、重复出现的核心团队。

        Args:
            hyperedges: 超边列表 (来自 _extract_collaboration_hyperedges)
            min_size: 最小团队规模
            max_size: 最大团队规模

        Returns:
            [{'members': [...], 'papers': int, 'size': int}, ...]
        """
        teams = []
        for edge, count in hyperedges:
            if min_size <= len(edge) <= max_size:
                teams.append({
                    'members': sorted(list(edge)),
                    'papers': count,
                    'size': len(edge),
                })
        return teams[:10]  # 最多返回 10 个稳定团队

    def _compute_team_stability_index(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
    ) -> float:
        """
        计算团队稳定性指数.

        衡量申请人倾向于与固定团队合作还是与不同人合作。

        计算方式:
            稳定性 = 重复合作论文数 / 总合作论文数

        高稳定性 (>0.5): 倾向于与核心团队持续合作
        低稳定性 (<0.3): 合作网络广泛但关系较浅

        Args:
            df: 文献 DataFrame
            name_patterns: 申请人姓名模式

        Returns:
            0-1 之间的稳定性指数
        """
        hyperedges = self._extract_collaboration_hyperedges(df, name_patterns)

        if not hyperedges:
            return 0.0

        # 统计总论文数和重复团队论文数
        total_papers = len(df)
        recurring_papers = sum(count for _, count in hyperedges if count >= 2)

        if total_papers == 0:
            return 0.0

        return round(recurring_papers / total_papers, 3)

    def _analyze_collaboration_structure(
        self,
        df: pd.DataFrame,
        name_patterns: list[str],
    ) -> dict[str, Any]:
        """
        分析合作结构的高阶特征.

        综合分析申请人的合作模式，返回完整的超图指标。

        Args:
            df: 文献 DataFrame
            name_patterns: 姓名模式

        Returns:
            {
                'hyperedges': [...],           # 合作超边
                'stable_teams': [...],         # 稳定团队
                'stability_index': float,      # 团队稳定性
                'avg_team_size': float,        # 平均团队规模
                'max_team_size': int,          # 最大团队规模
                'solo_ratio': float,           # 独立发表比例
            }
        """
        hyperedges = self._extract_collaboration_hyperedges(df, name_patterns)
        stable_teams = self._detect_stable_teams(hyperedges)
        stability = self._compute_team_stability_index(df, name_patterns)

        # 统计团队规模分布
        if 'authors' in df.columns:
            team_sizes = []
            solo_count = 0
            for authors in df['authors'].dropna():
                author_list = [a.strip() for a in str(authors).split(';') if a.strip()]
                size = len(author_list)
                team_sizes.append(size)
                if size == 1:
                    solo_count += 1

            avg_size = sum(team_sizes) / len(team_sizes) if team_sizes else 0
            max_size = max(team_sizes) if team_sizes else 0
            solo_ratio = solo_count / len(team_sizes) if team_sizes else 0
        else:
            avg_size = 0
            max_size = 0
            solo_ratio = 0

        return {
            'hyperedges': hyperedges[:20],  # 保留前 20 条超边
            'stable_teams': stable_teams,
            'stability_index': stability,
            'avg_team_size': round(avg_size, 2),
            'max_team_size': max_size,
            'solo_ratio': round(solo_ratio, 3),
        }

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

    @staticmethod
    def _check_data_quality(
        df: pd.DataFrame,
        label: str = 'all',
    ) -> tuple[pd.DataFrame, dict]:
        """
        数据质量检查与自动清洗。

        检查项:
        1. PMID 去重
        2. 年份异常值 (< 1950 或 > 当前年份+1)
        3. 缺失关键字段 (title, journal)
        4. 空行过滤

        Args:
            df: 原始 DataFrame
            label: 数据集标签 (用于日志输出)

        Returns:
            (cleaned_df, quality_report)
        """
        n_original = len(df)
        issues = []

        # 1. PMID 去重
        if 'pmid' in df.columns:
            n_before = len(df)
            df = df.drop_duplicates(subset='pmid', keep='first')
            n_dup = n_before - len(df)
            if n_dup > 0:
                issues.append(f"去除 {n_dup} 条重复 PMID")

        # 2. 年份异常值
        if 'year' in df.columns:
            df = df.copy()
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            current_year = pd.Timestamp.now().year
            bad_year_mask = (df['year'] < 1950) | (df['year'] > current_year + 1)
            bad_year_mask = bad_year_mask & df['year'].notna()
            n_bad_year = bad_year_mask.sum()
            if n_bad_year > 0:
                df.loc[bad_year_mask, 'year'] = pd.NA
                issues.append(f"修正 {n_bad_year} 条异常年份")

        # 3. 缺失 title 过滤
        if 'title' in df.columns:
            empty_title = df['title'].isna() | (df['title'].str.strip() == '')
            n_empty = empty_title.sum()
            if n_empty > 0:
                df = df[~empty_title]
                issues.append(f"过滤 {n_empty} 条无标题记录")

        # 4. 统计缺失字段
        missing_stats = {}
        for col in ['title', 'journal', 'authors', 'abstract', 'year']:
            if col in df.columns:
                n_missing = df[col].isna().sum()
                if n_missing > 0:
                    pct = n_missing / max(len(df), 1) * 100
                    missing_stats[col] = {'count': n_missing, 'pct': round(pct, 1)}

        quality = {
            'original': n_original,
            'cleaned': len(df),
            'removed': n_original - len(df),
            'issues': issues,
            'missing_fields': missing_stats,
        }

        if issues:
            print(f"[QC-{label}] {', '.join(issues)} ({n_original}→{len(df)})")

        return df, quality


def check_pubmed_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    独立的数据质量检查函数，可在分析前调用。

    Args:
        df: PubMed 文献 DataFrame

    Returns:
        (清洗后的 DataFrame, 质量报告 dict)

    Example:
        >>> df_clean, report = check_pubmed_data(df_raw)
        >>> print(f"去重: {report['removed']} 篇")
    """
    return ApplicantAnalyzer._check_data_quality(df)
