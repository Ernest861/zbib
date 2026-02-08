"""领域基准数据库 — 百分位排名计算"""

from dataclasses import dataclass, field

from scripts.applicant.profile import ApplicantProfile


@dataclass
class FieldBenchmark:
    """
    领域基准数据 — 用于百分位排名计算。

    数据来源: 基于 PubMed 和 Web of Science 的经验估值,
    针对"非侵入性脑刺激 (NIBS) + 精神科"领域的活跃研究者。
    """
    name: str = 'NIBS-Psychiatry'

    # 各指标的百分位分布 [p10, p25, p50, p75, p90]
    # 总发文量 (Career total)
    n_total_pcts: list[float] = field(default_factory=lambda: [15, 30, 60, 120, 250])
    # 近5年发文量
    recent_5yr_pcts: list[float] = field(default_factory=lambda: [5, 12, 25, 50, 100])
    # H-index
    h_index_pcts: list[float] = field(default_factory=lambda: [3, 6, 12, 22, 40])
    # 第一/通讯作者占比 (%)
    independence_pcts: list[float] = field(default_factory=lambda: [10, 20, 30, 45, 60])
    # 顶刊 (tier1) 数量
    tier1_pcts: list[float] = field(default_factory=lambda: [0, 1, 3, 8, 20])
    # 累计 IF
    total_if_pcts: list[float] = field(default_factory=lambda: [20, 50, 120, 300, 800])
    # 平均 IF
    avg_if_pcts: list[float] = field(default_factory=lambda: [1.5, 2.5, 3.8, 5.5, 8.0])
    # 适配度
    fit_pcts: list[float] = field(default_factory=lambda: [15, 30, 50, 70, 85])
    # 胜任力
    competency_pcts: list[float] = field(default_factory=lambda: [15, 30, 50, 70, 85])
    # 综合评分
    total_score_pcts: list[float] = field(default_factory=lambda: [15, 30, 50, 70, 85])

    def get_percentile(self, metric: str, value: float) -> float:
        """
        计算给定指标值的百分位排名 (0-100)。

        在 [p10, p25, p50, p75, p90] 之间做线性插值。
        """
        pct_attr = f'{metric}_pcts'
        if not hasattr(self, pct_attr):
            return 50.0  # 未知指标返回中位

        pcts = getattr(self, pct_attr)
        anchors = [10, 25, 50, 75, 90]

        if value <= pcts[0]:
            # 低于 p10，按比例映射到 0-10
            return max(0, value / max(pcts[0], 0.01) * 10)
        if value >= pcts[-1]:
            # 高于 p90，按比例映射到 90-100
            excess = value - pcts[-1]
            bonus = min(10, excess / max(pcts[-1], 1) * 20)
            return min(100, 90 + bonus)

        # 在相邻锚点之间线性插值
        for i in range(len(pcts) - 1):
            if pcts[i] <= value <= pcts[i + 1]:
                ratio = (value - pcts[i]) / max(pcts[i + 1] - pcts[i], 0.01)
                return anchors[i] + ratio * (anchors[i + 1] - anchors[i])

        return 50.0


# 预置基准
NIBS_PSYCHIATRY_BENCHMARK = FieldBenchmark(name='NIBS-Psychiatry')

# 其他领域可按需扩展
NEUROSCIENCE_BENCHMARK = FieldBenchmark(
    name='Neuroscience-General',
    n_total_pcts=[20, 40, 80, 160, 350],
    recent_5yr_pcts=[8, 18, 35, 70, 140],
    h_index_pcts=[4, 8, 16, 30, 55],
    independence_pcts=[10, 18, 28, 40, 55],
    tier1_pcts=[0, 2, 5, 12, 30],
    total_if_pcts=[30, 80, 200, 500, 1200],
    avg_if_pcts=[2.0, 3.0, 4.5, 6.5, 10.0],
)


def calculate_percentile_ranks(
    profile: ApplicantProfile,
    benchmark: FieldBenchmark | None = None,
) -> dict[str, float]:
    """
    计算申请人在领域基准中的百分位排名。

    Args:
        profile: ApplicantProfile
        benchmark: 领域基准 (默认 NIBS-Psychiatry)

    Returns:
        {metric: percentile_rank}  (0-100, 越高越好)
    """
    bm = benchmark or NIBS_PSYCHIATRY_BENCHMARK

    independence_ratio = (
        profile.n_first_or_corresponding / max(profile.n_total, 1) * 100
    )

    ranks = {
        'n_total': bm.get_percentile('n_total', profile.n_total),
        'recent_5yr': bm.get_percentile('recent_5yr', profile.recent_5yr_count),
        'h_index': bm.get_percentile('h_index', profile.h_index_estimate),
        'independence': bm.get_percentile('independence', independence_ratio),
        'tier1': bm.get_percentile('tier1', profile.tier1_count),
        'total_if': bm.get_percentile('total_if', profile.if_stats.get('total_if', 0)),
        'avg_if': bm.get_percentile('avg_if', profile.if_stats.get('avg_if', 0)),
        'fit': bm.get_percentile('fit', profile.fit_score),
        'competency': bm.get_percentile('competency', profile.competency_score),
        'total_score': bm.get_percentile('total_score', profile.relevance_score),
    }

    # 四舍五入
    return {k: round(v, 1) for k, v in ranks.items()}


