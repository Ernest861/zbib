"""顶级期刊列表 — 用于 PubMed 检索限定和后处理标记"""

import pandas as pd

# ═══════════════════════════════════════════════
# 期刊名映射: ISO缩写 → 类别
# ═══════════════════════════════════════════════
_MEDICAL: dict[str, str] = {
    # 四大刊
    "N Engl J Med": "NEJM", "Lancet": "Lancet",
    "JAMA": "JAMA", "BMJ": "BMJ",
    # 精神科顶刊
    "JAMA Psychiatry": "JAMA Psychiatry",
    "Lancet Psychiatry": "Lancet Psychiatry",
    "Am J Psychiatry": "Am J Psychiatry",
    "Biol Psychiatry": "Biol Psychiatry",
    "World Psychiatry": "World Psychiatry",
    "Schizophr Bull": "Schizophr Bull",
    "Br J Psychiatry": "Br J Psychiatry",
    # 神经科顶刊
    "Ann Neurol": "Ann Neurol",
    "Brain": "Brain",
    "Neurology": "Neurology",
    "JAMA Neurol": "JAMA Neurol",
    "Lancet Neurol": "Lancet Neurol",
}

_SCIENCE: dict[str, str] = {
    "Nature": "Nature", "Science": "Science", "Cell": "Cell",
    "Mol Psychiatry": "Mol Psychiatry",
    "Nat Neurosci": "Nat Neurosci",
    "Nat Med": "Nat Med",
    "Nat Rev Neurosci": "Nat Rev Neurosci",
    "Neuron": "Neuron",
    "Nat Commun": "Nat Commun",
    "Proc Natl Acad Sci U S A": "PNAS",
    "Curr Biol": "Curr Biol",
    "eLife": "eLife",
    "Sci Transl Med": "Sci Transl Med",
    "J Neurosci": "J Neurosci",
}

# PubMed [Journal] 检索式（各自带括号，可安全 OR 拼接）
MEDICAL_JOURNALS_QUERY = "(" + " OR ".join(f'"{j}"[Journal]' for j in _MEDICAL) + ")"
SCIENCE_JOURNALS_QUERY = "(" + " OR ".join(f'"{j}"[Journal]' for j in _SCIENCE) + ")"

# 用于快速查找的集合 (ISO缩写)
TOP_JOURNAL_NAMES: set[str] = set(_MEDICAL) | set(_SCIENCE)


def build_journal_query(medical: bool = True, science: bool = True) -> str:
    """拼接 PubMed 期刊限定检索式"""
    parts = []
    if medical:
        parts.append(MEDICAL_JOURNALS_QUERY)
    if science:
        parts.append(SCIENCE_JOURNALS_QUERY)
    if not parts:
        return ""
    return parts[0] if len(parts) == 1 else f"({' OR '.join(parts)})"


def is_top_journal(journal_name: str) -> str | None:
    """判断期刊是否为顶刊，返回 'medical'/'science'/None"""
    if not journal_name:
        return None
    j = journal_name.strip().rstrip(".")
    if j in _MEDICAL:
        return "medical"
    if j in _SCIENCE:
        return "science"
    return None


def tag_top_journals(df: pd.DataFrame, journal_col: str = "journal") -> pd.DataFrame:
    """给 DataFrame 加 top_journal 列 ('medical'/'science'/None)"""
    df = df.copy()
    df["top_journal"] = df[journal_col].apply(is_top_journal)
    return df


# ═══════════════════════════════════════════════
# 期刊影响因子数据 (2024 JCR 近似值)
# 用于加权分析和 H-index 估算
# ═══════════════════════════════════════════════
JOURNAL_IF: dict[str, float] = {
    # 综合顶刊 (IF > 50)
    "Nature": 64.8, "Science": 56.9, "Cell": 64.5,
    "N Engl J Med": 158.5, "Lancet": 168.9,
    "JAMA": 120.7, "Nat Med": 82.9,

    # 高影响神经/精神科 (IF 20-50)
    "Nat Neurosci": 25.0, "Neuron": 17.2, "Nat Rev Neurosci": 38.1,
    "Mol Psychiatry": 11.0, "JAMA Psychiatry": 25.9,
    "Lancet Psychiatry": 64.3, "Lancet Neurol": 48.0,
    "World Psychiatry": 73.3, "Am J Psychiatry": 19.2,
    "Biol Psychiatry": 10.6, "Brain": 14.5, "Ann Neurol": 11.2,

    # 中高影响 (IF 8-20)
    "JAMA Neurol": 29.0, "Nat Commun": 16.6, "Proc Natl Acad Sci U S A": 11.1,
    "Sci Transl Med": 17.1, "eLife": 8.1, "BMJ": 105.7,
    "Curr Biol": 9.2, "J Neurosci": 5.3, "Schizophr Bull": 7.4,
    "Neurology": 9.9, "Br J Psychiatry": 8.7,

    # 领域重要期刊 (IF 4-8)
    "Brain Stimul": 8.0, "Neuropsychopharmacology": 6.6,
    "Transl Psychiatry": 6.8, "Neuroimage": 5.7,
    "Hum Brain Mapp": 4.8, "Cereb Cortex": 3.7,
    "Cortex": 3.6, "Addiction": 6.3,
    "Drug Alcohol Depend": 4.0, "Psychol Med": 6.4,
    "J Affect Disord": 4.9, "Clin Neurophysiol": 4.0,

    # 其他常见期刊 (IF 2-4)
    "Front Psychiatry": 4.7, "Front Hum Neurosci": 2.9,
    "Psychiatry Res": 3.2, "J Psychiatr Res": 4.8,
    "Eur Psychiatry": 7.2, "Int J Neuropsychopharmacol": 5.4,
    "Psychopharmacology (Berl)": 3.5, "Behav Brain Res": 2.7,
}


def get_journal_if(journal_name: str) -> float:
    """获取期刊影响因子，未知期刊返回 1.0"""
    if not journal_name:
        return 1.0
    j = journal_name.strip().rstrip(".")
    return JOURNAL_IF.get(j, 1.0)


def get_journal_tier(journal_name: str) -> str:
    """获取期刊等级: 'tier1' (IF>=10), 'tier2' (IF>=4), 'tier3' (其他)"""
    if_val = get_journal_if(journal_name)
    if if_val >= 10:
        return 'tier1'
    elif if_val >= 4:
        return 'tier2'
    return 'tier3'


def estimate_citations(journal_name: str, years_since_pub: int) -> float:
    """
    基于期刊 IF 和发表年限估算引用数.

    公式: citations ≈ IF × sqrt(years) × 0.8
    (经验公式，实际引用受多种因素影响)
    """
    if_val = get_journal_if(journal_name)
    years = max(1, years_since_pub)
    return if_val * (years ** 0.5) * 0.8


def calculate_if_weighted_score(journals: list[str]) -> float:
    """计算 IF 加权总分"""
    return sum(get_journal_if(j) for j in journals)


def tag_journal_if(df: pd.DataFrame, journal_col: str = "journal") -> pd.DataFrame:
    """给 DataFrame 加 journal_if 和 journal_tier 列"""
    df = df.copy()
    df["journal_if"] = df[journal_col].apply(get_journal_if)
    df["journal_tier"] = df[journal_col].apply(get_journal_tier)
    return df
