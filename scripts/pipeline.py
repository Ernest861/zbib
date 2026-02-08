"""Pipeline — 全流程编排: 抓取 → 合并 → 分类 → 空白分析 → 出图"""

# 无头后端，避免 GUI/显示导致 SIGABRT（须在导入 plot 前设置）
import matplotlib
matplotlib.use('Agg')

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.config import TopicConfig, ProjectLayout, load_config, ApplicantConfig, NIBS_QUERY_EN, NIBS_PATTERN_CN, NIBS_PATTERN_EN
from scripts.fetch import PubMedClient, NIHClient
from scripts.journals import build_journal_query, tag_top_journals
from scripts.fetch_letpub import LetPubClient
from scripts.fetch_kd import NSFCKDClient
from scripts.fetch_intramural import IntramuralClient
from scripts.fetch_applicant import ApplicantClient, load_applicant_pubs
from scripts.transform import merge_nsfc_sources, create_search_text
from scripts.analyze import (
    TextClassifier, AspectClassifier, GapAnalyzer,
    NSFC_NEURO_CATEGORIES, NIH_NEURO_CATEGORIES,
)
from scripts.analyze_applicant import (
    ApplicantAnalyzer, ApplicantProfile, create_profile_summary,
    verify_with_orcid, apply_benchmark, get_quadrant_position,
)
from scripts.plot import LandscapePlot
from scripts.performance import PerformanceAnalyzer
from scripts.quality import QualityReporter
from scripts.analyze import TrendDetector


