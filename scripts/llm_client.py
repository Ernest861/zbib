"""
LLM 客户端模块 — zbib 3.0 智能摘要功能

提供基于大语言模型的文献分析能力：
- 研究现状自动摘要
- 关键文献智能提取
- 研究空白自然语言描述
- 创新性论证生成

支持的 LLM 后端：
- Anthropic Claude (默认)
- OpenAI GPT
- 本地模型 (Ollama)

使用示例:
    >>> from scripts.llm_client import LLMClient
    >>> client = LLMClient()
    >>> summary = client.summarize_research_landscape(papers_df, gap_data)
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════

@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: Literal['anthropic', 'openai', 'ollama'] = 'anthropic'
    model: str = 'claude-sonnet-4-20250514'
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.3

    def __post_init__(self):
        if self.api_key is None:
            if self.provider == 'anthropic':
                self.api_key = os.getenv('ANTHROPIC_API_KEY')
            elif self.provider == 'openai':
                self.api_key = os.getenv('OPENAI_API_KEY')


# ═══════════════════════════════════════════════
# Prompt 模板
# ═══════════════════════════════════════════════

PROMPTS = {
    'research_landscape': '''你是一位资深的文献计量学专家，正在协助撰写国家自然科学基金申请书。

基于以下文献数据和研究空白分析，请生成一段简洁的"研究现状"描述（300-400字），用于标书的"立项依据"部分。

## 文献数据概览
{data_overview}

## 研究空白分析
{gap_analysis}

## 要求
1. 客观陈述领域发展历程和当前热点
2. 突出研究空白的客观证据（引用具体数据）
3. 语言学术化，适合标书使用
4. 避免主观评价词（如"遗憾的是"）
5. 结尾自然引出本项目的必要性

请直接输出段落文本，不要加标题或编号。''',

    'key_papers_summary': '''你是一位神经科学领域的资深研究者，请对以下关键文献进行学术摘要。

## 文献列表
{papers}

## 要求
1. 每篇文献用1-2句话概括核心发现
2. 突出方法创新或结论的重要性
3. 适合放入标书的"研究基础"部分
4. 使用学术语言

请按以下格式输出：
1. [作者, 年份, 期刊]: 核心发现描述
2. ...''',

    'innovation_argument': '''你是一位经验丰富的基金评审专家，请基于以下研究空白数据，为申请人撰写"创新点"论述。

## 研究空白证据
{gap_evidence}

## 申请人优势
{applicant_strengths}

## 项目定位
靶点: {target}
症状维度: {symptom}
干预方式: {intervention}

## 要求
1. 提炼3个层次的创新点（靶点/机制/范式）
2. 每个创新点用客观数据支撑
3. 语言精炼，每个创新点控制在50字以内
4. 适合直接放入标书

请按以下格式输出：
**创新点一：[标题]**
[论述]

**创新点二：[标题]**
[论述]

**创新点三：[标题]**
[论述]''',

    'gap_narrative': '''基于以下症状×靶点研究空白矩阵，生成一段自然语言描述（150-200字）。

## 热力图数据
{heatmap}

## 要求
1. 指出研究最集中的区域
2. 指出研究最薄弱的区域（重点）
3. 量化对比（如"仅为...的X%"）
4. 客观陈述，不做价值判断

请直接输出段落。''',
}


# ═══════════════════════════════════════════════
# LLM 客户端
# ═══════════════════════════════════════════════

class LLMClient:
    """
    LLM 客户端，提供文献分析的智能摘要功能。

    支持多种后端：Anthropic Claude、OpenAI GPT、本地 Ollama。

    Attributes:
        config: LLM 配置
        _client: 底层 API 客户端

    Methods:
        summarize_research_landscape(): 生成研究现状摘要
        summarize_key_papers(): 摘要关键文献
        generate_innovation_argument(): 生成创新点论述
        describe_research_gap(): 描述研究空白
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化 API 客户端"""
        if self.config.provider == 'anthropic':
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
                logger.info("LLM 客户端初始化成功 (Anthropic)")
            except ImportError:
                logger.warning("anthropic 包未安装，LLM 功能不可用")
            except Exception as e:
                logger.warning("Anthropic 客户端初始化失败: %s", e)

        elif self.config.provider == 'openai':
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.config.api_key)
                logger.info("LLM 客户端初始化成功 (OpenAI)")
            except ImportError:
                logger.warning("openai 包未安装，LLM 功能不可用")

        elif self.config.provider == 'ollama':
            # Ollama 使用 HTTP API
            self.config.base_url = self.config.base_url or 'http://localhost:11434'
            logger.info("LLM 客户端初始化成功 (Ollama @ %s)", self.config.base_url)

    @property
    def available(self) -> bool:
        """检查 LLM 是否可用"""
        if self.config.provider == 'ollama':
            return True  # Ollama 通过 HTTP 调用
        return self._client is not None

    def _call(self, prompt: str) -> str:
        """调用 LLM API"""
        if not self.available:
            return "[LLM 不可用，请配置 API Key]"

        try:
            if self.config.provider == 'anthropic':
                response = self._client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif self.config.provider == 'openai':
                response = self._client.chat.completions.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content

            elif self.config.provider == 'ollama':
                import requests
                response = requests.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=120
                )
                return response.json().get('response', '')

        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            return f"[LLM 调用失败: {e}]"

    # ─── 公开方法 ───

    def summarize_research_landscape(
        self,
        papers_df: pd.DataFrame,
        gap_data: dict[str, Any],
    ) -> str:
        """
        生成研究现状摘要。

        Args:
            papers_df: 文献 DataFrame (需包含 title, year, journal 列)
            gap_data: 研究空白数据 (来自 GapAnalyzer)

        Returns:
            研究现状段落文本
        """
        # 构建数据概览
        n_papers = len(papers_df)
        year_range = f"{papers_df['year'].min()}-{papers_df['year'].max()}" if 'year' in papers_df else "N/A"
        top_journals = papers_df['journal'].value_counts().head(5).to_dict() if 'journal' in papers_df else {}

        data_overview = f"""- 文献总量: {n_papers} 篇
