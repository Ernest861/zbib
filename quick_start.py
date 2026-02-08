#!/usr/bin/env python3
"""
zbib 极简启动器 — 只需输入 4 个关键词

用法:
    python quick_start.py

或直接传参:
    python quick_start.py 精神分裂症 OFC 阴性症状 胡强
"""

import sys
from pathlib import Path
from datetime import date

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def generate_config(disease_cn: str, target: str, symptom: str, applicant_cn: str) -> dict:
    """从4个关键词生成完整配置"""

    # 自动推断英文
    DISEASE_MAP = {
        '精神分裂': ('schizophrenia', 'SCZ'),
        '精神分裂症': ('schizophrenia', 'SCZ'),
        '抑郁': ('depression OR depressive OR MDD', 'MDD'),
        '抑郁症': ('depression OR depressive OR MDD', 'MDD'),
        '成瘾': ('addiction OR "substance use disorder"', 'Addiction'),
        '焦虑': ('anxiety OR anxious', 'Anxiety'),
        '强迫症': ('OCD OR "obsessive compulsive"', 'OCD'),
        '自闭症': ('autism OR ASD', 'ASD'),
        '帕金森': ('parkinson', 'PD'),
        '阿尔茨海默': ('alzheimer OR dementia', 'AD'),
        '癫痫': ('epilepsy', 'Epilepsy'),
        '中风': ('stroke', 'Stroke'),
    }

    TARGET_MAP = {
        'OFC': ('orbitofrontal|\\bOFC\\b', '眶额'),
        'DLPFC': ('DLPFC|dorsolateral prefrontal', '背外侧前额叶'),
        'TPJ': ('temporoparietal|\\bTPJ\\b|angular gyrus', '颞顶联合区'),
        'mPFC': ('medial prefrontal|mPFC|vmPFC', '内侧前额叶'),
        'ACC': ('anterior cingulate|\\bACC\\b', '前扣带回'),
        'M1': ('motor cortex|\\bM1\\b|primary motor', '运动皮层'),
        'SMA': ('supplementary motor|\\bSMA\\b', '辅助运动区'),
        'Insula': ('insula|insular', '脑岛'),
        'Cerebellum': ('cerebell', '小脑'),
    }

    SYMPTOM_MAP = {
        '阴性症状': ('negative symptom|anhedonia|avolition|alogia|apathy', 'Negative'),
        '阳性症状': ('positive symptom|hallucination|delusion', 'Positive'),
        '认知': ('cogniti|memory|attention|executive', 'Cognitive'),
        '情绪': ('emotion|mood|affect', 'Emotion'),
        '运动': ('motor|movement|tremor', 'Motor'),
        '疼痛': ('pain|analges', 'Pain'),
        '睡眠': ('sleep|insomnia', 'Sleep'),
        '焦虑': ('anxiety|anxious', 'Anxiety'),
        '抑郁': ('depress', 'Depression'),
        '冲动': ('impulsiv|inhibit', 'Impulsivity'),
        '渴求': ('craving|urge', 'Craving'),
    }

    # 查找映射
    disease_en, disease_abbr = DISEASE_MAP.get(disease_cn, (disease_cn, disease_cn[:3].upper()))
    target_en, target_cn = TARGET_MAP.get(target.upper(), (target, target))
    symptom_en, symptom_abbr = SYMPTOM_MAP.get(symptom, (symptom, symptom[:3]))

    # 生成配置名
    today = date.today().strftime('%Y%m%d')
    name = f"{disease_abbr.lower()}_{target.lower()}_{applicant_cn}"
    project_dir = f"../projects/{disease_abbr}_{target}_{applicant_cn}_{today}"

    config = {
        'name': name,
        'title_zh': f'{target}-TMS治疗{disease_cn}{symptom}',
        'title_en': f'{target}-TMS for {disease_abbr} {symptom_abbr}',
        'suptitle': f'{target}-TMS治疗{disease_cn}{symptom}：研究空白与申请人前期基础',
        'project_dir': project_dir,

        # 检索式
        'disease_cn_keyword': disease_cn,
        'disease_cn_filter': disease_cn,
        'disease_en_query': disease_en,

        # 干预 (默认TMS)
        'intervention_query_en': '(TMS OR rTMS OR "transcranial magnetic stimulation" OR "theta burst")',
        'intervention_pattern_cn': '经颅磁|TMS|rTMS|磁刺激|theta.?burst|TBS',
        'intervention_pattern_en': 'transcranial magnetic|\\bTMS\\b|\\brTMS\\b|theta.?burst|\\bTBS\\b',

        # 症状维度
        'symptoms': {
            symptom_abbr: symptom_en,
        },

        # 靶区
        'targets': {
            target: target_en,
            'DLPFC': 'DLPFC|dorsolateral prefrontal',  # 对照
        },
        'highlight_target': target,

        # 热力图
        'heatmap_symptoms': {symptom_abbr: symptom_en},
        'heatmap_targets': {target: target_en, 'DLPFC': 'DLPFC|dorsolateral prefrontal'},

        # Gap 分析
        'gap_patterns': {
            'target': target_en,
            'target_cn': target_cn,
            'symptom': symptom_en,
            'tms_cn': '经颅磁|TMS|rTMS',
        },
        'gap_combinations': {
            f'PubMed_{target}_TMS': ['target', 'tms_cn'],
            f'NIH_{target}': ['target'],
            f'NIH_{target}_{symptom_abbr}': ['target', 'symptom'],
        },

        # Panel E
        'key_papers': [],
        'panel_e_title': f'E  {target}+{symptom}: 核心空白',
        'panel_e_summary': '(待填充)',

        # 申请人
        'applicant': {
            'name_cn': applicant_cn,
            'name_en': '',  # 需要用户补充
            'affiliations': [],  # 需要用户补充
            'aliases': [],
        },

        'use_top_journals': True,
    }

    return config


