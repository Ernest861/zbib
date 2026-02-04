#!/usr/bin/env python3
"""quick_search.py — 交互式文献空白检索向导

交互收集用户输入 → 生成 YAML 配置 → 创建输出文件夹 → 跑 Pipeline 全流程。
"""

import argparse
import getpass
import re
from datetime import date
from pathlib import Path

import yaml

from scripts.config import TopicConfig
from scripts.pipeline import Pipeline

# ═══════════════════════════════════════════════
# 干预手段预设
# ═══════════════════════════════════════════════
INTERVENTIONS = {
    '1': {  # NIBS全部
        'label': 'NIBS全部 (TMS/tDCS/TUS/DBS/光刺激/ECT)',
        'query': '(TMS OR rTMS OR tDCS OR "brain stimulation" OR TUS OR DBS '
                 'OR "theta burst" OR ECT OR "photobiomodulation" OR PBM)',
        'cn': (r'经颅磁|TMS|rTMS|tDCS|经颅直流|经颅电|神经调控|脑刺激|磁刺激|电刺激'
               r'|DBS|深部脑|theta.?burst|TBS|超声刺激|TUS|光刺激|光调控|PBM|ECT|电休克'),
        'en': (r'transcranial magnetic|\bTMS\b|\brTMS\b|\btDCS\b|transcranial direct'
               r'|brain stimulation|transcranial ultrasound|\bTUS\b|\bDBS\b|deep brain stimul'
               r'|theta.?burst|\bECT\b|electroconvulsive|photobiomodulation|\bPBM\b'),
    },
    '2': {  # 仅TMS
        'label': '仅TMS/rTMS',
        'query': '(TMS OR rTMS OR "transcranial magnetic stimulation" OR "theta burst")',
        'cn': r'经颅磁|TMS|rTMS|磁刺激|theta.?burst|TBS',
        'en': r'transcranial magnetic|\bTMS\b|\brTMS\b|theta.?burst|\bTBS\b',
    },
}


# ─── 交互函数 ───────────────────────────────────

def prompt_credentials():
    """→ (email, password) | (None, None)。输入后立即验证登录。"""
    print("\n1. LetPub 账号（回车跳过 NSFC 步骤）")
    email = input("   邮箱: ").strip()
    if not email:
        return None, None
    password = getpass.getpass("   密码: ")

    # 立即验证
    print("   正在验证 LetPub 登录...", end="", flush=True)
    from scripts.fetch_letpub import LetPubClient
    ok = LetPubClient.verify_login(email, password)
    if ok:
        print(" ✓ 登录成功")
        return email, password
    else:
        print(" ✗ 登录失败")
        retry = input("   重试？[Y/n]: ").strip().lower()
        if retry and retry != 'y':
            print("   跳过 NSFC 步骤。")
            return None, None
        return prompt_credentials()  # 递归重试


def prompt_disease():
    """→ (cn_keyword, cn_filter, en_query)"""
    print("\n2. 疾病/研究对象")
    cn_kw = input("   中文关键词（LetPub搜索用）: ").strip()
    default_filter = cn_kw
    cn_filter = input(f"   中文过滤正则 [回车={default_filter}]: ").strip() or default_filter
    en_query = input("   英文检索式（PubMed/NIH）: ").strip()
    return cn_kw, cn_filter, en_query


def prompt_intervention():
    """→ (query_en, pattern_cn, pattern_en)"""
    print("\n3. 干预手段")
    for k, v in INTERVENTIONS.items():
        default_mark = ' ← 默认' if k == '1' else ''
        print(f"   [{k}] {v['label']}{default_mark}")
    print("   [3] 自定义")
    choice = input("   选择 [1]: ").strip() or '1'
    if choice in INTERVENTIONS:
        iv = INTERVENTIONS[choice]
        return iv['query'], iv['cn'], iv['en']
    # 自定义
    q = input("   PubMed/NIH检索式: ").strip()
    cn = input("   中文正则: ").strip()
    en = input("   英文正则: ").strip()
    return q, cn, en


