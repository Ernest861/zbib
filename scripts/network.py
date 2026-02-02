"""网络分析: 合作网络(社会结构) + 关键词共现网络(概念结构)"""

import re
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
import networkx as nx


# ═══════════════════════════════════════════════
# 合作网络 (Social Structure)
# ═══════════════════════════════════════════════

class CollaborationNetwork:
    """Co-PI 合作网络

    从 NSFC "项目参与人" 字段构建合作图。
    字段格式: "姓名; 职称; 单位; 姓名; 职称; 单位; ..."
    """

    # 非姓名字段: 职称（精确匹配）和机构（含特征后缀）
    _TITLES = {
        '教授', '副教授', '讲师', '助教', '助理教授',
        '研究员', '副研究员', '助理研究员', '研究实习员',
        '主任医师', '副主任医师', '主治医师', '住院医师', '医师',
        '主任药师', '副主任药师', '主管药师',
        '主任护师', '副主任护师', '主管护师', '护师',
        '主任技师', '副主任技师', '主管技师', '技师', '技术员',
        '高级工程师', '工程师', '助理工程师',
        '实验师', '高级实验师', '博士后', '在读博士生', '在读硕士生',
        '实验员', '助理实验师',
    }
    _INST_SUFFIX = re.compile(r'大学|研究所|医院|中心|学院|公司|研究院|附属')

    def parse_collaborators(self, nsfc_df: pd.DataFrame,
                            pi_col: str = '负责人',
                            collab_col: str = '项目参与人') -> pd.DataFrame:
        """提取合作关系边表: (person_a, person_b, project_count)

        从每个项目的 PI + 参与人中提取所有两两合作对。
        """
        edges = Counter()

        for _, row in nsfc_df.iterrows():
            pi = str(row.get(pi_col, '')).strip()
            if not pi or pi == 'nan':
                continue

            # 解析参与人
            raw = str(row.get(collab_col, ''))
            if raw in ('nan', 'None', ''):
                members = [pi]
            else:
                parts = [p.strip() for p in re.split(r'[;；]', raw) if p.strip()]
                # 过滤掉职称（精确匹配）和单位（含机构后缀）
                names = [p for p in parts
                         if p not in self._TITLES and not self._INST_SUFFIX.search(p)]
                members = [pi] + names

            # 去重、标准化
            members = list(dict.fromkeys(self._normalize(n) for n in members if len(n) >= 2))

            # 生成所有两两对
            for a, b in combinations(members, 2):
                key = tuple(sorted([a, b]))
                edges[key] += 1

        rows = [{'source': k[0], 'target': k[1], 'weight': v} for k, v in edges.items()]
        return pd.DataFrame(rows)

    def build_graph(self, edges_df: pd.DataFrame, min_weight: int = 1) -> nx.Graph:
        """从边表构建 networkx 图"""
        G = nx.Graph()
        for _, row in edges_df.iterrows():
            if row['weight'] >= min_weight:
                G.add_edge(row['source'], row['target'], weight=row['weight'])
        return G

    def from_nsfc(self, nsfc_df: pd.DataFrame, min_weight: int = 1) -> nx.Graph:
        """一步构建合作网络"""
        edges = self.parse_collaborators(nsfc_df)
        return self.build_graph(edges, min_weight=min_weight)

    def centrality(self, G: nx.Graph, top_n: int = 20) -> pd.DataFrame:
        """计算节点中心性指标"""
        if len(G) == 0:
            return pd.DataFrame()

        degree = nx.degree_centrality(G)
        betweenness = nx.betweenness_centrality(G)
        try:
            eigenvector = nx.eigenvector_centrality(G, max_iter=500)
        except nx.PowerIterationFailedConvergence:
            eigenvector = {n: 0.0 for n in G.nodes()}

        df = pd.DataFrame({
            'name': list(G.nodes()),
            'degree': [G.degree(n) for n in G.nodes()],
            'degree_centrality': [round(degree[n], 4) for n in G.nodes()],
            'betweenness': [round(betweenness[n], 4) for n in G.nodes()],
            'eigenvector': [round(eigenvector[n], 4) for n in G.nodes()],
        }).sort_values('degree', ascending=False)

        return df.head(top_n)

    def communities(self, G: nx.Graph) -> dict[int, list[str]]:
        """Louvain 社区检测"""
        if len(G) == 0:
            return {}
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(G)
        except ImportError:
            # Fallback: connected components
            partition = {}
            for i, comp in enumerate(nx.connected_components(G)):
                for node in comp:
                    partition[node] = i

        result = {}
        for node, comm_id in partition.items():
            result.setdefault(comm_id, []).append(node)

        # Sort by community size
        return dict(sorted(result.items(), key=lambda x: -len(x[1])))

    def cross_institution_edges(self, G: nx.Graph, nsfc_df: pd.DataFrame,
                                pi_col: str = '负责人',
                                inst_col: str = '单位') -> float:
        """跨机构合作比例"""
        pi_inst = dict(zip(nsfc_df[pi_col].str.strip(), nsfc_df[inst_col].str.strip()))
        cross = 0
        total = 0
        for u, v in G.edges():
            inst_u = pi_inst.get(u, '')
            inst_v = pi_inst.get(v, '')
            if inst_u and inst_v:
                total += 1
                if inst_u != inst_v:
                    cross += 1
        return round(cross / max(total, 1), 3)

    def institution_network(self, nsfc_df: pd.DataFrame,
                            pi_col: str = '负责人',
                            collab_col: str = '项目参与人',
                            inst_col: str = '单位',
                            min_weight: int = 2) -> nx.Graph:
        """机构级合作网络

        如果同一项目中参与人来自不同机构，则机构间产生合作边。
        节点属性: n_projects, n_pis
        """
        # Build PI → institution mapping from collab data
        # Since collab field has "name; title; inst" pattern, we extract inst directly
        inst_edges = Counter()
        inst_projects = Counter()

        for _, row in nsfc_df.iterrows():
            pi = str(row.get(pi_col, '')).strip()
            pi_inst = str(row.get(inst_col, '')).strip()
            if not pi or pi == 'nan' or not pi_inst or pi_inst == 'nan':
                continue

            raw = str(row.get(collab_col, ''))
            if raw in ('nan', 'None', ''):
                continue

            # Extract institutions from collab field
            parts = [p.strip() for p in re.split(r'[;；]', raw) if p.strip()]
            collab_insts = set()
            for p in parts:
                if self._INST_SUFFIX.search(p):
                    collab_insts.add(p)
            collab_insts.add(pi_inst)

            inst_projects[pi_inst] += 1

            # Cross-institution edges
            inst_list = list(collab_insts)
            for a, b in combinations(inst_list, 2):
                key = tuple(sorted([a, b]))
                inst_edges[key] += 1

        G = nx.Graph()
        for inst, cnt in inst_projects.items():
            G.add_node(inst, n_projects=cnt)
        for (a, b), w in inst_edges.items():
            if w >= min_weight:
                G.add_edge(a, b, weight=w)
                # Ensure nodes exist
                for n in (a, b):
                    if n not in G.nodes:
                        G.add_node(n, n_projects=0)

        return G

    @staticmethod
    def largest_component(G: nx.Graph) -> nx.Graph:
        """返回最大连通分量"""
        if len(G) == 0:
            return G
        largest_cc = max(nx.connected_components(G), key=len)
        return G.subgraph(largest_cc).copy()

    @staticmethod
    def _normalize(name: str) -> str:
        """中文姓名标准化"""
        return name.strip().replace(' ', '').replace('\u3000', '')


