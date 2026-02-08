"""
申请人报告生成模块

本模块负责生成申请人前期工作基础的 Markdown 报告，包括：
- 单申请人完整报告 (create_markdown_report)
- 多申请人对比报告 (create_comparison_report)
- 纯文本摘要 (create_profile_summary)

报告结构:
    1. 申请人信息 - 基础统计概览
    2. 发表统计 - 文献数量、作者身份、期刊分布
    3. 研究维度覆盖 - 症状维度、靶区维度
    4. 合作网络 - 主要合作者
    5. 研究轨迹 - 主题演变
    6. 代表性论文 - 重要成果
    7. 顶刊论文详情 - 高影响力发表
    8. 适配度与胜任力评估 - 评分体系
    9. 叙事性评估 - 可用于标书的文本
    10. 薄弱维度分析 - 待提升领域
    11. ORCID 交叉验证 - 数据可信度

使用示例:
    >>> from scripts.applicant import create_markdown_report
    >>> report = create_markdown_report(profile, topic_name='OFC-rTMS治疗精神分裂症')
    >>> Path('report.md').write_text(report)
"""

from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Any

from .profile import ApplicantProfile, JOURNAL_TIERS
from .assessment import (
    generate_narrative_assessment,
    analyze_weaknesses,
    generate_improvement_plan,
    get_quadrant_position,
)
from .benchmark import create_benchmark_report_section


# ═══════════════════════════════════════════════
# 报告章节生成器
# ═══════════════════════════════════════════════


def _sanitize_topic_name(topic_name: str) -> str:
    """
    确保 topic_name 为可读的课题名称，避免误传入 config 的 repr 导致乱码。
    """
    if not topic_name or not isinstance(topic_name, str):
        return ''
    s = topic_name.strip()
    if not s or 'TopicConfig(' in s or 'ApplicantConfig(' in s or len(s) > 200:
        return ''
    return s


def _section_header(profile: ApplicantProfile, topic_name: str) -> list[str]:
    """
    生成报告标题和元信息。

    Args:
        profile: 申请人档案
        topic_name: 研究课题名称

    Returns:
        Markdown 行列表
    """
    lines = []
    title = "# 申请人前期工作基础报告"
    safe_name = _sanitize_topic_name(topic_name)
    if safe_name:
        title += f" — {safe_name}"
    lines.append(title)
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    return lines


def _section_basic_info(profile: ApplicantProfile) -> list[str]:
    """
    生成申请人基本信息表格。

    包含: 姓名、发表年限、H-index、适配度、胜任力、综合评分

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表
    """
    lines = []
    lines.append("## 1. 申请人信息")
    lines.append("")

    fit = getattr(profile, 'fit_score', 0)
    comp = getattr(profile, 'competency_score', 0)

    lines.append("| 项目 | 内容 |")
    lines.append("|:-----|:-----|")
    lines.append(f"| **姓名** | {profile.name_cn} ({profile.name_en}) |")
    lines.append(f"| **发表年限** | {profile.year_range[0]}-{profile.year_range[1]} ({profile.experience_years}年) |")
    lines.append(f"| **H-index (估算)** | {profile.h_index_estimate} |")
    lines.append(f"| **适配度** | {fit:.1f}/100 |")
    lines.append(f"| **胜任力** | {comp:.1f}/100 |")
    lines.append(f"| **综合评分** | **{profile.relevance_score}/100** |")
    lines.append("")
    return lines