def prompt_target():
    """→ (name, en_regex, cn_regex)"""
    print("\n4. 脑区靶点")
    name = input("   英文名: ").strip()
    en = input("   英文同义词正则: ").strip()
    cn = input("   中文同义词正则: ").strip()
    return name, en, cn


def prompt_symptom():
    """→ (name, en_regex, cn_regex)"""
    print("\n5. 症状维度")
    name = input("   英文名: ").strip()
    en = input("   英文同义词正则: ").strip()
    cn = input("   中文同义词正则: ").strip()
    return name, en, cn


def prompt_top_journals() -> bool:
    """→ bool: 是否额外检索顶刊子集"""
    print("\n6. 顶级期刊筛选")
    print("   额外检索 NEJM/Lancet/JAMA/Nature/Science 等顶刊子集")
    choice = input("   启用？[y/N]: ").strip().lower()
    return choice == 'y'


def prompt_applicant() -> dict | None:
    """→ 申请人配置字典或None (跳过)"""
    print("\n7. 申请人前期基础（可选）")
    print("   用于检索申请人在该领域的前期工作，论证标书'可行性'")
    skip = input("   跳过？[Y/n]: ").strip().lower()
    if skip != 'n':
        return None

    name_cn = input("   中文姓名: ").strip()
    name_en = input("   英文姓名 (PubMed检索): ").strip()
    if not name_en:
        print("   ⚠ 英文姓名为空，跳过申请人检索")
        return None

    affiliation = input("   机构 (过滤同名, 可选): ").strip()
    orcid = input("   ORCID (精准检索, 可选): ").strip()

    aliases_raw = input("   姓名变体 (逗号分隔, 可选): ").strip()
    aliases = [a.strip() for a in aliases_raw.split(',') if a.strip()] if aliases_raw else []

    return {
        'name_cn': name_cn,
        'name_en': name_en,
        'affiliation': affiliation,
        'orcid': orcid,
        'aliases': aliases,
    }


# ─── YAML 生成 ──────────────────────────────────

def _abbrev(s: str, max_len: int = 10) -> str:
    """简单缩写: 取首字母大写或截断"""
    # If already short / acronym-like, keep as-is
    if len(s) <= max_len and ' ' not in s:
        return s
    parts = s.split()
    if len(parts) >= 2:
        return ''.join(p[0].upper() for p in parts)
    return s[:max_len]


def generate_yaml(inputs: dict, yaml_path: Path):
    """根据交互输入生成完整 YAML 配置文件"""
    cn_kw = inputs['cn_keyword']
    cn_filter = inputs['cn_filter']
    en_query = inputs['en_query']
    target_name = inputs['target_name']
    target_en = inputs['target_en']
    target_cn = inputs['target_cn']
    symptom_name = inputs['symptom_name']
    symptom_en = inputs['symptom_en']
    symptom_cn = inputs['symptom_cn']
    iv_query = inputs['iv_query']
    iv_cn = inputs['iv_cn']
    iv_en = inputs['iv_en']

    disease_abbr = _abbrev(cn_kw)
    target_lower = target_name.lower()
    symptom_abbr = _abbrev(symptom_name)
    today = date.today().strftime('%Y%m%d')

    name = f"{disease_abbr}_{target_lower}_{symptom_abbr}".replace(' ', '_')
    data_dir = f"../nsfc_data/{cn_kw}_{target_name}_{symptom_abbr}_{today}"

    # Gap patterns
    gap_patterns = {
        'ofc': target_en,
        'ofc_cn': target_cn,
        'neg': symptom_en,
        'neg_cn': symptom_cn,
        'tms_cn': iv_cn,
    }

    # Standard 6 gap combinations
    gap_combinations = {
        'PubMed_OFC_Neg': ['ofc', 'neg'],
        'NIH_OFC': ['ofc'],
        'NIH_Neg': ['neg'],
        'NIH_OFC_Neg': ['ofc', 'neg'],
        'NSFC_OFC_TMS': ['ofc_cn', 'tms_cn'],
    }

    cfg = {
        'name': name,
        'title_zh': f'{cn_kw} + {target_name} + {symptom_name} 文献空白分析',
        'title_en': f'{en_query} Literature Gap Analysis',
        'disease_cn_keyword': cn_kw,
        'disease_cn_filter': cn_filter,
        'disease_en_query': en_query,
        'data_dir': data_dir,

        # 干预 (空 = 用默认 NIBS 常量)
        'intervention_query_en': iv_query,
        'intervention_pattern_cn': iv_cn,
        'intervention_pattern_en': iv_en,

        # 维度
        'symptoms': {symptom_name: f'{symptom_en}|{symptom_cn}'},
        'targets': {target_name: f'{target_en}|{target_cn}'},
        'highlight_target': target_name,

        # Gap
        'gap_patterns': gap_patterns,
        'gap_combinations': gap_combinations,

        # PubMed 顶刊
        'use_top_journals': inputs.get('use_top_journals', False),

        # Panel E 占位
        'key_papers': [],
        'panel_e_title': f'E  {target_name} + {symptom_name} 关键文献',
        'panel_e_summary': '(待填充)',
    }

    # 申请人配置 (可选)
    applicant = inputs.get('applicant')
    if applicant:
        cfg['applicant'] = applicant
        cfg['panel_g_title'] = f"G  申请人前期基础 ({applicant.get('name_cn', '')})"

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"\n[YAML] → {yaml_path}")
    return cfg