# ═══════════════════════════════════════════════
# 关键词共现网络 (Conceptual Structure)
# ═══════════════════════════════════════════════

class ConceptNetwork:
    """关键词共现网络

    从关键词字段构建共现图，支持聚类和主题地图(thematic map)。
    """

    def __init__(self):
        self._cn_sep = re.compile(r'[;；、,，.]+')
        self._en_sep = re.compile(r'[;,]+')

    def from_keywords(self, df: pd.DataFrame, col: str,
                      lang: str = 'cn', min_freq: int = 3,
                      stopwords: set[str] | None = None) -> nx.Graph:
        """从关键词字段构建共现网络

        Parameters
        ----------
        min_freq : 关键词最低出现频次(过滤低频词)
        stopwords : 停用词集合

        使用向量化拆分 + 批量共现计数，支持大数据集。
        """
        import pandas as _pd
        sep_pat = r'[;；、,，.]+' if lang == 'cn' else r'[;,]+'
        stop = stopwords or set()
        stop_lower = {s.lower() for s in stop}

        # Step 1: 向量化拆分 → 每个文档一个词列表
        series = df[col].astype(str).replace({'nan': '', 'None': ''})
        series = series[series.str.len() > 0]

        # 拆分为列表
        split_series = series.str.split(sep_pat)

        # 统计词频 + 构建文档列表
        all_words = Counter()
        docs = []
        for words_raw in split_series:
            words = []
            for w in words_raw:
                w = w.strip()
                if lang == 'en':
                    w = w.lower()
                if len(w) < 2 or w.lower() in stop_lower:
                    continue
                words.append(w)
                all_words[w] += 1
            if words:
                docs.append(list(dict.fromkeys(words)))  # dedupe within doc

        valid = {w for w, c in all_words.items() if c >= min_freq}

        # Step 2: 共现计数 (限制每文档最多 top-20 词以控制组合爆炸)
        cooccur = Counter()
        max_per_doc = 20
        for words in docs:
            filtered = [w for w in words if w in valid][:max_per_doc]
            for a, b in combinations(filtered, 2):
                key = tuple(sorted([a, b]))
                cooccur[key] += 1

        # Step 3: 构建图
        G = nx.Graph()
        for w in valid:
            G.add_node(w, freq=all_words[w])
        for (a, b), weight in cooccur.items():
            G.add_edge(a, b, weight=weight)

        return G

    def clusters(self, G: nx.Graph, n_clusters: int = 5) -> dict[str, list[str]]:
        """基于 Louvain 的主题簇"""
        if len(G) == 0:
            return {}
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(G, resolution=1.0)
        except ImportError:
            return {'cluster_0': list(G.nodes())}

        groups = {}
        for node, cid in partition.items():
            groups.setdefault(cid, []).append(node)

        # Sort clusters by size, limit to top n
        sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))[:n_clusters]

        # Label clusters by highest-freq keyword
        result = {}
        for cid, members in sorted_groups:
            members.sort(key=lambda w: G.nodes[w].get('freq', 0), reverse=True)
            label = members[0]
            result[label] = members
        return result

    def thematic_map(self, G: nx.Graph) -> pd.DataFrame:
        """四象限主题地图数据

        对每个社区计算:
        - centrality (Callon's centrality): 社区与其他社区的连接强度
        - density: 社区内部连接的紧密度

        四象限:
        - 高centrality + 高density = Motor themes (核心主题)
        - 高centrality + 低density = Basic themes (基础但重要)
        - 低centrality + 高density = Niche themes (小众深入)
        - 低centrality + 低density = Emerging/declining themes
        """
        if len(G) == 0:
            return pd.DataFrame()

        try:
            import community as community_louvain
            partition = community_louvain.best_partition(G)
        except ImportError:
            return pd.DataFrame()

        groups = {}
        for node, cid in partition.items():
            groups.setdefault(cid, []).append(node)

        rows = []
        for cid, members in groups.items():
            if len(members) < 2:
                continue

            subG = G.subgraph(members)

            # Density: internal edge weight / possible edges
            internal_weight = sum(d.get('weight', 1) for _, _, d in subG.edges(data=True))
            possible = len(members) * (len(members) - 1) / 2
            density = internal_weight / max(possible, 1)

            # Centrality: external edge weight
            external_weight = 0
            for m in members:
                for neighbor in G.neighbors(m):
                    if neighbor not in members:
                        external_weight += G[m][neighbor].get('weight', 1)
            centrality = external_weight / max(len(members), 1)

            # Label by top-freq word
            members.sort(key=lambda w: G.nodes[w].get('freq', 0), reverse=True)
            label = members[0]
            top_words = members[:5]

            rows.append({
                'cluster_id': cid,
                'label': label,
                'top_words': '; '.join(top_words),
                'size': len(members),
                'centrality': round(centrality, 3),
                'density': round(density, 3),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Classify quadrant
        med_c = df['centrality'].median()
        med_d = df['density'].median()
        def _quadrant(row):
            if row['centrality'] >= med_c and row['density'] >= med_d:
                return 'Motor'
            elif row['centrality'] >= med_c and row['density'] < med_d:
                return 'Basic'
            elif row['centrality'] < med_c and row['density'] >= med_d:
                return 'Niche'
            else:
                return 'Emerging/Declining'
        df['quadrant'] = df.apply(_quadrant, axis=1)

        return df

    # ─── 时间窗口共现网络 ─────────────────────────
    def temporal_networks(self, df: pd.DataFrame, col: str, year_col: str,
                          window: int = 5, step: int = 5,
                          lang: str = 'cn', min_freq: int = 3,
                          stopwords: set[str] | None = None) -> list[dict]:
        """按时间窗口切片，每个窗口构建共现网络

        Returns list[dict]: 每个 dict 含 period, graph, thematic_map, top_nodes
        """
        years = df[year_col].dropna().astype(int)
        min_y, max_y = int(years.min()), int(years.max())

        results = []
        start = min_y
        while start <= max_y:
            end = start + window - 1
            period_df = df[(df[year_col] >= start) & (df[year_col] <= end)]

            if len(period_df) >= 5:
                # 小窗口降低 min_freq
                mf = max(2, min_freq - 1) if len(period_df) < 50 else min_freq
                G = self.from_keywords(period_df, col, lang=lang, min_freq=mf,
                                       stopwords=stopwords)
                if len(G) > 0:
                    thematic = self.thematic_map(G)
                    top_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:10]
                    results.append({
                        'period': f"{start}-{end}",
                        'graph': G,
                        'thematic_map': thematic,
                        'top_nodes': top_nodes,
                        'n_nodes': len(G),
                        'n_edges': G.number_of_edges(),
                    })

            start += step

        return results

    def network_evolution_summary(self, temporal: list[dict]) -> pd.DataFrame:
        """对比相邻时期网络: 新增/消失节点、社区变化

        Parameters
        ----------
        temporal : temporal_networks() 的返回值
        """
        rows = []
        for i, snap in enumerate(temporal):
            G = snap['graph']
            nodes = set(G.nodes())

            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
                n_clusters = len(set(partition.values()))
                modularity = round(community_louvain.modularity(partition, G), 3)
            except (ImportError, Exception):
                n_clusters = nx.number_connected_components(G)
                modularity = 0.0

            new_kw = set()
            lost_kw = set()
            if i > 0:
                prev_nodes = set(temporal[i - 1]['graph'].nodes())
                new_kw = nodes - prev_nodes
                lost_kw = prev_nodes - nodes

            rows.append({
                'period': snap['period'],
                'n_nodes': snap['n_nodes'],
                'n_edges': snap['n_edges'],
                'n_clusters': n_clusters,
                'modularity': modularity,
                'new_keywords': '; '.join(sorted(new_kw)[:10]),
                'lost_keywords': '; '.join(sorted(lost_kw)[:10]),
                'n_new': len(new_kw),
                'n_lost': len(lost_kw),
            })

        return pd.DataFrame(rows)
