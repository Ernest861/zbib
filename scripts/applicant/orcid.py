"""ORCID 交叉验证 — PubMed 检索结果与 ORCID 比对"""

import logging
from typing import Literal

import pandas as pd

from scripts.orcid_client import OrcidClient
from scripts.applicant.profile import ApplicantProfile

logger = logging.getLogger(__name__)

ConfidenceLevel = Literal['high', 'medium', 'low']


def verify_with_orcid(
    profile: ApplicantProfile,
    df_all: pd.DataFrame,
    orcid: str,
    *,
    verbose: bool = True,
) -> ApplicantProfile:
    """
    用 ORCID 交叉验证 PubMed 检索结果，标记数据可信度。

    流程:
    1. 从 ORCID 获取作者确认的 PMID 列表
    2. 与 PubMed 检索结果交叉比对
    3. 标记三类论文: 双确认 / 仅PubMed / 仅ORCID
    4. 计算验证置信度

    Args:
        profile: 已有的 ApplicantProfile
        df_all: PubMed 检索到的全部文献 DataFrame
        orcid: ORCID ID
        verbose: 是否输出详细日志 (默认 True)

    Returns:
        更新后的 ApplicantProfile (原地修改并返回)

    Raises:
        不抛出异常，网络错误时返回未验证的 profile
    """
    client = OrcidClient()
    orcid_clean = client.validate_orcid(orcid)

    if not orcid_clean:
        logger.warning("无效的 ORCID: %s，跳过交叉验证", orcid)
        return profile

    profile.orcid_id = orcid_clean

    # 获取 ORCID 中的 PMID 列表
    try:
        logger.info("获取 ORCID %s 的发表记录...", orcid_clean)
        orcid_pmids_raw = client.get_pmids(orcid_clean)
        orcid_pmids = set(str(p) for p in orcid_pmids_raw)
    except Exception as e:
        logger.error("ORCID API 请求失败: %s", e)
        return profile

    if not orcid_pmids:
        logger.info("未获取到 PMID 记录，尝试通过 DOI 匹配...")
        # 尝试通过 DOI 匹配
        try:
            orcid_works = client.get_works(orcid_clean)
            orcid_dois = {w.doi.lower() for w in orcid_works if w.doi}
        except Exception as e:
            logger.error("获取 ORCID works 失败: %s", e)
            return profile

        if 'doi' in df_all.columns and orcid_dois:
            pubmed_dois = set(df_all['doi'].dropna().str.lower())
            doi_matches = pubmed_dois & orcid_dois
            profile.orcid_match_count = len(doi_matches)
            profile.orcid_only_count = len(orcid_dois - pubmed_dois)
            profile.pubmed_only_count = len(pubmed_dois - orcid_dois)
        else:
            logger.warning("无法进行交叉验证 (无 PMID 或 DOI)")
            return profile
    else:
        # PMID 交叉比对
        if 'pmid' not in df_all.columns:
            logger.warning("PubMed 数据缺少 pmid 列")
            return profile

        pubmed_pmids = set(df_all['pmid'].dropna().astype(str))
        matched = pubmed_pmids & orcid_pmids
        pubmed_only = pubmed_pmids - orcid_pmids
        orcid_only = orcid_pmids - pubmed_pmids

        profile.orcid_match_count = len(matched)
        profile.pubmed_only_count = len(pubmed_only)
        profile.orcid_only_count = len(orcid_only)

    profile.orcid_verified = True

    # 计算验证置信度
    total_union = profile.orcid_match_count + profile.pubmed_only_count + profile.orcid_only_count
    profile.verification_confidence = _calculate_confidence(
        profile.orcid_match_count, total_union
    )

    if verbose:
        logger.info(
            "ORCID 交叉验证完成: 双确认=%d, 仅PubMed=%d, 仅ORCID=%d, 置信度=%s",
            profile.orcid_match_count,
            profile.pubmed_only_count,
            profile.orcid_only_count,
            profile.verification_confidence,
        )

    # 如果 PubMed-only 比例过高，提示可能存在同名干扰
    if profile.pubmed_only_count > profile.orcid_match_count * 2:
        logger.warning("PubMed 检索可能包含同名他人的论文，建议人工核查")

    return profile


def _calculate_confidence(match_count: int, total_union: int) -> ConfidenceLevel:
    """计算验证置信度"""
    if total_union <= 0:
        return 'low'
    match_ratio = match_count / total_union
    if match_ratio >= 0.7:
        return 'high'
    elif match_ratio >= 0.4:
        return 'medium'
    return 'low'
