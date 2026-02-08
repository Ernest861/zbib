"""
申请人前期基础分析 — 后向兼容导出

该文件是旧版 API 的兼容层。实际实现已迁移到 scripts/applicant/ 包。

推荐使用新的导入方式:
    from scripts.applicant import ApplicantAnalyzer, ApplicantProfile

该文件将在未来版本中弃用。
"""

# Re-export all public APIs from the applicant package
from scripts.applicant import (
    # Profile
    ApplicantProfile,
    DEFAULT_SCORE_WEIGHTS,
    FIT_DIMENSIONS,
    COMPETENCY_DIMENSIONS,
    JOURNAL_TIERS,
    # Analyzer
    ApplicantAnalyzer,
    # Assessment
    generate_narrative_assessment,
    analyze_weaknesses,
    get_quadrant_position,
    generate_improvement_plan,
    # Benchmark
    FieldBenchmark,
    NIBS_PSYCHIATRY_BENCHMARK,
    NEUROSCIENCE_BENCHMARK,
    calculate_percentile_ranks,
    apply_benchmark,
    format_percentile_summary,
    create_benchmark_report_section,
    get_benchmark_by_name,
    quick_percentile,
    # Report
    create_markdown_report,
    save_markdown_report,
    compare_applicants,
    create_comparison_report,
    create_profile_summary,
    # ORCID
    verify_with_orcid,
)

__all__ = [
    'ApplicantProfile',
    'DEFAULT_SCORE_WEIGHTS',
    'FIT_DIMENSIONS',
    'COMPETENCY_DIMENSIONS',
    'JOURNAL_TIERS',
    'ApplicantAnalyzer',
    'generate_narrative_assessment',
    'analyze_weaknesses',
    'get_quadrant_position',
    'generate_improvement_plan',
    'FieldBenchmark',
    'NIBS_PSYCHIATRY_BENCHMARK',
    'NEUROSCIENCE_BENCHMARK',
    'calculate_percentile_ranks',
    'apply_benchmark',
    'format_percentile_summary',
    'create_benchmark_report_section',
    'get_benchmark_by_name',
    'quick_percentile',
    'create_markdown_report',
    'save_markdown_report',
    'compare_applicants',
    'create_comparison_report',
    'create_profile_summary',
    'verify_with_orcid',
]
