#!/usr/bin/env python3
"""quick_search.py — 交互式文献空白检索向导

交互收集用户输入 → 生成 YAML 配置 → 创建输出文件夹 → 跑 Pipeline 全流程。
"""

import argparse
import getpass
import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from scripts.config import TopicConfig
from scripts.pipeline import Pipeline


# ═══════════════════════════════════════════════
# 症状数据库
# ═══════════════════════════════════════════════
SYMPTOM_DB_PATH = Path(__file__).parent / 'data' / 'symptom_db.yaml'

def load_symptom_db() -> dict:
    """加载症状数据库"""
    if not SYMPTOM_DB_PATH.exists():
        return {}
    with open(SYMPTOM_DB_PATH, 'r', encoding='utf-8') as f:
        db = yaml.safe_load(f) or {}
    # 移除元数据
    db.pop('_meta', None)
    return db

def match_disease_key(disease_cn: str, disease_en: str, db: dict) -> Optional[str]:
    """根据疾病关键词匹配数据库中的疾病键"""
    # 直接匹配
    disease_lower = disease_en.lower()
    for key in db.keys():
        if key in disease_lower or disease_lower in key:
            return key

    # 中文关键词匹配
    CN_TO_KEY = {
        '精神分裂': 'schizophrenia',
        '抑郁': 'depression',
        '成瘾': 'addiction',
        '焦虑': 'anxiety',
        '强迫': 'ocd',
        '自闭': 'autism',
        '帕金森': 'parkinson',
        '中风': 'stroke',
        '卒中': 'stroke',
        '疼痛': 'pain',
        '癫痫': 'epilepsy',
    }
    for cn, key in CN_TO_KEY.items():
        if cn in disease_cn and key in db:
            return key
    return None

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
# 提示: 多个关键词用英文逗号分隔, 如: 自杀, 自伤

def prompt_credentials():
    """→ (email, password) | (None, None)。输入后立即验证登录。"""
    print("\n" + "─" * 50)
    print("[1/7] LetPub 账号")
    print("   用于检索 NSFC 国内基金项目 (可选)")
    print("   💡 直接回车跳过 NSFC 步骤")
    print("─" * 50)
    email = input("   邮箱: ").strip()
    if not email:
        print("   → 跳过 NSFC，仅检索 PubMed + NIH")
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
        if retry == 'n':
            print("   → 跳过 NSFC 步骤")
            return None, None
        return prompt_credentials()  # 递归重试


def prompt_disease():
    """→ (cn_keyword, cn_filter, en_query) 或 'BACK'"""
    print("\n" + "─" * 50)
    print("[2/7] 疾病/研究对象 (必填)")
    print("   💡 这是研究的核心主题，如：精神分裂症、抑郁症、成瘾")
    print("   💡 多个关键词用英文逗号分隔")
    print("   📝 示例: 精神分裂症")
    print("   📝 示例: 自杀, 自伤  (会分别检索)")
    print("─" * 50)
    cn_kw = input("   中文关键词 (LetPub搜索): ").strip()
    if cn_kw.lower() in BACK_COMMANDS:
        return 'BACK'
    if not cn_kw:
        print("   ⚠ 疾病关键词不能为空!")
        return prompt_disease()

    # 自动生成过滤正则
    default_filter = cn_kw.replace(', ', '|').replace(',', '|')
    print(f"   → 自动生成过滤正则: {default_filter}")
    cn_filter = input(f"   修改过滤正则? [回车确认]: ").strip() or default_filter
    if cn_filter.lower() in BACK_COMMANDS:
        return 'BACK'

    print()
    print("   💡 英文检索式用于 PubMed/NIH 检索")
    print("   📝 示例: schizophrenia")
    print("   📝 示例: (suicide[Title/Abstract]) OR (self-injury[Title/Abstract])")
    en_query = input("   英文检索式: ").strip()
    if en_query.lower() in BACK_COMMANDS:
        return 'BACK'
    if not en_query:
        print("   ⚠ 英文检索式不能为空!")
        return prompt_disease()

    return cn_kw, cn_filter, en_query


