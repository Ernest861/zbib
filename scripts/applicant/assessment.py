"""申请人评估与叙事分析模块

提供基于适配度×胜任力体系的评估功能:
- 生成可直接用于标书的叙事性评估文本
- 分析薄弱维度并提供改进建议
- 象限定位（明星/潜力/跨界/成长型）
- 生成针对性提升计划
"""

from typing import Literal, TypedDict

from scripts.applicant.profile import (
    ApplicantProfile,
    DEFAULT_SCORE_WEIGHTS,
    FIT_DIMENSIONS,
    COMPETENCY_DIMENSIONS,
)


# ═══════════════════════════════════════════════
# 类型定义
# ═══════════════════════════════════════════════

QuadrantType = Literal['star', 'potential', 'senior', 'developing']
"""象限类型: 明星/潜力/跨界/成长型"""


class WeaknessInfo(TypedDict):
    """薄弱维度信息"""
    dimension: str      # 维度名称 (disease/nibs/crossover/independence/impact/activity)
    score: float        # 该维度得分 (0-100)
    issue: str          # 问题描述
    suggestion: str     # 改进建议


class QuadrantPosition(TypedDict):
    """象限定位信息"""
    fit: float          # 适配度得分 (0-100)
    competency: float   # 胜任力得分 (0-100)
    quadrant: QuadrantType  # 象限类型
    label: str          # 中文标签 (明星申请人/潜力申请人/跨界申请人/成长型申请人)
    description: str    # 描述文字


