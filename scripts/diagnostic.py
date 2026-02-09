"""
项目诊断工具 — zbib 3.0

快速检查项目状态和完整性：
- 数据文件完整性
- 分析结果状态
- 图表生成情况
- 改进建议

使用示例:
    >>> from scripts.diagnostic import diagnose_project
    >>> diagnose_project('projects/xxx')

命令行:
    python -m scripts.diagnostic projects/xxx
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


class FileStatus(NamedTuple):
    """文件状态"""
    exists: bool
    size: int = 0
    modified: str = ''


class DiagnosticResult(NamedTuple):
    """诊断结果"""
    score: int  # 0-100
    status: str  # 'excellent', 'good', 'warning', 'error'
    summary: str
    details: dict
    suggestions: list[str]


def check_file(path: Path) -> FileStatus:
    """检查单个文件"""
    if not path.exists():
        return FileStatus(False)
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
    return FileStatus(True, stat.st_size, modified)


def format_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / 1024 / 1024:.1f} MB"


def diagnose_project(project_dir: str | Path) -> DiagnosticResult:
    """
    诊断项目状态。

    Args:
        project_dir: 项目目录路径

    Returns:
        DiagnosticResult 对象
    """
    project_dir = Path(project_dir)

    if not project_dir.exists():
        return DiagnosticResult(
            score=0,
            status='error',
            summary=f"项目目录不存在: {project_dir}",
            details={},
            suggestions=["创建项目目录或检查路径"]
        )

    # 定义检查项 (使用 glob 模式支持灵活命名)
    checks = {
        'data': {
            'required': [
                ('pubmed*.csv', 'PubMed 文献数据'),
                ('nih*.csv', 'NIH 项目数据'),
            ],
            'optional': [
                ('nsfc*.csv', 'NSFC 合并数据'),
                ('nsfcfund_*.xls', 'NSFC 原始数据'),
                ('applicant_*.csv*', '申请人发表数据'),
            ]
        },
        'results': {
            'required': [
                ('heatmap.csv', '热力图数据'),
                ('gap_counts.csv', '空白统计'),
            ],
            'optional': [
                ('NSFC标书支撑材料.md', 'NSFC 报告'),
                ('标书段落模板.md', '段落模板'),
                ('applicant_summary.txt', '申请人摘要'),
            ]
        },
        'figs': {
            'required': [
                ('*landscape*.png', '全景图 PNG'),
                ('*landscape*.pdf', '全景图 PDF'),
            ],
            'optional': [
                ('knowledge_graph.html', '知识图谱'),
                ('*applicant*.png', '申请人图'),
                ('*supplementary*.pdf', '补充图'),
            ]
        }
    }

    details = {}
    total_score = 0
    max_score = 0
    suggestions = []

    for category, items in checks.items():
        cat_dir = project_dir / category
        details[category] = {'found': [], 'missing': []}

        # 必需文件
        for pattern, desc in items['required']:
            max_score += 15
            if '*' in pattern:
                matches = list(cat_dir.glob(pattern))
                if matches:
                    f = matches[0]
                    status = check_file(f)
                    details[category]['found'].append({
                        'name': f.name,
                        'desc': desc,
                        'size': format_size(status.size),
                        'modified': status.modified,
                    })
                    total_score += 15
                else:
                    details[category]['missing'].append({'name': pattern, 'desc': desc, 'required': True})
                    suggestions.append(f"缺少 {desc} ({pattern})")
            else:
                f = cat_dir / pattern
                status = check_file(f)
                if status.exists:
                    details[category]['found'].append({
                        'name': pattern,
                        'desc': desc,
                        'size': format_size(status.size),
                        'modified': status.modified,
                    })
                    total_score += 15
                else:
                    details[category]['missing'].append({'name': pattern, 'desc': desc, 'required': True})
                    suggestions.append(f"缺少 {desc} ({pattern})")

        # 可选文件
        for pattern, desc in items['optional']:
            max_score += 5
            if '*' in pattern:
                matches = list(cat_dir.glob(pattern))
                if matches:
                    f = matches[0]
                    status = check_file(f)
                    details[category]['found'].append({
                        'name': f.name,
                        'desc': desc,
                        'size': format_size(status.size),
                        'modified': status.modified,
                    })
                    total_score += 5
            else:
                f = cat_dir / pattern
                status = check_file(f)
                if status.exists:
                    details[category]['found'].append({
                        'name': pattern,
                        'desc': desc,
                        'size': format_size(status.size),
                        'modified': status.modified,
                    })
                    total_score += 5

    # 计算得分
    score = int(total_score / max_score * 100) if max_score > 0 else 0

    # 状态判定
    if score >= 90:
        status = 'excellent'
        summary = '✅ 项目完整，所有核心文件就绪'
    elif score >= 70:
        status = 'good'
        summary = '✓ 项目基本完整，部分可选文件缺失'
    elif score >= 50:
        status = 'warning'
        summary = '⚠️ 项目不完整，缺少部分必需文件'
    else:
        status = 'error'
        summary = '❌ 项目严重不完整，请重新运行分析'

    # 添加通用建议
    if not suggestions:
        suggestions = ['项目状态良好，无需额外操作']

    return DiagnosticResult(
        score=score,
        status=status,
        summary=summary,
        details=details,
        suggestions=suggestions[:5]  # 最多5条建议
    )


def print_diagnostic(result: DiagnosticResult, verbose: bool = True):
    """打印诊断结果"""
    # 状态颜色
    colors = {
        'excellent': '\033[92m',  # 绿色
        'good': '\033[94m',       # 蓝色
        'warning': '\033[93m',    # 黄色
        'error': '\033[91m',      # 红色
    }
    reset = '\033[0m'
    color = colors.get(result.status, '')

    print("\n" + "=" * 60)
    print(f"📊 项目诊断报告")
    print("=" * 60)

    # 得分
    score_bar = '█' * (result.score // 5) + '░' * (20 - result.score // 5)
    print(f"\n得分: {color}{result.score}/100{reset} [{score_bar}]")
    print(f"状态: {color}{result.summary}{reset}")

    if verbose:
        # 详细信息
        for category, info in result.details.items():
            print(f"\n📁 {category}/")
            for f in info['found']:
                print(f"   ✓ {f['name']:<35} {f['size']:>10}  ({f['modified']})")
            for f in info['missing']:
                marker = '✗' if f.get('required') else '○'
                print(f"   {marker} {f['name']:<35} {'缺失':>10}  {f['desc']}")

    # 建议
    if result.suggestions and result.suggestions[0] != '项目状态良好，无需额外操作':
        print(f"\n💡 改进建议:")
        for i, s in enumerate(result.suggestions, 1):
            print(f"   {i}. {s}")

    print("\n" + "=" * 60)


def main():
    """命令行入口"""
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m scripts.diagnostic <project_dir>")
        print("示例: python -m scripts.diagnostic projects/精神分裂症_OFC_Negative_胡强_20260207")
        sys.exit(1)

    project_dir = sys.argv[1]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    result = diagnose_project(project_dir)
    print_diagnostic(result, verbose=True)


if __name__ == '__main__':
    main()