def prompt_intervention():
    """→ (query_en, pattern_cn, pattern_en) 或 'BACK'"""
    print("\n" + "─" * 50)
    print("[3/7] 干预手段 (必填)")
    print("   💡 选择研究涉及的神经调控技术")
    print("─" * 50)
    for k, v in INTERVENTIONS.items():
        default_mark = ' ← 默认' if k == '1' else ''
        print(f"   [{k}] {v['label']}{default_mark}")
    print("   [3] 自定义")
    choice = input("   选择 [1]: ").strip() or '1'
    if choice.lower() in BACK_COMMANDS:
        return 'BACK'
    if choice in INTERVENTIONS:
        iv = INTERVENTIONS[choice]
        return iv['query'], iv['cn'], iv['en']
    # 自定义
    print("   💡 自定义干预手段检索")
    q = input("   PubMed/NIH检索式: ").strip()
    if q.lower() in BACK_COMMANDS:
        return 'BACK'
    cn = input("   中文正则: ").strip()
    if cn.lower() in BACK_COMMANDS:
        return 'BACK'
    en = input("   英文正则: ").strip()
    if en.lower() in BACK_COMMANDS:
        return 'BACK'
    return q, cn, en


def prompt_target():
    """→ (name, en_regex, cn_regex) 或 (None, None, None) 或 'BACK'"""
    print("\n" + "─" * 50)
    print("[4/7] 脑区靶点 (可选)")
    print("   💡 用于热力图分析的干预靶点")
    print("   💡 直接回车跳过，将进行疾病全领域检索")
    print("   📝 示例: OFC (眶额叶), DLPFC (背外侧前额叶), TPJ (颞顶联合区)")
    print("─" * 50)
    name = input("   英文缩写 (如 OFC): ").strip()
    if name.lower() in BACK_COMMANDS:
        return 'BACK'
    if not name:
        print("   → 跳过靶点筛选")
        return None, None, None

    print(f"   💡 输入 {name} 的英文同义词，用英文逗号分隔")
    print(f"   📝 示例: orbitofrontal cortex, OFC")
    en = input("   英文同义词: ").strip()
    if en.lower() in BACK_COMMANDS:
        return 'BACK'

    print(f"   💡 输入 {name} 的中文同义词，用英文逗号分隔")
    print(f"   📝 示例: 眶额叶, 眶额皮层")
    cn = input("   中文同义词: ").strip()
    if cn.lower() in BACK_COMMANDS:
        return 'BACK'

    # 自动转换为正则
    if en:
        en = en.replace(', ', '|').replace(',', '|')
    if cn:
        cn = cn.replace(', ', '|').replace(',', '|')

    return name, en, cn