- 时间跨度: {year_range}
- 主要期刊: {', '.join(f"{j}({c})" for j, c in top_journals.items())}"""

        # 构建空白分析
        gap_analysis = json.dumps(gap_data, ensure_ascii=False, indent=2)

        prompt = PROMPTS['research_landscape'].format(
            data_overview=data_overview,
            gap_analysis=gap_analysis
        )

        return self._call(prompt)

    def summarize_key_papers(
        self,
        papers: list[dict[str, Any]],
    ) -> str:
        """
        摘要关键文献。

        Args:
            papers: 文献列表，每篇需包含 title, authors, year, journal, abstract

        Returns:
            结构化的文献摘要
        """
        papers_text = "\n".join([
            f"- [{p.get('authors', 'N/A')}, {p.get('year', 'N/A')}, {p.get('journal', 'N/A')}]\n"
            f"  标题: {p.get('title', 'N/A')}\n"
            f"  摘要: {p.get('abstract', 'N/A')[:500]}..."
            for p in papers[:10]  # 限制数量
        ])

        prompt = PROMPTS['key_papers_summary'].format(papers=papers_text)
        return self._call(prompt)

    def generate_innovation_argument(
        self,
        gap_evidence: dict[str, Any],
        applicant_strengths: dict[str, Any],
        target: str,
        symptom: str,
        intervention: str = 'rTMS',
    ) -> str:
        """
        生成创新点论述。

        Args:
            gap_evidence: 研究空白证据
            applicant_strengths: 申请人优势数据
            target: 干预靶点
            symptom: 症状维度
            intervention: 干预方式

        Returns:
            三个创新点的结构化文本
        """
        prompt = PROMPTS['innovation_argument'].format(
            gap_evidence=json.dumps(gap_evidence, ensure_ascii=False, indent=2),
            applicant_strengths=json.dumps(applicant_strengths, ensure_ascii=False, indent=2),
            target=target,
            symptom=symptom,
            intervention=intervention,
        )

        return self._call(prompt)

    def describe_research_gap(
        self,
        heatmap_df: pd.DataFrame,
    ) -> str:
        """
        描述研究空白（基于热力图数据）。

        Args:
            heatmap_df: 症状×靶点矩阵 DataFrame

        Returns:
            研究空白的自然语言描述
        """
        # 使用 CSV 格式，兼容性更好
        heatmap_text = heatmap_df.to_csv()
        prompt = PROMPTS['gap_narrative'].format(heatmap=heatmap_text)
        return self._call(prompt)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

_default_client: LLMClient | None = None


def get_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """获取默认 LLM 客户端（单例）"""
    global _default_client
    if _default_client is None or config is not None:
        _default_client = LLMClient(config)
    return _default_client


def llm_summarize_landscape(papers_df: pd.DataFrame, gap_data: dict) -> str:
    """便捷函数：生成研究现状摘要"""
    return get_llm_client().summarize_research_landscape(papers_df, gap_data)


def llm_summarize_papers(papers: list[dict]) -> str:
    """便捷函数：摘要关键文献"""
    return get_llm_client().summarize_key_papers(papers)


def llm_innovation_argument(gap: dict, strengths: dict, target: str, symptom: str) -> str:
    """便捷函数：生成创新点论述"""
    return get_llm_client().generate_innovation_argument(gap, strengths, target, symptom)


def llm_describe_gap(heatmap: pd.DataFrame) -> str:
    """便捷函数：描述研究空白"""
    return get_llm_client().describe_research_gap(heatmap)
