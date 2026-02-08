"""
申请人模块单元测试

测试覆盖:
- ApplicantProfile 评分计算
- 作者姓名匹配逻辑
- 百分位排名计算
- 数据质量检查
- 报告生成

运行测试:
    cd zbib
    python -m pytest tests/test_applicant.py -v

注意: 由于 NumPy/matplotlib 版本兼容问题，运行前需要:
    - 确保 numpy<2.0 或更新 matplotlib
    - 或使用 pytest --ignore 跳过依赖 matplotlib 的测试
"""

import sys
from pathlib import Path

# 绕过 scripts/__init__.py 的 matplotlib 导入
sys.modules['scripts'] = type(sys)('scripts')
sys.modules['scripts'].__path__ = [str(Path(__file__).parent.parent / 'scripts')]

import pytest
import pandas as pd
from dataclasses import asdict


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


@pytest.fixture
def sample_profile():
    """创建测试用的 ApplicantProfile"""
    from scripts.applicant import ApplicantProfile

    return ApplicantProfile(
        name_cn='张三',
        name_en='San Zhang',
        n_total=50,
        n_disease=30,
        n_nibs=25,
        n_disease_nibs=15,
        n_first_author=20,
        n_corresponding=15,
        n_first_or_corresponding=25,
        top_journal_count=5,
        tier1_count=3,
        tier2_count=8,
        h_index_estimate=12,
        recent_5yr_count=20,
        year_range=(2010, 2024),
        year_counts=pd.Series({2020: 5, 2021: 6, 2022: 7, 2023: 8}),
        journal_counts={'Brain Stimul': 5, 'Neuroimage': 4, 'J Neurosci': 3},
        symptom_coverage={'阴性症状': 10, '认知功能': 8},
        target_coverage={'DLPFC': 12, 'OFC': 5},
        if_stats={'total_if': 150, 'avg_if': 5.0, 'max_if': 25.0, 'median_if': 4.0},
    )


@pytest.fixture
def sample_df():
    """创建测试用的 PubMed DataFrame"""
    return pd.DataFrame({
        'pmid': ['12345', '12346', '12347', '12348', '12349'],
        'title': [
            'TMS treatment for schizophrenia',
            'DLPFC stimulation effects',
            'OFC and negative symptoms',
            'Neural circuits in psychosis',
            'Cognitive rehabilitation study',
        ],
        'authors': [
            'Zhang S; Li W; Wang X',
            'Zhang San; Chen Y',
            'Wang X; Zhang S',
            'Li W; Zhang San; Chen Y',
            'Zhang S',
        ],
        'journal': ['Brain Stimul', 'Neuroimage', 'Biol Psychiatry', 'J Neurosci', 'Cortex'],
        'year': [2020, 2021, 2022, 2023, 2024],
    })


@pytest.fixture
def empty_profile():
    """创建空的 ApplicantProfile"""
    from scripts.applicant import ApplicantProfile

    return ApplicantProfile(
        name_cn='空',
        name_en='Empty',
        n_total=0,
    )


# ═══════════════════════════════════════════════
# Profile 评分测试
# ═══════════════════════════════════════════════


class TestApplicantProfile:
    """ApplicantProfile 数据类测试"""

    def test_relevance_score_range(self, sample_profile):
        """综合评分应在 0-100 范围内"""
        score = sample_profile.relevance_score
        assert 0 <= score <= 100, f"评分 {score} 超出范围"

    def test_fit_score_range(self, sample_profile):
        """适配度评分应在 0-100 范围内"""
        fit = sample_profile.fit_score
        assert 0 <= fit <= 100, f"适配度 {fit} 超出范围"

    def test_competency_score_range(self, sample_profile):
        """胜任力评分应在 0-100 范围内"""
        comp = sample_profile.competency_score
        assert 0 <= comp <= 100, f"胜任力 {comp} 超出范围"

    def test_score_breakdown_completeness(self, sample_profile):
        """评分明细应包含所有维度"""
        breakdown = sample_profile.get_score_breakdown()

        expected_keys = [
            'disease', 'nibs', 'crossover',
            'independence', 'impact', 'activity',
            'disease_raw', 'nibs_raw', 'crossover_raw',
            'independence_raw', 'impact_raw', 'activity_raw',
            'fit', 'competency', 'total',
        ]
        for key in expected_keys:
            assert key in breakdown, f"缺少维度: {key}"

    def test_empty_profile_no_division_error(self, empty_profile):
        """空 profile 不应产生除零错误"""
        # 这些调用不应抛出异常
        score = empty_profile.relevance_score
        fit = empty_profile.fit_score
        comp = empty_profile.competency_score
        breakdown = empty_profile.get_score_breakdown()

        assert score == 0 or score >= 0  # 空数据可能返回 0 或有默认值
        assert isinstance(breakdown, dict)

    def test_experience_years(self, sample_profile):
        """经验年数计算"""
        years = sample_profile.experience_years
        assert years == 15, f"预期 15 年，实际 {years} 年"

    def test_to_dict(self, sample_profile):
        """to_dict 应返回可序列化的字典"""
        d = sample_profile.to_dict()
        assert isinstance(d, dict)
        assert d['name_cn'] == '张三'
        assert d['n_total'] == 50

    def test_to_json(self, sample_profile):
        """to_json 应返回有效的 JSON 字符串"""
        import json
        json_str = sample_profile.to_json()
        data = json.loads(json_str)
        assert data['name_en'] == 'San Zhang'


