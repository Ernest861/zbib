"""
申请人前期基础分析包 (Applicant Background Analysis)

该包提供申请人文献分析、评分、报告生成等功能，用于支撑 NSFC 标书的「前期工作基础」论证。

模块结构:
    - profile: ApplicantProfile 数据类及评分计算
    - analyzer: ApplicantAnalyzer 主分析类
    - assessment: 叙事性评估、薄弱分析、提升建议
    - benchmark: 领域基准数据库及百分位排名
    - report: Markdown 报告生成
    - orcid: ORCID 交叉验证

用法示例:
    from scripts.applicant import ApplicantAnalyzer, ApplicantProfile
    analyzer = ApplicantAnalyzer(df_pubmed, topic_config)
    profile = analyzer.build_profile('作者姓名')
"""

# ═══════════════════════════════════════════════
# Profile 模块
# ═══════════════════════════════════════════════
from .profile import (
    ApplicantProfile,
    DEFAULT_SCORE_WEIGHTS,
    FIT_DIMENSIONS,
    COMPETENCY_DIMENSIONS,
    JOURNAL_TIERS,
)

# ═══════════════════════════════════════════════
# Analyzer 模块
# ═══════════════════════════════════════════════
from .analyzer import ApplicantAnalyzer, check_pubmed_data

# ═══════════════════════════════════════════════
# Assessment 模块
# ═══════════════════════════════════════════════
from .assessment import (
    # 类型定义
    WeaknessInfo,
    QuadrantPosition,
    QuadrantType,
    # 函数
    generate_narrative_assessment,
    analyze_weaknesses,
    get_quadrant_position,
    generate_improvement_plan,
)

# ═══════════════════════════════════════════════
# Benchmark 模块
# ═══════════════════════════════════════════════
from .benchmark import (
    FieldBenchmark,
    NIBS_PSYCHIATRY_BENCHMARK,
    NEUROSCIENCE_BENCHMARK,
    calculate_percentile_ranks,
    apply_benchmark,
    format_percentile_summary,
    create_benchmark_report_section,
    get_benchmark_by_name,
    quick_percentile,
)

# ═══════════════════════════════════════════════
# Report 模块
# ═══════════════════════════════════════════════
from .report import (
    create_markdown_report,
    save_markdown_report,
    compare_applicants,
    create_comparison_report,
    create_profile_summary,
)

# ═══════════════════════════════════════════════
# ORCID 模块
# ═══════════════════════════════════════════════
from .orcid import verify_with_orcid


# Public API
__all__ = [
    # Profile
    'ApplicantProfile',
    'DEFAULT_SCORE_WEIGHTS',
    'FIT_DIMENSIONS',
    'COMPETENCY_DIMENSIONS',
    'JOURNAL_TIERS',
    # Analyzer
    'ApplicantAnalyzer',
    'check_pubmed_data',
    # Assessment (types)
    'WeaknessInfo',
    'QuadrantPosition',
    'QuadrantType',
    # Assessment (functions)
    'generate_narrative_assessment',
    'analyze_weaknesses',
    'get_quadrant_position',
    'generate_improvement_plan',
    # Benchmark
    'FieldBenchmark',
    'NIBS_PSYCHIATRY_BENCHMARK',
    'NEUROSCIENCE_BENCHMARK',
    'calculate_percentile_ranks',
    'apply_benchmark',
    'format_percentile_summary',
    'create_benchmark_report_section',
    'get_benchmark_by_name',
    'quick_percentile',
    # Report
    'create_markdown_report',
    'save_markdown_report',
    'compare_applicants',
    'create_comparison_report',
    'create_profile_summary',
    # ORCID
    'verify_with_orcid',
]
