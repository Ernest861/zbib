"""申请人文献检索: PubMed E-utilities API

检索策略:
1. 若有 ORCID: {orcid}[auid]
2. 否则: ({name_en}[AU] OR {aliases}[AU]) AND {affiliation}[ad]
3. 分三层过滤: 全部 → 疾病相关 → NIBS相关

优化:
- 只发1次PubMed请求获取全部文献
- 本地用正则过滤疾病/NIBS相关子集 (减少API调用)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from scripts.config import ApplicantConfig
from scripts.fetch import PubMedClient


@dataclass
class ApplicantSearchResult:
    """申请人检索结果"""
    name_cn: str
    name_en: str
    df_all: pd.DataFrame           # 全部文献
    df_disease: pd.DataFrame       # 疾病相关子集
    df_nibs: pd.DataFrame          # NIBS相关子集
    df_disease_nibs: pd.DataFrame  # 疾病+NIBS交集
    n_total: int = 0
    n_disease: int = 0
    n_nibs: int = 0
    n_disease_nibs: int = 0

    def __post_init__(self):
        self.n_total = len(self.df_all)
        self.n_disease = len(self.df_disease)
        self.n_nibs = len(self.df_nibs)
        self.n_disease_nibs = len(self.df_disease_nibs)


class ApplicantClient:
    """申请人文献检索客户端"""

    def __init__(self):
        self.pubmed = PubMedClient()

    def search(
        self,
        config: ApplicantConfig,
        disease_query: str = '',
        nibs_query: str = '',
        disease_pattern: str = '',
        nibs_pattern: str = '',
        use_local_filter: bool = True,
    ) -> ApplicantSearchResult:
        """
        检索申请人文献，分三层过滤。

        Args:
            config: 申请人配置
            disease_query: 疾病相关PubMed检索式 (仅当 use_local_filter=False 时使用)
            nibs_query: NIBS相关检索式 (仅当 use_local_filter=False 时使用)
            disease_pattern: 疾病相关正则表达式 (本地过滤用)
            nibs_pattern: NIBS相关正则表达式 (本地过滤用)
            use_local_filter: 是否使用本地过滤 (True=更快，False=更准确)

        Returns:
            ApplicantSearchResult 包含多个DataFrame
        """
        author_query = self._build_author_query(config)
        print(f"[Applicant] 检索作者: {config.name_cn} ({config.name_en})")
        print(f"  检索式: {author_query}")

        # Step 1: 获取全部文献
        df_all = self.pubmed.search(author_query)
        print(f"  全部文献: {len(df_all)} 篇")

        if df_all.empty:
            return ApplicantSearchResult(
                name_cn=config.name_cn,
                name_en=config.name_en,
                df_all=df_all,
                df_disease=pd.DataFrame(),
                df_nibs=pd.DataFrame(),
                df_disease_nibs=pd.DataFrame(),
            )

        # 创建搜索文本列
        df_all = self._create_search_text(df_all)

        if use_local_filter:
            # 本地过滤 (快速，但可能不如PubMed检索精确)
            df_disease, df_nibs, df_disease_nibs = self._filter_local(
                df_all, disease_pattern, nibs_pattern
            )
        else:
            # PubMed API 过滤 (精确，但慢)
            df_disease, df_nibs, df_disease_nibs = self._filter_via_api(
                df_all, author_query, disease_query, nibs_query
            )

        print(f"  疾病相关: {len(df_disease)} 篇")
        print(f"  NIBS相关: {len(df_nibs)} 篇")
        print(f"  疾病+NIBS: {len(df_disease_nibs)} 篇")

        return ApplicantSearchResult(
            name_cn=config.name_cn,
            name_en=config.name_en,
            df_all=df_all,
            df_disease=df_disease,
            df_nibs=df_nibs,
            df_disease_nibs=df_disease_nibs,
        )

    def _create_search_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建用于本地搜索的文本列"""
        df = df.copy()
        text_parts = []
        for col in ['title', 'abstract', 'mesh', 'keywords']:
            if col in df.columns:
                text_parts.append(df[col].fillna(''))
        if text_parts:
            df['_search_text'] = ' '.join(text_parts) if len(text_parts) == 1 else \
                text_parts[0].str.cat(text_parts[1:], sep=' ')
        else:
            df['_search_text'] = ''
        return df

    def _filter_local(
        self,
        df_all: pd.DataFrame,
        disease_pattern: str,
        nibs_pattern: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """本地正则过滤"""
        df_disease = pd.DataFrame()
        df_nibs = pd.DataFrame()
        df_disease_nibs = pd.DataFrame()

        disease_mask = pd.Series([False] * len(df_all), index=df_all.index)
        nibs_mask = pd.Series([False] * len(df_all), index=df_all.index)

        if disease_pattern and '_search_text' in df_all.columns:
            disease_mask = df_all['_search_text'].str.contains(
                disease_pattern, flags=re.I, na=False
            )
            df_disease = df_all[disease_mask].copy()

        if nibs_pattern and '_search_text' in df_all.columns:
            nibs_mask = df_all['_search_text'].str.contains(
                nibs_pattern, flags=re.I, na=False
            )
            df_nibs = df_all[nibs_mask].copy()

        # 交集
        if disease_pattern and nibs_pattern:
            both_mask = disease_mask & nibs_mask
            df_disease_nibs = df_all[both_mask].copy()

        return df_disease, df_nibs, df_disease_nibs

    def _filter_via_api(
        self,
        df_all: pd.DataFrame,
        author_query: str,
        disease_query: str,
        nibs_query: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """通过PubMed API过滤 (更精确但更慢)"""
        df_disease = pd.DataFrame()
        df_nibs = pd.DataFrame()
        df_disease_nibs = pd.DataFrame()

        all_pmids = set(df_all['pmid'].dropna().astype(str))

        if disease_query:
            disease_full_query = f"({author_query}) AND ({disease_query})"
            df_disease_raw = self.pubmed.search(disease_full_query)
            if not df_disease_raw.empty:
                disease_pmids = set(df_disease_raw['pmid'].dropna().astype(str))
                # 确保是子集
                valid_pmids = all_pmids & disease_pmids
                df_disease = df_all[df_all['pmid'].astype(str).isin(valid_pmids)].copy()

        if nibs_query:
            nibs_full_query = f"({author_query}) AND ({nibs_query})"
            df_nibs_raw = self.pubmed.search(nibs_full_query)
            if not df_nibs_raw.empty:
                nibs_pmids = set(df_nibs_raw['pmid'].dropna().astype(str))
                valid_pmids = all_pmids & nibs_pmids
                df_nibs = df_all[df_all['pmid'].astype(str).isin(valid_pmids)].copy()

        # 交集
        if not df_disease.empty and not df_nibs.empty:
            disease_pmids = set(df_disease['pmid'].dropna().astype(str))
            nibs_pmids = set(df_nibs['pmid'].dropna().astype(str))
            both_pmids = disease_pmids & nibs_pmids
            df_disease_nibs = df_all[df_all['pmid'].astype(str).isin(both_pmids)].copy()

        return df_disease, df_nibs, df_disease_nibs

    def _build_author_query(self, config: ApplicantConfig) -> str:
        """
        构建作者检索式。

        策略:
        1. 若有 ORCID: 直接用 ORCID[auid]
        2. 否则: (name[AU] OR aliases[AU]) AND affiliation[ad]
        """
        if config.orcid:
            return f"{config.orcid}[auid]"

        # 构建作者名检索
        author_parts = [f'"{config.name_en}"[AU]']
        for alias in config.aliases:
            author_parts.append(f'"{alias}"[AU]')
        author_clause = ' OR '.join(author_parts)

        # 加机构过滤
        if config.affiliation:
            return f"({author_clause}) AND {config.affiliation}[ad]"
        return f"({author_clause})"

    def save(
        self,
        result: ApplicantSearchResult,
        output_dir: str | Path,
        prefix: str = 'applicant',
    ):
        """
        保存检索结果到CSV文件。

        输出文件:
        - {prefix}_{name}_all.csv.gz
        - {prefix}_{name}_disease.csv.gz
        - {prefix}_{name}_nibs.csv.gz
        - {prefix}_{name}_disease_nibs.csv.gz
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 用英文名作为文件名（去除空格）
        name_slug = result.name_en.replace(' ', '_').lower()

        # 保存时移除内部搜索列
        def _clean_df(df):
            if '_search_text' in df.columns:
                return df.drop(columns=['_search_text'])
            return df

        if not result.df_all.empty:
            path_all = output_dir / f"{prefix}_{name_slug}_all.csv.gz"
            _clean_df(result.df_all).to_csv(path_all, index=False, compression='gzip')
            print(f"  保存: {path_all} ({len(result.df_all)} 篇)")

        if not result.df_disease.empty:
            path_disease = output_dir / f"{prefix}_{name_slug}_disease.csv.gz"
            _clean_df(result.df_disease).to_csv(path_disease, index=False, compression='gzip')
            print(f"  保存: {path_disease} ({len(result.df_disease)} 篇)")

        if not result.df_nibs.empty:
            path_nibs = output_dir / f"{prefix}_{name_slug}_nibs.csv.gz"
            _clean_df(result.df_nibs).to_csv(path_nibs, index=False, compression='gzip')
            print(f"  保存: {path_nibs} ({len(result.df_nibs)} 篇)")

        if not result.df_disease_nibs.empty:
            path_both = output_dir / f"{prefix}_{name_slug}_disease_nibs.csv.gz"
            _clean_df(result.df_disease_nibs).to_csv(path_both, index=False, compression='gzip')
            print(f"  保存: {path_both} ({len(result.df_disease_nibs)} 篇)")


def load_applicant_pubs(
    output_dir: str | Path,
    name_en: str,
    prefix: str = 'applicant',
) -> dict[str, pd.DataFrame]:
    """
    加载已保存的申请人文献数据。

    Returns:
        {'all': df_all, 'disease': df_disease, 'nibs': df_nibs, 'disease_nibs': df}
    """
    output_dir = Path(output_dir)
    name_slug = name_en.replace(' ', '_').lower()
    result = {}

    for suffix in ['all', 'disease', 'nibs', 'disease_nibs']:
        for ext in ['.csv.gz', '.csv']:
            path = output_dir / f"{prefix}_{name_slug}_{suffix}{ext}"
            if path.exists():
                result[suffix] = pd.read_csv(path, low_memory=False)
                break

    return result
