"""数据获取: PubMed + NIH Reporter API"""

import csv
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

import pandas as pd


class PubMedClient:
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    BATCH = 200

    def search(self, query: str, retmax: int = 10000) -> pd.DataFrame:
        pmids = self._esearch(query, retmax)
        if not pmids:
            return pd.DataFrame()
        articles = self._efetch_batch(pmids)
        return pd.DataFrame(articles)

    def _esearch(self, query: str, retmax: int) -> list[str]:
        params = urlencode({
            "db": "pubmed", "term": query,
            "retmax": retmax, "retmode": "json", "usehistory": "y",
        })
        url = f"{self.BASE}/esearch.fcgi?{params}"
        print(f"搜索: {query}")
        with urlopen(Request(url)) as resp:
            data = json.loads(resp.read())
        result = data["esearchresult"]
        count = int(result["count"])
        ids = result["idlist"]
        print(f"命中 {count} 篇，获取 {len(ids)} 个PMID")
        if count > retmax:
            print(f"  ⚠ 总数 {count} 超过 retmax={retmax}，只获取前 {retmax} 条")
        return ids

    def _efetch_batch(self, pmids: list[str]) -> list[dict]:
        all_articles = []
        for start in range(0, len(pmids), self.BATCH):
            batch = pmids[start:start + self.BATCH]
            print(f"  获取 {start+1}-{start+len(batch)} / {len(pmids)} ...")
            params = urlencode({
                "db": "pubmed", "id": ",".join(batch),
                "retmode": "xml", "rettype": "abstract",
            })
            url = f"{self.BASE}/efetch.fcgi?{params}"
            with urlopen(Request(url)) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for elem in root.findall(".//PubmedArticle"):
                article = self._parse_article(elem)
                if article:
                    all_articles.append(article)
            time.sleep(0.4)
        return all_articles

    @staticmethod
    def _parse_article(elem) -> dict | None:
        medline = elem.find("MedlineCitation")
        if medline is None:
            return None
        article = medline.find("Article")
        if article is None:
            return None

        pmid_elem = medline.find("PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        title_elem = article.find("ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

        year = ""
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            y = pub_date.find("Year")
            if y is not None:
                year = y.text
            else:
                md = pub_date.find("MedlineDate")
                if md is not None and md.text:
                    year = md.text.strip()[:4]

        journal_elem = article.find(".//ISOAbbreviation")
        if journal_elem is None:
            journal_elem = article.find(".//Title")
        journal = journal_elem.text.strip() if journal_elem is not None and journal_elem.text else ""

        abstract_parts = []
        for at in article.findall(".//AbstractText"):
            label = at.get("Label", "")
            text = "".join(at.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        mesh_terms = [mh.text for mh in medline.findall(".//MeshHeading/DescriptorName")]
        mesh = "; ".join(mesh_terms)

        keywords = [kw.text.strip() for kw in medline.findall(".//Keyword") if kw.text]
        kw_str = "; ".join(keywords)

        doi = ""
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = eid.text or ""
                break

        authors = []
        for au in article.findall(".//Author"):
            last = au.find("LastName")
            fore = au.find("ForeName")
            if last is not None and last.text:
                name = last.text
                if fore is not None and fore.text:
                    name += f" {fore.text}"
                authors.append(name)

        return {
            "pmid": pmid, "title": title, "year": year, "journal": journal,
            "authors": "; ".join(authors), "abstract": abstract,
            "mesh": mesh, "keywords": kw_str, "doi": doi,
        }

    @staticmethod
    def save(df: pd.DataFrame, path: str):
        path = str(path)
        if not path.endswith('.gz'):
            path = path + '.gz' if path.endswith('.csv') else path + '.csv.gz'
        df.to_csv(path, index=False, compression='gzip')
        print(f"已保存 {len(df)} 篇 → {path}")


class NIHClient:
    API_URL = "https://api.reporter.nih.gov/v2/projects/search"
    PUB_API = "https://api.reporter.nih.gov/v2/publications/search"
    PAGE_SIZE = 500
    MAX_OFFSET = 14500

    def search(self, query: str, fy_min: int = None, fy_max: int = None) -> pd.DataFrame:
        projects = self._search_nih(query, fy_min, fy_max)
        return pd.DataFrame(projects)

    def _search_nih(self, query: str, fy_min: int = None, fy_max: int = None) -> list[dict]:
        import re
        criteria = {
            "advanced_text_search": {
                "operator": "advanced",
                "search_field": "projecttitle,terms,abstracttext",
                "search_text": query,
            },
            "exclude_subprojects": True,
        }
        if fy_min or fy_max:
            criteria["fiscal_years"] = list(range(fy_min or 2000, (fy_max or 2026) + 1))

        # Probe total
        probe_body = {"criteria": criteria, "offset": 0, "limit": 1}
        req = Request(self.API_URL, data=json.dumps(probe_body).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=60) as resp:
            probe = json.loads(resp.read())
        total = probe.get("meta", {}).get("total", 0)
        print(f"命中 {total} 个项目")

        all_projects = []
        if total > 14000:
            print(f"  总数超过14000，按财年分批获取...")
            for fy in range(fy_min or 1985, (fy_max or 2026) + 1):
                fy_criteria = dict(criteria)
                fy_criteria["fiscal_years"] = [fy]
                batch = self._fetch_all_pages(fy_criteria)
                if batch:
                    print(f"  财年 {fy}: {len(batch)} 项")
                    all_projects.extend(batch)
                time.sleep(0.3)
        else:
            all_projects = self._fetch_all_pages(criteria)

        # Dedup by project_num
        seen = set()
        deduped = []
        for p in all_projects:
            key = p["project_num"]
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        if len(deduped) < len(all_projects):
            print(f"去重: {len(all_projects)} → {len(deduped)} 个独立项目")
        return deduped

    def _fetch_all_pages(self, criteria: dict) -> list[dict]:
        results = []
        offset = 0
        while True:
            body = {
                "criteria": criteria, "offset": offset, "limit": self.PAGE_SIZE,
                "sort_field": "fiscal_year", "sort_order": "desc",
            }
            req = Request(self.API_URL, data=json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            batch = data.get("results", [])
            total = data.get("meta", {}).get("total", 0)
            for proj in batch:
                results.append(self._parse_project(proj))
            offset += self.PAGE_SIZE
            if offset >= total or offset > self.MAX_OFFSET or not batch:
                break
            time.sleep(0.3)
        return results

    @staticmethod
    def _parse_project(proj: dict) -> dict:
        import re
        pi_names = []
        for pi in (proj.get("principal_investigators") or []):
            name = pi.get("full_name", "").strip()
            if name:
                pi_names.append(name)

        org = proj.get("organization", {})
        org_name = org.get("org_name", "") if org else ""

        abstract = (proj.get("abstract_text") or "").strip()
        for prefix in ["ABSTRACT", "PROJECT SUMMARY", "PROJECT SUMMARY/ABSTRACT"]:
            if abstract.upper().startswith(prefix):
                abstract = abstract[len(prefix):].strip().lstrip("\n\r")
                break

        terms_list = proj.get("terms") or ""
        if isinstance(terms_list, list):
            terms = "; ".join(str(t) for t in terms_list if t)
        else:
            terms = str(terms_list).strip()
        if "<" in terms:
            terms = re.sub(r'<([^>]+)>', r'\1; ', terms).strip("; ")

        amount = proj.get("award_amount")
        if amount is not None:
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = ""

        return {
            "project_num": proj.get("project_num", ""),
            "title": (proj.get("project_title") or "").strip(),
            "pi": "; ".join(pi_names),
            "org": org_name,
            "fiscal_year": proj.get("fiscal_year", ""),
            "award_amount": amount,
            "activity_code": proj.get("activity_code", ""),
            "project_start": proj.get("project_start_date", ""),
            "project_end": proj.get("project_end_date", ""),
            "abstract": abstract,
            "terms": terms,
        }

    def fetch_publications(self, project_nums: list[str], batch_size: int = 100) -> pd.DataFrame:
        """项目号 → PMID 链接表 (来自 annual report publications)"""
        all_rows = []
        for start in range(0, len(project_nums), batch_size):
            batch = project_nums[start:start + batch_size]
            print(f"  Pubs: 项目 {start+1}-{start+len(batch)} / {len(project_nums)} ...")
            offset = 0
            while True:
                body = {
                    "criteria": {"core_project_nums": batch},
                    "offset": offset,
                    "limit": self.PAGE_SIZE,
                }
                req = Request(self.PUB_API, data=json.dumps(body).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                results = data.get("results", [])
                total = data.get("meta", {}).get("total", 0)
                for pub in results:
                    all_rows.append({
                        "core_project_num": pub.get("coreproject", ""),
                        "pmid": str(pub.get("pmid", "")),
                        "appl_id": pub.get("applid", ""),
                    })
                offset += self.PAGE_SIZE
                if offset >= total or not results:
                    break
                time.sleep(0.3)
            time.sleep(0.3)
        df = pd.DataFrame(all_rows)
        if not df.empty:
            df = df.drop_duplicates(subset=["core_project_num", "pmid"])
        print(f"  共 {len(df)} 条项目-PMID链接")
        return df

    def fetch_publications_full(
        self, project_nums: list[str], pubmed_client: 'PubMedClient | None' = None
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """链接表 + PubMed 详情合并"""
        link_df = self.fetch_publications(project_nums)
        if link_df.empty:
            return link_df, link_df

        if pubmed_client is None:
            pubmed_client = PubMedClient()

        unique_pmids = link_df["pmid"].unique().tolist()
        print(f"  获取 {len(unique_pmids)} 篇 PubMed 详情 ...")
        articles = pubmed_client._efetch_batch(unique_pmids)
        pub_df = pd.DataFrame(articles)

        if pub_df.empty:
            return link_df, link_df

        full_df = link_df.merge(pub_df, on="pmid", how="left")
        print(f"  合并完成: {len(full_df)} 行")
        return link_df, full_df

    @staticmethod
    def save(df: pd.DataFrame, path: str):
        path = str(path)
        if not path.endswith('.gz'):
            path = path + '.gz' if path.endswith('.csv') else path + '.csv.gz'
        df.to_csv(path, index=False, compression='gzip')
        print(f"已保存 {len(df)} 项 → {path}")