def interactive_mode():
    """交互式输入"""
    print("=" * 50)
    print("  zbib 极简启动器")
    print("  只需输入 4 个关键词，自动生成完整配置")
    print("=" * 50)
    print()

    print("示例: 精神分裂症 OFC 阴性症状 胡强")
    print()

    disease = input("1. 疾病 (如 精神分裂症): ").strip()
    target = input("2. 靶点 (如 OFC, DLPFC, TPJ): ").strip()
    symptom = input("3. 症状 (如 阴性症状, 认知): ").strip()
    applicant = input("4. 申请人中文名: ").strip()

    if not all([disease, target, symptom, applicant]):
        print("错误: 请填写所有字段")
        return None

    # 补充申请人信息
    print()
    print("--- 申请人详细信息 (可选，回车跳过) ---")
    name_en = input(f"   英文名 (如 Qiang Hu): ").strip()
    affiliation = input(f"   单位 (如 Shanghai Mental Health Center): ").strip()

    config = generate_config(disease, target, symptom, applicant)

    if name_en:
        config['applicant']['name_en'] = name_en
    if affiliation:
        config['applicant']['affiliations'] = [affiliation]

    return config


def save_and_run(config: dict):
    """保存配置并运行"""
    import yaml
    from scripts.pipeline import Pipeline
    from scripts.config import TopicConfig

    # 保存 YAML
    config_dir = Path(__file__).parent / 'configs'
    config_dir.mkdir(exist_ok=True)

    yaml_path = config_dir / f"{config['name']}.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n配置已保存: {yaml_path}")

    # 询问是否运行
    run = input("\n立即运行分析? [Y/n]: ").strip().lower()
    if run and run != 'y':
        print(f"\n稍后运行: ./venv/bin/python run_all.py -c {yaml_path}")
        return

    # 运行 Pipeline
    print("\n开始分析...")
    try:
        cfg = TopicConfig(**config)
        pipe = Pipeline(cfg)
        pipe.fetch_pubmed()
        pipe.fetch_nih()
        if config['applicant'].get('name_en'):
            pipe.fetch_applicant()
        pipe.load_data()
        pipe.classify()
        analysis = pipe.analyze_gaps()
        pipe.analyze_applicant()
        pipe.save_results(analysis)
        data_dict = pipe.build_plot_data(analysis)
        pipe.plot_applicant()
        pipe.plot(data_dict)
        print("\n分析完成!")
        print(f"结果目录: {config['project_dir']}")
    except Exception as e:
        print(f"\n运行出错: {e}")
        print(f"可手动运行: ./venv/bin/python run_all.py -c {yaml_path} --step 6")


def main():
    if len(sys.argv) == 5:
        # 命令行模式
        disease, target, symptom, applicant = sys.argv[1:5]
        config = generate_config(disease, target, symptom, applicant)
        save_and_run(config)
    else:
        # 交互模式
        config = interactive_mode()
        if config:
            save_and_run(config)


if __name__ == '__main__':
    main()