# ─── 从 input YAML 读取 ────────────────────────

def load_input_yaml(path: Path) -> dict:
    """从 input YAML 读取向导参数，返回 inputs dict + credentials。"""
    with open(path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)

    # 干预手段: 支持 preset 或自定义
    iv = raw.get('intervention', {})
    preset = str(iv.get('preset', ''))
    if preset in INTERVENTIONS:
        iv_data = INTERVENTIONS[preset]
        iv_query, iv_cn, iv_en = iv_data['query'], iv_data['cn'], iv_data['en']
    else:
        iv_query = iv.get('query', '')
        iv_cn = iv.get('cn', '')
        iv_en = iv.get('en', '')

    disease = raw.get('disease', {})
    target = raw.get('target', {})
    symptom = raw.get('symptom', {})

    inputs = dict(
        cn_keyword=disease.get('cn_keyword', ''),
        cn_filter=disease.get('cn_filter', disease.get('cn_keyword', '')),
        en_query=disease.get('en_query', ''),
        iv_query=iv_query, iv_cn=iv_cn, iv_en=iv_en,
        target_name=target.get('name', ''),
        target_en=target.get('en', ''),
        target_cn=target.get('cn', ''),
        symptom_name=symptom.get('name', ''),
        symptom_en=symptom.get('en', ''),
        symptom_cn=symptom.get('cn', ''),
        use_top_journals=raw.get('use_top_journals', False),
    )

    # 申请人配置 (可选)
    applicant = raw.get('applicant', None)
    if applicant:
        inputs['applicant'] = applicant

    letpub = raw.get('letpub', {})
    email = letpub.get('email', '') or None
    password = letpub.get('password', '') or None

    return inputs, email, password


# ─── 执行流程 (交互/YAML共用) ───────────────────

