"""
综合报告生成器 — zbib 3.0

将所有分析结果整合成一个精美的 HTML 报告：
- 研究空白热力图
- 申请人评估
- 知识图谱
- 标书建议

使用示例:
    >>> from scripts.report_generator import generate_full_report
    >>> generate_full_report(project_dir)
"""

from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def _read_file(path: Path) -> str:
    """安全读取文件"""
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ''


def _read_csv(path: Path) -> pd.DataFrame | None:
    """安全读取 CSV"""
    if path.exists():
        return pd.read_csv(path, index_col=0)
    return None


def _image_to_base64(path: Path) -> str:
    """图片转 base64"""
    if not path.exists():
        return ''
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    suffix = path.suffix.lower()
    mime = 'image/png' if suffix == '.png' else 'image/jpeg'
    return f'data:{mime};base64,{data}'


def _markdown_to_html(md: str) -> str:
    """简单的 Markdown 转 HTML"""
    # 标题
    md = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
    md = re.sub(r'^## (.+)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
    md = re.sub(r'^# (.+)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)

    # 粗体
    md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)

    # 引用块
    md = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', md, flags=re.MULTILINE)

    # 列表
    md = re.sub(r'^- (.+)$', r'<li>\1</li>', md, flags=re.MULTILINE)
    md = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', md, flags=re.MULTILINE)

    # 表格 (简化处理)
    lines = md.split('\n')
    in_table = False
    result = []
    for line in lines:
        if '|' in line and not line.strip().startswith('|--'):
            if not in_table:
                result.append('<table class="data-table">')
                in_table = True
            cells = [c.strip() for c in line.split('|') if c.strip()]
            tag = 'th' if not any('<td>' in r for r in result[-3:] if '<t' in r) else 'td'
            result.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
        elif in_table and '|' not in line:
            result.append('</table>')
            in_table = False
            result.append(line)
        elif '|--' not in line:
            result.append(line)
    if in_table:
        result.append('</table>')

    # 段落
    html = '\n'.join(result)
    html = re.sub(r'\n\n+', '</p><p>', html)
    html = f'<p>{html}</p>'

    return html


def _build_heatmap_html(df: pd.DataFrame | None) -> str:
    """构建热力图 HTML"""
    if df is None:
        return ''

    html = '<table class="heatmap">'
    html += '<tr><th></th>' + ''.join(f'<th>{c}</th>' for c in df.columns) + '</tr>'
    for idx, row in df.iterrows():
        html += f'<tr><th>{idx}</th>'
        for val in row:
            intensity = min(val / 100, 1) if val > 0 else 0
            color = f'rgba(76, 175, 80, {intensity})' if val > 0 else '#2a2a3e'
            html += f'<td style="background:{color}">{int(val)}</td>'
        html += '</tr>'
    html += '</table>'
    return html


def generate_full_report(
    project_dir: str | Path,
    output_name: str = 'full_report.html',
) -> Path:
    """
    生成综合 HTML 报告。

    Args:
        project_dir: 项目目录路径
        output_name: 输出文件名

    Returns:
        生成的报告路径
    """
    project_dir = Path(project_dir)
    results_dir = project_dir / 'results'
    figs_dir = project_dir / 'figs'

    # 收集数据
    heatmap_df = _read_csv(results_dir / 'heatmap.csv')
    nsfc_report = _read_file(results_dir / 'NSFC标书支撑材料.md')
    applicant_summary = _read_file(results_dir / 'applicant_summary.txt')
    template_md = _read_file(results_dir / '标书段落模板.md')

    # 图片
    landscape_img = ''
    for f in figs_dir.glob('*landscape*.png'):
        landscape_img = _image_to_base64(f)
        break

    applicant_img = ''
    for f in figs_dir.glob('*applicant_summary*.png'):
        applicant_img = _image_to_base64(f)
        break

    # 知识图谱 JSON
    kg_json = '{"nodes":[],"edges":[]}'
    kg_path = figs_dir / 'knowledge_graph.json'
    if kg_path.exists():
        kg_json = kg_path.read_text(encoding='utf-8')

    # 项目名称和时间
    project_name = project_dir.name
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 构建各部分 HTML
    heatmap_html = _build_heatmap_html(heatmap_df)

    # 全景图部分
    landscape_section = ''
    if landscape_img:
        landscape_section = f'''
        <section class="section">
            <h2>研究全景图</h2>
            <img src="{landscape_img}" alt="研究全景图" />
        </section>'''

    # 申请人部分
    applicant_section = ''
    if applicant_img or applicant_summary:
        img_tag = f'<img src="{applicant_img}" alt="申请人评估" style="max-width: 800px;" />' if applicant_img else ''
        pre_tag = f'<pre style="background:#0a0a15;padding:20px;border-radius:8px;overflow-x:auto;margin-top:20px;font-size:12px;">{applicant_summary}</pre>' if applicant_summary else ''
        applicant_section = f'''
        <section class="section">
            <h2>申请人评估</h2>
            {img_tag}
            {pre_tag}
        </section>'''

    # NSFC 和模板内容
    nsfc_html = _markdown_to_html(nsfc_report) if nsfc_report else '<p>暂无数据</p>'
    template_html = _markdown_to_html(template_md) if template_md else '<p>暂无数据</p>'

    # 组装完整 HTML
    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - 研究分析报告</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        :root {{
            --bg: #0f0f1a;
            --card-bg: #1a1a2e;
            --text: #e0e0e0;
            --text-dim: #888;
            --accent: #4CAF50;
            --accent2: #2196F3;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        header {{
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-bottom: 1px solid #333;
        }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; color: #fff; }}
        header p {{ color: var(--text-dim); }}
        .section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
            margin: 30px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .section h2 {{
            color: var(--accent);
            border-bottom: 2px solid var(--accent);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .section h3 {{ color: var(--accent2); margin: 20px 0 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 20px;
        }}
        .card h4 {{ color: var(--accent); margin-bottom: 10px; }}
        .heatmap {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .heatmap th, .heatmap td {{
            padding: 8px 12px;
            text-align: center;
            border: 1px solid #333;
        }}
        .heatmap th {{ background: #252540; color: var(--accent); }}
        .data-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .data-table th, .data-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        .data-table th {{ color: var(--accent); }}
        blockquote {{
            border-left: 3px solid var(--accent);
            padding-left: 15px;
            margin: 15px 0;
            color: var(--text-dim);
            font-style: italic;
        }}
        img {{ max-width: 100%; border-radius: 8px; margin: 20px 0; }}
        #kg-mini {{ height: 400px; background: #0a0a15; border-radius: 8px; overflow: hidden; }}
        .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .tab {{
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 6px;
            color: var(--text);
            cursor: pointer;
        }}
        .tab.active {{ background: var(--accent); color: #000; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        footer {{
            text-align: center;
            padding: 40px;
            color: var(--text-dim);
            font-size: 0.9em;
        }}
        footer a {{ color: var(--accent); text-decoration: none; }}
    </style>
</head>
<body>
    <header>
        <h1>{project_name}</h1>
        <p>研究空白分析报告 | 生成时间: {gen_time}</p>
    </header>

    <div class="container">
        <section class="section">
            <h2>数据概览</h2>
            <div class="grid">
                <div class="card">
                    <h4>研究空白矩阵</h4>
                    {heatmap_html if heatmap_html else '<p>暂无数据</p>'}
                </div>
            </div>
        </section>

        {landscape_section}
        {applicant_section}

        <section class="section">
            <h2>知识图谱</h2>
            <p style="color:var(--text-dim);margin-bottom:15px;">交互式知识图谱请打开 <code>figs/knowledge_graph.html</code></p>
            <div id="kg-mini"></div>
        </section>

        <section class="section">
            <h2>标书撰写建议</h2>
            <div class="tabs">
                <button class="tab active" onclick="showTab('nsfc')">NSFC支撑材料</button>
                <button class="tab" onclick="showTab('template')">段落模板</button>
            </div>
            <div id="nsfc" class="tab-content active">
                {nsfc_html}
            </div>
            <div id="template" class="tab-content">
                {template_html}
            </div>
        </section>
    </div>

    <footer>
        <p>由 zbib 3.0 自动生成 | 文献情报学空白挖掘工具</p>
    </footer>

    <script>
    function showTab(id) {{
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        event.target.classList.add('active');
    }}

    const kgData = {kg_json};
    if (kgData.nodes && kgData.nodes.length > 0) {{
        const width = document.getElementById('kg-mini').clientWidth;
        const height = 400;
        const svg = d3.select('#kg-mini').append('svg').attr('width', width).attr('height', height);
        const g = svg.append('g');

        const zoom = d3.zoom().scaleExtent([0.5, 5]).on('zoom', e => g.attr('transform', e.transform));
        svg.call(zoom);

        const simulation = d3.forceSimulation(kgData.nodes)
            .force('link', d3.forceLink(kgData.edges).id(d => d.id).distance(60))
            .force('charge', d3.forceManyBody().strength(-100))
            .force('center', d3.forceCenter(width/2, height/2));

        const link = g.selectAll('line').data(kgData.edges).join('line')
            .attr('stroke', '#333').attr('stroke-opacity', 0.6);

        const node = g.selectAll('circle').data(kgData.nodes).join('circle')
            .attr('r', d => Math.sqrt(d.weight || 1) * 2 + 4)
            .attr('fill', d => d.type === 'concept' ? '#4CAF50' : '#2196F3')
            .attr('stroke', d => d.is_key ? '#FFD700' : 'none')
            .attr('stroke-width', 2);

        node.append('title').text(d => d.label);

        simulation.on('tick', () => {{
            link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            node.attr('cx', d => d.x).attr('cy', d => d.y);
        }});
    }}
    </script>
</body>
</html>'''

    output_path = project_dir / output_name
    output_path.write_text(html, encoding='utf-8')
    print(f"[Report] 综合报告 -> {output_path}")

    return output_path