def _section_publication_stats(profile: ApplicantProfile) -> list[str]:
    """
    生成发表统计章节。

    包含三个子部分:
    - 2.1 文献数量: 总数、近5年、疾病相关、NIBS相关、交叉
    - 2.2 作者身份: 第一作者、通讯作者比例
    - 2.3 期刊影响力: 顶刊数量、IF统计、主要期刊列表

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表
    """
    lines = []
    total = profile.n_total or 1  # 避免除零

    # ─── 2.1 文献数量 ───
    lines.append("## 2. 发表统计")
    lines.append("")
    lines.append("### 2.1 文献数量")
    lines.append("")
    lines.append("| 类别 | 数量 | 占比 |")
    lines.append("|:-----|-----:|-----:|")
    lines.append(f"| 全部文献 | {profile.n_total} | 100% |")
    lines.append(f"| 近5年发文 | {profile.recent_5yr_count} | {profile.recent_5yr_count*100//total}% |")
    lines.append(f"| 疾病相关 | {profile.n_disease} | {profile.n_disease*100//total}% |")
    lines.append(f"| NIBS相关 | {profile.n_nibs} | {profile.n_nibs*100//total}% |")
    lines.append(f"| 疾病+NIBS | {profile.n_disease_nibs} | {profile.n_disease_nibs*100//total}% |")
    lines.append("")

    # ─── 2.2 作者身份 ───
    lines.append("### 2.2 作者身份")
    lines.append("")
    lines.append("| 身份 | 数量 | 占比 |")
    lines.append("|:-----|-----:|-----:|")
    lines.append(f"| 第一作者 | {profile.n_first_author} | {profile.n_first_author*100//total}% |")
    lines.append(f"| 通讯作者 | {profile.n_corresponding} | {profile.n_corresponding*100//total}% |")
    lines.append(f"| 第一或通讯 | {profile.n_first_or_corresponding} | {profile.n_first_or_corresponding*100//total}% |")
    lines.append("")

    # ─── 2.3 期刊影响力 ───
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
        lines.append("| 指标 | 数值 |")
        lines.append("|:-----|-----:|")
        lines.append(f"| 累计 IF | {if_stats.get('total_if', 0)} |")
        lines.append(f"| 平均 IF | {if_stats.get('avg_if', 0)} |")
        lines.append(f"| 最高 IF | {if_stats.get('max_if', 0)} |")
        lines.append(f"| 中位 IF | {if_stats.get('median_if', 0)} |")
    lines.append("")

    # 主要期刊列表
    if profile.journal_counts:
        lines.append("**主要发表期刊:**")
        lines.append("")
        lines.append("| 期刊 | 篇数 |")
        lines.append("|:-----|-----:|")
        for journal, count in list(profile.journal_counts.items())[:10]:
            tier_mark = ""
            if journal in JOURNAL_TIERS['tier1']:
                tier_mark = " ⭐"
            elif journal in JOURNAL_TIERS['tier2']:
                tier_mark = " ★"
            lines.append(f"| {journal}{tier_mark} | {count} |")
        lines.append("")

    return lines


def _section_dimension_coverage(profile: ApplicantProfile) -> list[str]:
    """
    生成研究维度覆盖章节。

    显示申请人在不同症状维度和靶区维度的研究分布，
    帮助评估其与课题的匹配程度。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无覆盖数据则返回空列表)
    """
    if not profile.symptom_coverage and not profile.target_coverage:
        return []

    lines = []
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

    return lines


def _section_collaboration(profile: ApplicantProfile) -> list[str]:
    """
    生成合作网络章节。

    展示申请人的主要合作者及合作频次，
    反映其学术网络广度和团队协作能力。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无合作者数据则返回空列表)
    """
    if not profile.top_collaborators:
        return []

    lines = []
    lines.append("## 4. 合作网络")
    lines.append("")
    lines.append("### 主要合作者")
    lines.append("")
    lines.append("| 合作者 | 合作次数 |")
    lines.append("|:-------|--------:|")
    for name, count in profile.top_collaborators[:10]:
        lines.append(f"| {name} | {count} |")
    lines.append("")
    return lines


def _section_trajectory(profile: ApplicantProfile) -> list[str]:
    """
    生成研究轨迹章节。

    展示申请人研究主题随时间的演变，
    帮助理解其学术发展路径和当前研究方向。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无轨迹数据则返回空列表)
    """
    if not profile.research_trajectory:
        return []

    lines = []
    lines.append("## 5. 研究轨迹")
    lines.append("")
    lines.append("研究主题随时间的演变:")
    lines.append("")
    for period, keywords in profile.research_trajectory.items():
        kw_str = ', '.join(keywords)
        lines.append(f"- **{period}**: {kw_str}")
    lines.append("")
    return lines


