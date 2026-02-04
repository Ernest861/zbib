"""ORCID API 客户端 — 获取作者精确发表记录

ORCID Public API 免费使用，无需认证即可获取公开数据。
API 文档: https://info.orcid.org/documentation/api-tutorials/

用途:
- 获取作者的精确发表列表 (避免姓名歧义)
- 获取 DOI/PMID 用于与 PubMed 数据交叉验证
- 获取机构历史信息
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class OrcidWork:
    """ORCID 作品记录"""
    title: str = ''
    journal: str = ''
    year: int = 0
    doi: str = ''
    pmid: str = ''
    work_type: str = ''  # journal-article, book-chapter, etc.
    external_ids: dict[str, str] = field(default_factory=dict)


@dataclass
class OrcidProfile:
    """ORCID 作者信息"""
    orcid: str = ''
    name: str = ''
    other_names: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    works: list[OrcidWork] = field(default_factory=list)
    n_works: int = 0


class OrcidClient:
    """ORCID Public API 客户端"""

    BASE_URL = "https://pub.orcid.org/v3.0"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
        })

    def _get(self, endpoint: str) -> dict | None:
        """发送 GET 请求"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[ORCID] 请求失败: {e}")
            return None

    def validate_orcid(self, orcid: str) -> str | None:
        """
        验证并标准化 ORCID。

        支持格式:
        - 0000-0002-1234-5678
        - https://orcid.org/0000-0002-1234-5678
        - orcid.org/0000-0002-1234-5678

        Returns:
            标准化的 ORCID (xxxx-xxxx-xxxx-xxxx) 或 None
        """
        if not orcid:
            return None

        # 提取 ORCID 数字部分
        pattern = r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])'
        match = re.search(pattern, orcid, re.I)
        if match:
            return match.group(1).upper()
        return None

    def get_profile(self, orcid: str) -> OrcidProfile | None:
        """
        获取作者基本信息。

        Args:
            orcid: ORCID ID (会自动验证格式)

        Returns:
            OrcidProfile 或 None
        """
        orcid = self.validate_orcid(orcid)
        if not orcid:
            print(f"[ORCID] 无效的 ORCID 格式")
            return None

        data = self._get(f"{orcid}/person")
        if not data:
            return None

        profile = OrcidProfile(orcid=orcid)

        # 姓名
        name_data = data.get('name', {})
        if name_data:
            given = name_data.get('given-names', {}).get('value', '')
            family = name_data.get('family-name', {}).get('value', '')
            profile.name = f"{given} {family}".strip()

        # 其他名字
        other_names = data.get('other-names', {}).get('other-name', [])
        profile.other_names = [n.get('content', '') for n in other_names if n.get('content')]

        return profile

    def get_works(self, orcid: str, max_works: int = 500) -> list[OrcidWork]:
        """
        获取作者发表作品列表。

        Args:
            orcid: ORCID ID
            max_works: 最大获取数量

        Returns:
            OrcidWork 列表
        """
        orcid = self.validate_orcid(orcid)
        if not orcid:
            return []

        data = self._get(f"{orcid}/works")
        if not data:
            return []

        works = []
        groups = data.get('group', [])

        for group in groups[:max_works]:
            work_summary = group.get('work-summary', [])
            if not work_summary:
                continue

            # 取第一个 summary (同一作品可能有多个来源)
            summary = work_summary[0]

            work = OrcidWork()
            work.work_type = summary.get('type', '')

            # 标题
            title_data = summary.get('title', {})
            if title_data:
                work.title = title_data.get('title', {}).get('value', '')

            # 期刊
            journal_data = summary.get('journal-title', {})
            if journal_data:
                work.journal = journal_data.get('value', '')

            # 年份
            pub_date = summary.get('publication-date', {})
            if pub_date and pub_date.get('year'):
                try:
                    work.year = int(pub_date['year'].get('value', 0))
                except (ValueError, TypeError):
                    pass

            # 外部 ID (DOI, PMID 等)
            ext_ids = summary.get('external-ids', {}).get('external-id', [])
            for ext_id in ext_ids:
                id_type = ext_id.get('external-id-type', '').lower()
                id_value = ext_id.get('external-id-value', '')
                if id_type and id_value:
                    work.external_ids[id_type] = id_value
                    if id_type == 'doi':
                        work.doi = id_value
                    elif id_type == 'pmid':
                        work.pmid = id_value

            works.append(work)

        return works

    def get_full_profile(self, orcid: str) -> OrcidProfile | None:
        """
        获取完整的作者信息 (含发表列表)。

        Args:
            orcid: ORCID ID

        Returns:
            完整的 OrcidProfile
        """
        profile = self.get_profile(orcid)
        if not profile:
            return None

        # 获取发表作品
        profile.works = self.get_works(orcid)
        profile.n_works = len(profile.works)

        # 获取机构信息
        orcid_clean = self.validate_orcid(orcid)
        emp_data = self._get(f"{orcid_clean}/employments")
        if emp_data:
            affiliations = []
            for group in emp_data.get('affiliation-group', []):
                summaries = group.get('summaries', [])
                for s in summaries:
                    emp = s.get('employment-summary', {})
                    org = emp.get('organization', {})
                    org_name = org.get('name', '')
                    if org_name and org_name not in affiliations:
                        affiliations.append(org_name)
            profile.affiliations = affiliations

        return profile

    def get_pmids(self, orcid: str) -> list[str]:
        """
        获取作者在 ORCID 中记录的所有 PMID。

        用于与 PubMed 检索结果交叉验证。

        Returns:
            PMID 字符串列表
        """
        works = self.get_works(orcid)
        pmids = []
        for work in works:
            if work.pmid:
                pmids.append(work.pmid)
            elif 'pmid' in work.external_ids:
                pmids.append(work.external_ids['pmid'])
        return pmids


def fetch_orcid_publications(orcid: str) -> dict:
    """
    便捷函数: 获取 ORCID 作者的发表统计。

    Returns:
        {
            'orcid': str,
            'name': str,
            'affiliations': list[str],
            'n_works': int,
            'n_journal_articles': int,
            'pmids': list[str],
            'years': list[int],
        }
    """
    client = OrcidClient()
    profile = client.get_full_profile(orcid)

    if not profile:
        return {'error': 'Failed to fetch ORCID profile'}

    # 统计
    journal_articles = [w for w in profile.works if w.work_type == 'journal-article']
    pmids = [w.pmid for w in profile.works if w.pmid]
    years = [w.year for w in profile.works if w.year > 0]

    return {
        'orcid': profile.orcid,
        'name': profile.name,
        'other_names': profile.other_names,
        'affiliations': profile.affiliations,
        'n_works': profile.n_works,
        'n_journal_articles': len(journal_articles),
        'pmids': pmids,
        'years': sorted(set(years)),
    }
