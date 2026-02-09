"""
进度显示工具 — zbib 3.0

提供美观的终端进度显示：
- 步骤进度条
- 任务状态指示
- 耗时统计

使用示例:
    >>> from scripts.progress import ProgressTracker
    >>> with ProgressTracker(total=6, title='Pipeline') as p:
    ...     p.step('抓取数据')
    ...     # do work
    ...     p.done()
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Iterator


class ProgressTracker:
    """
    进度追踪器。

    提供步骤式进度显示，适合多阶段任务。
    """

    # 状态符号
    SYMBOLS = {
        'pending': '○',
        'running': '◐',
        'done': '●',
        'error': '✗',
    }

    # ANSI 颜色
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'red': '\033[91m',
        'cyan': '\033[96m',
    }

    def __init__(self, total: int, title: str = 'Progress', width: int = 40):
        """
        初始化进度追踪器。

        Args:
            total: 总步骤数
            title: 标题
            width: 进度条宽度
        """
        self.total = total
        self.title = title
        self.width = width
        self.current = 0
        self.steps: list[dict] = []
        self.start_time = None
        self.step_start_time = None

    def __enter__(self) -> 'ProgressTracker':
        self.start_time = time.time()
        self._print_header()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._print_footer()
        return False

    def _print_header(self):
        """打印标题"""
        c = self.COLORS
        print(f"\n{c['bold']}{c['cyan']}{'═' * 60}{c['reset']}")
        print(f"{c['bold']}{c['cyan']}  {self.title}{c['reset']}")
        print(f"{c['cyan']}{'═' * 60}{c['reset']}\n")

    def _print_footer(self):
        """打印结尾"""
        c = self.COLORS
        elapsed = time.time() - self.start_time
        success = sum(1 for s in self.steps if s['status'] == 'done')
        failed = sum(1 for s in self.steps if s['status'] == 'error')

        print(f"\n{c['cyan']}{'─' * 60}{c['reset']}")
        print(f"  {c['green']}✓ {success} 成功{c['reset']}", end='')
        if failed:
            print(f"  {c['red']}✗ {failed} 失败{c['reset']}", end='')
        print(f"  {c['dim']}耗时 {elapsed:.1f}s{c['reset']}")
        print(f"{c['cyan']}{'═' * 60}{c['reset']}\n")

    def step(self, name: str, status: str = 'running') -> int:
        """
        开始新步骤。

        Args:
            name: 步骤名称
            status: 初始状态

        Returns:
            步骤索引
        """
        self.step_start_time = time.time()
        step_info = {
            'name': name,
            'status': status,
            'start_time': self.step_start_time,
            'end_time': None,
        }
        self.steps.append(step_info)
        self._print_step(len(self.steps) - 1)
        return len(self.steps) - 1

    def done(self, message: str = ''):
        """标记当前步骤完成"""
        if self.steps:
            self.steps[-1]['status'] = 'done'
            self.steps[-1]['end_time'] = time.time()
            self.current += 1
            self._update_step(len(self.steps) - 1, message)

    def error(self, message: str = ''):
        """标记当前步骤失败"""
        if self.steps:
            self.steps[-1]['status'] = 'error'
            self.steps[-1]['end_time'] = time.time()
            self._update_step(len(self.steps) - 1, message)

    def _print_step(self, idx: int):
        """打印步骤（初始状态）"""
        c = self.COLORS
        step = self.steps[idx]
        symbol = self.SYMBOLS[step['status']]

        # 进度条
        progress = self.current / self.total
        filled = int(self.width * progress)
        bar = '█' * filled + '░' * (self.width - filled)

        print(f"  {c['yellow']}{symbol}{c['reset']} {step['name']:<30} ", end='')
        print(f"{c['dim']}[{bar}] {self.current}/{self.total}{c['reset']}", end='\r')
        sys.stdout.flush()

    def _update_step(self, idx: int, message: str = ''):
        """更新步骤状态"""
        c = self.COLORS
        step = self.steps[idx]
        symbol = self.SYMBOLS[step['status']]
        color = c['green'] if step['status'] == 'done' else c['red']

        elapsed = step['end_time'] - step['start_time']

        # 进度条
        progress = self.current / self.total
        filled = int(self.width * progress)
        bar = '█' * filled + '░' * (self.width - filled)

        # 清除当前行并打印完成状态
        print(f"\r  {color}{symbol}{c['reset']} {step['name']:<30} ", end='')
        print(f"[{bar}] {self.current}/{self.total} ", end='')
        print(f"{c['dim']}({elapsed:.1f}s){c['reset']}")

        if message:
            print(f"    {c['dim']}→ {message}{c['reset']}")


@contextmanager
def progress_step(name: str) -> Iterator[None]:
    """
    简单的步骤计时器。

    使用示例:
        with progress_step('处理数据'):
            # do work
    """
    c = ProgressTracker.COLORS
    print(f"  {c['yellow']}◐{c['reset']} {name}...", end='', flush=True)
    start = time.time()
    try:
        yield
        elapsed = time.time() - start
        print(f"\r  {c['green']}●{c['reset']} {name:<40} {c['dim']}({elapsed:.1f}s){c['reset']}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"\r  {c['red']}✗{c['reset']} {name:<40} {c['dim']}({elapsed:.1f}s){c['reset']}")
        print(f"    {c['red']}错误: {e}{c['reset']}")
        raise


def print_banner(text: str, style: str = 'box'):
    """打印横幅"""
    c = ProgressTracker.COLORS
    if style == 'box':
        print(f"\n{c['cyan']}╔{'═' * (len(text) + 2)}╗{c['reset']}")
        print(f"{c['cyan']}║{c['reset']} {c['bold']}{text}{c['reset']} {c['cyan']}║{c['reset']}")
        print(f"{c['cyan']}╚{'═' * (len(text) + 2)}╝{c['reset']}\n")
    else:
        print(f"\n{c['bold']}{c['cyan']}═══ {text} ═══{c['reset']}\n")