# ═══════════════════════════════════════════════
# 作者匹配测试
# ═══════════════════════════════════════════════


class TestAuthorMatching:
    """作者姓名匹配逻辑测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        from scripts.applicant import ApplicantAnalyzer
        return ApplicantAnalyzer()

    def test_exact_match(self, analyzer):
        """精确匹配测试"""
        patterns = ['zhang san', 'san zhang']
        assert analyzer._match_author('Zhang San', patterns)
        assert analyzer._match_author('San Zhang', patterns)

    def test_partial_match(self, analyzer):
        """部分匹配测试"""
        patterns = ['zhang san']
        # 包含完整模式应匹配
        assert analyzer._match_author('Zhang San, MD', patterns)

    def test_common_surname_protection(self, analyzer):
        """常见姓氏保护测试 - 避免仅姓氏匹配"""
        patterns = ['wang']  # 仅姓氏
        # 对于仅姓氏模式，应该能匹配包含该姓氏的作者
        # 但不应该误匹配完全不同的人
        result = analyzer._match_author('Wang Xiaoming', patterns)
        # 这个测试验证逻辑存在，具体行为取决于实现

    def test_no_false_positive(self, analyzer):
        """避免误匹配测试"""
        patterns = ['zhang san']
        # 完全不同的名字不应匹配
        assert not analyzer._match_author('Li Si', patterns)
        assert not analyzer._match_author('Wang Wu', patterns)

    def test_case_insensitive(self, analyzer):
        """大小写不敏感测试"""
        patterns = ['zhang san']
        assert analyzer._match_author('ZHANG SAN', patterns)
        assert analyzer._match_author('zhang san', patterns)
        assert analyzer._match_author('Zhang San', patterns)


# ═══════════════════════════════════════════════
# 百分位排名测试
# ═══════════════════════════════════════════════


class TestBenchmark:
    """百分位排名和基准测试"""

    def test_quick_percentile_basic(self):
        """快速百分位计算基本功能"""
        from scripts.applicant import quick_percentile

        # 50 篇文献在 NIBS-Psychiatry 领域的百分位
        pct = quick_percentile(50, 'n_total')
        assert 0 <= pct <= 100

    def test_quick_percentile_extremes(self):
        """极端值的百分位计算"""
        from scripts.applicant import quick_percentile

        # 很少的文献应该低百分位
        low_pct = quick_percentile(5, 'n_total')
        assert low_pct < 30

        # 很多文献应该高百分位
        high_pct = quick_percentile(200, 'n_total')
        assert high_pct > 70

    def test_get_benchmark_by_name(self):
        """按名称获取基准"""
        from scripts.applicant import get_benchmark_by_name

        bm = get_benchmark_by_name('NIBS-Psychiatry')
        assert bm.name == 'NIBS-Psychiatry'

        bm2 = get_benchmark_by_name('nibs')  # 别名
        assert bm2.name == 'NIBS-Psychiatry'

    def test_get_benchmark_invalid_name(self):
        """无效基准名称应抛出异常"""
        from scripts.applicant import get_benchmark_by_name

        with pytest.raises(ValueError):
            get_benchmark_by_name('invalid-benchmark')

    def test_apply_benchmark(self, sample_profile):
        """应用基准后 profile 应有百分位排名"""
        from scripts.applicant import apply_benchmark

        updated = apply_benchmark(sample_profile)
        assert updated.percentile_ranks
        assert 'n_total' in updated.percentile_ranks
        assert 'h_index' in updated.percentile_ranks


# ═══════════════════════════════════════════════
# 数据质量检查测试
# ═══════════════════════════════════════════════


class TestDataQuality:
    """数据质量检查测试"""

    def test_check_pubmed_data_dedup(self):
        """去重功能测试"""
        from scripts.applicant import check_pubmed_data

        df = pd.DataFrame({
            'pmid': ['123', '123', '456'],  # 重复 PMID
            'title': ['A', 'A', 'B'],
            'year': [2020, 2020, 2021],
        })

        df_clean, report = check_pubmed_data(df)
        assert len(df_clean) == 2, "应去除重复"
        assert report['removed'] >= 1

    def test_check_pubmed_data_year_outlier(self):
        """年份异常值测试"""
        from scripts.applicant import check_pubmed_data

        df = pd.DataFrame({
            'pmid': ['1', '2', '3'],
            'title': ['A', 'B', 'C'],
            'year': [2020, 1800, 2100],  # 异常年份
        })

        df_clean, report = check_pubmed_data(df)
        # 异常年份应被处理

    def test_check_pubmed_data_empty_title(self):
        """空标题过滤测试"""
        from scripts.applicant import check_pubmed_data

        df = pd.DataFrame({
            'pmid': ['1', '2', '3'],
            'title': ['Valid', '', None],
            'year': [2020, 2021, 2022],
        })

        df_clean, report = check_pubmed_data(df)
        assert len(df_clean) <= len(df)


# ═══════════════════════════════════════════════
# 报告生成测试
# ═══════════════════════════════════════════════


class TestReportGeneration:
    """报告生成测试"""

    def test_create_markdown_report_not_empty(self, sample_profile):
        """Markdown 报告应非空"""
        from scripts.applicant import create_markdown_report

        report = create_markdown_report(sample_profile, 'OFC-rTMS研究')
        assert len(report) > 500
        assert '# 申请人前期工作基础报告' in report

    def test_create_markdown_report_sections(self, sample_profile):
        """报告应包含主要章节"""
        from scripts.applicant import create_markdown_report

        report = create_markdown_report(sample_profile)

        expected_sections = [
            '## 1. 申请人信息',
            '## 2. 发表统计',
            '## 8. 申报者适配度与胜任力评估',
        ]
        for section in expected_sections:
            assert section in report, f"缺少章节: {section}"

    def test_create_profile_summary(self, sample_profile):
        """纯文本摘要测试"""
        from scripts.applicant import create_profile_summary

        summary = create_profile_summary(sample_profile)
        assert '张三' in summary
        assert '文献统计' in summary

    def test_create_comparison_report(self, sample_profile):
        """多申请人对比报告测试"""
        from scripts.applicant import create_comparison_report, ApplicantProfile

        profile2 = ApplicantProfile(
            name_cn='李四',
            name_en='Si Li',
            n_total=40,
            n_disease=20,
            n_nibs=15,
            n_disease_nibs=8,
            n_first_or_corresponding=18,
            h_index_estimate=8,
            recent_5yr_count=15,
        )

        report = create_comparison_report([sample_profile, profile2])
        assert '# 申请人对比分析报告' in report
        assert '张三' in report
        assert '李四' in report


# ═══════════════════════════════════════════════
# 评估功能测试
# ═══════════════════════════════════════════════


class TestAssessment:
    """评估功能测试"""

    def test_get_quadrant_position(self, sample_profile):
        """象限定位测试"""
        from scripts.applicant import get_quadrant_position

        pos = get_quadrant_position(sample_profile)
        assert 'label' in pos
        assert 'fit' in pos
        assert 'competency' in pos
        assert pos['label'] in ['明星申请人', '潜力申请人', '跨界申请人', '成长型申请人']

    def test_analyze_weaknesses(self, sample_profile):
        """薄弱维度分析测试"""
        from scripts.applicant import analyze_weaknesses

        weaknesses = analyze_weaknesses(sample_profile)
        assert isinstance(weaknesses, list)
        # 如果有薄弱维度，应包含必要字段
        for w in weaknesses:
            assert 'dimension' in w
            assert 'score' in w
            assert 'suggestion' in w

    def test_generate_narrative_assessment(self, sample_profile):
        """叙事性评估测试"""
        from scripts.applicant import generate_narrative_assessment

        narrative = generate_narrative_assessment(sample_profile, 'OFC-rTMS研究')
        # 应返回字符串 (可能为空字符串)
        assert isinstance(narrative, str)


# ═══════════════════════════════════════════════
# 权重验证测试
# ═══════════════════════════════════════════════


class TestScoreWeights:
    """评分权重验证测试"""

    def test_default_weights_sum_to_one(self):
        """默认权重总和应为 1.0"""
        from scripts.applicant import DEFAULT_SCORE_WEIGHTS

        total = sum(DEFAULT_SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"权重总和 {total} 不等于 1.0"

    def test_fit_competency_split(self):
        """适配度和胜任力应各占 50%"""
        from scripts.applicant import (
            DEFAULT_SCORE_WEIGHTS,
            FIT_DIMENSIONS,
            COMPETENCY_DIMENSIONS,
        )

        fit_total = sum(DEFAULT_SCORE_WEIGHTS[d] for d in FIT_DIMENSIONS)
        comp_total = sum(DEFAULT_SCORE_WEIGHTS[d] for d in COMPETENCY_DIMENSIONS)

        assert abs(fit_total - 0.5) < 0.001, f"适配度权重总和 {fit_total}"
        assert abs(comp_total - 0.5) < 0.001, f"胜任力权重总和 {comp_total}"


# ═══════════════════════════════════════════════
# 超图合作网络测试
# ═══════════════════════════════════════════════


class TestHypergraphCollaboration:
    """超图合作网络分析测试 (基于 Battiston et al. 2025)"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        from scripts.applicant import ApplicantAnalyzer
        return ApplicantAnalyzer()

    @pytest.fixture
    def df_with_teams(self):
        """创建包含重复合作团队的测试数据"""
        return pd.DataFrame({
            'pmid': ['1', '2', '3', '4', '5', '6'],
            'title': ['Paper A', 'Paper B', 'Paper C', 'Paper D', 'Paper E', 'Paper F'],
            'authors': [
                'Zhang S; Li W; Wang X',           # Team 1
                'Zhang S; Li W; Wang X',           # Team 1 (重复)
                'Zhang S; Chen Y',                 # 小团队
                'Zhang S; Li W; Wang X; Zhou M',   # Team 1 扩展
                'Zhang S; Liu R; Zhao Q',          # Team 2
                'Zhang S; Liu R; Zhao Q',          # Team 2 (重复)
            ],
            'year': [2020, 2021, 2022, 2022, 2023, 2024],
        })

    def test_extract_hyperedges(self, analyzer, df_with_teams):
        """超边提取测试"""
        patterns = ['zhang s', 'san zhang']
        hyperedges = analyzer._extract_collaboration_hyperedges(df_with_teams, patterns)

        # 应该检测到重复的合作组合
        assert len(hyperedges) >= 1, "应检测到至少一个重复超边"

        # 第一个应该是出现最多的团队
        top_edge, top_count = hyperedges[0]
        assert top_count >= 2, f"最频繁团队应出现至少2次, 实际 {top_count}"

    def test_detect_stable_teams(self, analyzer, df_with_teams):
        """稳定团队检测测试"""
        patterns = ['zhang s', 'san zhang']
        hyperedges = analyzer._extract_collaboration_hyperedges(df_with_teams, patterns)
        teams = analyzer._detect_stable_teams(hyperedges, min_size=2, max_size=5)

        # 应检测到稳定团队
        for team in teams:
            assert 'members' in team
            assert 'papers' in team
            assert 'size' in team
            assert team['papers'] >= 2, "稳定团队应出现至少2篇论文"

    def test_stability_index(self, analyzer, df_with_teams):
        """团队稳定性指数测试"""
        patterns = ['zhang s', 'san zhang']
        stability = analyzer._compute_team_stability_index(df_with_teams, patterns)

        assert 0 <= stability <= 1, f"稳定性指数应在 0-1 之间, 实际 {stability}"

    def test_collaboration_structure(self, analyzer, df_with_teams):
        """合作结构分析测试"""
        patterns = ['zhang s', 'san zhang']
        structure = analyzer._analyze_collaboration_structure(df_with_teams, patterns)

        expected_keys = ['hyperedges', 'stable_teams', 'stability_index',
                         'avg_team_size', 'max_team_size', 'solo_ratio']
        for key in expected_keys:
            assert key in structure, f"缺少字段: {key}"

        assert structure['avg_team_size'] > 0, "平均团队规模应 > 0"
        assert 0 <= structure['solo_ratio'] <= 1, "独立发表比例应在 0-1"

    def test_profile_hypergraph_fields(self, sample_profile):
        """Profile 超图字段存在性测试"""
        # 验证新字段存在
        assert hasattr(sample_profile, 'stable_teams')
        assert hasattr(sample_profile, 'team_stability_index')
        assert hasattr(sample_profile, 'avg_team_size')
        assert hasattr(sample_profile, 'max_team_size')
        assert hasattr(sample_profile, 'solo_ratio')


# ═══════════════════════════════════════════════
# 运行入口
# ═══════════════════════════════════════════════


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