class Pipeline:
    """YAML驱动的文献空白分析全流程"""

    def __init__(self, config: TopicConfig, config_path: Path | None = None):
        self.cfg = config
        self._config_path = config_path
        self._run_log: list[str] = []  # 记录每一步调用
        self.layout = config.layout  # None if project_dir unset
        self._legacy_data_dir = Path(config.data_dir)  # 原始 data_dir (用于回退)

        if self.layout:
            self.layout.ensure_dirs()
            self.data_dir = self.layout.data
        else:
            self.data_dir = Path(config.data_dir)

        # DataFrames populated by load_data()
        self.nsfc = None
        self.nih_all = None
        self.nih_nibs = None
        self.pubmed = None

        # Applicant profile populated by analyze_applicant()
        self.applicant_profile: ApplicantProfile | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'Pipeline':
        path = Path(path).resolve()
        return cls(load_config(path), config_path=path)

    # ─── Step 1: Fetch LetPub ────────────────────
    def fetch_letpub(self, email: str, password: str):
        cfg = self.cfg
        client = LetPubClient(
            keyword=cfg.disease_cn_keyword,
            output_dir=str(self.data_dir),
        )
        client.download(email=email, password=password)
        client.merge()
        print(f"[LetPub] done → {self.data_dir}")

    # ─── Step 2: Fetch KD ────────────────────────
    def fetch_kd(self):
        cfg = self.cfg
        letpub_file = self.data_dir / f"nsfcfund_{cfg.disease_cn_keyword}_all.xlsx"
        output_file = self.data_dir / f"nsfc_kd_{cfg.name}.csv"
        client = NSFCKDClient()
        client.scrape(str(letpub_file), str(output_file))
        print(f"[KD] done → {output_file}")

    # ─── Step 3: Fetch PubMed ────────────────────
    def fetch_pubmed(self):
        cfg = self.cfg
        client = PubMedClient()

        # 高级检索式优先；否则自动拼接
        if cfg.pubmed_query:
            query = cfg.pubmed_query
        else:
            nibs_q = cfg.intervention_query_en or NIBS_QUERY_EN
            query = f"{nibs_q} AND {cfg.disease_en_query}"

        df = client.search(query)
        out = self.data_dir / f"pubmed_nibs_{cfg.name}.csv"
        client.save(df, str(out))
        print(f"[PubMed] {len(df)} articles → {out}")

        # 顶刊子集 (NIBS + disease + top journals)
        if cfg.use_top_journals:
            journal_q = build_journal_query()
            top_query = f"({query}) AND {journal_q}"
            df_top = client.search(top_query)
            out_top = self.data_dir / f"pubmed_top_{cfg.name}.csv"
            client.save(df_top, str(out_top))
            print(f"[PubMed-Top] {len(df_top)} articles → {out_top}")

    # ─── Step 3b: Fetch PubMed burden (Panel A) ──
    def fetch_pubmed_burden(self):
        cfg = self.cfg
        if not cfg.burden_query:
            print("[PubMed-Burden] 跳过: burden_query 为空")
            return
        client = PubMedClient()
        df = client.search(cfg.burden_query)
        out = self.data_dir / f"pubmed_burden_{cfg.name}.csv"
        client.save(df, str(out))
        print(f"[PubMed-Burden] {len(df)} articles → {out}")

    # ─── Step 3c: Fetch Applicant publications ──
    def fetch_applicant(self):
        """检索申请人文献 (全部 → 疾病相关 → NIBS相关)"""
        cfg = self.cfg
        applicant_cfg = cfg.applicant

        # 解析 applicant 配置
        if applicant_cfg is None:
            print("[Applicant] 跳过: 未配置 applicant")
            return
        if isinstance(applicant_cfg, dict):
            applicant_cfg = ApplicantConfig.from_dict(applicant_cfg)

        if not applicant_cfg.name_en:
            print("[Applicant] 跳过: name_en 为空")
            return

        client = ApplicantClient()

        # 构建疾病和NIBS正则 (用于本地过滤)
        # 从 gap_patterns 获取，或使用 disease_en_query 作为简单正则
        disease_pattern = cfg.disease_en_query  # 简化：直接用检索式作为正则
        nibs_pattern = cfg.intervention_pattern_en or NIBS_PATTERN_EN

        # 也保留API检索式 (如果需要更精确的结果)
        disease_query = cfg.disease_en_query
        nibs_query = cfg.intervention_query_en or NIBS_QUERY_EN

        result = client.search(
            config=applicant_cfg,
            disease_query=disease_query,
            nibs_query=nibs_query,
            disease_pattern=disease_pattern,
            nibs_pattern=nibs_pattern,
            use_local_filter=True,  # 使用本地过滤更快
        )

        client.save(result, self.data_dir)
        print(f"[Applicant] {applicant_cfg.name_cn}: 全部={result.n_total}, "
              f"疾病={result.n_disease}, NIBS={result.n_nibs}, "
              f"疾病+NIBS={result.n_disease_nibs}")

    # ─── Step 4: Fetch NIH ──────────────────────
    def fetch_nih(self):
        cfg = self.cfg
        client = NIHClient()

        # NIBS + disease
        nibs_q = cfg.intervention_query_en or NIBS_QUERY_EN
        query_nibs = f"{nibs_q} AND {cfg.disease_en_query}"
        df_nibs = client.search(query_nibs)
        out1 = self.data_dir / f"nih_nibs_{cfg.name}.csv"
        client.save(df_nibs, str(out1))
        print(f"[NIH-NIBS] {len(df_nibs)} projects → {out1}")

        # disease only (全量)
        df_all = client.search(cfg.disease_en_query)
        out2 = self.data_dir / f"nih_all_{cfg.name}.csv"
        client.save(df_all, str(out2))
        print(f"[NIH-all] {len(df_all)} projects → {out2}")

    # ─── Step 4b: Fetch NIH Publications ────────
    def fetch_nih_pubs(self):
        cfg = self.cfg
        nibs_file = None
        for ext in ['.csv.gz', '.parquet', '.csv']:
            p = self.data_dir / f"nih_nibs_{cfg.name}{ext}"
            if p.exists():
                nibs_file = p
                break
        if not nibs_file:
            print(f"[NIH-Pubs] 跳过: nih_nibs 不存在，请先运行 fetch_nih()")
            return
        df_nibs = pd.read_csv(nibs_file, low_memory=False)
        # Convert to core_project_num: 5R01MH112189-05 → R01MH112189
        raw_nums = df_nibs["project_num"].dropna().unique().tolist()
        core_nums = list({re.sub(r'^\d+', '', re.sub(r'-\d+\w*$', '', n)) for n in raw_nums})
        print(f"[NIH-Pubs] 提取 {len(core_nums)} 个项目 (从 {len(raw_nums)} 条去重) 的 publications ...")

        client = NIHClient()
        pubmed = PubMedClient()
        link_df, full_df = client.fetch_publications_full(core_nums, pubmed)

        out_link = self.data_dir / f"nih_pubs_link_{cfg.name}.csv"
        out_full = self.data_dir / f"nih_pubs_full_{cfg.name}.csv"
        client.save(link_df, str(out_link))
        client.save(full_df, str(out_full))
        print(f"[NIH-Pubs] link={len(link_df)}, full={len(full_df)}")

    # ─── Step 4c: Fetch NIH Intramural Annual Reports ──
    def fetch_intramural(self, years: list[int] | None = None):
        cfg = self.cfg
        # Try csv.gz first, then csv, then legacy names
        nih_file = None
        for name in [f"nih_{cfg.name}", f"nih_nibs_{cfg.name}"]:
            for ext in ['.csv.gz', '.csv']:
                p = self.data_dir / (name + ext)
                if p.exists():
                    nih_file = p
                    break
            if nih_file:
                break
        if not nih_file:
            for fallback in ["nih_scz_all.csv.gz", "nih_scz_all.csv", "nih_tms_scz.csv.gz", "nih_tms_scz.csv"]:
                p = self.data_dir / fallback
                if p.exists():
                    nih_file = p
                    break
        if not nih_file:
            print(f"[Intramural] 跳过: 无 NIH 数据文件")
            return
        df_nih = pd.read_csv(nih_file, low_memory=False)
        # Filter intramural projects by activity_code (ZIA, Z01)
        intramural_codes = {'ZIA', 'Z01'}
        if 'activity_code' in df_nih.columns:
            intramural = df_nih[
                df_nih['activity_code'].isin(intramural_codes)
            ]['project_num'].dropna().unique().tolist()
        else:
            # Fallback: match ZIA/Z01 prefix in project_num
            intramural = df_nih[
                df_nih['project_num'].str.contains(r'Z(?:IA|01)', na=False, regex=True)
            ]['project_num'].dropna().unique().tolist()
        # Extract core_project_num: 1ZIAMH002652-17 → ZIAMH002652
        import re
        cores = list({re.sub(r'^\d+', '', re.sub(r'-\d+\w*$', '', p)) for p in intramural})
        if not cores:
            print("[Intramural] 无 intramural 项目，跳过")
            return
        print(f"[Intramural] 找到 {len(cores)} 个 intramural 项目")

        client = IntramuralClient()
        df = client.fetch(cores, years=years)
        out = self.data_dir / f"nih_intramural_{cfg.name}.csv"
        client.save(df, str(out))

    # ─── Step 5: Merge NSFC ─────────────────────
    def merge_nsfc(self):
        cfg = self.cfg
        letpub = self.data_dir / f"nsfcfund_{cfg.disease_cn_keyword}_all.xlsx"
        kd = self.data_dir / f"nsfc_kd_{cfg.name}.csv"
        output = self.data_dir / f"nsfc_merged_{cfg.name}.xlsx"
        merge_nsfc_sources(str(letpub), str(kd), str(output))
        print(f"[Merge] → {output}")

    # ─── Step 6a: Load data ─────────────────────
    def load_data(self):
        cfg = self.cfg
        d = self.data_dir

        # Fallback: also look in legacy data_dir (for old flat layout)
        fallback_dir = self._legacy_data_dir if self.layout else None

        def _search_dirs(filename):
            """Search data_dir first, then fallback dir.
            For .csv candidates, try .csv.gz and .parquet variants first."""
            variants = [filename]
            if filename.endswith('.csv'):
                variants.insert(0, filename + '.gz')
                variants.insert(1, filename[:-4] + '.parquet')
            for fn in variants:
                for dir_ in [d] + ([fallback_dir] if fallback_dir else []):
                    p = dir_ / fn
                    if p.exists():
                        return p
            return None

        def _load_tabular(*candidates):
            for c in candidates:
                p = _search_dirs(c)
                if p:
                    s = str(p)
                    if s.endswith('.parquet'):
                        return pd.read_parquet(p)
                    return pd.read_csv(p, low_memory=False)  # handles .csv and .csv.gz
            raise FileNotFoundError(f"None found: {candidates}")

        def _load_excel(*candidates):
            for c in candidates:
                p = _search_dirs(c)
                if p:
                    return pd.read_excel(p)
            raise FileNotFoundError(f"None found: {candidates}")

        # NSFC (cleaned) — optional, may not exist for new projects
        try:
            self.nsfc = _load_excel(
                f"nsfc_{cfg.disease_cn_filter}_clean.xlsx",
                f"nsfc_merged_{cfg.name}.xlsx",
            )
            self.nsfc = create_search_text(self.nsfc, ['项目标题', '中文关键词', '申请摘要', '结题摘要'])
        except FileNotFoundError:
            print("[Load] NSFC 数据不存在，跳过")
            self.nsfc = None

        # NIH all
        self.nih_all = _load_tabular(
            f"nih_all_{cfg.name}.csv",
            f"nih_scz_all.csv",
        )
        self.nih_all = create_search_text(self.nih_all, ['title', 'terms', 'abstract'])

        # NIH NIBS subset
        self.nih_nibs = _load_tabular(
            f"nih_nibs_{cfg.name}.csv",
            f"nih_tms_scz.csv",
        )
        self.nih_nibs = create_search_text(self.nih_nibs, ['title', 'terms', 'abstract'])

        # PubMed
        self.pubmed = _load_tabular(
            f"pubmed_nibs_{cfg.name}.csv",
            f"pubmed_tms_scz.csv",
        )
        self.pubmed = create_search_text(self.pubmed, ['title', 'abstract', 'mesh', 'keywords'])
        if 'journal' in self.pubmed.columns:
            self.pubmed = tag_top_journals(self.pubmed)

        # PubMed burden (optional, for Panel A)
        self.pubmed_burden = None
        burden_p = _search_dirs(f"pubmed_burden_{cfg.name}.csv")
        if burden_p:
            self.pubmed_burden = pd.read_csv(burden_p, low_memory=False)

        # PubMed top journal subset (optional, for Panel H)
        self.pubmed_top = None
        top_p = _search_dirs(f"pubmed_top_{cfg.name}.csv")
        if top_p:
            self.pubmed_top = pd.read_csv(top_p, low_memory=False)

        print(f"[Load] NSFC={len(self.nsfc) if self.nsfc is not None else 'N/A'}, NIH-all={len(self.nih_all)}, "
              f"NIH-NIBS={len(self.nih_nibs)}, PubMed={len(self.pubmed)}"
              f"{f', Burden={len(self.pubmed_burden)}' if self.pubmed_burden is not None else ''}"
              f"{f', Top={len(self.pubmed_top)}' if self.pubmed_top is not None else ''}")

    # ─── Step 6b: Classify ──────────────────────
    def classify(self):
        cfg = self.cfg

        # NSFC
        if self.nsfc is not None:
            nsfc_clf = TextClassifier(NSFC_NEURO_CATEGORIES)
            self.nsfc['category'] = nsfc_clf.classify(self.nsfc['text'])
            self.nsfc['cat_merged'] = TextClassifier.merge_categories(
                self.nsfc['category'], cfg.nsfc_merge_map)

        # NIH
        nih_clf = TextClassifier(NIH_NEURO_CATEGORIES)
        self.nih_all['category'] = nih_clf.classify(self.nih_all['text'])
        self.nih_all['cat_merged'] = TextClassifier.merge_categories(
            self.nih_all['category'], cfg.nih_to_zh_map)

        print("[Classify] done")

    # ─── Step 6c: Analyze gaps ──────────────────
    def analyze_gaps(self) -> dict:
        cfg = self.cfg

        # Aspect counts
        symptom_clf = AspectClassifier(cfg.symptoms)
        target_clf = AspectClassifier(cfg.targets)
        pubmed_targets = target_clf.count(self.pubmed['text'])
        pubmed_symptoms = symptom_clf.count(self.pubmed['text'])

        # Heatmap (may use different labels than main symptoms/targets)
        hm_symp = AspectClassifier(cfg.heatmap_symptoms or cfg.symptoms)
        hm_targ = AspectClassifier(cfg.heatmap_targets or cfg.targets)
        heatmap_df = hm_symp.build_matrix(self.pubmed['text'], hm_symp, hm_targ)
        hm_symptom_counts = hm_symp.count(self.pubmed['text'])
        hm_target_counts = hm_targ.count(self.pubmed['text'])

        # Gap counts
        gap_analyzer = GapAnalyzer(cfg.gap_patterns)

        # Compute individual gap counts via combinations + direct regex
        gaps = {}
        # PubMed: OFC in NIBS+disease corpus
        ofc_pat = cfg.gap_patterns.get('ofc', '')
        if ofc_pat:
            gaps['PubMed_OFC_TMS'] = self.pubmed['text'].str.contains(
                ofc_pat, flags=re.I, na=False).sum()
        # PubMed combos
        if 'PubMed_OFC_Neg' in cfg.gap_combinations:
            gaps['PubMed_OFC_Neg'] = gap_analyzer.count_combinations(
                self.pubmed['text'], {'x': cfg.gap_combinations['PubMed_OFC_Neg']})['x']
        gaps['PubMed_total'] = len(self.pubmed)

        # NIH combos
        for combo_name in ['NIH_OFC', 'NIH_Neg', 'NIH_OFC_Neg']:
            if combo_name in cfg.gap_combinations:
                gaps[combo_name] = gap_analyzer.count_combinations(
                    self.nih_nibs['text'], {'x': cfg.gap_combinations[combo_name]})['x']
        gaps['NIH_total'] = len(self.nih_nibs)

        # NSFC direct regex
        if self.nsfc is not None:
            if ofc_pat:
                gaps['NSFC_OFC'] = self.nsfc['text'].str.contains(
                    ofc_pat, flags=re.I, na=False).sum()
            tms_cn = cfg.gap_patterns.get('tms_cn', NIBS_PATTERN_CN)
            gaps['NSFC_TMS'] = self.nsfc['text'].str.contains(
                tms_cn, flags=re.I, na=False).sum()
            if 'NSFC_OFC_TMS' in cfg.gap_combinations:
                gaps['NSFC_OFC_TMS'] = gap_analyzer.count_combinations(
                    self.nsfc['text'], {'x': cfg.gap_combinations['NSFC_OFC_TMS']})['x']
            neg_cn = cfg.gap_patterns.get('neg_cn', '')
            if neg_cn:
                gaps['NSFC_Neg'] = self.nsfc['text'].str.contains(
                    neg_cn, flags=re.I, na=False).sum()
            gaps['NSFC_total'] = len(self.nsfc)

        # Burden yearly (Panel A)
        burden_yearly = None
        if self.pubmed_burden is not None and 'year' in self.pubmed_burden.columns:
            burden_yearly = self.pubmed_burden.groupby('year').size()

        # OFC yearly from pubmed (Panel B)
        ofc_yearly = None
        ofc_pat = cfg.gap_patterns.get('ofc', '')
        if ofc_pat and 'year' in self.pubmed.columns:
            ofc_mask = self.pubmed['text'].str.contains(ofc_pat, flags=re.I, na=False)
            ofc_yearly = self.pubmed[ofc_mask].groupby('year').size()

        # Top journal stats (Panel H)
        top_journal_stats = None
        if 'top_journal' in self.pubmed.columns:
            top_journal_stats = self.pubmed.groupby(
                ['year', 'top_journal']).size().unstack(fill_value=0)

        print(f"[Gaps] {gaps}")
        return {
            'gaps': gaps,
            'pubmed_targets': pubmed_targets,
            'pubmed_symptoms': pubmed_symptoms,
            'heatmap_df': heatmap_df,
            'hm_symptom_counts': hm_symptom_counts,
            'hm_target_counts': hm_target_counts,
            'burden_yearly': burden_yearly,
            'ofc_yearly': ofc_yearly,
            'top_journal_stats': top_journal_stats,
        }

    def extract_key_papers(self, max_papers: int = 8) -> list[dict]:
        """
        自动从 PubMed 数据中提取关键文献 (靶点+症状交集).

        返回符合 YAML key_papers 格式的列表，可直接用于 Panel E.
        """
        cfg = self.cfg
        if self.pubmed is None or self.pubmed.empty:
            return []

        # 获取靶点和症状模式
        target_patterns = list(cfg.targets.values()) if cfg.targets else []
        symptom_patterns = list(cfg.symptoms.values()) if cfg.symptoms else []

        if not target_patterns or not symptom_patterns:
            return []

        # 合并为单个正则
        target_re = re.compile('|'.join(target_patterns), re.I)
        symptom_re = re.compile('|'.join(symptom_patterns), re.I)

        # 筛选交集文献
        def match_both(row):
            text = f"{row.get('title', '')} {row.get('abstract', '')}"
            return bool(target_re.search(text)) and bool(symptom_re.search(text))

        matches = self.pubmed[self.pubmed.apply(match_both, axis=1)].copy()

        if matches.empty:
            print(f"[KeyPapers] 未找到靶点+症状交集文献")
            return []

        # 按年份排序
        matches = matches.sort_values('year', ascending=False)

        # 提取关键信息
        key_papers = []
        for _, row in matches.head(max_papers).iterrows():
            authors = row.get('authors', '')
            first_author = authors.split(',')[0].strip() if authors else 'Unknown'
            title = row.get('title', '')

            # 自动生成描述
            if 'rTMS' in title or 'TMS' in title:
                desc = '靶点-TMS 干预研究'
            elif 'target' in title.lower():
                desc = '靶点定位研究'
            else:
                desc = '靶点-症状机制研究'

            paper = {
                'year': int(row['year']) if pd.notna(row.get('year')) else 2024,
                'journal': row.get('journal', 'Unknown'),
                'author': first_author,
                'desc': desc,
            }
            key_papers.append(paper)

        print(f"[KeyPapers] 提取 {len(key_papers)} 篇关键文献 (靶点+症状交集共 {len(matches)} 篇)")
        return key_papers

    # ─── Step 6c-2: Analyze Applicant ───────────
    def analyze_applicant(self) -> ApplicantProfile | None:
        """
        分析申请人前期工作基础，生成 ApplicantProfile.

        包含完整的错误处理以确保管道不会因申请人分析失败而中断。
        """
        cfg = self.cfg
        applicant_cfg = cfg.applicant

        if applicant_cfg is None:
            print("[Applicant] 跳过分析: 未配置 applicant")
            return None
        if isinstance(applicant_cfg, dict):
            try:
                applicant_cfg = ApplicantConfig.from_dict(applicant_cfg)
            except Exception as e:
                print(f"[Applicant] 配置解析失败: {e}")
                return None

        if not applicant_cfg.name_en:
            print("[Applicant] 跳过分析: name_en 为空")
            return None

        try:
            # 加载申请人文献数据
            pubs = load_applicant_pubs(self.data_dir, applicant_cfg.name_en)
            df_all = pubs.get('all', pd.DataFrame())
            df_disease = pubs.get('disease', pd.DataFrame())
            df_nibs = pubs.get('nibs', pd.DataFrame())
            df_disease_nibs = pubs.get('disease_nibs', pd.DataFrame())

            if df_all.empty:
                print(f"[Applicant] 跳过分析: 未找到 {applicant_cfg.name_en} 的文献数据")
                print(f"  提示: 请先运行 fetch_applicant() 获取数据")
                return None

            # 创建分析器 (传入别名用于更精确的作者匹配)
            analyzer = ApplicantAnalyzer(
                symptoms=cfg.symptoms,
                targets=cfg.targets,
                aliases=applicant_cfg.aliases,
            )

            profile = analyzer.analyze(
                name_cn=applicant_cfg.name_cn,
                name_en=applicant_cfg.name_en,
                df_all=df_all,
                df_disease=df_disease,
                df_nibs=df_nibs,
            )

            # 更新 disease_nibs 交集数（如果本地有更准确的数据）
            if not df_disease_nibs.empty:
                profile.n_disease_nibs = len(df_disease_nibs)

            # ORCID 交叉验证 (如果配置了 ORCID)
            if applicant_cfg.orcid:
                try:
                    verify_with_orcid(profile, df_all, applicant_cfg.orcid)
                except Exception as e:
                    print(f"[ORCID] 交叉验证失败 (非致命): {e}")

            # 领域基准排名
            apply_benchmark(profile)

            self.applicant_profile = profile

            # 打印摘要
            print(f"[Applicant] {profile.name_cn}: 总={profile.n_total}, "
                  f"疾病={profile.n_disease}, NIBS={profile.n_nibs}, "
                  f"疾病+NIBS={profile.n_disease_nibs}")
            print(f"  第一/通讯作者={profile.n_first_or_corresponding}, "
                  f"H-index≈{profile.h_index_estimate}, "
                  f"相关度={profile.relevance_score}/100")

            # 适配度 × 胜任力
            pos = get_quadrant_position(profile)
            print(f"  适配度={profile.fit_score:.1f}, "
                  f"胜任力={profile.competency_score:.1f} → {pos['label']}")

            # 期刊分级统计
            tier1 = getattr(profile, 'tier1_count', 0)
            tier2 = getattr(profile, 'tier2_count', 0)
            if tier1 > 0 or tier2 > 0:
                print(f"  顶刊={tier1}篇, 高质量期刊={tier2}篇")

            # 基准排名摘要
            ranks = profile.percentile_ranks
            if ranks:
                print(f"  基准排名: 综合P{ranks.get('total_score',0):.0f}, "
                      f"适配P{ranks.get('fit',0):.0f}, "
                      f"胜任P{ranks.get('competency',0):.0f}")

            # 主要合作者
            if profile.top_collaborators:
                top3 = ', '.join([f"{n[:15]}({c})" for n, c in profile.top_collaborators[:3]])
                print(f"  主要合作者: {top3}")

            # 保存摘要到 results/
            if self.layout:
                summary_path = self.layout.results / 'applicant_summary.txt'
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(create_profile_summary(profile))
                print(f"[Applicant] 摘要 → {summary_path}")

            return profile

        except Exception as e:
            print(f"[Applicant] 分析过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ─── Step 6d: Build plot data dict ──────────
    def build_plot_data(self, analysis: dict) -> dict:
        cfg = self.cfg
        gaps = analysis['gaps']
        pubmed_targets = analysis['pubmed_targets']
        pubmed_symptoms = analysis['pubmed_symptoms']
        heatmap_df = analysis['heatmap_df']

        display_cats = cfg.display_cats
        nsfc_yearly = self.nsfc.groupby('批准年份').size() if self.nsfc is not None else pd.Series(dtype=int)
        nih_year_cat = self.nih_all[
            self.nih_all['fiscal_year'].between(1990, 2025)
        ].groupby(['fiscal_year', 'cat_merged']).size().unstack(fill_value=0)

        symp_keys = list(heatmap_df.index)
        targ_keys = list(heatmap_df.columns)

        # Find highlight column index
        hl_target = cfg.highlight_target
        highlight_col = targ_keys.index(hl_target) if hl_target in targ_keys else -1

        # Papers: convert from list[dict] to list[tuple]
        papers = [
            (p['year'], p['journal'], p['author'], p['desc'])
            for p in cfg.key_papers
        ]

        # Gap table
        gap_table = [
            ['检索组合', 'PubMed', 'NIH', 'NSFC'],
            [f'TMS+SCZ\n(总量)', str(gaps.get('PubMed_total', '')),
             str(gaps.get('NIH_total', '')), str(gaps.get('NSFC_TMS', ''))],
            [f'OFC+TMS\n+SCZ', str(gaps.get('PubMed_OFC_TMS', '')),
             str(gaps.get('NIH_OFC', '0')), str(gaps.get('NSFC_OFC_TMS', '0'))],
            [f'OFC+Neg.\nSymptoms', str(gaps.get('PubMed_OFC_Neg', '0')),
             str(gaps.get('NIH_OFC_Neg', '0')), '0'],
            [f'Negative\nSymptoms', str(pubmed_symptoms.get('Negative', '')),
             str(gaps.get('NIH_Neg', '')), str(gaps.get('NSFC_Neg', ''))],
        ]

        period_ranges = [tuple(r) for r in cfg.period_ranges]

        return {
            'display_cats': display_cats,
            'nih_year_cat': nih_year_cat,
            'nsfc_yearly': nsfc_yearly,
            'nih_total': len(self.nih_all),
            'nsfc_total': len(self.nsfc) if self.nsfc is not None else 0,
            'nsfc': self.nsfc if self.nsfc is not None else pd.DataFrame(columns=['批准年份', 'cat_merged']),
            'cat_col': 'cat_merged',
            'period_labels': cfg.period_labels,
            'period_ranges': period_ranges,
            'heatmap': heatmap_df.values,
            'row_labels': symp_keys,
            'col_labels': targ_keys,
            'row_totals': [analysis['hm_symptom_counts'].get(k, 0) for k in symp_keys],
            'col_totals': [analysis['hm_target_counts'].get(k, 0) for k in targ_keys],
            'highlight_col': highlight_col,
            'highlight_annotation': cfg.highlight_annotation,
            'panel_a_title': cfg.panel_a_title,
            'panel_b_title': cfg.panel_b_title,
            'panel_c_title': f'C  症状×靶区 (PubMed TMS+SCZ, N={len(self.pubmed):,})',
            'panel_d_title': cfg.panel_d_title,
            'gap_table': gap_table,
            'papers': papers,
            'panel_e_title': cfg.panel_e_title,
            'panel_e_summary': cfg.panel_e_summary,
            'suptitle': cfg.suptitle or f'{cfg.title_zh}    {cfg.title_en}',
            # New panels A/B/H
            'burden_yearly': analysis.get('burden_yearly'),
            'ofc_yearly': analysis.get('ofc_yearly'),
            'top_journal_stats': analysis.get('top_journal_stats'),
            'panel_h_title': cfg.panel_h_title or 'H  顶刊发文分布',
            'milestones': cfg.key_papers,
            'pubmed_df': self.pubmed,
        }

    # ─── Step 6e: Plot ──────────────────────────
    def plot(self, data_dict: dict):
        out_dir = self.layout.figs if self.layout else self.data_dir
        if self.layout:
            self.layout.ensure_dirs()  # 确保 figs/ 存在
        output = str(out_dir / f"{self.cfg.name}_landscape")
        plotter = LandscapePlot()
        plotter.create_landscape(data_dict, output)

    # ─── Step 6f: Plot Applicant ─────────────────
    def plot_applicant(self, extended: bool = True, basic: bool = False, summary: bool = False):
        """
        生成申请人前期基础独立图.

        Args:
            extended: 生成扩展版 6-panel 图 (包含合作网络和研究轨迹) — 默认开启
            basic: 生成基础 4-panel 图 — 默认关闭 (与 extended 重复)
            summary: 生成单页摘要图 — 默认关闭 (与 extended 重复)
        """
        if self.applicant_profile is None:
            print("[Applicant] 跳过出图: 无 applicant profile")
            return

        out_dir = self.layout.figs if self.layout else self.data_dir
        if self.layout:
            self.layout.ensure_dirs()  # 确保 figs/ 存在
        output = str(out_dir / f"{self.cfg.name}_applicant")
        title = self.cfg.panel_g_title or 'G  申请人前期基础'

        plotter = LandscapePlot()

        # 基础 4-panel 图 (默认跳过，与 extended 重复)
        if basic:
            plotter.create_applicant_figure(
                profile=self.applicant_profile,
                output=output,
                symptoms=self.cfg.symptoms,
                targets=self.cfg.targets,
                title=title,
            )

        # 扩展 6-panel 图 (包含合作网络和研究轨迹) — 默认生成
        if extended:
            output_ext = str(out_dir / f"{self.cfg.name}_applicant")
            plotter.create_applicant_extended_figure(
                profile=self.applicant_profile,
                output=output_ext,
                title=title,
            )

        # 评估总览图 (象限 + 六维雷达) — 默认跳过，与 extended 重复
        if summary:
            try:
                output_summary = str(out_dir / f"{self.cfg.name}_applicant")
                plotter.create_applicant_summary_figure(
                    profile=self.applicant_profile,
                    output=output_summary,
                    title='申请人适配度与胜任力评估',
                )
            except Exception as e:
                print(f"[Applicant] 评估总览图生成失败 (非致命): {e}")

        # 生成 Markdown 报告（用人可读的课题名称，避免 config repr 乱码）
        from scripts.analyze_applicant import save_markdown_report
        topic_name = getattr(self.cfg, 'title_zh', None) or self.cfg.name
        report_path = str(out_dir / f"{self.cfg.name}_applicant_report.md")
        save_markdown_report(self.applicant_profile, report_path, topic_name=topic_name)
        # 同时保存到 results/，便于按申请人命名（如 胡强 → Qiang_Hu_report.md）
        if self.layout and self.cfg.applicant:
            app = self.cfg.applicant
            name_en = app.name_en if hasattr(app, 'name_en') else getattr(app, 'name_en', '')
            if name_en:
                slug = name_en.replace(' ', '_')
                results_report = self.layout.results / f"{slug}_report.md"
                save_markdown_report(self.applicant_profile, str(results_report), topic_name=topic_name)
                print(f"[Applicant] 报告 → {results_report}")

    # ─── Phase 1: Performance Analysis ──────────
    def analyze_performance(self) -> dict:
        """PI/机构排名、Bradford定律、资金趋势、新兴PI"""
        perf = PerformanceAnalyzer(self.nsfc, self.nih_all)
        result = {
            'top_pis': perf.top_pis(),
            'top_institutions': perf.top_institutions(),
            'bradford_nsfc': perf.bradford_zones('nsfc'),
            'bradford_nih': perf.bradford_zones('nih'),
            'funding_trends': perf.funding_trends(),
            'emerging_pis': perf.emerging_pis(),
        }
        print(f"[Performance] top PIs: {len(result['top_pis'])}, "
              f"top institutions: {len(result['top_institutions'])}, "
              f"emerging PIs: {len(result['emerging_pis'])}")
        return result

    # ─── Phase 1: Quality Assessment ─────────────
    def assess_quality(self) -> dict:
        """数据完整性评估"""
        qr = QualityReporter()
        dfs = {}
        if self.nsfc is not None:
            dfs['NSFC'] = self.nsfc
        if self.nih_all is not None:
            dfs['NIH'] = self.nih_all
        if self.pubmed is not None:
            dfs['PubMed'] = self.pubmed

        result = {
            'completeness': qr.completeness_matrix(dfs),
            'summary': qr.summary(dfs),
        }
        print(f"[Quality]\n{result['summary']}")
        return result

    # ─── Phase 1: Trend Detection ────────────────
    def detect_trends(self) -> dict:
        """趋势检测: 拐点、CAGR、上升/下降类别"""
        td = TrendDetector()
        result = {}

        # NSFC yearly total inflections
        if self.nsfc is not None:
            yearly = self.nsfc.groupby('批准年份').size()
            result['nsfc_inflections'] = td.detect_inflections(yearly)

            # Per-category trends
            nsfc_long = self.nsfc[['批准年份', 'cat_merged']].rename(
                columns={'批准年份': 'year', 'cat_merged': 'category'})
            result['nsfc_cagr'] = td.growth_rates(nsfc_long)
            result['nsfc_emerging'] = td.emerging_declining(nsfc_long)

        if self.nih_all is not None:
            yearly = self.nih_all.groupby('fiscal_year').size()
            result['nih_inflections'] = td.detect_inflections(yearly)

            nih_long = self.nih_all[['fiscal_year', 'cat_merged']].rename(
                columns={'fiscal_year': 'year', 'cat_merged': 'category'})
            result['nih_cagr'] = td.growth_rates(nih_long)
            result['nih_emerging'] = td.emerging_declining(nih_long)

        emerging = result.get('nsfc_emerging', {}).get('emerging', [])
        declining = result.get('nsfc_emerging', {}).get('declining', [])
        print(f"[Trends] NSFC emerging: {[e['category'] for e in emerging]}, "
              f"declining: {[d['category'] for d in declining]}")
        return result

    # ─── Phase 1b: Supplementary Analysis ────────
    def analyze_supplementary(self) -> dict:
        """生成补充数据: NIH经费、新兴关键词、机构×靶区、主题地图"""
        from scripts.keywords import KeywordAnalyzer, STOPWORDS_EN
        from scripts.network import ConceptNetwork

        result = {}

        # a) NIH funding by category
        perf = PerformanceAnalyzer(nih_df=self.nih_all)
        funding_all = perf.funding_trends()
        result['nih_funding'] = funding_all[funding_all['source'] == 'NIH']

        # b) Emerging keywords from PubMed
        kw = KeywordAnalyzer()
        emerging = kw.emerging_keywords(
            self.pubmed, col='mesh', year_col='year',
            recent_years=3, min_count=5, lang='en')
        result['emerging_kw'] = emerging

        # c) Institution × target matrix (NIH NIBS)
        # For each target, check which NIH NIBS projects match
        from scripts.analyze import AspectClassifier
        targ_clf = AspectClassifier(self.cfg.targets)

        # Get top-15 institutions by project count
        top_inst = self.nih_nibs.groupby('org').size().nlargest(15).index
        subset = self.nih_nibs[self.nih_nibs['org'].isin(top_inst)].copy()

        # For each target, mark projects that match
        target_names = list(self.cfg.targets.keys())
        for tname, tpat in self.cfg.targets.items():
            subset[tname] = subset['text'].str.contains(tpat, flags=re.I, na=False).astype(int)

        # Cross-tab: institution × target
        matrix = subset.groupby('org')[target_names].sum()
        # Reorder by total
        matrix['_total'] = matrix.sum(axis=1)
        matrix = matrix.sort_values('_total', ascending=False).drop('_total', axis=1)
        result['inst_target_matrix'] = matrix

        # d) Thematic map from PubMed
        cn = ConceptNetwork()
        G = cn.from_keywords(self.pubmed, col='mesh', lang='en',
                              min_freq=5, stopwords=STOPWORDS_EN)
        thematic_df = cn.thematic_map(G)
        result['thematic_map'] = thematic_df

        print(f"[Supplementary] NIH funding: {len(result['nih_funding'])} rows, "
              f"Emerging keywords: {len(result['emerging_kw'])}, "
              f"Inst×Target: {matrix.shape}, Thematic: {len(thematic_df)}")
        return result

    def plot_supplementary(self, supp_data: dict):
        """生成补充图"""
        out_dir = self.layout.figs if self.layout else self.data_dir
        output = str(out_dir / f"{self.cfg.name}_supplementary")
        plotter = LandscapePlot()
        plotter.create_supplementary_figure(
            supp_data, output,
            display_cats=self.cfg.display_cats,
            highlight_target=self.cfg.highlight_target)

    # ─── Manifest & Results ────────────────────
    def _save_manifest(self):
        """YAML副本 + manifest.json → parameters/"""
        if not self.layout:
            return
        # Copy config YAML (skip if already in parameters/)
        if self._config_path and self._config_path.exists():
            dest = self.layout.parameters / self._config_path.name
            if self._config_path.resolve() != dest.resolve():
                shutil.copy2(self._config_path, dest)
        # Write manifest
        manifest = {
            'created': datetime.now().isoformat(),
            'config': self._config_path.name if self._config_path else None,
            'project_dir': self.cfg.project_dir,
            'name': self.cfg.name,
        }
        with open(self.layout.parameters / 'manifest.json', 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        # Scripts: record how to reproduce this run
        import sys
        config_rel = self._config_path.name if self._config_path else '?'
        reproduce = {
            'command': ' '.join(sys.argv),
            'config_file': config_rel,
            'python': sys.executable,
            'cwd': str(Path.cwd()),
            'created': datetime.now().isoformat(),
            'steps_executed': self._run_log,
            'reproduce': f'{sys.executable} run_all.py -c {config_rel} --step 6',
        }
        with open(self.layout.scripts_meta / 'run_info.json', 'w', encoding='utf-8') as f:
            json.dump(reproduce, f, ensure_ascii=False, indent=2)
        print(f"[Manifest] → {self.layout.parameters}")

    def save_results(self, analysis: dict):
        """Gap/heatmap/counts CSV → results/"""
        if not self.layout:
            return
        out = self.layout.results
        # Gap counts
        gaps = analysis.get('gaps', {})
        if gaps:
            pd.DataFrame([gaps]).to_csv(out / 'gap_counts.csv', index=False)
        # Heatmap
        hm = analysis.get('heatmap_df')
        if hm is not None:
            hm.to_csv(out / 'heatmap.csv')
        # Target/symptom counts
        for key in ['pubmed_targets', 'pubmed_symptoms']:
            counts = analysis.get(key)
            if counts:
                pd.Series(counts, name='count').to_csv(out / f'{key}.csv')
        print(f"[Results] → {out}")

    # ─── NSFC 标书支撑报告 ────────────────────
    def generate_nsfc_report(self, analysis: dict | None = None) -> Path | None:
        """
        生成 NSFC 标书支撑材料 (Markdown 格式).

        包含:
        - 研究空白客观证据
        - 申请人前期基础
        - 关键文献列表
        - 创新性与可行性论证要点
        """
        if not self.layout:
            return None

        from datetime import datetime

        cfg = self.cfg
        profile = self.applicant_profile
        out = self.layout.results

        import re

        # 基础统计
        n_pubmed = len(self.pubmed) if self.pubmed is not None else 0
        n_nih = len(self.nih_nibs) if self.nih_nibs is not None else 0
        n_nsfc = len(self.nsfc) if self.nsfc is not None else 0

        # 靶点名称 (中英文映射)
        target_name = list(cfg.targets.keys())[0] if cfg.targets else 'Target'
        symptom_key = list(cfg.symptoms.keys())[0] if cfg.symptoms else 'Symptom'

        # 获取正则模式
        target_pattern = list(cfg.targets.values())[0] if cfg.targets else ''
        symptom_pattern = list(cfg.symptoms.values())[0] if cfg.symptoms else ''

        # 直接计算空白统计
        def count_matches(df, pattern):
            if df is None or df.empty or not pattern:
                return 0
            return df['text'].str.contains(pattern, flags=re.I, na=False).sum()

        def count_intersection(df, pat1, pat2):
            if df is None or df.empty or not pat1 or not pat2:
                return 0
            m1 = df['text'].str.contains(pat1, flags=re.I, na=False)
            m2 = df['text'].str.contains(pat2, flags=re.I, na=False)
            return (m1 & m2).sum()

        # PubMed 空白统计
        n_target_tms = count_matches(self.pubmed, target_pattern)
        n_target_symptom = count_intersection(self.pubmed, target_pattern, symptom_pattern)
        n_symptom = count_matches(self.pubmed, symptom_pattern)

        # 症状中文名称映射
        symptom_cn_map = {
            'Negative': '阴性症状', 'Positive': '阳性症状', 'Cognitive': '认知功能',
            'Anhedonia': '快感缺失', 'Depression': '抑郁', 'Anxiety': '焦虑',
            'Motor': '运动症状', 'Sleep': '睡眠障碍', 'Social': '社交功能',
            'Craving': '渴求', 'Relapse': '复发', 'Withdrawal': '戒断',
        }
        symptom_name = symptom_cn_map.get(symptom_key, symptom_key)

        # 报告标题
        disease_cn = cfg.disease_cn_keyword or cfg.name
        intervention = 'rTMS' if 'TMS' in (cfg.intervention_query_en or '') else 'NIBS'

        report = f"""# {target_name}-{intervention} 治疗{disease_cn}{symptom_name}
## 创新性论证支撑材料

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据来源: PubMed ({n_pubmed}篇), NIH Reporter ({n_nih}项), NSFC ({n_nsfc}项)

---

## 一、研究空白的客观证据

### 1.1 数据概览

| 数据源 | 检索范围 | 记录数 |
|--------|----------|--------|
| PubMed | {intervention} + {disease_cn} | {n_pubmed} 篇 |
| NIH Reporter | {intervention} + {disease_cn} | {n_nih} 项 |
| NSFC | {intervention} + {disease_cn} | {n_nsfc} 项 |

### 1.2 核心空白

| 检索条件 | PubMed |
|----------|--------|
| {target_name} + {intervention} | {n_target_tms} 篇 |
| {target_name} + {symptom_name} | {n_target_symptom} 篇 |
| {symptom_name}相关 | {n_symptom} 篇 |

**结论**: {target_name} + {symptom_name}交叉领域仅 **{n_target_symptom} 篇** — 明确的研究空白。

"""
        # 关键文献 (key_papers)
        if cfg.key_papers:
            report += f"""### 1.3 关键文献 ({target_name} + {symptom_name} 交集)

"""
            for i, paper in enumerate(cfg.key_papers[:8], 1):
                year = paper.get('year', '')
                journal = paper.get('journal', '')
                author = paper.get('author', '')
                desc = paper.get('desc', '')
                report += f"{i}. [{year}] **{journal}** — {author}\n   _{desc}_\n"
            report += "\n"

        report += """---

## 二、申请人前期基础

"""
        if profile:
            # 基本信息
            year_range = f"{profile.year_range[0]}-{profile.year_range[1]}" if profile.year_range else 'N/A'

            report += f"""### 2.1 发表统计

| 类别 | 数量 |
|------|------|
| 全部发表 | {profile.n_total} 篇 |
| {disease_cn}相关 | {profile.n_disease} 篇 |
| NIBS相关 | {profile.n_nibs} 篇 |
| 疾病+NIBS交叉 | {profile.n_disease_nibs} 篇 |
| 第一/通讯作者 | {profile.n_first_or_corresponding} 篇 |
| 顶刊 | {profile.tier1_count} 篇 |
| 高质量期刊 | {profile.tier2_count} 篇 |

### 2.2 综合评分

| 维度 | 得分 | 百分位 |
|------|------|--------|
| 适配度 | {profile.fit_score:.1f}/100 | P{int(profile.fit_score * 0.9)} |
| 胜任力 | {profile.competency_score:.1f}/100 | P{int(profile.competency_score * 0.9)} |
| 综合评分 | {profile.relevance_score:.1f}/100 | P{int(profile.relevance_score * 0.9)} |
| 象限 | {'明星申请人' if profile.fit_score > 60 and profile.competency_score > 50 else '潜力申请人'} | — |

### 2.3 代表性论文

"""
            for i, paper in enumerate(profile.key_papers[:5], 1):
                year = paper.get('year', '')
                journal = paper.get('journal', '')
                title = paper.get('title', '')[:60]
                report += f"{i}. [{year}] **{journal}** - {title}...\n"

            # 研究轨迹
            if profile.research_trajectory:
                report += "\n### 2.4 研究轨迹\n\n"
                for period, keywords in profile.research_trajectory.items():
                    kw_str = ', '.join(keywords[:5])
                    report += f"- **{period}**: {kw_str}\n"

            # 主要合作者
            if profile.top_collaborators:
                report += "\n### 2.5 核心合作网络\n\n"
                report += "| 合作者 | 合作次数 |\n|--------|----------|\n"
                for name, count in profile.top_collaborators[:5]:
                    report += f"| {name} | {count} |\n"
        else:
            report += "_申请人分析未配置或数据不足_\n"

        # 标书建议
        report += f"""

---

## 三、标书撰写建议

### 创新点
1. **靶点创新**: {target_name} 靶向治疗{symptom_name}，国际研究近乎空白
2. **机制创新**: 奖赏环路 ({target_name}-NAc) 角度
3. **范式创新**: "反转化"策略

### 可行性
"""
        if profile:
            report += f"""1. 团队在 {target_name}-{intervention}-{disease_cn} 领域领先
2. {profile.n_disease_nibs} 篇疾病+NIBS交叉发表
3. 综合评分 {profile.relevance_score:.1f}/100，处于 P{int(profile.relevance_score * 0.9)}
"""
        else:
            report += "1. 需补充申请人前期工作基础\n"

        report += """
---

*由 zbib 自动生成*
"""

        # 保存报告
        report_path = out / 'NSFC标书支撑材料.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"[Report] NSFC标书支撑材料 → {report_path}")
        return report_path

    # ─── Cooccurrence integration ────────────
    def run_cooccurrence(self):
        """共现分析，输出到 figs/ + results/"""
        from scripts.keywords import KeywordAnalyzer, STOPWORDS_CN, STOPWORDS_EN
        from scripts.network import ConceptNetwork

        ka = KeywordAnalyzer()
        cn = ConceptNetwork()
        plotter = LandscapePlot()
        out_figs = self.layout.figs if self.layout else self.data_dir
        out_results = self.layout.results if self.layout else self.data_dir

        # Read params from config (with backward-compatible defaults)
        cfg = self.cfg
        window = getattr(cfg, 'cooccurrence_window', 5)
        step = getattr(cfg, 'cooccurrence_step', 3)
        min_freq_cn = getattr(cfg, 'cooccurrence_min_freq_cn', 2)
        min_freq_en = getattr(cfg, 'cooccurrence_min_freq_en', 50)
        max_year = getattr(cfg, 'cooccurrence_max_year', 2024)
        extra_sw_cn = set(getattr(cfg, 'extra_stopwords_cn', []))
        extra_sw_en = set(getattr(cfg, 'extra_stopwords_en', []))
        emerging_years = getattr(cfg, 'emerging_recent_years', 3)

        sw_cn = STOPWORDS_CN | extra_sw_cn
        sw_en = STOPWORDS_EN | extra_sw_en

        # NSFC temporal networks
        if self.nsfc is not None and '中文关键词' in self.nsfc.columns:
            nsfc_temporal = cn.temporal_networks(
                self.nsfc, '中文关键词', '批准年份', window=window, step=step,
                lang='cn', min_freq=min_freq_cn, stopwords=sw_cn)
            plotter.plot_temporal_network(
                nsfc_temporal, str(out_figs / 'NSFC_共现网络演变'),
                title=f'NSFC 关键词共现网络演变 ({window}年窗口, 步长{step})')
            evo_nsfc = cn.network_evolution_summary(nsfc_temporal)
            if not evo_nsfc.empty:
                evo_nsfc.to_csv(out_results / 'nsfc_network_evolution.csv', index=False)
        else:
            nsfc_temporal, evo_nsfc = [], pd.DataFrame()

        # NIH temporal networks
        if self.nih_all is not None and 'terms' in self.nih_all.columns:
            nih_complete = self.nih_all[self.nih_all['fiscal_year'] <= max_year]
            nih_temporal = cn.temporal_networks(
                nih_complete, 'terms', 'fiscal_year', window=window, step=step,
                lang='en', min_freq=min_freq_en, stopwords=sw_en)
            plotter.plot_temporal_network(
                nih_temporal, str(out_figs / 'NIH_cooccurrence_evolution'),
                title=f'NIH Keyword Co-occurrence Network Evolution ({window}-year windows, step {step})')
            evo_nih = cn.network_evolution_summary(nih_temporal)
            if not evo_nih.empty:
                evo_nih.to_csv(out_results / 'nih_network_evolution.csv', index=False)
        else:
            nih_temporal, evo_nih = [], pd.DataFrame()

        # Thematic maps
        if nsfc_temporal:
            plotter.plot_thematic_map_temporal(
                nsfc_temporal, str(out_figs / 'NSFC_thematic_map'),
                title='NSFC 主题地图演变 (四象限)')
        if nih_temporal:
            plotter.plot_thematic_map_temporal(
                nih_temporal, str(out_figs / 'NIH_thematic_map'),
                title='NIH Thematic Map Evolution (Quadrant)')

        # Emerging keywords
        emerging_nsfc = pd.DataFrame()
        if self.nsfc is not None and '中文关键词' in self.nsfc.columns:
            emerging_nsfc = ka.emerging_keywords(
                self.nsfc, col='中文关键词', year_col='批准年份',
                recent_years=emerging_years, min_count=2, lang='cn')
            if not emerging_nsfc.empty:
                emerging_nsfc.to_csv(out_results / 'emerging_keywords_nsfc.csv', index=False)

        emerging_nih = pd.DataFrame()
        if self.nih_all is not None and 'terms' in self.nih_all.columns:
            nih_for_emerging = self.nih_all[self.nih_all['fiscal_year'] <= max_year]
            emerging_nih = ka.emerging_keywords(
                nih_for_emerging, col='terms', year_col='fiscal_year',
                recent_years=emerging_years, min_count=30, lang='en')
            if not emerging_nih.empty:
                emerging_nih.to_csv(out_results / 'emerging_keywords_nih.csv', index=False)

        if not emerging_nsfc.empty or not emerging_nih.empty:
            plotter.plot_emerging_keywords(
                emerging_nsfc, emerging_nih,
                str(out_figs / 'emerging_keywords'))

        # Keyword prediction
        nsfc_kw = ka.explode_keywords(self.nsfc, '中文关键词', year_col='批准年份', lang='cn') \
            if self.nsfc is not None and '中文关键词' in self.nsfc.columns \
            else pd.DataFrame(columns=['keyword', 'year'])
        nsfc_for_pred = nsfc_kw[nsfc_kw['year'] <= max_year] if not nsfc_kw.empty else nsfc_kw

        nih_fused = ka.explode_keywords(self.nih_all, 'terms', year_col='fiscal_year', lang='en') \
            if self.nih_all is not None and 'terms' in self.nih_all.columns \
            else pd.DataFrame(columns=['keyword', 'year'])
        nih_for_pred = nih_fused[nih_fused['year'] <= max_year] if not nih_fused.empty else nih_fused

        nsfc_top = nsfc_for_pred['keyword'].value_counts().head(30).index.tolist() if not nsfc_for_pred.empty else []
        pred_nsfc = ka.predict_trend(nsfc_for_pred, nsfc_top, forecast_years=5, min_yearly_avg=0.5)
        nih_top = nih_for_pred['keyword'].value_counts().head(30).index.tolist() if not nih_for_pred.empty else []
        pred_nih = ka.predict_trend(nih_for_pred, nih_top, forecast_years=5, min_yearly_avg=5)

        plotter.plot_keyword_prediction(pred_nsfc, pred_nih, str(out_figs / 'keyword_trend_prediction'))
        plotter.plot_evolution_summary(evo_nsfc, evo_nih, str(out_figs / 'network_evolution_summary'))

        # Keyword trajectory sparklines (top-20 keywords over time)
        wg_nsfc = ka.word_growth(self.nsfc, '中文关键词', '批准年份', top_n=20, lang='cn') \
            if self.nsfc is not None and '中文关键词' in self.nsfc.columns else None
        wg_nih = ka.word_growth(
            self.nih_all[self.nih_all['fiscal_year'] <= max_year] if self.nih_all is not None else pd.DataFrame(),
            'terms', 'fiscal_year', top_n=20, lang='en') \
            if self.nih_all is not None and 'terms' in self.nih_all.columns else None
        plotter.plot_keyword_trajectories(
            wg_nsfc, wg_nih, str(out_figs / 'keyword_trajectories'),
            title='关键词生命周期轨迹 (Top-20 Keyword Trajectories)')

        # Community evolution tracking
        if nsfc_temporal:
            plotter.plot_community_evolution(
                nsfc_temporal, str(out_figs / 'NSFC_community_evolution'),
                title='NSFC 社区主题演变追踪')
        if nih_temporal:
            plotter.plot_community_evolution(
                nih_temporal, str(out_figs / 'NIH_community_evolution'),
                title='NIH Community Theme Evolution')

        # Combined keyword dashboard (NSFC + NIH)
        plotter.plot_keyword_landscape(
            emerging_nsfc, wg_nsfc, nsfc_temporal,
            str(out_figs / 'NSFC_keyword_dashboard'),
            title='NSFC 关键词全景仪表板')
        plotter.plot_keyword_landscape(
            emerging_nih, wg_nih, nih_temporal,
            str(out_figs / 'NIH_keyword_dashboard'),
            title='NIH Keyword Landscape Dashboard')

        # Keyword heatmaps (time × keyword intensity)
        if wg_nsfc is not None and not wg_nsfc.empty:
            plotter.plot_keyword_heatmap(
                wg_nsfc, str(out_figs / 'NSFC_keyword_heatmap'),
                title='NSFC 关键词热力演变', top_n=25)
        if wg_nih is not None and not wg_nih.empty:
            plotter.plot_keyword_heatmap(
                wg_nih, str(out_figs / 'NIH_keyword_heatmap'),
                title='NIH Keyword Intensity Heatmap', top_n=25)

        # Cooccurrence matrices
        if nsfc_temporal:
            plotter.plot_cooccurrence_matrix(
                nsfc_temporal, str(out_figs / 'NSFC_cooccurrence_matrix'),
                title='NSFC 关键词共现强度矩阵', top_n=20)
        if nih_temporal:
            plotter.plot_cooccurrence_matrix(
                nih_temporal, str(out_figs / 'NIH_cooccurrence_matrix'),
                title='NIH Keyword Co-occurrence Matrix', top_n=20)

        # Keyword flow diagrams (theme continuity)
        if nsfc_temporal:
            plotter.plot_keyword_flow(
                nsfc_temporal, str(out_figs / 'NSFC_keyword_flow'),
                title='NSFC 主题社区流动图')
        if nih_temporal:
            plotter.plot_keyword_flow(
                nih_temporal, str(out_figs / 'NIH_keyword_flow'),
                title='NIH Theme Flow Diagram')

        # Research frontier detection
        if nsfc_temporal:
            plotter.plot_research_frontier(
                emerging_nsfc, nsfc_temporal,
                str(out_figs / 'NSFC_research_frontier'),
                title='NSFC 研究前沿检测')
        if nih_temporal:
            plotter.plot_research_frontier(
                emerging_nih, nih_temporal,
                str(out_figs / 'NIH_research_frontier'),
                title='NIH Research Frontier Detection')

        # Radar comparison (NSFC vs NIH category distribution)
        if self.nsfc is not None and self.nih_all is not None:
            nsfc_cats = self.nsfc['cat_merged'].value_counts().to_dict() if 'cat_merged' in self.nsfc.columns else {}
            nih_cats = self.nih_all['cat_merged'].value_counts().to_dict() if 'cat_merged' in self.nih_all.columns else {}
            if nsfc_cats and nih_cats:
                plotter.plot_radar_comparison(
                    nsfc_cats, nih_cats,
                    str(out_figs / 'NSFC_NIH_radar_comparison'),
                    title='中美研究方向对比雷达图')

        # Wordcloud evolution
        if wg_nsfc is not None and not wg_nsfc.empty:
            plotter.plot_wordcloud_evolution(
                wg_nsfc, str(out_figs / 'NSFC_wordcloud_evolution'),
                n_periods=4, title='NSFC 词云演变')
        if wg_nih is not None and not wg_nih.empty:
            plotter.plot_wordcloud_evolution(
                wg_nih, str(out_figs / 'NIH_wordcloud_evolution'),
                n_periods=4, title='NIH Wordcloud Evolution')

        print(f"[Cooccurrence] done → {out_figs}")

    # ─── Main runner ────────────────────────────
    def run(self, step: int | None = None, skip_fetch: bool = False,
            email: str = '', password: str = ''):
        """
        step=None: 跑全部
        step=6: 只跑分析+出图 (需要数据文件已存在)
        skip_fetch: 跳过爬虫步骤 (1-4), 从merge开始
        """
        def _log(name):
            self._run_log.append(f"{datetime.now().isoformat()} {name}")

        if step is None and not skip_fetch:
            print("═══ Step 1: LetPub ═══"); _log("fetch_letpub")
            self.fetch_letpub(email, password)
            print("═══ Step 2: KD ═══"); _log("fetch_kd")
            self.fetch_kd()
            print("═══ Step 3: PubMed ═══"); _log("fetch_pubmed")
            self.fetch_pubmed()
            print("═══ Step 3b: PubMed Burden ═══"); _log("fetch_pubmed_burden")
            self.fetch_pubmed_burden()
            print("═══ Step 3c: Applicant ═══"); _log("fetch_applicant")
            self.fetch_applicant()
            print("═══ Step 4: NIH ═══"); _log("fetch_nih")
            self.fetch_nih()
            print("═══ Step 4b: NIH Publications ═══"); _log("fetch_nih_pubs")
            self.fetch_nih_pubs()
            print("═══ Step 4c: NIH Intramural Reports ═══"); _log("fetch_intramural")
            self.fetch_intramural()

        if step is None or step == 5:
            if not skip_fetch:
                print("═══ Step 5: Merge ═══"); _log("merge_nsfc")
                self.merge_nsfc()

        if step is None or step >= 6:
            print("═══ Step 6: Analyze & Plot ═══"); _log("analyze_and_plot")
            self.load_data()
            self.classify()
            analysis = self.analyze_gaps()
            # Analyze applicant (if configured)
            self.analyze_applicant()
            self.save_results(analysis)

            # ─── 自动提取 key_papers (若配置为空) ───
            if not getattr(self.cfg, 'key_papers', None):
                try:
                    extracted = self.extract_key_papers(max_papers=8)
                    if extracted:
                        self.cfg.key_papers = extracted
                        print(f"[KeyPapers] 自动提取 {len(extracted)} 篇关键文献")
                except Exception as e:
                    print(f"[KeyPapers] 自动提取失败: {e}")

            data_dict = self.build_plot_data(analysis)
            # 先出申请人图与报告，再出主图（避免主图崩溃时丢失申请人结果）
            self.plot_applicant()
            try:
                self.plot(data_dict)
            except Exception as e:
                print(f"[Plot] 主全景图生成失败: {e}")
            try:
                supp_data = self.analyze_supplementary()
                self.plot_supplementary(supp_data)
            except Exception as e:
                print(f"[Plot] 补充图生成失败: {e}")

            # ─── 共现网络分析 (内置功能) ───
            try:
                print("─── 共现网络分析 ───")
                self.run_cooccurrence()
            except Exception as e:
                print(f"[Cooccurrence] 共现分析失败: {e}")

            # ─── NSFC 标书支撑报告 (内置功能) ───
            try:
                print("─── 生成标书支撑材料 ───")
                self.generate_nsfc_report(analysis)
            except Exception as e:
                print(f"[Report] 标书报告生成失败: {e}")

            self._save_manifest()
            print("═══ Done ═══")
