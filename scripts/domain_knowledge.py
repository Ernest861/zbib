"""疾病领域知识库 — 症状维度与TMS靶点

基于 PubMed 文献综合分析，提供各疾病常见的：
1. 症状维度 (symptoms)
2. TMS 干预靶点 (targets)

用于自动扩展热力图分析维度，而非仅使用用户配置的单一维度。
"""

from __future__ import annotations

import re
from typing import TypedDict


class DimensionPattern(TypedDict):
    """维度定义"""
    cn: str          # 中文名
    pattern_en: str  # 英文正则
    pattern_cn: str  # 中文正则


# =============================================================================
# 精神分裂症 (Schizophrenia)
# =============================================================================

SCZ_SYMPTOMS: dict[str, DimensionPattern] = {
    'Negative': {
        'cn': '阴性症状',
        'pattern_en': r'negative\s*symptom|avolition|anhedonia|alogia|apathy|blunt|flat\s*affect|social\s*withdraw',
        'pattern_cn': r'阴性症状|快感缺失|意志缺乏|情感淡漠',
    },
    'Positive': {
        'cn': '阳性症状',
        'pattern_en': r'positive\s*symptom|hallucination|delusion|thought\s*disorder|paranoi',
        'pattern_cn': r'阳性症状|幻觉|妄想|思维障碍',
    },
    'Cognitive': {
        'cn': '认知功能',
        'pattern_en': r'cogniti|working\s*memory|attention|executive\s*function|processing\s*speed',
        'pattern_cn': r'认知|工作记忆|注意力|执行功能',
    },
    'AVH': {
        'cn': '幻听',
        'pattern_en': r'auditory\s*(verbal\s*)?hallucination|\bAVH\b|voice\s*hearing',
        'pattern_cn': r'幻听|言语性幻觉',
    },
    'Disorganization': {
        'cn': '瓦解症状',
        'pattern_en': r'disorganiz|formal\s*thought\s*disorder|incoherence',
        'pattern_cn': r'瓦解|思维松弛',
    },
}

SCZ_TARGETS: dict[str, DimensionPattern] = {
    'DLPFC': {
        'cn': '背外侧前额叶',
        'pattern_en': r'\bDLPFC\b|dorsolateral\s*prefrontal',
        'pattern_cn': r'背外侧前额|DLPFC',
    },
    'OFC': {
        'cn': '眶额皮层',
        'pattern_en': r'\bOFC\b|orbitofrontal',
        'pattern_cn': r'眶额|OFC',
    },
    'TPJ': {
        'cn': '颞顶联合区',
        'pattern_en': r'\bTPJ\b|temporo.?parietal\s*junction',
        'pattern_cn': r'颞顶联合|TPJ',
    },
    'mPFC': {
        'cn': '内侧前额叶',
        'pattern_en': r'\bmPFC\b|medial\s*prefrontal|ventromedial\s*prefrontal|\bvmPFC\b',
        'pattern_cn': r'内侧前额|mPFC',
    },
    'ACC': {
        'cn': '前扣带回',
        'pattern_en': r'\bACC\b|anterior\s*cingulate',
        'pattern_cn': r'前扣带|ACC',
    },
    'Cerebellum': {
        'cn': '小脑',
        'pattern_en': r'cerebell',
        'pattern_cn': r'小脑',
    },
    'STS': {
        'cn': '颞上沟',
        'pattern_en': r'\bSTS\b|superior\s*temporal\s*sulcus',
        'pattern_cn': r'颞上沟|STS',
    },
}

# =============================================================================
# 抑郁症 (Depression)
# =============================================================================

DEP_SYMPTOMS: dict[str, DimensionPattern] = {
    'Anhedonia': {
        'cn': '快感缺失',
        'pattern_en': r'anhedonia|reward|pleasure',
        'pattern_cn': r'快感缺失|奖赏',
    },
    'Rumination': {
        'cn': '反刍思维',
        'pattern_en': r'ruminat|brooding|self.?referential',
        'pattern_cn': r'反刍|沉思',
    },
    'Cognitive': {
        'cn': '认知功能',
        'pattern_en': r'cogniti|concentration|memory|executive',
        'pattern_cn': r'认知|注意|记忆',
    },
    'Suicidal': {
        'cn': '自杀意念',
        'pattern_en': r'suicid|self.?harm|self.?injury',
        'pattern_cn': r'自杀|自伤',
    },
    'Anxiety': {
        'cn': '焦虑',
        'pattern_en': r'anxi|worry|fear',
        'pattern_cn': r'焦虑|担忧',
    },
    'Sleep': {
        'cn': '睡眠障碍',
        'pattern_en': r'sleep|insomnia|hypersomnia',
        'pattern_cn': r'睡眠|失眠',
    },
}