def run_pipeline(inputs: dict, email: str | None, password: str | None):
    """生成配置 YAML → 创建文件夹 → 跑 Pipeline。"""
    cn_kw = inputs['cn_keyword']
    target_name = inputs['target_name']
    symptom_name = inputs['symptom_name']

    disease_abbr = _abbrev(cn_kw)
    target_lower = target_name.lower()
    symptom_abbr = _abbrev(symptom_name)
    today = date.today().strftime('%Y%m%d')
    yaml_name = f"{disease_abbr}_{target_lower}_{symptom_abbr}_{today}.yaml"
    yaml_path = Path(__file__).parent / yaml_name

    raw_cfg = generate_yaml(inputs, yaml_path)

    # 创建输出文件夹
    data_dir = Path(raw_cfg['data_dir'])
    if not data_dir.is_absolute():
        data_dir = (Path(__file__).parent / data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"[DIR] → {data_dir}")

    # 构建 TopicConfig 并运行 Pipeline
    cfg = TopicConfig(**raw_cfg)
    pipe = Pipeline(cfg)

    if email:
        # 验证登录
        print("正在验证 LetPub 登录...", end="", flush=True)
        from scripts.fetch_letpub import LetPubClient
        if LetPubClient.verify_login(email, password):
            print(" ✓")
            pipe.run(email=email, password=password)
        else:
            print(" ✗ 登录失败，跳过 NSFC，只跑 PubMed/NIH")
            pipe.fetch_pubmed()
            pipe.fetch_nih()
            pipe.fetch_nih_pubs()
    else:
        print("\n[跳过 NSFC 爬虫，从 PubMed/NIH 开始]")
        pipe.fetch_pubmed()
        pipe.fetch_nih()
        pipe.fetch_nih_pubs()
        print("\n[提示] NSFC 数据未获取，无法运行完整分析。")
        print("  如需完整流程，请用 -i 指定含 letpub 账号的输入文件。")
        print("  或手动将 NSFC 数据放入:", data_dir)
        print(f"  然后运行: python run_all.py -c {yaml_path} --step 6")


# ─── Main ───────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='zbib 快速检索向导 — 交互式或 YAML 批量模式')
    parser.add_argument('-i', '--input', type=str, default=None,
                        help='输入参数 YAML 文件 (跳过交互问答)')
    args = parser.parse_args()

    print("═══ zbib 快速检索向导 ═══")

    if args.input:
        # ── YAML 批量模式 ──
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"✗ 文件不存在: {input_path}")
            return
        inputs, email, password = load_input_yaml(input_path)
        print(f"[读取] {input_path}")
        print(f"  疾病: {inputs['cn_keyword']} / {inputs['en_query']}")
        print(f"  靶点: {inputs['target_name']} ({inputs['target_en']})")
        print(f"  症状: {inputs['symptom_name']} ({inputs['symptom_en']})")
        print(f"  干预: {inputs['iv_query'][:60]}...")
        applicant = inputs.get('applicant')
        if applicant:
            print(f"  申请人: {applicant.get('name_cn', '')} ({applicant.get('name_en', '')})")
        print(f"  LetPub: {'有账号' if email else '跳过'}")
        run_pipeline(inputs, email, password)
    else:
        # ── 交互模式 ──
        email, password = prompt_credentials()
        cn_kw, cn_filter, en_query = prompt_disease()
        iv_query, iv_cn, iv_en = prompt_intervention()
        target_name, target_en, target_cn = prompt_target()
        symptom_name, symptom_en, symptom_cn = prompt_symptom()
        use_top = prompt_top_journals()
        applicant = prompt_applicant()

        inputs = dict(
            cn_keyword=cn_kw, cn_filter=cn_filter, en_query=en_query,
            iv_query=iv_query, iv_cn=iv_cn, iv_en=iv_en,
            target_name=target_name, target_en=target_en, target_cn=target_cn,
            symptom_name=symptom_name, symptom_en=symptom_en, symptom_cn=symptom_cn,
            use_top_journals=use_top,
        )
        if applicant:
            inputs['applicant'] = applicant

        print("\n─── 确认 ───")
        print(f"  疾病: {cn_kw} / {en_query}")
        print(f"  靶点: {target_name} ({target_en} | {target_cn})")
        print(f"  症状: {symptom_name} ({symptom_en} | {symptom_cn})")
        print(f"  干预: {iv_query[:60]}...")
        print(f"  顶刊筛选: {'是' if use_top else '否'}")
        if applicant:
            print(f"  申请人: {applicant.get('name_cn', '')} ({applicant.get('name_en', '')})")
        else:
            print(f"  申请人: 跳过")
        ok = input("\n确认并开始？[Y/n]: ").strip().lower()
        if ok and ok != 'y':
            print("已取消。")
            return
        run_pipeline(inputs, email, password)


if __name__ == '__main__':
    main()
