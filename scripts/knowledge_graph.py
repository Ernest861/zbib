"""
知识图谱模块 — zbib 3.0 研究前沿可视化

提供基于文献数据的知识图谱构建和可视化：
- 概念-作者-机构 三层网络
- 研究前沿演化分析
- 交互式可视化导出

数据结构:
    节点类型: concept, author, institution, paper
    边类型: writes, affiliated_with, cites, co_occurs

使用示例:
    >>> from scripts.knowledge_graph import KnowledgeGraph
    >>> kg = KnowledgeGraph()
    >>> kg.build_from_papers(papers_df)
    >>> kg.export_interactive('output.html')
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Any, Literal
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

@dataclass
class Node:
    """图谱节点"""
    id: str
    label: str
    type: Literal['concept', 'author', 'institution', 'paper']
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'label': self.label,
            'type': self.type,
            'weight': self.weight,
            **self.metadata
        }


@dataclass
class Edge:
    """图谱边"""
    source: str
    target: str
    type: Literal['writes', 'affiliated_with', 'cites', 'co_occurs']
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'weight': self.weight,
            **self.metadata
        }


# ═══════════════════════════════════════════════
# 知识图谱
# ═══════════════════════════════════════════════

class KnowledgeGraph:
    """
    文献知识图谱。

    支持从 PubMed/NSFC/NIH 数据构建多层网络：
    - 概念层: 关键词共现网络
    - 作者层: 合作网络
    - 时序层: 研究前沿演化

    Attributes:
        nodes: 节点字典 {id: Node}
        edges: 边列表

    Methods:
        build_from_papers(): 从文献 DataFrame 构建
        build_concept_layer(): 构建概念共现网络
        build_author_layer(): 构建作者合作网络
        detect_communities(): 社区检测
        export_json(): 导出 JSON
        export_interactive(): 导出交互式 HTML
    """

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._concept_cooccur: Counter = Counter()
        self._author_collab: Counter = Counter()

    def clear(self):
        """清空图谱"""
        self.nodes.clear()
        self.edges.clear()
        self._concept_cooccur.clear()
        self._author_collab.clear()

    # ─── 构建方法 ───

    def build_from_papers(
        self,
        df: pd.DataFrame,
        concept_col: str | list[str] = 'keywords',
        author_col: str = 'authors',
        year_col: str = 'year',
        title_col: str = 'title',
        min_concept_freq: int = 3,
        min_author_freq: int = 2,
        auto_adjust: bool = True,
    ) -> 'KnowledgeGraph':
        """
        从文献 DataFrame 构建完整知识图谱。

        Args:
            df: 文献数据，需包含关键词和作者列
            concept_col: 关键词列名，可以是单列名或列名列表（会合并）
            author_col: 作者列名
            year_col: 年份列名
            title_col: 标题列名（用于补充提取关键词）
            min_concept_freq: 概念最小出现频次
            min_author_freq: 作者最小出现频次
            auto_adjust: 是否根据数据量自动调整阈值

        Returns:
            self (链式调用)
        """
        self.clear()

        n_papers = len(df)

        # 自动调整阈值（小数据集降低要求）
        if auto_adjust:
            if n_papers < 20:
                min_concept_freq = 1
                min_author_freq = 1
            elif n_papers < 50:
                min_concept_freq = min(2, min_concept_freq)
                min_author_freq = min(2, min_author_freq)
            logger.info(f"数据量 {n_papers}，调整阈值: concept>={min_concept_freq}, author>={min_author_freq}")

        # 合并多个概念列
        concept_cols = [concept_col] if isinstance(concept_col, str) else concept_col
        # 自动检测可用列
        available_cols = [c for c in concept_cols if c in df.columns]
        # 也检查 mesh 列
        if 'mesh' in df.columns and 'mesh' not in available_cols:
            available_cols.append('mesh')

        if available_cols:
            self._build_concept_layer_multi(df, available_cols, year_col, title_col, min_concept_freq)

        # 构建作者层
        if author_col in df.columns:
            self._build_author_layer(df, author_col, min_author_freq)

        # 构建作者-概念跨层链接
        if available_cols and author_col in df.columns:
            self._build_author_concept_links(df, available_cols, author_col, title_col)

        logger.info(
            "知识图谱构建完成: %d 节点, %d 边",
            len(self.nodes), len(self.edges)
        )
        return self

    def _build_concept_layer_multi(
        self,
        df: pd.DataFrame,
        concept_cols: list[str],
        year_col: str,
        title_col: str,
        min_freq: int,
    ):
        """从多列构建概念共现网络，并从标题补充提取"""
        concept_freq = Counter()
        concept_years = defaultdict(list)

        # 定义常见停用词和无意义词
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'to', 'for', 'with',
            'on', 'by', 'at', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'study', 'studies', 'effect', 'effects',
            'using', 'based', 'analysis', 'results', 'data', 'patients', 'group',
            'subjects', 'methods', 'method', 'randomized', 'controlled', 'trial',
        }

        for _, row in df.iterrows():
            keywords = []
            year = row.get(year_col)

            # 从所有概念列收集关键词
            for col in concept_cols:
                keywords.extend(self._parse_list(row.get(col, '')))

            # 如果关键词太少，从标题提取重要术语
            if len(keywords) < 3 and title_col in df.columns:
                title = str(row.get(title_col, ''))
                title_terms = self._extract_title_terms(title, stopwords)
                keywords.extend(title_terms)

            # 标准化关键词
            keywords = self._normalize_keywords(keywords)

            # 统计频次
            for kw in keywords:
                concept_freq[kw] += 1
                if year:
                    concept_years[kw].append(year)

            # 统计共现
            unique_kws = list(set(keywords))
            for i, kw1 in enumerate(unique_kws):
                for kw2 in unique_kws[i+1:]:
                    pair = tuple(sorted([kw1, kw2]))
                    self._concept_cooccur[pair] += 1

        # 添加概念节点
        for concept, freq in concept_freq.items():
            if freq >= min_freq:
                years = concept_years[concept]
                self.nodes[f"c:{concept}"] = Node(
                    id=f"c:{concept}",
                    label=concept,
                    type='concept',
                    weight=freq,
                    metadata={
                        'first_year': min(years) if years else None,
                        'last_year': max(years) if years else None,
                    }
                )

        # 添加共现边（小数据集降低共现阈值）
        min_cooccur = 1 if len(df) < 20 else 2
        valid_concepts = {c for c, f in concept_freq.items() if f >= min_freq}
        for (c1, c2), weight in self._concept_cooccur.items():
            if c1 in valid_concepts and c2 in valid_concepts and weight >= min_cooccur:
                self.edges.append(Edge(
                    source=f"c:{c1}",
                    target=f"c:{c2}",
                    type='co_occurs',
                    weight=weight,
                ))

        logger.info(f"概念层: {len([n for n in self.nodes.values() if n.type=='concept'])} 概念节点")

    def _extract_title_terms(self, title: str, stopwords: set) -> list[str]:
        """从标题提取重要术语"""
        import re
        # 分词
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        # 过滤停用词
        terms = [w for w in words if w not in stopwords]
        # 提取常见研究术语组合
        patterns = [
            r'\b(schizophrenia|psychosis|psychotic)\b',
            r'\b(rTMS|TMS|tDCS|neuromodulation)\b',
            r'\b(orbitofrontal|prefrontal|dlpfc|ofc)\b',
            r'\b(anxiety|depression|negative|positive|cognitive)\b',
            r'\b(EEG|fMRI|MRI|imaging)\b',
            r'\b(treatment|therapy|intervention)\b',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            terms.extend([m.lower() for m in matches])
        return list(set(terms))

    def _normalize_keywords(self, keywords: list[str]) -> list[str]:
        """标准化关键词"""
        normalized = []
        # 同义词映射
        synonyms = {
            'rtms': 'rTMS',
            'tms': 'TMS',
            'tdcs': 'tDCS',
            'ofc': 'OFC',
            'dlpfc': 'DLPFC',
            'fmri': 'fMRI',
            'eeg': 'EEG',
            'scz': 'schizophrenia',
            'sz': 'schizophrenia',
        }
        for kw in keywords:
            kw = kw.strip()
            if not kw or len(kw) < 2:
                continue
            # 标准化
            kw_lower = kw.lower()
            if kw_lower in synonyms:
                kw = synonyms[kw_lower]
            normalized.append(kw)
        return normalized

    def _build_concept_layer(
        self,
        df: pd.DataFrame,
        concept_col: str,
        year_col: str,
        min_freq: int,
    ):
        """构建概念共现网络（单列版本，保留兼容性）"""
        self._build_concept_layer_multi(df, [concept_col], year_col, 'title', min_freq)

    def _build_author_layer(
        self,
        df: pd.DataFrame,
        author_col: str,
        min_freq: int,
    ):
        """构建作者合作网络"""
        author_freq = Counter()

        for _, row in df.iterrows():
            authors = self._parse_list(row.get(author_col, ''))

            # 统计频次
            for auth in authors:
                author_freq[auth] += 1

            # 统计合作
            for i, a1 in enumerate(authors):
                for a2 in authors[i+1:]:
                    pair = tuple(sorted([a1, a2]))
                    self._author_collab[pair] += 1

        # 添加作者节点
        for author, freq in author_freq.items():
            if freq >= min_freq:
                self.nodes[f"a:{author}"] = Node(
                    id=f"a:{author}",
                    label=author,
                    type='author',
                    weight=freq,
                )

        # 添加合作边
        valid_authors = {a for a, f in author_freq.items() if f >= min_freq}
        for (a1, a2), weight in self._author_collab.items():
            if a1 in valid_authors and a2 in valid_authors:
                self.edges.append(Edge(
                    source=f"a:{a1}",
                    target=f"a:{a2}",
                    type='writes',
                    weight=weight,
                ))

    def _build_author_concept_links(
        self,
        df: pd.DataFrame,
        concept_cols: list[str],
        author_col: str,
        title_col: str,
    ):
        """构建作者-概念跨层链接"""
        # 收集每个作者研究的概念
        author_concepts = defaultdict(Counter)

        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'to', 'for', 'with',
            'on', 'by', 'at', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'study', 'studies', 'effect', 'effects', 'using', 'based', 'analysis',
            'results', 'data', 'patients', 'group', 'subjects', 'methods',
        }

        for _, row in df.iterrows():
            authors = self._parse_list(row.get(author_col, ''))
            keywords = []

            # 收集概念
            for col in concept_cols:
                keywords.extend(self._parse_list(row.get(col, '')))

            # 从标题补充
            if title_col in df.columns:
                title = str(row.get(title_col, ''))
                title_terms = self._extract_title_terms(title, stopwords)
                keywords.extend(title_terms)

            keywords = self._normalize_keywords(keywords)

            # 记录每个作者与概念的关联
            for author in authors:
                for concept in keywords:
                    author_concepts[author][concept] += 1

        # 只为图中已有的节点建立链接
        valid_authors = {n.label for n in self.nodes.values() if n.type == 'author'}
        valid_concepts = {n.label for n in self.nodes.values() if n.type == 'concept'}

        cross_links = Counter()
        for author, concepts in author_concepts.items():
            if author not in valid_authors:
                continue
            for concept, count in concepts.items():
                if concept in valid_concepts:
                    cross_links[(author, concept)] += count

        # 添加跨层边（只保留权重>=1的链接）
        for (author, concept), weight in cross_links.items():
            if weight >= 1:
                self.edges.append(Edge(
                    source=f"a:{author}",
                    target=f"c:{concept}",
                    type='author_concept',
                    weight=weight,
                ))

        n_cross = len([e for e in self.edges if e.type == 'author_concept'])
        logger.info(f"跨层链接: {n_cross} 条作者-概念边")

    def _parse_list(self, value: Any) -> list[str]:
        """解析列表字段（支持字符串分隔和真实列表）"""
        if pd.isna(value) or value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        if isinstance(value, str):
            # 尝试多种分隔符
            for sep in [';', ',', '|']:
                if sep in value:
                    return [v.strip() for v in value.split(sep) if v.strip()]
            return [value.strip()] if value.strip() else []
        return []

    # ─── 分析方法 ───

    def get_top_concepts(self, n: int = 20) -> list[tuple[str, int]]:
        """获取高频概念"""
        concept_nodes = [
            (n.label, int(n.weight))
            for n in self.nodes.values()
            if n.type == 'concept'
        ]
        return sorted(concept_nodes, key=lambda x: -x[1])[:n]

    def get_top_authors(self, n: int = 20) -> list[tuple[str, int]]:
        """获取高产作者"""
        author_nodes = [
            (n.label, int(n.weight))
            for n in self.nodes.values()
            if n.type == 'author'
        ]
        return sorted(author_nodes, key=lambda x: -x[1])[:n]

    def get_concept_evolution(self) -> dict[str, dict]:
        """获取概念时序演化数据"""
        evolution = {}
        for node in self.nodes.values():
            if node.type == 'concept':
                evolution[node.label] = {
                    'weight': node.weight,
                    'first_year': node.metadata.get('first_year'),
                    'last_year': node.metadata.get('last_year'),
                }
        return evolution

    def compute_centrality(self) -> dict[str, float]:
        """
        计算节点度中心性。

        Returns:
            {node_id: centrality_score}
        """
        degree = defaultdict(int)
        for edge in self.edges:
            degree[edge.source] += edge.weight
            degree[edge.target] += edge.weight

        # 归一化
        max_degree = max(degree.values()) if degree else 1
        return {k: v / max_degree for k, v in degree.items()}

    def detect_communities(self) -> dict[str, int]:
        """
        简单社区检测（基于连通分量）。

        Returns:
            {node_id: community_id}
        """
        # 构建邻接表
        adj = defaultdict(set)
        for edge in self.edges:
            adj[edge.source].add(edge.target)
            adj[edge.target].add(edge.source)

        # BFS 找连通分量
        visited = set()
        communities = {}
        community_id = 0

        for node_id in self.nodes:
            if node_id in visited:
                continue

            # BFS
            queue = [node_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                communities[current] = community_id

                for neighbor in adj[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            community_id += 1

        return communities

    def get_key_nodes(self, top_n: int = 10) -> list[str]:
        """获取关键节点（高中心性）"""
        centrality = self.compute_centrality()
        sorted_nodes = sorted(centrality.items(), key=lambda x: -x[1])
        return [node_id for node_id, _ in sorted_nodes[:top_n]]

    # ─── 导出方法 ───

    def to_dict(self, include_analysis: bool = True) -> dict:
        """
        转换为字典。

        Args:
            include_analysis: 是否包含中心性和社区分析
        """
        # 基础数据
        nodes_data = [n.to_dict() for n in self.nodes.values()]
        edges_data = [e.to_dict() for e in self.edges]

        # 添加分析数据
        if include_analysis and self.nodes:
            centrality = self.compute_centrality()
            communities = self.detect_communities()
            key_nodes = set(self.get_key_nodes(10))

            for node in nodes_data:
                node['centrality'] = centrality.get(node['id'], 0)
                node['community'] = communities.get(node['id'], 0)
                node['is_key'] = node['id'] in key_nodes

        return {
            'nodes': nodes_data,
            'edges': edges_data,
        }

    def export_json(self, path: str | Path) -> None:
        """导出 JSON 文件"""
        path = Path(path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info("知识图谱已导出: %s", path)

    def export_interactive(self, path: str | Path, title: str = '研究知识图谱') -> None:
        """
        导出交互式 HTML 可视化。

        使用 D3.js force-directed graph 实现交互式探索。
        增强功能：
        - 阈值控制滑块
        - 节点数量限制
        - 中心性计算方法选择
        - 视图模式切换（概念/作者/联动）
        """
        path = Path(path)
        data = self.to_dict()

        # 同时导出 JSON 供报告使用
        json_path = path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        # 节点颜色映射 (绿白紫配色)
        type_colors = {
            'concept': '#2E7D32',   # 深绿色 - 概念
            'author': '#7B1FA2',    # 紫色 - 作者
            'institution': '#FF6F00',
            'paper': '#1565C0',
        }

        html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: -apple-system, sans-serif; background: #fafafa; overflow: hidden; }}
        #graph {{ width: 100vw; height: 100vh; background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%); }}
        .node {{ cursor: grab; }}
        .node:active {{ cursor: grabbing; }}
        .node text {{ font-size: 10px; fill: #333; pointer-events: none;
                     text-shadow: 0 0 3px #fff, 0 0 5px #fff, 1px 1px 2px #fff, -1px -1px 2px #fff; }}
        .node.dimmed {{ opacity: 0.1; }}
        .node.highlighted circle {{ stroke: #333; stroke-width: 3; }}
        .node.hidden {{ display: none; }}
        .link {{ stroke: #bbb; stroke-opacity: 0.4; stroke-linecap: round; }}
        .link.dimmed {{ opacity: 0.03; }}
        .link.hidden {{ display: none; }}
        .link.co_occurs {{ stroke: #2E7D32; }}
        .link.writes {{ stroke: #7B1FA2; }}
        .link.author_concept {{ stroke: #E91E63; stroke-dasharray: 6,4; }}
        .tooltip {{ position: absolute; background: #fff; color: #333; padding: 10px 14px;
                   border-radius: 8px; font-size: 12px; pointer-events: none; z-index: 1000;
                   max-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); border: 1px solid #e0e0e0; }}
        h1 {{ position: absolute; top: 15px; left: 20px; color: #333; margin: 0; font-size: 18px; z-index: 100; }}

        /* ─── 控制面板 ─── */
        #control-panel {{
            position: absolute; top: 15px; right: 20px;
            background: #fff; padding: 15px; border-radius: 12px;
            z-index: 100; width: 260px; color: #333; font-size: 12px;
            max-height: 90vh; overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;
        }}
        #control-panel h3 {{ margin: 0 0 12px; font-size: 14px; color: #2E7D32; border-bottom: 2px solid #4CAF50; padding-bottom: 8px; }}
        .control-group {{ margin-bottom: 15px; }}
        .control-group label {{ display: block; color: #666; margin-bottom: 5px; font-size: 11px; }}
        .control-group .value {{ float: right; color: #2E7D32; font-weight: bold; }}
        input[type="range"] {{ width: 100%; margin: 5px 0; accent-color: #4CAF50; }}
        select {{ width: 100%; padding: 8px; background: #f5f5f5; border: 1px solid #ddd; color: #333;
                 border-radius: 6px; margin-top: 5px; }}
        .btn-group {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .mode-btn {{ flex: 1; min-width: 70px; padding: 8px 5px; background: #f5f5f5;
                    border: 1px solid #ddd; color: #666; border-radius: 6px; cursor: pointer;
                    font-size: 11px; text-align: center; transition: all 0.2s; }}
        .mode-btn:hover {{ background: #e8f5e9; border-color: #4CAF50; }}
        .mode-btn.active {{ background: #e8f5e9; border-color: #2E7D32; color: #2E7D32; font-weight: bold; }}
        #search {{ width: 100%; padding: 8px; background: #f5f5f5; border: 1px solid #ddd;
                  color: #333; border-radius: 6px; outline: none; margin-bottom: 10px; }}
        #search:focus {{ border-color: #4CAF50; background: #fff; }}
        #search::placeholder {{ color: #999; }}

        /* ─── 统计信息 ─── */
        #stats-panel {{ background: #f8f9fa; padding: 12px; border-radius: 8px; margin-top: 10px; border: 1px solid #e0e0e0; }}
        #stats-panel .stat-row {{ display: flex; justify-content: space-between; margin: 3px 0; }}
        #stats-panel .stat-label {{ color: #666; }}
        #stats-panel .stat-value {{ color: #333; font-weight: bold; }}
        .legend-item {{ display: flex; align-items: center; margin: 4px 0; }}
        .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
        .legend-line {{ width: 20px; height: 3px; margin-right: 8px; }}

        /* ─── 底部控制 ─── */
        #bottom-controls {{ position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                           background: #fff; padding: 8px 15px; border-radius: 8px; z-index: 100;
                           display: flex; gap: 8px; align-items: center;
                           box-shadow: 0 2px 10px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }}
        #bottom-controls button {{ background: #f5f5f5; border: 1px solid #ddd; color: #333;
                                   width: 32px; height: 32px; border-radius: 6px; cursor: pointer; font-size: 16px; }}
        #bottom-controls button:hover {{ background: #e8f5e9; border-color: #4CAF50; }}
        #tips {{ color: #888; font-size: 10px; margin-left: 10px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>

    <div id="control-panel">
        <h3>图谱控制</h3>

        <input type="text" id="search" placeholder="搜索节点..." />

        <div class="control-group">
            <label>视图模式</label>
            <div class="btn-group">
                <button class="mode-btn active" data-mode="all">全部联动</button>
                <button class="mode-btn" data-mode="concept">仅概念</button>
                <button class="mode-btn" data-mode="author">仅作者</button>
            </div>
        </div>

        <div class="control-group">
            <label>最小频次 <span class="value" id="freq-value">2</span></label>
            <input type="range" id="min-freq" min="1" max="10" value="2" />
        </div>

        <div class="control-group">
            <label>最大节点数 <span class="value" id="max-nodes-value">50</span></label>
            <input type="range" id="max-nodes" min="10" max="200" value="50" />
        </div>

        <div class="control-group">
            <label>最小边权重 <span class="value" id="edge-weight-value">1</span></label>
            <input type="range" id="min-edge-weight" min="1" max="10" value="1" />
        </div>

        <div class="control-group">
            <label>节点间距 <span class="value" id="spacing-value">150</span></label>
            <input type="range" id="node-spacing" min="50" max="300" value="150" />
        </div>

        <div class="control-group">
            <label>排斥力 <span class="value" id="repulsion-value">-300</span></label>
            <input type="range" id="repulsion" min="-800" max="-50" value="-300" />
        </div>

        <div class="control-group">
            <label>中心性计算</label>
            <select id="centrality-method">
                <option value="degree">度中心性 (连接数)</option>
                <option value="weight">权重中心性 (频次)</option>
                <option value="pagerank">PageRank (重要性)</option>
            </select>
        </div>

        <div class="control-group">
            <label>节点大小</label>
            <select id="node-size-by">
                <option value="weight">按频次</option>
                <option value="centrality">按中心性</option>
                <option value="fixed">固定大小</option>
            </select>
        </div>

        <div class="control-group">
            <label>
                <input type="checkbox" id="show-labels" checked style="margin-right:5px;">
                显示标签
            </label>
        </div>

        <div class="control-group">
            <label>
                <input type="checkbox" id="show-cross-links" checked style="margin-right:5px;">
                显示跨层链接
            </label>
        </div>

        <div id="stats-panel">
            <div style="font-weight:bold;color:#333;margin-bottom:8px;">节点类型</div>
            <div class="legend-item"><div class="legend-dot" style="background:#2E7D32"></div>概念 <span id="concept-count" style="margin-left:auto;color:#2E7D32;font-weight:bold"></span></div>
            <div class="legend-item"><div class="legend-dot" style="background:#7B1FA2"></div>作者 <span id="author-count" style="margin-left:auto;color:#7B1FA2;font-weight:bold"></span></div>
            <div class="legend-item"><div class="legend-dot" style="background:#fff;border:3px solid #FF9800"></div>关键节点</div>
            <hr style="border-color:#e0e0e0;margin:10px 0;">
            <div style="font-weight:bold;color:#333;margin-bottom:8px;">边类型</div>
            <div class="legend-item"><div class="legend-line" style="background:#4CAF50"></div>概念共现</div>
            <div class="legend-item"><div class="legend-line" style="background:#9C27B0"></div>作者合作</div>
            <div class="legend-item"><div class="legend-line" style="background:#E91E63;border-style:dashed"></div>作者-概念</div>
            <hr style="border-color:#e0e0e0;margin:10px 0;">
            <div class="stat-row"><span class="stat-label">显示节点</span><span class="stat-value" id="visible-nodes">0</span></div>
            <div class="stat-row"><span class="stat-label">显示边</span><span class="stat-value" id="visible-edges">0</span></div>
            <div class="stat-row"><span class="stat-label">跨层链接</span><span class="stat-value" id="cross-link-count">0</span></div>
        </div>
    </div>

    <div id="graph"></div>

    <div id="bottom-controls">
        <button id="zoom-in" title="放大">+</button>
        <button id="zoom-out" title="缩小">-</button>
        <button id="zoom-reset" title="重置">R</button>
        <button id="export-png" title="导出PNG">P</button>
        <span id="tips">滚轮缩放 | 双击聚焦 | ESC重置</span>
    </div>

    <div class="tooltip" style="display:none"></div>

    <script>
    // ═══════════════════════════════════════════════
    // 数据与配置
    // ═══════════════════════════════════════════════
    const rawData = {data_json};
    const width = window.innerWidth;
    const height = window.innerHeight;
    const typeColors = {type_colors};

    // 状态变量
    let currentMode = 'all';  // all, concept, author
    let minFreq = 2;
    let maxNodes = 50;
    let minEdgeWeight = 1;
    let nodeSpacing = 150;
    let repulsion = -300;
    let centralityMethod = 'degree';
    let nodeSizeBy = 'weight';
    let showLabels = true;
    let showCrossLinks = true;

    // ═══════════════════════════════════════════════
    // 中心性计算
    // ═══════════════════════════════════════════════
    function computeCentrality(nodes, edges, method) {{
        const scores = {{}};
        nodes.forEach(n => scores[n.id] = 0);

        if (method === 'degree') {{
            edges.forEach(e => {{
                const sid = typeof e.source === 'object' ? e.source.id : e.source;
                const tid = typeof e.target === 'object' ? e.target.id : e.target;
                scores[sid] = (scores[sid] || 0) + 1;
                scores[tid] = (scores[tid] || 0) + 1;
            }});
        }} else if (method === 'weight') {{
            nodes.forEach(n => scores[n.id] = n.weight || 1);
        }} else if (method === 'pagerank') {{
            // 简化版 PageRank
            const d = 0.85, iterations = 20;
            const N = nodes.length || 1;
            nodes.forEach(n => scores[n.id] = 1 / N);

            const adj = {{}};
            nodes.forEach(n => adj[n.id] = []);
            edges.forEach(e => {{
                const sid = typeof e.source === 'object' ? e.source.id : e.source;
                const tid = typeof e.target === 'object' ? e.target.id : e.target;
                if (adj[sid]) adj[sid].push(tid);
                if (adj[tid]) adj[tid].push(sid);
            }});

            for (let i = 0; i < iterations; i++) {{
                const newScores = {{}};
                nodes.forEach(n => {{
                    let sum = 0;
                    adj[n.id].forEach(neighbor => {{
                        const outDegree = adj[neighbor]?.length || 1;
                        sum += (scores[neighbor] || 0) / outDegree;
                    }});
                    newScores[n.id] = (1 - d) / N + d * sum;
                }});
                Object.assign(scores, newScores);
            }}
        }}

        // 归一化
        const maxScore = Math.max(...Object.values(scores)) || 1;
        Object.keys(scores).forEach(k => scores[k] /= maxScore);
        return scores;
    }}

    // ═══════════════════════════════════════════════
    // 数据过滤
    // ═══════════════════════════════════════════════
    function filterData() {{
        let nodes = [...rawData.nodes];
        let edges = [...rawData.edges];

        // 1. 按模式过滤节点类型
        if (currentMode === 'concept') {{
            nodes = nodes.filter(n => n.type === 'concept');
        }} else if (currentMode === 'author') {{
            nodes = nodes.filter(n => n.type === 'author');
        }}

        // 2. 按最小频次过滤
        nodes = nodes.filter(n => (n.weight || 1) >= minFreq);

        // 3. 按中心性排序并限制数量
        const centrality = computeCentrality(nodes, edges, centralityMethod);
        nodes.forEach(n => n.centrality = centrality[n.id] || 0);
        nodes.sort((a, b) => b.centrality - a.centrality);
        nodes = nodes.slice(0, maxNodes);

        // 4. 标记关键节点 (Top 10)
        const keyIds = new Set(nodes.slice(0, 10).map(n => n.id));
        nodes.forEach(n => n.is_key = keyIds.has(n.id));

        // 5. 过滤边 - 连接存在的节点
        const nodeIds = new Set(nodes.map(n => n.id));
        edges = edges.filter(e => {{
            const sid = typeof e.source === 'object' ? e.source.id : e.source;
            const tid = typeof e.target === 'object' ? e.target.id : e.target;
            return nodeIds.has(sid) && nodeIds.has(tid);
        }});

        // 6. 按边权重过滤
        edges = edges.filter(e => (e.weight || 1) >= minEdgeWeight);

        // 7. 按模式过滤边类型
        if (currentMode === 'concept') {{
            edges = edges.filter(e => e.type === 'co_occurs');
        }} else if (currentMode === 'author') {{
            edges = edges.filter(e => e.type === 'writes');
        }} else {{
            // all 模式下根据开关过滤跨层链接
            if (!showCrossLinks) {{
                edges = edges.filter(e => e.type !== 'author_concept');
            }}
        }}

        return {{ nodes, edges }};
    }}

    // ═══════════════════════════════════════════════
    // 节点大小计算
    // ═══════════════════════════════════════════════
    function getNodeRadius(d) {{
        if (nodeSizeBy === 'fixed') return 10;
        if (nodeSizeBy === 'centrality') return Math.sqrt(d.centrality || 0.1) * 20 + 6;
        return Math.sqrt(d.weight || 1) * 4 + 6;
    }}

    // ═══════════════════════════════════════════════
    // 更新统计
    // ═══════════════════════════════════════════════
    function updateStats(nodes, edges) {{
        const concepts = nodes.filter(n => n.type === 'concept').length;
        const authors = nodes.filter(n => n.type === 'author').length;
        const crossLinks = edges.filter(e => e.type === 'author_concept').length;

        document.getElementById('concept-count').textContent = concepts;
        document.getElementById('author-count').textContent = authors;
        document.getElementById('visible-nodes').textContent = nodes.length;
        document.getElementById('visible-edges').textContent = edges.length;
        document.getElementById('cross-link-count').textContent = crossLinks;
    }}

    // ═══════════════════════════════════════════════
    // 创建图谱
    // ═══════════════════════════════════════════════
    const svg = d3.select("#graph").append("svg").attr("width", width).attr("height", height);
    const container = svg.append("g");

    const zoom = d3.zoom().scaleExtent([0.1, 10]).on("zoom", e => container.attr("transform", e.transform));
    svg.call(zoom);

    let simulation, link, node;
    const tooltip = d3.select(".tooltip");

    function renderGraph() {{
        const data = filterData();
        updateStats(data.nodes, data.edges);

        // 清除旧图
        container.selectAll("*").remove();

        if (data.nodes.length === 0) return;

        // 力导向模拟 - 使用动态参数
        simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges).id(d => d.id).distance(nodeSpacing))
            .force("charge", d3.forceManyBody().strength(repulsion))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => getNodeRadius(d) + 15))
            .force("x", d3.forceX(width / 2).strength(0.03))
            .force("y", d3.forceY(height / 2).strength(0.03));

        // 边颜色映射
        const edgeColors = {{
            'co_occurs': '#4CAF50',
            'writes': '#9C27B0',
            'author_concept': '#E91E63'
        }};

        // 计算边权重范围用于透明度映射
        const edgeWeights = data.edges.map(e => e.weight || 1);
        const maxEdgeWeight = Math.max(...edgeWeights, 1);
        const minEdgeWeight = Math.min(...edgeWeights, 1);

        // 边 - 加粗线条，基于权重的透明度渐变
        link = container.append("g").selectAll("line").data(data.edges).join("line")
            .attr("class", d => "link " + d.type)
            .attr("stroke", d => edgeColors[d.type] || '#bbb')
            .attr("stroke-width", d => {{
                if (d.type === 'author_concept') return 1.5;
                // 基于权重的线宽: 2-6px
                const normalized = (d.weight - minEdgeWeight) / (maxEdgeWeight - minEdgeWeight + 0.01);
                return 2 + normalized * 4;
            }})
            .attr("stroke-dasharray", d => d.type === 'author_concept' ? "6,4" : "none")
            .attr("stroke-opacity", d => {{
                // 基于权重的透明度渐变: 跨层链接 0.15-0.4，其他 0.3-0.8
                const normalized = (d.weight - minEdgeWeight) / (maxEdgeWeight - minEdgeWeight + 0.01);
                if (d.type === 'author_concept') return 0.15 + normalized * 0.25;
                return 0.3 + normalized * 0.5;
            }});

        // 节点
        node = container.append("g").selectAll("g").data(data.nodes).join("g")
            .attr("class", "node")
            .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

        node.append("circle")
            .attr("r", d => getNodeRadius(d))
            .attr("fill", d => typeColors[d.type] || "#999")
            .attr("stroke", d => d.is_key ? "#FF9800" : "#fff")
            .attr("stroke-width", d => d.is_key ? 3 : 1.5);

        // 标签 (根据开关显示)
        if (showLabels) {{
            // 先添加白色背景矩形
            node.each(function(d) {{
                const g = d3.select(this);
                const label = d.label.length > 20 ? d.label.slice(0, 20) + "..." : d.label;
                const fontSize = d.is_key ? 11 : 10;
                const dx = getNodeRadius(d) + 5;

                // 临时文本测量宽度
                const tempText = g.append("text")
                    .attr("font-size", fontSize + "px")
                    .attr("visibility", "hidden")
                    .text(label);
                const bbox = tempText.node().getBBox();
                tempText.remove();

                // 背景矩形
                g.append("rect")
                    .attr("class", "label-bg")
                    .attr("x", dx - 2)
                    .attr("y", -fontSize / 2 - 2)
                    .attr("width", bbox.width + 4)
                    .attr("height", fontSize + 4)
                    .attr("fill", "rgba(255,255,255,0.85)")
                    .attr("rx", 2);

                // 文本标签
                g.append("text")
                    .attr("dx", dx)
                    .attr("dy", fontSize / 3)
                    .attr("font-weight", d.is_key ? "bold" : "normal")
                    .attr("font-size", fontSize + "px")
                    .text(label);
            }});
        }}

        // 提示框
        node.on("mouseover", (event, d) => {{
            const keyLabel = d.is_key ? '<br><span style="color:#FF9800">★ 关键节点</span>' : '';
            const typeLabel = d.type === 'concept' ? '概念' : '作者';
            tooltip.style("display", "block")
                .html(`<strong>${{d.label}}</strong><br>类型: ${{typeLabel}}<br>频次: ${{d.weight}}<br>中心性: ${{(d.centrality * 100).toFixed(1)}}%${{keyLabel}}`)
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px");
        }}).on("mouseout", () => tooltip.style("display", "none"));

        // 双击聚焦
        node.on('dblclick', (event, d) => {{
            event.stopPropagation();
            const neighborIds = new Set([d.id]);
            data.edges.forEach(e => {{
                const sid = typeof e.source === 'object' ? e.source.id : e.source;
                const tid = typeof e.target === 'object' ? e.target.id : e.target;
                if (sid === d.id) neighborIds.add(tid);
                if (tid === d.id) neighborIds.add(sid);
            }});
            node.classed('dimmed', n => !neighborIds.has(n.id));
            node.classed('highlighted', n => n.id === d.id);
            link.classed('dimmed', l => {{
                const sid = typeof l.source === 'object' ? l.source.id : l.source;
                const tid = typeof l.target === 'object' ? l.target.id : l.target;
                return !neighborIds.has(sid) || !neighborIds.has(tid);
            }});
        }});

        simulation.on("tick", () => {{
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});
    }}

    // 拖拽函数
    function dragstarted(event) {{
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }}
    function dragged(event) {{
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }}
    function dragended(event) {{
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }}

    // ═══════════════════════════════════════════════
    // 事件绑定
    // ═══════════════════════════════════════════════

    // 视图模式切换
    document.querySelectorAll('.mode-btn').forEach(btn => {{
        btn.addEventListener('click', () => {{
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            renderGraph();
        }});
    }});

    // 最小频次
    document.getElementById('min-freq').addEventListener('input', e => {{
        minFreq = parseInt(e.target.value);
        document.getElementById('freq-value').textContent = minFreq;
        renderGraph();
    }});

    // 最大节点数
    document.getElementById('max-nodes').addEventListener('input', e => {{
        maxNodes = parseInt(e.target.value);
        document.getElementById('max-nodes-value').textContent = maxNodes;
        renderGraph();
    }});

    // 中心性方法
    document.getElementById('centrality-method').addEventListener('change', e => {{
        centralityMethod = e.target.value;
        renderGraph();
    }});

    // 节点大小
    document.getElementById('node-size-by').addEventListener('change', e => {{
        nodeSizeBy = e.target.value;
        renderGraph();
    }});

    // 最小边权重
    document.getElementById('min-edge-weight').addEventListener('input', e => {{
        minEdgeWeight = parseInt(e.target.value);
        document.getElementById('edge-weight-value').textContent = minEdgeWeight;
        renderGraph();
    }});

    // 节点间距
    document.getElementById('node-spacing').addEventListener('input', e => {{
        nodeSpacing = parseInt(e.target.value);
        document.getElementById('spacing-value').textContent = nodeSpacing;
        renderGraph();
    }});

    // 排斥力
    document.getElementById('repulsion').addEventListener('input', e => {{
        repulsion = parseInt(e.target.value);
        document.getElementById('repulsion-value').textContent = repulsion;
        renderGraph();
    }});

    // 显示标签
    document.getElementById('show-labels').addEventListener('change', e => {{
        showLabels = e.target.checked;
        renderGraph();
    }});

    // 显示跨层链接
    document.getElementById('show-cross-links').addEventListener('change', e => {{
        showCrossLinks = e.target.checked;
        renderGraph();
    }});

    // 搜索
    document.getElementById('search').addEventListener('input', e => {{
        const query = e.target.value.toLowerCase();
        if (!query) {{
            node?.classed('highlighted', false).classed('dimmed', false);
            link?.classed('dimmed', false);
            return;
        }}
        node?.classed('highlighted', d => d.label.toLowerCase().includes(query));
        node?.classed('dimmed', d => !d.label.toLowerCase().includes(query));
        link?.classed('dimmed', true);
    }});

    // 缩放控制
    d3.select("#zoom-in").on("click", () => svg.transition().call(zoom.scaleBy, 1.5));
    d3.select("#zoom-out").on("click", () => svg.transition().call(zoom.scaleBy, 0.67));
    d3.select("#zoom-reset").on("click", () => svg.transition().call(zoom.transform, d3.zoomIdentity));

    // ESC 重置
    document.addEventListener('keydown', e => {{
        if (e.key === 'Escape') {{
            node?.classed('highlighted', false).classed('dimmed', false);
            link?.classed('dimmed', false);
            document.getElementById('search').value = '';
        }}
    }});

    svg.on('dblclick', () => {{
        node?.classed('highlighted', false).classed('dimmed', false);
        link?.classed('dimmed', false);
    }});

    // 导出 PNG
    document.getElementById('export-png').addEventListener('click', () => {{
        const svgEl = document.querySelector('#graph svg');
        const svgData = new XMLSerializer().serializeToString(svgEl);
        const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
        const url = URL.createObjectURL(svgBlob);
        const img = new Image();
        img.onload = () => {{
            const canvas = document.createElement('canvas');
            canvas.width = width * 2;
            canvas.height = height * 2;
            const ctx = canvas.getContext('2d');
            ctx.scale(2, 2);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0);
            const a = document.createElement('a');
            a.download = 'knowledge_graph.png';
            a.href = canvas.toDataURL('image/png');
            a.click();
            URL.revokeObjectURL(url);
        }};
        img.src = url;
    }});

    // 初始渲染
    renderGraph();
    </script>
</body>
</html>'''

        html = html_template.format(
            title=title,
            data_json=json.dumps(data, ensure_ascii=False),
            type_colors=json.dumps(type_colors),
            node_count=len(data['nodes']),
            edge_count=len(data['edges']),
        )

        path.write_text(html, encoding='utf-8')
        logger.info("交互式知识图谱已导出: %s", path)
        print(f"[KG] 交互式可视化 → {path}")


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def build_knowledge_graph(
    papers_df: pd.DataFrame,
    output_dir: str | Path,
    name: str = 'knowledge_graph',
) -> KnowledgeGraph:
    """
    便捷函数：从文献构建知识图谱并导出。

    Args:
        papers_df: 文献 DataFrame
        output_dir: 输出目录
        name: 输出文件名前缀

    Returns:
        构建好的 KnowledgeGraph 对象
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kg = KnowledgeGraph()
    kg.build_from_papers(papers_df)

    # 导出
    kg.export_json(output_dir / f"{name}.json")
    kg.export_interactive(output_dir / f"{name}.html", title='研究知识图谱')

    return kg