DEP_TARGETS: dict[str, DimensionPattern] = {
    'L-DLPFC': {
        'cn': '左背外侧前额叶',
        'pattern_en': r'left\s*(DLPFC|dorsolateral)|L.?DLPFC',
        'pattern_cn': r'左(背外侧)?前额|L-DLPFC',
    },
    'R-DLPFC': {
        'cn': '右背外侧前额叶',
        'pattern_en': r'right\s*(DLPFC|dorsolateral)|R.?DLPFC',
        'pattern_cn': r'右(背外侧)?前额|R-DLPFC',
    },
    'DLPFC': {
        'cn': '背外侧前额叶',
        'pattern_en': r'\bDLPFC\b|dorsolateral\s*prefrontal',
        'pattern_cn': r'背外侧前额|DLPFC',
    },
    'dmPFC': {
        'cn': '背内侧前额叶',
        'pattern_en': r'\bdmPFC\b|dorsomedial\s*prefrontal',
        'pattern_cn': r'背内侧前额|dmPFC',
    },
    'OFC': {
        'cn': '眶额皮层',
        'pattern_en': r'\bOFC\b|orbitofrontal',
        'pattern_cn': r'眶额|OFC',
    },
    'sgACC': {
        'cn': '膝下扣带回',
        'pattern_en': r'sgACC|subgenual\s*(anterior\s*)?cingulate',
        'pattern_cn': r'膝下扣带|sgACC',
    },
}

# =============================================================================
# 成瘾 (Addiction)
# =============================================================================

ADD_SYMPTOMS: dict[str, DimensionPattern] = {
    'Craving': {
        'cn': '渴求',
        'pattern_en': r'craving|urge|desire',
        'pattern_cn': r'渴求|欲望',
    },
    'Relapse': {
        'cn': '复发/复吸',
        'pattern_en': r'relapse|recurrence|lapse',
        'pattern_cn': r'复发|复吸',
    },
    'Withdrawal': {
        'cn': '戒断',
        'pattern_en': r'withdraw|abstinence',
        'pattern_cn': r'戒断|脱瘾',
    },
    'Impulsivity': {
        'cn': '冲动性',
        'pattern_en': r'impulsiv|inhibit|self.?control|delay\s*discount',
        'pattern_cn': r'冲动|抑制|自控',
    },
    'Cue-reactivity': {
        'cn': '线索反应',
        'pattern_en': r'cue.?reactiv|cue.?induced|drug.?cue',
        'pattern_cn': r'线索反应|诱发',
    },
}

ADD_TARGETS: dict[str, DimensionPattern] = {
    'DLPFC': {
        'cn': '背外侧前额叶',
        'pattern_en': r'\bDLPFC\b|dorsolateral\s*prefrontal',
        'pattern_cn': r'背外侧前额|DLPFC',
    },
    'vmPFC': {
        'cn': '腹内侧前额叶',
        'pattern_en': r'\bvmPFC\b|ventromedial\s*prefrontal',
        'pattern_cn': r'腹内侧前额|vmPFC',
    },
    'OFC': {
        'cn': '眶额皮层',
        'pattern_en': r'\bOFC\b|orbitofrontal',
        'pattern_cn': r'眶额|OFC',
    },
    'ACC': {
        'cn': '前扣带回',
        'pattern_en': r'\bACC\b|anterior\s*cingulate',
        'pattern_cn': r'前扣带|ACC',
    },
    'Insula': {
        'cn': '脑岛',
        'pattern_en': r'insul',
        'pattern_cn': r'脑岛|岛叶',
    },
    'TPJ': {
        'cn': '颞顶联合区',
        'pattern_en': r'\bTPJ\b|temporo.?parietal',
        'pattern_cn': r'颞顶联合|TPJ',
    },
}

# =============================================================================
# 强迫症 (OCD)
# =============================================================================

OCD_SYMPTOMS: dict[str, DimensionPattern] = {
    'Obsession': {
        'cn': '强迫观念',
        'pattern_en': r'obsession|intrusive\s*thought',
        'pattern_cn': r'强迫观念|侵入性思维',
    },
    'Compulsion': {
        'cn': '强迫行为',
        'pattern_en': r'compulsion|ritual|checking|washing|ordering',
        'pattern_cn': r'强迫行为|仪式',
    },
    'Anxiety': {
        'cn': '焦虑',
        'pattern_en': r'anxi|distress',
        'pattern_cn': r'焦虑|痛苦',
    },
    'Cognitive': {
        'cn': '认知功能',
        'pattern_en': r'cogniti|flexibility|set.?shifting|inhibit',
        'pattern_cn': r'认知|灵活性|抑制',
    },
}