def generate_narrative_assessment(profile: ApplicantProfile, topic_name: str = '') -> str:
    """
    生成叙事性评估报告，可直接用于标书"研究基础"或"可行性分析"部分。

    Args:
        profile: ApplicantProfile 对象
        topic_name: 研究课题名称

    Returns:
        自然语言描述的评估文本
    """
    name = profile.name_cn or profile.name_en
    fit = getattr(profile, 'fit_score', 0)
    comp = getattr(profile, 'competency_score', 0)
    breakdown = profile.get_score_breakdown()

    paragraphs = []

    # ═══ 第一段: 总体评价 ═══
    topic_str = f"「{topic_name}」" if topic_name else "本课题"

    if fit >= 80 and comp >= 80:
        opening = f"申请人{name}在{topic_str}研究方向具有深厚的前期工作基础和卓越的独立研究能力。"
    elif fit >= 60 and comp >= 60:
        opening = f"申请人{name}在{topic_str}研究方向具有扎实的前期积累和良好的独立研究能力。"
    elif fit >= 60:
        opening = f"申请人{name}在{topic_str}研究方向具有较好的前期工作基础。"
    elif comp >= 60:
        opening = f"申请人{name}具有较强的独立研究能力和学术影响力。"
    else:
        opening = f"申请人{name}在相关领域开展了一定的前期研究工作。"

    paragraphs.append(opening)

    # ═══ 第二段: 发表成果概述 ═══
    pub_parts = []
    pub_parts.append(f"截至目前，申请人已发表学术论文{profile.n_total}篇")

    if profile.n_disease > 0:
        pub_parts.append(f"其中{profile.n_disease}篇与目标疾病相关")
    if profile.n_nibs > 0:
        pub_parts.append(f"{profile.n_nibs}篇涉及神经调控技术")
    if profile.n_disease_nibs > 0:
        pub_parts.append(f"{profile.n_disease_nibs}篇为疾病与神经调控的交叉研究")

    tier1 = getattr(profile, 'tier1_count', profile.top_journal_count)
    tier2 = getattr(profile, 'tier2_count', 0)
    if tier1 > 0 or tier2 > 0:
        journal_str = []
        if tier1 > 0:
            journal_str.append(f"{tier1}篇发表于顶级期刊")
        if tier2 > 0:
            journal_str.append(f"{tier2}篇发表于高影响力期刊")
        pub_parts.append("，".join(journal_str))

    paragraphs.append("，".join(pub_parts) + "。")

    # ═══ 第三段: 学术独立性 ═══
    if profile.n_first_or_corresponding > 0:
        independence_ratio = profile.n_first_or_corresponding / profile.n_total * 100
        ind_text = f"在上述成果中，申请人以第一作者或通讯作者身份发表{profile.n_first_or_corresponding}篇（占比{independence_ratio:.0f}%），"

        if independence_ratio >= 50:
            ind_text += "表明申请人具备独立开展研究和主持科研项目的能力。"
        elif independence_ratio >= 30:
            ind_text += "具有较好的学术独立性。"
        else:
            ind_text += "在团队合作中发挥了重要作用。"
        paragraphs.append(ind_text)

    # ═══ 第四段: 研究活跃度 ═══
    if profile.recent_5yr_count > 0:
        recent_ratio = profile.recent_5yr_count / profile.n_total * 100
        if recent_ratio >= 60:
            activity_text = f"近五年发表{profile.recent_5yr_count}篇（占比{recent_ratio:.0f}%），保持着高度活跃的研究产出。"
        elif recent_ratio >= 40:
            activity_text = f"近五年发表{profile.recent_5yr_count}篇，研究产出稳定持续。"
        else:
            activity_text = f"近五年发表{profile.recent_5yr_count}篇。"
        paragraphs.append(activity_text)

    # ═══ 第五段: H-index ═══
    if profile.h_index_estimate > 0:
        h_text = f"申请人 H-index 约为{profile.h_index_estimate}，"
        if profile.h_index_estimate >= 15:
            h_text += "具有较高的学术影响力。"
        elif profile.h_index_estimate >= 8:
            h_text += "在领域内有一定的学术影响力。"
        else:
            h_text += "研究成果获得了同行认可。"
        paragraphs.append(h_text)

    # ═══ 第六段: 合作网络 ═══
    if profile.top_collaborators and len(profile.top_collaborators) >= 3:
        top3 = [c[0] for c in profile.top_collaborators[:3]]
        collab_text = f"申请人与国内外多位学者建立了稳定的合作关系，主要合作者包括{top3[0]}、{top3[1]}等，"
        collab_text += "具备开展多学科合作研究的条件。"
        paragraphs.append(collab_text)

    # ═══ 第七段: 总结 ═══
    summary_parts = []
    if fit >= 60:
        summary_parts.append("前期工作与本课题高度契合")
    if comp >= 60:
        summary_parts.append("具备独立完成课题的能力")
    if profile.recent_5yr_count > profile.n_total * 0.4:
        summary_parts.append("近年研究产出活跃")

    if summary_parts:
        summary = "综上所述，申请人" + "、".join(summary_parts) + "，为本课题的顺利实施提供了坚实的研究基础。"
        paragraphs.append(summary)

    return "\n\n".join(paragraphs)


def analyze_weaknesses(profile: ApplicantProfile) -> list[WeaknessInfo]:
    """
    分析申请人的薄弱维度并提供改进建议。

    Returns:
        薄弱维度列表，每项包含 dimension/score/issue/suggestion 字段
    """
    breakdown = profile.get_score_breakdown()
    weaknesses = []

    # 检查各维度
    checks = [
        ('disease', '疾病领域', 60, '疾病相关研究积累不足',
         '建议在目标疾病方向发表更多研究成果，可通过合作或综述切入'),
        ('nibs', '技术方法', 60, 'NIBS 技术相关经验有限',
         '建议开展 NIBS 相关的方法学研究或参与相关临床试验'),
        ('crossover', '交叉研究', 40, '疾病与 NIBS 的交叉研究较少',
         '建议将现有技术应用于目标疾病，产出交叉领域成果'),
        ('independence', '学术独立性', 50, '第一/通讯作者占比偏低',
         '建议主导更多独立研究项目，提升学术独立性'),
        ('impact', '学术影响力', 50, '高影响力成果较少',
         '建议向顶级期刊投稿，提升研究的学术影响力'),
        ('activity', '研究活跃度', 50, '近年发表数量下降',
         '建议保持稳定的研究产出，展示持续的科研活力'),
    ]

    for dim, name, threshold, issue, suggestion in checks:
        raw_score = breakdown.get(f'{dim}_raw', 0)
        if raw_score < threshold:
            weaknesses.append({
                'dimension': name,
                'score': raw_score,
                'threshold': threshold,
                'issue': issue,
                'suggestion': suggestion,
            })

    # 按得分排序（最薄弱的在前）
    weaknesses.sort(key=lambda x: x['score'])

    return weaknesses