def prompt_symptom(disease_cn: str = '', disease_en: str = ''):
    """→ (name, en_regex, cn_regex) 或 (None, None, None) 或 'BACK'

    如果数据库中有该疾病的症状列表，显示供选择；否则手动输入。
    """
    print("\n" + "─" * 50)
    print("[5/7] 症状/表型维度 (可选)")
    print("   💡 用于热力图分析的症状维度")
    print("   💡 直接回车跳过")
    print("─" * 50)

    # 尝试从数据库加载该疾病的症状
    db = load_symptom_db()
    disease_key = match_disease_key(disease_cn, disease_en, db)
    symptoms = db.get(disease_key, []) if disease_key else []

    if symptoms:
        print(f"   📋 已知症状 ({disease_key}):")
        for i, s in enumerate(symptoms, 1):
            print(f"      {i}. {s['name']} — {s['cn'].split('|')[0]}")
        print(f"      0. 自定义输入")
        print()
        choice = input("   选择编号或直接回车跳过: ").strip()

        if choice.lower() in BACK_COMMANDS:
            return 'BACK'
        if not choice:
            print("   → 跳过症状维度")
            return None, None, None

        if choice.isdigit() and 1 <= int(choice) <= len(symptoms):
            selected = symptoms[int(choice) - 1]
            print(f"   → 已选择: {selected['name']}")
            return selected['name'], selected['en'], selected['cn']

        if choice == '0':
            print("   → 自定义输入模式")
        else:
            print(f"   ⚠ 无效选择，进入自定义输入模式")

    # 自定义输入模式
    print("   📝 示例: Negative (阴性症状), Cognitive (认知)")
    name = input("   英文名 (如 Negative): ").strip()
    if name.lower() in BACK_COMMANDS:
        return 'BACK'
    if not name:
        print("   → 跳过症状维度")
        return None, None, None

    print(f"   💡 输入 {name} 的英文同义词，用英文逗号分隔")
    print(f"   📝 示例: negative symptom, anhedonia, avolition")
    en = input("   英文同义词: ").strip()
    if en.lower() in BACK_COMMANDS:
        return 'BACK'

    print(f"   💡 输入 {name} 的中文同义词，用英文逗号分隔")
    print(f"   📝 示例: 阴性症状, 快感缺失")
    cn = input("   中文同义词: ").strip()
    if cn.lower() in BACK_COMMANDS:
        return 'BACK'

    # 自动转换为正则
    if en:
        en = en.replace(', ', '|').replace(',', '|')
    if cn:
        cn = cn.replace(', ', '|').replace(',', '|')

    return name, en, cn


def prompt_top_journals():
    """→ bool 或 'BACK'"""
    print("\n" + "─" * 50)
    print("[6/7] 顶级期刊筛选")
    print("   额外检索 NEJM/Lancet/JAMA/Nature/Science 等顶刊子集")
    print("─" * 50)
    choice = input("   启用？[Y/n]: ").strip().lower()
    if choice in BACK_COMMANDS:
        return 'BACK'
    return choice != 'n'  # 默认启用