OCD_TARGETS: dict[str, DimensionPattern] = {
    'OFC': {
        'cn': '眶额皮层',
        'pattern_en': r'\bOFC\b|orbitofrontal',
        'pattern_cn': r'眶额|OFC',
    },
    'pre-SMA': {
        'cn': '前辅助运动区',
        'pattern_en': r'pre.?SMA|pre.?supplementary\s*motor',
        'pattern_cn': r'前辅助运动|pre-SMA',
    },
    'SMA': {
        'cn': '辅助运动区',
        'pattern_en': r'\bSMA\b|supplementary\s*motor',
        'pattern_cn': r'辅助运动区|SMA',
    },
    'DLPFC': {
        'cn': '背外侧前额叶',
        'pattern_en': r'\bDLPFC\b|dorsolateral\s*prefrontal',
        'pattern_cn': r'背外侧前额|DLPFC',
    },
    'ACC': {
        'cn': '前扣带回',
        'pattern_en': r'\bACC\b|anterior\s*cingulate',
        'pattern_cn': r'前扣带|ACC',
    },
}

# =============================================================================
# 疾病知识库注册表
# =============================================================================

DISEASE_REGISTRY: dict[str, dict] = {
    'schizophrenia': {
        'cn': '精神分裂症',
        'aliases': ['scz', 'psychosis', '精神分裂', '精神分裂症'],
        'symptoms': SCZ_SYMPTOMS,
        'targets': SCZ_TARGETS,
    },
    'depression': {
        'cn': '抑郁症',
        'aliases': ['mdd', 'major depression', '抑郁', '抑郁症'],
        'symptoms': DEP_SYMPTOMS,
        'targets': DEP_TARGETS,
    },
    'addiction': {
        'cn': '成瘾',
        'aliases': ['substance use', 'drug', 'alcohol', '成瘾', '物质依赖'],
        'symptoms': ADD_SYMPTOMS,
        'targets': ADD_TARGETS,
    },
    'ocd': {
        'cn': '强迫症',
        'aliases': ['obsessive compulsive', '强迫症', '强迫'],
        'symptoms': OCD_SYMPTOMS,
        'targets': OCD_TARGETS,
    },
}


# =============================================================================
# 公共 API
# =============================================================================

def normalize_disease_name(disease: str) -> str | None:
    """将疾病名称标准化为注册表中的键

    Args:
        disease: 疾病名称（可以是别名）

    Returns:
        标准化后的疾病键，或 None 如果未找到
    """
    disease_lower = disease.lower().strip()

    # 直接匹配
    if disease_lower in DISEASE_REGISTRY:
        return disease_lower

    # 别名匹配
    for key, info in DISEASE_REGISTRY.items():
        for alias in info['aliases']:
            if alias.lower() in disease_lower or disease_lower in alias.lower():
                return key

    return None


def get_disease_dimensions(
    disease: str,
    include_symptoms: bool = True,
    include_targets: bool = True,
) -> dict:
    """获取疾病的完整维度定义

    Args:
        disease: 疾病名称
        include_symptoms: 是否包含症状维度
        include_targets: 是否包含靶点维度

    Returns:
        {
            'disease_key': str,
            'disease_cn': str,
            'symptoms': dict[name, pattern],  # 用于分类器
            'symptoms_info': dict[name, DimensionPattern],  # 完整信息
            'targets': dict[name, pattern],
            'targets_info': dict[name, DimensionPattern],
        }
    """
    disease_key = normalize_disease_name(disease)

    if not disease_key:
        # 未知疾病，返回空
        return {
            'disease_key': None,
            'disease_cn': disease,
            'symptoms': {},
            'symptoms_info': {},
            'targets': {},
            'targets_info': {},
        }

    info = DISEASE_REGISTRY[disease_key]

    result = {
        'disease_key': disease_key,
        'disease_cn': info['cn'],
        'symptoms': {},
        'symptoms_info': {},
        'targets': {},
        'targets_info': {},
    }

    if include_symptoms:
        symptoms = info['symptoms']
        # 合并英文和中文正则
        result['symptoms'] = {
            name: f"{dim['pattern_en']}|{dim['pattern_cn']}"
            for name, dim in symptoms.items()
        }
        result['symptoms_info'] = symptoms

    if include_targets:
        targets = info['targets']
        result['targets'] = {
            name: f"{dim['pattern_en']}|{dim['pattern_cn']}"
            for name, dim in targets.items()
        }
        result['targets_info'] = targets

    return result