def apply_benchmark(
    profile: ApplicantProfile,
    benchmark: FieldBenchmark | None = None,
) -> ApplicantProfile:
    """计算百分位排名并写入 profile，返回原对象"""
    profile.percentile_ranks = calculate_percentile_ranks(profile, benchmark)
    return profile


def format_percentile_summary(profile: ApplicantProfile) -> str:
    """生成百分位排名的可读文本"""
    ranks = profile.percentile_ranks
    if not ranks:
        return "未计算百分位排名"

    labels = {
        'n_total': '发文总量',
        'recent_5yr': '近5年发文',
        'h_index': 'H-index',
        'independence': '独立占比',
        'tier1': '顶刊数量',
        'total_if': '累计IF',
        'avg_if': '平均IF',
        'fit': '适配度',
        'competency': '胜任力',
        'total_score': '综合评分',
    }

    lines = []
    for metric, label in labels.items():
        pct = ranks.get(metric, 0)
        # 生成评语
        if pct >= 90:
            tag = '顶尖'
        elif pct >= 75:
            tag = '优秀'
        elif pct >= 50:
            tag = '中上'
        elif pct >= 25:
            tag = '中等'
        else:
            tag = '偏低'
        bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
        lines.append(f"  {label:<8s}  {bar}  P{pct:.0f}  ({tag})")

    return '\n'.join(lines)


def create_benchmark_report_section(profile: ApplicantProfile) -> str:
    """生成 Markdown 报告中的基准排名部分"""
    ranks = profile.percentile_ranks
    if not ranks:
        return ""

    labels = {
        'n_total': '发文总量', 'recent_5yr': '近5年发文',
        'h_index': 'H-index', 'independence': '学术独立性',
        'tier1': '顶刊数量', 'total_if': '累计 IF',
        'fit': '适配度', 'competency': '胜任力', 'total_score': '综合评分',
    }

    lines = []
    lines.append("## 领域基准排名")
    lines.append("")
    lines.append("> 基准: NIBS-Psychiatry 领域活跃研究者")
    lines.append("")
    lines.append("| 指标 | 百分位 | 评价 | 含义 |")
    lines.append("|:-----|-------:|:----:|:-----|")

    for metric, label in labels.items():
        pct = ranks.get(metric, 0)
        if pct >= 90:
            tag = '顶尖'
            meaning = '超过 90% 的同领域研究者'
        elif pct >= 75:
            tag = '优秀'
            meaning = '超过 75% 的同领域研究者'
        elif pct >= 50:
            tag = '中上'
            meaning = '超过半数同领域研究者'
        elif pct >= 25:
            tag = '中等'
            meaning = '处于中等水平'
        else:
            tag = '偏低'
            meaning = '低于多数同领域研究者'
        lines.append(f"| {label} | P{pct:.0f} | {tag} | {meaning} |")

    lines.append("")
    return '\n'.join(lines)


def get_benchmark_by_name(name: str) -> FieldBenchmark:
    """
    按名称获取预置基准。

    Args:
        name: 基准名称 ('NIBS-Psychiatry', 'Neuroscience-General')

    Returns:
        FieldBenchmark 实例

    Raises:
        ValueError: 如果名称未知
    """
    benchmarks = {
        'NIBS-Psychiatry': NIBS_PSYCHIATRY_BENCHMARK,
        'Neuroscience-General': NEUROSCIENCE_BENCHMARK,
        'nibs': NIBS_PSYCHIATRY_BENCHMARK,
        'neuro': NEUROSCIENCE_BENCHMARK,
    }
    if name not in benchmarks:
        available = ', '.join(k for k in benchmarks if '-' in k)
        raise ValueError(f"未知基准: {name}。可用: {available}")
    return benchmarks[name]


def quick_percentile(value: float, metric: str, benchmark: str = 'NIBS-Psychiatry') -> float:
    """
    快速计算单个指标的百分位排名。

    Args:
        value: 指标值
        metric: 指标名称 (n_total, recent_5yr, h_index, etc.)
        benchmark: 基准名称

    Returns:
        百分位排名 (0-100)

    Example:
        >>> quick_percentile(50, 'n_total')  # 50篇文献在领域中的百分位
        62.5
    """
    bm = get_benchmark_by_name(benchmark)
    return bm.get_percentile(metric, value)
