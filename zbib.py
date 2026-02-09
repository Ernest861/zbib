#!/usr/bin/env python3
"""
zbib — 文献情报学空白挖掘工具 v2.3

统一命令行入口，支持以下命令：

    zbib new          创建新项目配置
    zbib run          运行完整分析流程
    zbib diagnose     诊断项目状态
    zbib report       生成综合报告
    zbib kg           生成知识图谱

使用示例:
    python zbib.py new
    python zbib.py run configs/my_project.yaml
    python zbib.py diagnose projects/xxx
    python zbib.py report projects/xxx
"""

import sys
import argparse
from pathlib import Path

# 确保可以导入 scripts
sys.path.insert(0, str(Path(__file__).parent))


def cmd_new(args):
    """创建新项目"""
    from quick_search import main as quick_search_main
    quick_search_main()


def cmd_run(args):
    """运行分析流程"""
    if not args.config:
        print("错误: 请指定配置文件")
        print("用法: python zbib.py run <config.yaml>")
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        return 1

    from scripts.pipeline import Pipeline
    pipeline = Pipeline.from_yaml(config_path)

    if args.step:
        pipeline.run(step=args.step)
    elif args.skip_fetch:
        pipeline.run(skip_fetch=True)
    else:
        # 需要 LetPub 账号
        email = args.email or input("LetPub 邮箱: ")
        password = args.password or input("LetPub 密码: ")
        pipeline.run(email=email, password=password)

    return 0


def cmd_diagnose(args):
    """诊断项目"""
    import types
    sys.modules['scripts'] = types.ModuleType('scripts')
    sys.modules['scripts'].__path__ = [str(Path(__file__).parent / 'scripts')]

    from scripts.diagnostic import diagnose_project, print_diagnostic

    project_dir = args.project or '.'
    result = diagnose_project(project_dir)
    print_diagnostic(result, verbose=not args.brief)

    return 0 if result.score >= 70 else 1


def cmd_report(args):
    """生成报告"""
    import types
    sys.modules['scripts'] = types.ModuleType('scripts')
    sys.modules['scripts'].__path__ = [str(Path(__file__).parent / 'scripts')]

    from scripts.report_generator import generate_full_report

    project_dir = args.project or '.'
    output_name = args.output or 'full_report.html'

    report_path = generate_full_report(project_dir, output_name)
    print(f"\n打开报告: open '{report_path}'")

    return 0


def cmd_kg(args):
    """生成知识图谱"""
    import types
    sys.modules['scripts'] = types.ModuleType('scripts')
    sys.modules['scripts'].__path__ = [str(Path(__file__).parent / 'scripts')]

    import pandas as pd
    from scripts.knowledge_graph import KnowledgeGraph

    project_dir = Path(args.project or '.')
    data_dir = project_dir / 'data'
    figs_dir = project_dir / 'figs'
    figs_dir.mkdir(exist_ok=True)

    # 查找数据文件 — 按优先级尝试多种模式
    df = None
    search_patterns = [
        'applicant_*.csv.gz',
        'applicant_*.csv',
        'pubmed*.csv',
        'nih_tms*.csv',
        'nih_nibs*.csv',
    ]
    for pattern in search_patterns:
        matches = sorted(data_dir.glob(pattern), key=lambda f: f.stat().st_size, reverse=True)
        if matches:
            f = matches[0]
            compression = 'gzip' if f.suffix == '.gz' else None
            df = pd.read_csv(f, compression=compression)
            print(f"[Data] 加载 {len(df)} 条记录: {f.name}")
            break

    if df is None:
        print(f"错误: 在 {data_dir} 中未找到数据文件")
        print(f"  支持的文件: {', '.join(search_patterns)}")
        return 1

    kg = KnowledgeGraph()
    # 使用 keywords 和 mesh 双列，auto_adjust 会根据数据量调整阈值
    kg.build_from_papers(df, concept_col=['keywords', 'mesh'])
    kg.export_interactive(figs_dir / 'knowledge_graph.html', title=project_dir.name)

    print(f"\n打开图谱: open '{figs_dir / 'knowledge_graph.html'}'")
    return 0


def cmd_version(args):
    """显示版本"""
    print("""
╔═══════════════════════════════════════════════════╗
║  zbib — 文献情报学空白挖掘工具                      ║
║  版本: 2.3                                         ║
║  功能: 研究空白分析 | 申请人评估 | 知识图谱          ║
╚═══════════════════════════════════════════════════╝
""")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='zbib — 文献情报学空白挖掘工具 v2.3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python zbib.py new                     创建新项目
  python zbib.py run config.yaml         运行分析
  python zbib.py diagnose projects/xxx   诊断项目
  python zbib.py report projects/xxx     生成报告
  python zbib.py kg projects/xxx         生成知识图谱
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # new
    p_new = subparsers.add_parser('new', help='创建新项目配置')

    # run
    p_run = subparsers.add_parser('run', help='运行分析流程')
    p_run.add_argument('config', nargs='?', help='配置文件路径')
    p_run.add_argument('--step', type=int, help='只运行指定步骤')
    p_run.add_argument('--skip-fetch', action='store_true', help='跳过数据抓取')
    p_run.add_argument('--email', help='LetPub 邮箱')
    p_run.add_argument('--password', help='LetPub 密码')

    # diagnose
    p_diag = subparsers.add_parser('diagnose', help='诊断项目状态')
    p_diag.add_argument('project', nargs='?', help='项目目录')
    p_diag.add_argument('--brief', action='store_true', help='简要输出')

    # report
    p_report = subparsers.add_parser('report', help='生成综合报告')
    p_report.add_argument('project', nargs='?', help='项目目录')
    p_report.add_argument('-o', '--output', help='输出文件名')

    # kg
    p_kg = subparsers.add_parser('kg', help='生成知识图谱')
    p_kg.add_argument('project', nargs='?', help='项目目录')

    # version
    p_ver = subparsers.add_parser('version', help='显示版本信息')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        'new': cmd_new,
        'run': cmd_run,
        'diagnose': cmd_diagnose,
        'report': cmd_report,
        'kg': cmd_kg,
        'version': cmd_version,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main() or 0)