def _section_key_papers(profile: ApplicantProfile) -> list[str]:
    """
    生成代表性论文章节。

    列出申请人最重要的 5 篇论文，包括:
    - 发表年份和期刊
    - 论文标题
    - PubMed 链接

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无论文数据则返回空列表)
    """
    if not profile.key_papers:
        return []

    lines = []
    lines.append("## 6. 代表性论文")
    lines.append("")
    for i, paper in enumerate(profile.key_papers[:5], 1):
        title_text = paper.get('title', '')
        year = paper.get('year', '')
        journal = paper.get('journal', '')
        pmid = paper.get('pmid', '')
        lines.append(f"**{i}. [{year}] {journal}**")
        lines.append("")
        lines.append(f"> {title_text}")
        if pmid:
            lines.append(f"> PMID: [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
        lines.append("")
    return lines


def _section_tier_papers(profile: ApplicantProfile) -> list[str]:
    """
    生成顶刊论文详情章节。

    单独列出发表在顶级期刊 (IF≥10) 的论文，
    这些论文对标书的「研究基础」部分尤为重要。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无顶刊论文则返回空列表)
    """
    tier_papers = getattr(profile, 'journal_tier_papers', {})
    if not tier_papers.get('tier1'):
        return []

    lines = []
    lines.append("## 7. 顶刊论文详情")
    lines.append("")
    for paper in tier_papers['tier1']:
        lines.append(f"- **[{paper.get('year', '')}] {paper.get('journal', '')}**")
        lines.append(f"  {paper.get('title', '')}")
    lines.append("")
    return lines


def _get_score_comment(score: float, dim_type: str) -> str:
    """
    根据评分生成评语。

    Args:
        score: 评分 (0-100)
        dim_type: 维度类型 ('fit' 或 'competency')

    Returns:
        评语字符串
    """
    if dim_type == 'fit':
        if score >= 80:
            return "**极高适配** - 前期工作与课题高度契合"
        elif score >= 60:
            return "**良好适配** - 具备扎实的领域基础"
        elif score >= 40:
            return "**中等适配** - 有一定相关研究积累"
        else:
            return "**适配度偏低** - 建议加强领域积累"
    else:  # competency
        if score >= 80:
            return "**卓越胜任** - 具备独立主持课题的能力"
        elif score >= 60:
            return "**良好胜任** - 学术独立性和影响力较好"
        elif score >= 40:
            return "**基本胜任** - 需进一步提升学术独立性"
        else:
            return "**胜任力待提升** - 建议增加独立主持的研究"


def _section_assessment(profile: ApplicantProfile) -> list[str]:
    """
    生成适配度与胜任力评估章节。

    这是报告的核心章节，包含:
    - 8.1 评估结果: 可视化评分框图
    - 8.2 评分维度详解: 各维度定义和权重
    - 8.3 各维度得分明细: 原始分和加权分

    评分体系说明:
    - 适配度 (50%): 疾病领域 + 技术方法 + 交叉经验
    - 胜任力 (50%): 学术独立性 + 学术影响力 + 研究活跃度

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表
    """
    lines = []
    fit = getattr(profile, 'fit_score', 0)
    comp = getattr(profile, 'competency_score', 0)
    total_score = profile.relevance_score

    lines.append("## 8. 申报者适配度与胜任力评估")
    lines.append("")

    # ─── 8.1 评估结果 ───
    lines.append("### 8.1 评估结果")
    lines.append("")
    lines.append("```")
    lines.append("┌────────────────────────────────────────┐")
    lines.append(f"│  适配度: {fit:>5.1f}/100    胜任力: {comp:>5.1f}/100  │")
    lines.append("│  ────────────────────────────────────  │")
    lines.append(f"│           综合评分: {total_score:>5.1f}/100           │")
    lines.append("└────────────────────────────────────────┘")
    lines.append("```")
    lines.append("")
    lines.append(f"- **适配度**: {_get_score_comment(fit, 'fit')}")
    lines.append(f"- **胜任力**: {_get_score_comment(comp, 'competency')}")
    lines.append("")

    # ─── 8.2 评分维度详解 ───
    lines.append("### 8.2 评分维度详解")
    lines.append("")
    lines.append("**【适配度】** 前期工作与本课题的契合程度 (50%)")
    lines.append("")
    lines.append("| 维度 | 权重 | 含义 |")
    lines.append("|:-----|:----:|:-----|")
    lines.append("| 疾病领域深度 | 20% | 在该疾病方向的研究积累 |")
    lines.append("| 技术方法专长 | 20% | 对 NIBS 技术的掌握程度 |")
    lines.append("| 交叉研究经验 | 10% | 疾病+NIBS 结合的工作 |")
    lines.append("")
    lines.append("**【胜任力】** 独立完成课题的能力 (50%)")
    lines.append("")
    lines.append("| 维度 | 权重 | 含义 |")
    lines.append("|:-----|:----:|:-----|")
    lines.append("| 学术独立性 | 20% | 第一/通讯作者占比 |")
    lines.append("| 学术影响力 | 15% | 顶刊发表 + H-index |")
    lines.append("| 研究活跃度 | 15% | 近5年持续产出 |")
    lines.append("")

    # ─── 8.3 各维度得分明细 ───
    breakdown = profile.get_score_breakdown()
    lines.append("### 8.3 各维度得分明细")
    lines.append("")
    lines.append("| 维度 | 原始分 | 加权分 |")
    lines.append("|:-----|-------:|-------:|")
    lines.append(f"| 疾病领域 | {breakdown.get('disease_raw', 0):.0f} | {breakdown.get('disease', 0):.1f} |")
    lines.append(f"| 技术方法 | {breakdown.get('nibs_raw', 0):.0f} | {breakdown.get('nibs', 0):.1f} |")
    lines.append(f"| 交叉经验 | {breakdown.get('crossover_raw', 0):.0f} | {breakdown.get('crossover', 0):.1f} |")
    lines.append(f"| 学术独立 | {breakdown.get('independence_raw', 0):.0f} | {breakdown.get('independence', 0):.1f} |")
    lines.append(f"| 学术影响 | {breakdown.get('impact_raw', 0):.0f} | {breakdown.get('impact', 0):.1f} |")
    lines.append(f"| 研究活跃 | {breakdown.get('activity_raw', 0):.0f} | {breakdown.get('activity', 0):.1f} |")
    lines.append(f"| **合计** | - | **{total_score:.1f}** |")
    lines.append("")

    return lines


def _section_narrative(profile: ApplicantProfile, topic_name: str) -> list[str]:
    """
    生成叙事性评估章节。

    该部分生成可直接用于标书「研究基础」或「可行性分析」的文本，
    采用第三人称客观叙述风格。

    Args:
        profile: 申请人档案
        topic_name: 研究课题名称

    Returns:
        Markdown 行列表 (如无内容则返回空列表)
    """
    safe_name = _sanitize_topic_name(topic_name)
    narrative = generate_narrative_assessment(profile, safe_name)
    if not narrative:
        return []

    lines = []
    lines.append("## 9. 叙事性评估")
    lines.append("")
    lines.append("> 以下文本可直接用于标书「研究基础」或「可行性分析」部分")
    lines.append("")
    lines.append(narrative)
    lines.append("")
    return lines


def _section_weaknesses(profile: ApplicantProfile) -> list[str]:
    """
    生成薄弱维度分析章节。

    识别申请人评分较低的维度，并给出针对性的改进建议，
    帮助申请人在标书准备阶段有的放矢地补强。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无薄弱维度则返回空列表)
    """
    weaknesses = analyze_weaknesses(profile)
    if not weaknesses:
        return []

    lines = []
    lines.append("## 10. 薄弱维度分析")
    lines.append("")
    for i, w in enumerate(weaknesses, 1):
        lines.append(f"**{i}. {w['dimension']}** (得分: {w['score']:.0f}/100, 阈值: {w['threshold']})")
        lines.append(f"- 问题: {w['issue']}")
        lines.append(f"- 建议: {w['suggestion']}")
        lines.append("")
    return lines


def _section_improvement(profile: ApplicantProfile) -> list[str]:
    """
    生成提升计划章节。

    基于薄弱维度分析，生成 12 个月内可执行的提升计划，
    包括具体的行动建议和时间节点。

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如无提升计划则返回空列表)
    """
    improvement = generate_improvement_plan(profile)
    if not improvement:
        return []

    lines = []
    lines.append(improvement)
    lines.append("")
    return lines


def _section_orcid(profile: ApplicantProfile) -> list[str]:
    """
    生成 ORCID 交叉验证章节。

    显示 PubMed 检索结果与 ORCID 官方记录的比对结果，
    帮助评估数据可信度，识别可能的同名干扰。

    验证结果分类:
    - 双确认: 同时出现在 PubMed 和 ORCID
    - 仅 PubMed: 可能包含同名他人论文
    - 仅 ORCID: ORCID 中有但 PubMed 未检索到

    Args:
        profile: 申请人档案

    Returns:
        Markdown 行列表 (如未进行 ORCID 验证则返回空列表)
    """
    if not profile.orcid_verified:
        return []

    lines = []
    conf_label = {'high': '高', 'medium': '中', 'low': '低'}.get(
        profile.verification_confidence, '未知'
    )

    lines.append("## 11. ORCID 交叉验证")
    lines.append("")
    lines.append("| 项目 | 结果 |")
    lines.append("|:-----|:-----|")
    lines.append(f"| ORCID | [{profile.orcid_id}](https://orcid.org/{profile.orcid_id}) |")
    lines.append(f"| 双确认论文 | {profile.orcid_match_count} 篇 |")
    lines.append(f"| 仅PubMed | {profile.pubmed_only_count} 篇 |")
    lines.append(f"| 仅ORCID | {profile.orcid_only_count} 篇 |")
    lines.append(f"| 数据置信度 | **{conf_label}** |")
    lines.append("")

    if profile.pubmed_only_count > profile.orcid_match_count * 2:
        lines.append("> **注意**: PubMed 检索结果中可能包含同名他人的论文，建议人工核查。")
        lines.append("")

    return lines


# ═══════════════════════════════════════════════
# 主报告生成函数
# ═══════════════════════════════════════════════


def create_markdown_report(profile: ApplicantProfile, topic_name: str = '') -> str:
    """
    生成申请人前期工作基础 Markdown 报告。

    该报告旨在为 NSFC 标书的「研究基础与可行性分析」部分提供支撑材料，
    通过量化分析和叙事性评估全面展示申请人的前期积累。

    报告结构 (11 个章节):
        1. 申请人信息 - 基础概览
        2. 发表统计 - 文献数量、作者身份、期刊分布
        3. 研究维度覆盖 - 症状/靶区维度
        4. 合作网络 - 主要合作者
        5. 研究轨迹 - 主题演变
        6. 代表性论文 - 重要成果
        7. 顶刊论文详情 - 高影响力发表
        8. 适配度与胜任力评估 - 核心评分
        9. 叙事性评估 - 标书可用文本
        10. 薄弱维度分析 - 待提升领域
        11. ORCID 交叉验证 - 数据可信度

    Args:
        profile: ApplicantProfile 对象，包含分析结果
        topic_name: 研究课题名称 (可选)，用于报告标题和叙事评估

    Returns:
        Markdown 格式的完整报告文本

    Example:
        >>> profile = analyzer.analyze('张三', 'San Zhang', df_all)
        >>> report = create_markdown_report(profile, 'OFC-rTMS治疗精神分裂症')
        >>> Path('张三_报告.md').write_text(report)
    """
    safe_topic_name = _sanitize_topic_name(topic_name)
    lines = []

    # 按章节顺序组装报告
    lines.extend(_section_header(profile, safe_topic_name))
    lines.extend(_section_basic_info(profile))
    lines.extend(_section_publication_stats(profile))
    lines.extend(_section_dimension_coverage(profile))
    lines.extend(_section_collaboration(profile))
    lines.extend(_section_trajectory(profile))
    lines.extend(_section_key_papers(profile))
    lines.extend(_section_tier_papers(profile))
    lines.extend(_section_assessment(profile))
    lines.extend(_section_narrative(profile, safe_topic_name))
    lines.extend(_section_weaknesses(profile))
    lines.extend(_section_improvement(profile))
    lines.extend(_section_orcid(profile))

    # 领域基准排名
    if profile.percentile_ranks:
        lines.append(create_benchmark_report_section(profile))

    # 页脚
    lines.append("---")
    lines.append("*报告由 zbib 自动生成 | 适配度+胜任力评估体系*")

    return '\n'.join(lines)


def save_markdown_report(
    profile: ApplicantProfile,
    output_path: str,
    topic_name: str = ''
) -> str:
    """
    保存 Markdown 报告到文件。

    Args:
        profile: ApplicantProfile 对象
        output_path: 输出文件路径
        topic_name: 研究课题名称 (可选)

    Returns:
        保存的文件路径

    Example:
        >>> save_markdown_report(profile, 'output/report.md', 'OFC-rTMS研究')
        'output/report.md'
    """
    report = create_markdown_report(profile, topic_name)
    Path(output_path).write_text(report, encoding='utf-8')
    return output_path


# ═══════════════════════════════════════════════
# 多申请人对比
# ═══════════════════════════════════════════════


def compare_applicants(profiles: list[ApplicantProfile]) -> dict[str, Any]:
    """
    对比多个申请人的前期工作基础。

    用于团队申报时评估各成员的优势互补情况，
    或在多个候选人中选择最合适的申请人。

    Args:
        profiles: ApplicantProfile 列表

    Returns:
        对比结果字典:
        {
            'comparison_table': list[dict],  # 各指标对比表
            'rankings': dict[str, list],     # 各维度排名
            'best_fit': str,                 # 适配度最高者姓名
            'best_competency': str,          # 胜任力最高者姓名
            'best_overall': str,             # 综合最优者姓名
            'team_assessment': str,          # 团队评估文本
        }

    Example:
        >>> comparison = compare_applicants([profile1, profile2, profile3])
        >>> print(f"综合最优: {comparison['best_overall']}")
    """
    if not profiles:
        return {}

    # ─── 构建对比表 ───
    table = []
    for p in profiles:
        name = p.name_cn or p.name_en
        breakdown = p.get_score_breakdown()
        row = {
            '姓名': name,
            '总文献': p.n_total,
            '疾病相关': p.n_disease,
            'NIBS相关': p.n_nibs,
            '交叉': p.n_disease_nibs,
            '第一/通讯': p.n_first_or_corresponding,
            '独立占比': f"{p.n_first_or_corresponding / max(p.n_total, 1) * 100:.0f}%",
            '顶刊': p.tier1_count,
            'H-index': p.h_index_estimate,
            '近5年': p.recent_5yr_count,
            '适配度': round(p.fit_score, 1),
            '胜任力': round(p.competency_score, 1),
            '综合分': round(p.relevance_score, 1),
            '象限': get_quadrant_position(p)['label'],
        }
        # 各维度原始分
        for dim in ['disease', 'nibs', 'crossover', 'independence', 'impact', 'activity']:
            row[f'{dim}_raw'] = round(breakdown.get(f'{dim}_raw', 0), 1)
        table.append(row)

    # ─── 各维度排名 ───
    rank_dims = ['适配度', '胜任力', '综合分', 'H-index', '总文献', '近5年']
    rankings = {}
    for dim in rank_dims:
        sorted_names = sorted(table, key=lambda r: -r[dim])
        rankings[dim] = [(r['姓名'], r[dim]) for r in sorted_names]

    # ─── 找出最优者 ───
    best_fit_row = max(table, key=lambda r: r['适配度'])
    best_comp_row = max(table, key=lambda r: r['胜任力'])
    best_overall_row = max(table, key=lambda r: r['综合分'])

    # ─── 团队评估 ───
    team_text = _generate_team_assessment(profiles, table)

    return {
        'comparison_table': table,
        'rankings': rankings,
        'best_fit': best_fit_row['姓名'],
        'best_competency': best_comp_row['姓名'],
        'best_overall': best_overall_row['姓名'],
        'team_assessment': team_text,
    }


def _generate_team_assessment(
    profiles: list[ApplicantProfile],
    table: list[dict]
) -> str:
    """
    生成团队整体评估文本。

    分析团队成员的能力分布、互补性和薄弱环节，
    为团队申报提供整体评价。

    Args:
        profiles: 申请人档案列表
        table: 对比表数据

    Returns:
        团队评估文本
    """
    n = len(profiles)
    avg_fit = sum(r['适配度'] for r in table) / n
    avg_comp = sum(r['胜任力'] for r in table) / n

    lines = []
    lines.append(f"团队共 {n} 人参与评估，整体适配度均值 {avg_fit:.1f}，胜任力均值 {avg_comp:.1f}。")

    # 团队构成分析
    quadrant_counts = Counter(r['象限'] for r in table)
    for label, count in quadrant_counts.most_common():
        lines.append(f"- {label}: {count} 人")

    # 互补性分析
    fit_scores = [r['适配度'] for r in table]
    comp_scores = [r['胜任力'] for r in table]
    fit_range = max(fit_scores) - min(fit_scores)
    comp_range = max(comp_scores) - min(comp_scores)

    if fit_range > 30 or comp_range > 30:
        lines.append("\n团队成员在能力维度上存在明显差异，具有互补优势。")
    else:
        lines.append("\n团队成员能力较为均衡。")

    # 薄弱环节
    dim_avgs = {}
    for dim in ['disease_raw', 'nibs_raw', 'crossover_raw',
                'independence_raw', 'impact_raw', 'activity_raw']:
        dim_avgs[dim] = sum(r.get(dim, 0) for r in table) / n

    weakest = min(dim_avgs, key=dim_avgs.get)
    dim_labels = {
        'disease_raw': '疾病领域',
        'nibs_raw': '技术方法',
        'crossover_raw': '交叉经验',
        'independence_raw': '学术独立性',
        'impact_raw': '学术影响力',
        'activity_raw': '研究活跃度',
    }
    lines.append(
        f"\n团队整体最薄弱维度: **{dim_labels.get(weakest, weakest)}** "
        f"(均分 {dim_avgs[weakest]:.0f}/100)"
    )

    return '\n'.join(lines)


def create_comparison_report(
    profiles: list[ApplicantProfile],
    topic_name: str = ''
) -> str:
    """
    生成多申请人对比 Markdown 报告。

    用于团队申报或候选人筛选场景，
    提供多维度的量化对比和可视化排名。

    报告结构:
        1. 综合对比表 - 所有指标一览
        2. 各维度排名 - 按维度排序
        3. 最优人选 - 各维度最佳候选
        4. 各维度评分 - 六维雷达数据
        5. 团队整体评估 - 互补性分析

    Args:
        profiles: ApplicantProfile 列表
        topic_name: 研究课题名称 (可选)

    Returns:
        Markdown 格式的对比报告

    Example:
        >>> report = create_comparison_report([p1, p2, p3], 'OFC-rTMS研究')
        >>> Path('team_comparison.md').write_text(report)
    """
    comparison = compare_applicants(profiles)
    if not comparison:
        return "无申请人数据"

    lines = []
    lines.append("# 申请人对比分析报告")
    if topic_name:
        lines.append(f"\n> 课题: {topic_name}")
    lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # ─── 1. 综合对比表 ───
    lines.append("## 1. 综合对比")
    lines.append("")
    table = comparison['comparison_table']
    display_cols = [
        '姓名', '总文献', '疾病相关', 'NIBS相关', '第一/通讯',
        '顶刊', 'H-index', '适配度', '胜任力', '综合分', '象限'
    ]
    header = '| ' + ' | '.join(display_cols) + ' |'
    separator = '|' + '|'.join(
        ':-----:' if c != '姓名' else ':-----' for c in display_cols
    ) + '|'
    lines.append(header)
    lines.append(separator)
    for row in sorted(table, key=lambda r: -r['综合分']):
        vals = [str(row[c]) for c in display_cols]
        lines.append('| ' + ' | '.join(vals) + ' |')
    lines.append("")

    # ─── 2. 各维度排名 ───
    lines.append("## 2. 各维度排名")
    lines.append("")
    for dim, ranking in comparison['rankings'].items():
        rank_str = ' > '.join(f"**{name}**({val})" for name, val in ranking)
        lines.append(f"- **{dim}**: {rank_str}")
    lines.append("")

    # ─── 3. 最优人选 ───
    lines.append("## 3. 最优人选")
    lines.append("")
    lines.append(f"- 适配度最高: **{comparison['best_fit']}**")
    lines.append(f"- 胜任力最高: **{comparison['best_competency']}**")
    lines.append(f"- 综合最优: **{comparison['best_overall']}**")
    lines.append("")

    # ─── 4. 各维度评分 ───
    lines.append("## 4. 各维度评分")
    lines.append("")
    dim_display = {
        'disease_raw': '疾病领域',
        'nibs_raw': '技术方法',
        'crossover_raw': '交叉经验',
        'independence_raw': '学术独立性',
        'impact_raw': '学术影响力',
        'activity_raw': '研究活跃度',
    }
    dim_header = '| 姓名 | ' + ' | '.join(dim_display.values()) + ' |'
    dim_sep = '|:-----|' + '|'.join(':----:' for _ in dim_display) + '|'
    lines.append(dim_header)
    lines.append(dim_sep)
    for row in table:
        vals = [f"{row.get(d, 0):.0f}" for d in dim_display]
        lines.append(f"| {row['姓名']} | " + ' | '.join(vals) + ' |')
    lines.append("")

    # ─── 5. 团队评估 ───
    lines.append("## 5. 团队整体评估")
    lines.append("")
    lines.append(comparison['team_assessment'])
    lines.append("")

    lines.append("---")
    lines.append("*报告由 zbib 自动生成 | 多申请人对比分析*")

    return '\n'.join(lines)


# ═══════════════════════════════════════════════
# 纯文本摘要
# ═══════════════════════════════════════════════


def create_profile_summary(profile: ApplicantProfile) -> str:
    """
    生成申请人前期工作摘要 (纯文本格式)。

    适用于终端输出、日志记录或快速预览，
    不含 Markdown 格式，可直接打印。

    Args:
        profile: ApplicantProfile 对象

    Returns:
        纯文本格式的摘要

    Example:
        >>> summary = create_profile_summary(profile)
        >>> print(summary)
    """
    lines = [
        "═══════════════════════════════════════════════",
        "申请人前期工作基础报告",
        "═══════════════════════════════════════════════",
        "",
        f"姓名: {profile.name_cn} ({profile.name_en})",
        f"发表年限: {profile.year_range[0]}-{profile.year_range[1]} ({profile.experience_years}年)",
        f"H-index (估算): {profile.h_index_estimate}",
        "",
        "───────────────────────────────────────────────",
        "文献统计",
        "───────────────────────────────────────────────",
        f"  全部文献: {profile.n_total} 篇",
        f"  近5年发文: {profile.recent_5yr_count} 篇",
        f"  疾病相关: {profile.n_disease} 篇",
        f"  NIBS相关: {profile.n_nibs} 篇",
        f"  疾病+NIBS: {profile.n_disease_nibs} 篇",
        "",
        f"  第一作者: {profile.n_first_author} 篇",
        f"  通讯作者: {profile.n_corresponding} 篇",
        f"  第一或通讯: {profile.n_first_or_corresponding} 篇",
        f"  顶刊发表: {profile.top_journal_count} 篇",
        "",
        "───────────────────────────────────────────────",
        f"相关度评分: {profile.relevance_score}/100",
        "───────────────────────────────────────────────",
    ]

    if profile.symptom_coverage:
        lines.append("\n症状维度覆盖:")
        for name, count in sorted(profile.symptom_coverage.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count} 篇")

    if profile.target_coverage:
        lines.append("\n靶区维度覆盖:")
        for name, count in sorted(profile.target_coverage.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count} 篇")

    if profile.top_journal_list:
        lines.append("\n顶刊论文:")
        for i, title in enumerate(profile.top_journal_list[:5], 1):
            title_short = title[:55] + '...' if len(title) > 55 else title
            lines.append(f"  [{i}] {title_short}")

    if profile.top_collaborators:
        lines.append(f"\n主要合作者 (共{len(profile.top_collaborators)}人):")
        for name, count in profile.top_collaborators[:5]:
            lines.append(f"  {name}: {count}次")

    if profile.research_trajectory:
        lines.append("\n研究轨迹:")
        for period, keywords in profile.research_trajectory.items():
            kw_str = ', '.join(keywords[:4])
            lines.append(f"  {period}: {kw_str}")

    if profile.key_papers:
        lines.append("\n代表性论文:")
        for i, p in enumerate(profile.key_papers[:5], 1):
            title = p.get('title', '')[:55]
            if len(p.get('title', '')) > 55:
                title += '...'
            lines.append(f"  [{i}] {p.get('year', '')} {p.get('journal', '')}")
            lines.append(f"      {title}")

    lines.append("\n═══════════════════════════════════════════════")
    return '\n'.join(lines)
