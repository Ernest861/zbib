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