def prompt_applicant():
    """→ 申请人配置字典 或 None (跳过) 或 'BACK'

    支持确认时回退修改
    """
    print("\n" + "─" * 50)
    print("[7/7] 申请人前期基础")
    print("   💡 用于检索申请人在该领域的前期工作，论证标书'可行性'")
    print("─" * 50)
    add = input("   添加申请人？[Y/n/b]: ").strip().lower()
    if add in BACK_COMMANDS:
        return 'BACK'
    if add == 'n':
        print("   → 跳过申请人分析")
        return None

    while True:  # 支持回退修改
        print()
        name_cn = input("   中文姓名 (如 张正, 或 b 返回): ").strip()
        if name_cn.lower() in BACK_COMMANDS:
            return 'BACK'
        if not name_cn:
            print("   ⚠ 姓名为空，跳过申请人分析")
            return None

        print()
        print("   ⚠ PubMed 格式: Lastname FirstInitial (如 Zhang Z)")
        print("   ⚠ 中国人姓名重复率高，建议同时填写机构或 ORCID")
        print(f"   📝 示例: Zheng Zhang 或 Z Zhang")
        name_en = input("   英文姓名: ").strip()
        if name_en.lower() in BACK_COMMANDS:
            return 'BACK'
        if not name_en:
            print("   ⚠ 英文姓名为空，跳过申请人检索")
            return None

        print()
        print("   💡 机构用于过滤同名作者 (强烈建议填写)")
        print("   📝 示例: Shanghai Mental Health Center")
        affiliation = input("   机构: ").strip()
        if affiliation.lower() in BACK_COMMANDS:
            return 'BACK'

        print()
        print("   💡 ORCID 可精准识别作者，避免重名问题 (推荐)")
        print("   📝 示例: 0000-0001-2345-6789")
        print("   📝 查询: https://orcid.org/orcid-search/search")
        orcid = input("   ORCID: ").strip()
        if orcid.lower() in BACK_COMMANDS:
            return 'BACK'

        print()
        print("   💡 姓名变体用于匹配不同写法，用英文逗号分隔 (可选)")
        print("   📝 示例: Z Zhang, Zhang Z, Zhang Zheng")
        aliases_raw = input("   姓名变体: ").strip()
        if aliases_raw.lower() in BACK_COMMANDS:
            return 'BACK'
        aliases = [a.strip() for a in aliases_raw.split(',') if a.strip()] if aliases_raw else []

        # ─── 确认或修改 ───
        print()
        print("   ─── 申请人信息确认 ───")
        print(f"   中文姓名: {name_cn}")
        print(f"   英文姓名: {name_en}")
        print(f"   机构: {affiliation or '(未填)'}")
        print(f"   ORCID: {orcid or '(未填)'}")
        print(f"   姓名变体: {', '.join(aliases) if aliases else '(无)'}")

        if not affiliation and not orcid:
            print()
            print("   ⚠ 警告: 未填机构和 ORCID，可能匹配到大量同名作者!")

        print()
        confirm = input("   确认？[Y/n/r/b] (r=重新输入, b=返回上一步): ").strip().lower()
        if confirm in BACK_COMMANDS:
            return 'BACK'
        if confirm == 'n':
            print("   → 跳过申请人分析")
            return None
        if confirm == 'r':
            print("   → 重新输入...")
            continue  # 回到 while 循环开头

        # 确认通过
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
    """根据交互输入生成完整 YAML 配置文件

    支持可选的 target 和 symptom — 当为空时生成疾病全领域检索配置
    """
    cn_kw = inputs['cn_keyword']
    cn_filter = inputs['cn_filter']
    en_query = inputs['en_query']
    target_name = inputs.get('target_name') or ''
    target_en = inputs.get('target_en') or ''
    target_cn = inputs.get('target_cn') or ''
    symptom_name = inputs.get('symptom_name') or ''
    symptom_en = inputs.get('symptom_en') or ''
    symptom_cn = inputs.get('symptom_cn') or ''
    iv_query = inputs['iv_query']
    iv_cn = inputs['iv_cn']
    iv_en = inputs['iv_en']

    disease_abbr = _abbrev(cn_kw)
    today = date.today().strftime('%Y%m%d')

    # 根据有无 target/symptom 生成不同的命名
    name_parts = [disease_abbr]
    if target_name:
        name_parts.append(target_name.lower())
    if symptom_name:
        name_parts.append(_abbrev(symptom_name))
    name = '_'.join(name_parts).replace(' ', '_')

    # 项目目录命名 (不含 projects/ 前缀，Pipeline 会自动加)
    dir_parts = [cn_kw]
    if target_name:
        dir_parts.append(target_name)
    if symptom_name:
        dir_parts.append(_abbrev(symptom_name))
    # 如果有申请人，加入申请人名字
    applicant = inputs.get('applicant')
    if applicant and applicant.get('name_cn'):
        dir_parts.append(applicant['name_cn'])
    dir_parts.append(today)
    project_dir = '_'.join(dir_parts)  # 只是目录名，不含 projects/ 前缀

    # Gap patterns — 只添加有值的
    gap_patterns = {'tms_cn': iv_cn}
    if target_en:
        gap_patterns['target'] = target_en
        gap_patterns['target_cn'] = target_cn
    if symptom_en:
        gap_patterns['symptom'] = symptom_en
        gap_patterns['symptom_cn'] = symptom_cn

    # Gap combinations — 根据有无 target/symptom 动态生成
    gap_combinations = {}
    if target_en and symptom_en:
        gap_combinations['PubMed_Target_Symptom'] = ['target', 'symptom']
        gap_combinations['NIH_Target_Symptom'] = ['target', 'symptom']
    if target_en:
        gap_combinations['NIH_Target'] = ['target']
        gap_combinations['NSFC_Target_TMS'] = ['target_cn', 'tms_cn']
    if symptom_en:
        gap_combinations['NIH_Symptom'] = ['symptom']

    # 标题生成
    title_parts = [cn_kw]
    if target_name:
        title_parts.append(target_name)
    if symptom_name:
        title_parts.append(symptom_name)
    title_zh = ' + '.join(title_parts) + ' 文献空白分析'

    cfg = {
        'name': name,
        'title_zh': title_zh,
        'title_en': f'{en_query} Literature Gap Analysis',
        'disease_cn_keyword': cn_kw,
        'disease_cn_filter': cn_filter,
        'disease_en_query': en_query,

        # 项目目录 (标准化结构: data/, results/, figs/, parameters/, scripts/)
        'project_dir': project_dir,

        # 干预 (空 = 用默认 NIBS 常量)
        'intervention_query_en': iv_query,
        'intervention_pattern_cn': iv_cn,
        'intervention_pattern_en': iv_en,

        # 维度 — 只在有值时添加
        'symptoms': {symptom_name: f'{symptom_en}|{symptom_cn}'} if symptom_name else {},
        'targets': {target_name: f'{target_en}|{target_cn}'} if target_name else {},
        'highlight_target': target_name or '',

        # Gap
        'gap_patterns': gap_patterns,
        'gap_combinations': gap_combinations,

        # PubMed 顶刊
        'use_top_journals': inputs.get('use_top_journals', False),

        # Panel E 占位
        'key_papers': [],
        'panel_e_title': f'E  {" + ".join([p for p in [target_name, symptom_name] if p]) or cn_kw} 关键文献',
        'panel_e_summary': '(待填充)',
    }

    # 申请人配置 (可选)
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
    target_name = inputs.get('target_name') or ''
    symptom_name = inputs.get('symptom_name') or ''

    disease_abbr = _abbrev(cn_kw)
    today = date.today().strftime('%Y%m%d')

    # 根据有无 target/symptom 生成文件名
    name_parts = [disease_abbr]
    if target_name:
        name_parts.append(target_name.lower())
    if symptom_name:
        name_parts.append(_abbrev(symptom_name))
    # 如果有申请人，也加入文件名
    applicant = inputs.get('applicant')
    if applicant and applicant.get('name_cn'):
        name_parts.append(applicant['name_cn'])
    name_parts.append(today)
    yaml_name = '_'.join(name_parts) + '.yaml'
    # 配置文件放到 configs/ 目录
    configs_dir = Path(__file__).parent / 'configs'
    configs_dir.mkdir(exist_ok=True)
    yaml_path = configs_dir / yaml_name

    raw_cfg = generate_yaml(inputs, yaml_path)

    # 项目目录 (Pipeline 会自动在 zbib/projects/ 下创建)
    project_name = raw_cfg['project_dir']
    project_dir = Path(__file__).parent / 'projects' / project_name
    print(f"[项目目录] → {project_dir}")

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
        print(f"  或手动将 NSFC 数据放入: {project_dir}/data/")
        print(f"  然后运行: python run_all.py -c {yaml_path} --step 6")