def expand_config_dimensions(
    disease: str,
    user_symptoms: dict[str, str] | None = None,
    user_targets: dict[str, str] | None = None,
    highlight_symptom: str | None = None,
    highlight_target: str | None = None,
) -> dict:
    """扩展用户配置的维度，合并知识库中的默认维度

    用户配置的维度会被保留，知识库中的其他维度会被添加。
    高亮的维度会被放在列表最前面。

    Args:
        disease: 疾病名称
        user_symptoms: 用户配置的症状维度
        user_targets: 用户配置的靶点维度
        highlight_symptom: 要高亮的症状（放在最前）
        highlight_target: 要高亮的靶点（放在最前）

    Returns:
        {
            'symptoms': dict[name, pattern],
            'targets': dict[name, pattern],
            'symptoms_cn': dict[name, str],  # 中文名映射
            'targets_cn': dict[name, str],
        }
    """
    # 获取知识库维度
    kb = get_disease_dimensions(disease)

    # 合并症状维度
    symptoms = {}
    symptoms_cn = {}

    # 先添加知识库维度
    for name, pattern in kb['symptoms'].items():
        symptoms[name] = pattern
        symptoms_cn[name] = kb['symptoms_info'][name]['cn']

    # 用户配置覆盖/补充
    if user_symptoms:
        for name, pattern in user_symptoms.items():
            symptoms[name] = pattern
            if name not in symptoms_cn:
                symptoms_cn[name] = name  # 无中文名则用英文

    # 合并靶点维度
    targets = {}
    targets_cn = {}

    for name, pattern in kb['targets'].items():
        targets[name] = pattern
        targets_cn[name] = kb['targets_info'][name]['cn']

    if user_targets:
        for name, pattern in user_targets.items():
            targets[name] = pattern
            if name not in targets_cn:
                targets_cn[name] = name

    # 重排序：高亮维度放最前
    def reorder(d: dict, highlight: str | None) -> dict:
        if not highlight or highlight not in d:
            return d
        return {highlight: d[highlight], **{k: v for k, v in d.items() if k != highlight}}

    symptoms = reorder(symptoms, highlight_symptom)
    targets = reorder(targets, highlight_target)

    return {
        'symptoms': symptoms,
        'targets': targets,
        'symptoms_cn': symptoms_cn,
        'targets_cn': targets_cn,
    }


def list_diseases() -> list[dict]:
    """列出所有支持的疾病

    Returns:
        [{'key': str, 'cn': str, 'n_symptoms': int, 'n_targets': int}, ...]
    """
    return [
        {
            'key': key,
            'cn': info['cn'],
            'n_symptoms': len(info['symptoms']),
            'n_targets': len(info['targets']),
        }
        for key, info in DISEASE_REGISTRY.items()
    ]


def list_dimensions(disease: str) -> dict:
    """列出疾病的所有维度（用于调试/展示）

    Args:
        disease: 疾病名称

    Returns:
        {
            'disease': str,
            'symptoms': [{'name': str, 'cn': str}, ...],
            'targets': [{'name': str, 'cn': str}, ...],
        }
    """
    kb = get_disease_dimensions(disease)

    return {
        'disease': kb['disease_cn'],
        'symptoms': [
            {'name': name, 'cn': info['cn']}
            for name, info in kb['symptoms_info'].items()
        ],
        'targets': [
            {'name': name, 'cn': info['cn']}
            for name, info in kb['targets_info'].items()
        ],
    }


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    # 测试：列出所有疾病
    print('支持的疾病:')
    for d in list_diseases():
        print(f"  {d['key']}: {d['cn']} ({d['n_symptoms']}症状, {d['n_targets']}靶点)")

    # 测试：获取精神分裂症维度
    print('\n精神分裂症维度:')
    dims = list_dimensions('schizophrenia')
    print(f"  症状: {[s['name'] for s in dims['symptoms']]}")
    print(f"  靶点: {[t['name'] for t in dims['targets']]}")

    # 测试：扩展配置
    print('\n扩展配置测试:')
    expanded = expand_config_dimensions(
        disease='schizophrenia',
        user_symptoms={'Negative': 'negative.*'},
        user_targets={'OFC': 'OFC|orbitofrontal'},
        highlight_symptom='Negative',
        highlight_target='OFC',
    )
    print(f"  扩展后症状: {list(expanded['symptoms'].keys())}")
    print(f"  扩展后靶点: {list(expanded['targets'].keys())}")