def get_quadrant_position(profile: ApplicantProfile) -> QuadrantPosition:
    """
    获取申请人在适配度×胜任力象限图中的位置。

    象限定义:
        - star (明星申请人): fit≥60, competency≥60
        - potential (潜力申请人): fit≥60, competency<60
        - senior (跨界申请人): fit<60, competency≥60
        - developing (成长型申请人): fit<60, competency<60
    """
    fit = getattr(profile, 'fit_score', 0)
    comp = getattr(profile, 'competency_score', 0)

    # 象限判定 (以 60 分为界)
    if fit >= 60 and comp >= 60:
        quadrant = 'star'
        label = '明星申请人'
        desc = '前期工作契合度高，独立研究能力强，是理想的课题负责人'
    elif fit >= 60 and comp < 60:
        quadrant = 'potential'
        label = '潜力申请人'
        desc = '领域积累扎实但学术独立性待提升，适合作为骨干成员或联合申请'
    elif fit < 60 and comp >= 60:
        quadrant = 'senior'
        label = '跨界申请人'
        desc = '学术能力强但需补充领域知识，建议加强前期调研或寻求合作'
    else:
        quadrant = 'developing'
        label = '成长型申请人'
        desc = '需要在领域积累和学术独立性两方面同时提升'

    return {
        'fit': fit,
        'competency': comp,
        'quadrant': quadrant,
        'label': label,
        'description': desc,
    }


def generate_improvement_plan(profile: ApplicantProfile, months: int = 12) -> str:
    """
    生成针对性的提升计划建议。

    Args:
        profile: ApplicantProfile
        months: 计划周期（月）

    Returns:
        提升计划文本
    """
    weaknesses = analyze_weaknesses(profile)
    position = get_quadrant_position(profile)

    lines = []
    lines.append(f"## 申报者提升计划 ({months}个月)")
    lines.append("")
    lines.append(f"**当前定位**: {position['label']}")
    lines.append(f"> {position['description']}")
    lines.append("")

    if not weaknesses:
        lines.append("✅ 各维度表现均衡，建议保持当前研究节奏。")
        return '\n'.join(lines)

    lines.append("### 需要改进的维度")
    lines.append("")

    for i, w in enumerate(weaknesses[:3], 1):  # 最多列出 3 个
        lines.append(f"**{i}. {w['dimension']}** (当前: {w['score']:.0f}/100)")
        lines.append(f"- 问题: {w['issue']}")
        lines.append(f"- 建议: {w['suggestion']}")
        lines.append("")

    # 根据象限给出总体建议
    lines.append("### 总体建议")
    lines.append("")

    if position['quadrant'] == 'potential':
        lines.append("- 重点提升学术独立性：争取主持小型课题或作为 Co-PI 参与项目")
        lines.append("- 尝试独立撰写并投稿高质量论文")
        lines.append("- 参加学术会议，扩大学术影响力")
    elif position['quadrant'] == 'senior':
        lines.append("- 快速补充领域知识：阅读近 5 年该领域综述和重要文献")
        lines.append("- 寻找领域内合作者，开展联合研究")
        lines.append("- 发表 1-2 篇领域相关论文建立学术 footprint")
    elif position['quadrant'] == 'developing':
        lines.append("- 建议先以骨干成员身份参与相关课题积累经验")
        lines.append("- 同时提升领域知识和研究独立性")
        lines.append("- 考虑申请青年基金或面上项目的子课题")

    return '\n'.join(lines)