# ─── 交互式状态机 (支持回退) ─────────────────────

BACK_COMMANDS = {'b', 'back', '<', '返回', '上一步'}

def interactive_wizard() -> tuple[dict, str | None, str | None] | None:
    """交互式向导，支持每一步回退。返回 (inputs, email, password) 或 None (取消)"""

    # 步骤结果存储
    results = {}
    step = 1
    max_step = 8  # 1-7 输入 + 8 确认

    print("\n  💡 提示: 任意输入框输入 b 可返回上一步\n")

    while step <= max_step:
        if step == 1:
            # ── Step 1: LetPub 账号 ──
            email, password = prompt_credentials()
            results[1] = (email, password)
            step += 1

        elif step == 2:
            # ── Step 2: 疾病 ──
            result = prompt_disease()
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            cn_kw, cn_filter, en_query = result
            results[2] = (cn_kw, cn_filter, en_query)
            step += 1

        elif step == 3:
            # ── Step 3: 干预手段 ──
            result = prompt_intervention()
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            iv_query, iv_cn, iv_en = result
            results[3] = (iv_query, iv_cn, iv_en)
            step += 1

        elif step == 4:
            # ── Step 4: 靶点 ──
            result = prompt_target()
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            target_name, target_en, target_cn = result
            results[4] = (target_name, target_en, target_cn)
            step += 1

        elif step == 5:
            # ── Step 5: 症状 ──
            cn_kw, _, en_query = results[2]
            result = prompt_symptom(cn_kw, en_query)
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            symptom_name, symptom_en, symptom_cn = result
            results[5] = (symptom_name, symptom_en, symptom_cn)
            step += 1

        elif step == 6:
            # ── Step 6: 顶刊筛选 ──
            result = prompt_top_journals()
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            use_top = result
            results[6] = use_top
            step += 1

        elif step == 7:
            # ── Step 7: 申请人 ──
            result = prompt_applicant()
            if result == 'BACK':
                step = max(1, step - 1)
                continue
            applicant = result
            results[7] = applicant
            step += 1

        elif step == 8:
            # ── Step 8: 确认 ──
            email, password = results[1]
            cn_kw, cn_filter, en_query = results[2]
            iv_query, iv_cn, iv_en = results[3]
            target_name, target_en, target_cn = results[4]
            symptom_name, symptom_en, symptom_cn = results[5]
            use_top = results[6]
            applicant = results[7]

            print("\n" + "═" * 50)
            print("  [8/8] 配置确认")
            print("═" * 50)
            print(f"  1. LetPub: {'有账号' if email else '跳过'}")
            print(f"  2. 疾病: {cn_kw} / {en_query}")
            print(f"  3. 干预: {iv_query[:50]}...")
            if target_name:
                print(f"  4. 靶点: {target_name} ({target_en})")
            else:
                print(f"  4. 靶点: (跳过)")
            if symptom_name:
                print(f"  5. 症状: {symptom_name} ({symptom_en})")
            else:
                print(f"  5. 症状: (跳过)")
            print(f"  6. 顶刊筛选: {'是' if use_top else '否'}")
            if applicant:
                print(f"  7. 申请人: {applicant.get('name_cn', '')} ({applicant.get('name_en', '')})")
            else:
                print(f"  7. 申请人: (跳过)")
            print("─" * 50)
            print("  💡 输入 1-7 跳转修改，b 返回上一步")
            ok = input("  确认并开始？[Y/n/1-7/b]: ").strip().lower()

            if ok == 'n':
                print("  已取消。")
                return None
            if ok in BACK_COMMANDS:
                step = 7
                continue
            if ok.isdigit() and 1 <= int(ok) <= 7:
                step = int(ok)
                continue

            # 确认通过，构建 inputs
            inputs = dict(
                cn_keyword=cn_kw, cn_filter=cn_filter, en_query=en_query,
                iv_query=iv_query, iv_cn=iv_cn, iv_en=iv_en,
                target_name=target_name or '', target_en=target_en or '', target_cn=target_cn or '',
                symptom_name=symptom_name or '', symptom_en=symptom_en or '', symptom_cn=symptom_cn or '',
                use_top_journals=use_top,
            )
            if applicant:
                inputs['applicant'] = applicant

            return inputs, email, password

    return None


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
        target_name = inputs.get('target_name') or ''
        symptom_name = inputs.get('symptom_name') or ''
        if target_name:
            print(f"  靶点: {target_name} ({inputs.get('target_en', '')})")
        else:
            print(f"  靶点: (跳过 — 全领域检索)")
        if symptom_name:
            print(f"  症状: {symptom_name} ({inputs.get('symptom_en', '')})")
        else:
            print(f"  症状: (跳过 — 全领域检索)")
        print(f"  干预: {inputs['iv_query'][:60]}...")
        applicant = inputs.get('applicant')
        if applicant:
            print(f"  申请人: {applicant.get('name_cn', '')} ({applicant.get('name_en', '')})")
        print(f"  LetPub: {'有账号' if email else '跳过'}")
        run_pipeline(inputs, email, password)
    else:
        # ── 交互模式 (支持回退) ──
        result = interactive_wizard()
        if result is None:
            return
        inputs, email, password = result
        run_pipeline(inputs, email, password)


if __name__ == '__main__':
    main()
