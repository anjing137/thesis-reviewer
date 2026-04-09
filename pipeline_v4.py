"""
Pipeline v4: Python精准统计 + LLM深度评价架构 v3

设计理念：
- Python只做可量化指标：字数、文献数量、章节结构等精确统计
- 所有质量判断全部交给LLM：文献质量、创新性、方法匹配度、数据质量等
- Python统计作为上下文信息传递给LLM，LLM完全独立判断

流程：
1. 文档解析（Python）
2. 精准统计（Python）→ 统计数据（仅包含可量化指标）
3. 生成增强Prompt（包含统计+完整参考文献）
4. LLM深度评价（质量判断）→ 返回结构化JSON
5. Python解析JSON并生成最终格式化报告
"""

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime

# 导入解析器
try:
    from .parser.xml_parser import (
        parse_hierarchical, ThesisModules, ChapterModule,
        ParserError, FileNotFoundParserError, UnsupportedFormatError,
        EmptyDocumentError, PDFParseError, DOCXParseError
    )
except ImportError:
    from parser.xml_parser import (
        parse_hierarchical, ThesisModules, ChapterModule,
        ParserError, FileNotFoundParserError, UnsupportedFormatError,
        EmptyDocumentError, PDFParseError, DOCXParseError
    )

# 导入评分器
try:
    from .scoring.scorer import ThesisScorer, ScoringResult
except ImportError:
    from scoring.scorer import ThesisScorer, ScoringResult


# ============================================================================
# 精准统计层（Python）
# ============================================================================

@dataclass
class PreciseStatistics:
    """精准统计数据"""
    # 基本信息
    title: str = ""
    total_char_count: int = 0
    chapter_count: int = 0

    # 字数统计
    char_counts: Dict[str, int] = field(default_factory=dict)  # 各章节字数

    # 文献统计
    reference_stats: Dict[str, Any] = field(default_factory=dict)

    # 论文类型
    paper_type: str = "未知"
    detected_methods: List[str] = field(default_factory=list)

    # 内容片段
    research_background: str = ""  # 研究背景（绪论前500字）
    research_conclusion: str = ""  # 研究结论（最后章节前500字）

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'total_char_count': self.total_char_count,
            'chapter_count': self.chapter_count,
            'char_counts': self.char_counts,
            'reference_stats': self.reference_stats,
            'paper_type': self.paper_type,
            'detected_methods': self.detected_methods,
        }


class PreciseStatisticsExtractor:
    """精准统计提取器 - Python实现"""

    # 论文类型识别关键词
    PAPER_TYPE_KEYWORDS = {
        '实证经济学型': ['面板数据', '固定效应', '随机效应', '工具变量', 'IV', 'GMM',
                       'DID', '双重差分', '倾向得分', 'PSM', '回归分析', '计量模型'],
        '问卷调查型': ['问卷', '信度', '效度', 'Cronbach', 'KMO', '因子分析',
                     '样本量', '抽样', '量表', 'Likert'],
        '政策评价型': ['指标体系', '熵权法', '熵值法', '耦合协调度', '障碍度',
                     '综合评价', '测度', '评价模型', 'AHP', '模糊评价'],
        '案例分析型': ['案例', '单案例', '多案例', '深度访谈', '叙事', '质性研究'],
        '混合型': ['问卷', '实证', '案例', '评价', '回归']
    }

    # 方法关键词
    METHOD_KEYWORDS = [
        ('面板数据回归', ['面板数据', '固定效应', '随机效应', 'panel data']),
        ('双重差分DID', ['DID', '双重差分', '倍差法']),
        ('工具变量法IV', ['工具变量', 'IV', '两阶段最小二乘法']),
        ('Logistic回归', ['logit', 'Logistic', '二元选择']),
        ('熵权法', ['熵权法', '熵值法', '熵值']),
        ('耦合协调度模型', ['耦合协调度', '耦合度']),
        ('障碍度模型', ['障碍度', '障碍因子']),
        ('地理探测器', ['地理探测器', 'Geodetector']),
        ('GIS空间分析', ['GIS', '地理信息系统', '空间分析']),
        ('核密度估计', ['核密度', 'Kernel density']),
        ('Cronbach α信度', ['Cronbach', '信度系数', 'α系数']),
        ('KMO检验', ['KMO', 'Kaiser-Meyer-Olkin']),
    ]

    def extract(self, modules: ThesisModules) -> PreciseStatistics:
        """执行精准统计"""
        stats = PreciseStatistics()

        # 基本信息
        stats.title = modules.title
        stats.chapter_count = len(modules.chapters)

        # 字数统计
        total_chars = 0
        for ch in modules.chapters:
            stats.char_counts[f"第{ch.number}章"] = ch.char_count
            total_chars += ch.char_count
        stats.total_char_count = total_chars

        # 文献统计
        stats.reference_stats = self._extract_reference_stats(modules.references)

        # 论文类型检测
        all_text = ' '.join([ch.content for ch in modules.chapters])
        paper_type, methods = self._detect_paper_type(all_text)
        stats.paper_type = paper_type
        stats.detected_methods = methods

        # 内容片段
        if modules.chapters:
            stats.research_background = modules.chapters[0].content[:1000]
            stats.research_conclusion = modules.chapters[-1].content[:1000]

        return stats

    def _extract_reference_stats(self, references: List[str]) -> Dict[str, Any]:
        """统计参考文献"""
        total = len(references)
        if total == 0:
            return {
                'total': 0, 'chinese': 0, 'foreign': 0,
                'journals': 0, 'journal_ratio': 0,
                'recent_5yr': 0, 'recent_5yr_ratio': 0
            }

        chinese_count = 0
        foreign_count = 0
        journal_count = 0
        recent_5yr_count = 0
        current_year = 2026

        for ref in references:
            # 简单判断中英文：前50字符中文字符占比
            first_50 = ref[:50]
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', first_50))
            english_chars = len(re.findall(r'[A-Za-z]', first_50))
            if chinese_chars > english_chars:
                chinese_count += 1
            else:
                foreign_count += 1

            # 期刊标记
            if re.search(r'\[J\]', ref):
                journal_count += 1

            # 年份检测
            year_match = re.search(r'[（(]?(20[12]\d)[)）]?', ref)
            if year_match:
                year = int(year_match.group(1))
                if current_year - year <= 5:
                    recent_5yr_count += 1

        return {
            'total': total,
            'chinese': chinese_count,
            'foreign': foreign_count,
            'journals': journal_count,
            'journal_ratio': round(journal_count / total, 2) if total > 0 else 0,
            'recent_5yr': recent_5yr_count,
            'recent_5yr_ratio': round(recent_5yr_count / total, 2) if total > 0 else 0
        }

    def _detect_paper_type(self, text: str) -> tuple:
        """检测论文类型和识别方法"""
        type_scores = {pt: 0 for pt in self.PAPER_TYPE_KEYWORDS}

        for pt, keywords in self.PAPER_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    type_scores[pt] += 1

        # 找出最高分类型
        max_score = max(type_scores.values())
        if max_score == 0:
            return "未知", []

        detected_types = [pt for pt, score in type_scores.items() if score == max_score]

        # 混合型判断：如果检测到多个类型且没有单一明显类型
        if len(detected_types) > 1 and '混合型' not in detected_types:
            paper_type = '混合型'
        elif len(detected_types) == 1:
            paper_type = detected_types[0]
        else:
            paper_type = '混合型'

        # 识别具体方法
        detected_methods = []
        for method_name, keywords in self.METHOD_KEYWORDS:
            for kw in keywords:
                if kw in text:
                    detected_methods.append(method_name)
                    break

        return paper_type, list(set(detected_methods))


# ============================================================================
# LLM评分数据结构
# ============================================================================

@dataclass
class LLMEvaluation:
    """LLM深度评价结果 - 包含质量判断依据"""
    total_score: float
    paper_type: str
    dimensions: List[Dict]  # 各维度评分，包含quality_judgment
    overall_comment: str
    high_priority: List[str]
    medium_priority: List[str]
    low_priority: List[str]
    raw_json: str = ""  # 原始JSON字符串

    def to_dict(self) -> Dict:
        return {
            'total_score': self.total_score,
            'paper_type': self.paper_type,
            'dimensions': self.dimensions,
            'overall_comment': self.overall_comment,
            'high_priority': self.high_priority,
            'medium_priority': self.medium_priority,
            'low_priority': self.low_priority
        }


# ============================================================================
# 深度评价Prompt生成（LLM直接打分版）
# ============================================================================

def generate_llm_evaluation_prompt(
    modules: ThesisModules,
    stats: PreciseStatistics
) -> str:
    """
    生成深度评价Prompt - LLM全权打分版本

    Python只做精准统计，所有质量判断全部交给LLM：
    - 文献质量（期刊等级、经典文献、相关性、前沿性）
    - 创新性（选题、方法、数据）
    - 方法匹配度
    - 数据质量
    - 稳健性检验充分性
    - 写作质量
    - 政策建议可操作性
    """
    lines = []

    # === 论文基本信息（Python精准统计）===
    lines.append("# 硕士学位论文深度评价\n\n")
    lines.append("> **⚠️ 说明**：以下统计数据由Python精确提取，LLM需结合全文内容进行质量判断。\n\n")
    lines.append(f"**论文题目**：{stats.title}\n")
    lines.append(f"**论文类型（初判）**：{stats.paper_type}\n")
    lines.append(f"**总字数**：约{stats.total_char_count}字\n")
    lines.append(f"**章节数**：{stats.chapter_count}章\n")
    lines.append(f"**参考文献**：{stats.reference_stats.get('total', 0)}篇\n")
    lines.append(f"**外文文献**：{stats.reference_stats.get('foreign', 0)}篇\n")
    lines.append(f"**期刊占比**：{stats.reference_stats.get('journal_ratio', 0):.1%}\n")
    lines.append(f"**近五年文献**：{stats.reference_stats.get('recent_5yr_ratio', 0):.1%}\n")
    if stats.detected_methods:
        lines.append(f"**识别方法**：{'、'.join(stats.detected_methods)}\n")
    lines.append("\n---\n\n")

    # === 章节结构 ===
    lines.append("## 章节结构\n\n")
    lines.append(modules.chapter_summary())
    lines.append("\n\n")

    # === 章节内容摘要（前2000字+后1000字）===
    lines.append("## 章节内容摘要\n\n")
    for ch in modules.chapters:
        content = ch.content
        if len(content) > 3000:
            content_preview = content[:2000] + "\n\n...[省略中间部分]...\n\n" + content[-1000:]
        else:
            content_preview = content
        lines.append(f"### 第{ch.number}章 {ch.title}\n")
        lines.append(content_preview)
        lines.append("\n\n")

    # === 摘录内容 ===
    if modules.abstract_cn:
        lines.append("### 中文摘要\n")
        lines.append(modules.abstract_cn)
        lines.append("\n\n")

    # === 完整参考文献（让LLM评判质量）===
    if modules.references:
        lines.append("### 完整参考文献列表\n\n")
        lines.append("> **LLM质量判断依据**：请根据以下参考文献信息判断文献质量。\n")
        lines.append("> - 中文核心期刊识别：CSSCI/CSCD/北大核心期刊（如《中国农村经济》《管理世界》等）\n")
        lines.append("> - 英文顶刊识别：Nature/Science/PNAS/RePEc/Scopus Q1等\n")
        lines.append("> - 经典文献识别：年被引次数高、行业奠基性工作\n\n")
        for i, ref in enumerate(modules.references, 1):
            lines.append(f"{i}. {ref}\n")
        lines.append("\n")

    # === LLM质量评价要求 ===
    lines.append("""---
# 评价任务

请作为专业的硕士学位论文评审专家，对该论文进行全面深度评价。**所有质量判断均由您独立完成。**

## 核心原则

1. **文献质量判断**：根据参考文献的期刊来源（如CSSCI/CSCD/北大核心 vs 普通期刊）、发表期刊影响力、是否为经典高被引文献，独立判断文献质量
2. **创新性判断**：根据论文实际贡献判断，不依赖关键词匹配
3. **方法匹配度判断**：根据研究问题与方法的实际匹配程度判断
4. **数据质量判断**：根据数据来源权威性、时效性、完整性判断
5. **稳健性充分性判断**：根据检验方法多样性、结果稳定性判断
6. **写作质量判断**：根据逻辑连贯性、论证严密性判断
7. **建议可操作性判断**：根据建议的具体性、可行性、数据支撑判断

## 论文类型权重体系

| 论文类型 | 选题 | 综述 | 方法 | 实证 | 创新 | 写作 | 结论 |
|---------|------|------|------|------|------|------|------|
| 实证经济学型 | 10% | 10% | 25% | 30% | 15% | 5% | 5% |
| 问卷调查型 | 10% | 10% | 20% | 30% | 15% | 10% | 5% |
| 政策评价型 | 15% | 10% | 25% | 20% | 15% | 10% | 5% |
| 案例分析型 | 15% | 15% | 15% | 15% | 20% | 15% | 5% |
| 混合型 | 12% | 12% | 23% | 25% | 15% | 8% | 5% |

## 各维度质量判断要点

### 1. 选题与研究意义（10-15%）
- **文献质量视角**：参考文献中核心期刊（如《中国农村经济》《农业技术经济》）占比，经典文献（如田云、李波等）引用情况
- **问题清晰度**：研究问题是否具体、明确
- **理论意义**：对学科理论是否有推进（如修正EKC曲线、提出新机制）
- **实践价值**：对"双碳"目标、乡村振兴等现实问题的指导价值

### 2. 文献综述与理论基础（10-15%）
- **文献质量判断**（重点）：
  - 核心期刊占比（CSSCI/CSCD/北大核心 > 普通期刊）
  - 英文文献中高影响力期刊（Q1/顶刊 > 一般期刊）
  - 经典文献识别（被引>100次或行业奠基性工作）
  - 近五年文献占比（>50%为优，<30%为劣）
  - 文献与研究主题的相关性强弱
- **评述深度**：是否清晰指出研究空白

### 3. 研究方法与技术路线（15-25%）
- **方法匹配度**：所用方法是否真正适合研究问题
- **方法明确度**：公式、模型设定是否清晰
- **技术路线**：章节结构是否体现方法流程

### 4. 实证分析与结果（20-30%）
- **数据质量判断**：
  - 数据来源权威性（统计年鉴/官方数据 > 一般数据）
  - 数据时效性（最新年份数据占比）
  - 数据完整性（缺失值处理是否合理）
  - 变量测度科学性
- **稳健性充分性判断**：
  - 是否进行多种稳健性检验（如更换变量、缩尾、剔除样本）
  - 是否讨论内生性问题及处理方法
  - 异质性分析是否充分

### 5. 创新性（15-20%）
- **选题创新**：是否提出新问题、新视角、新场景
- **方法创新**：是否引入新模型、新算法
- **数据/应用创新**：是否使用新数据源、新指标

### 6. 写作规范与表达（5-15%）
- **逻辑连贯性**：结构是否清晰、论证是否严密
- **语言规范性**：学术表达是否专业、无语病
- **格式规范性**：引用、图表是否规范

### 7. 结论与建议（5-10%）
- **建议可操作性判断**：
  - 建议是否具体（不是泛泛而谈）
  - 建议是否可行（有实施路径）
  - 建议是否有数据支撑
- **局限性说明**：是否客观讨论研究不足

## 输出格式要求

### 第一部分：结构化JSON评分（必须）

```json
{
  "total_score": 72.5,
  "paper_type": "混合型",
  "dimensions": [
    {
      "name": "选题与研究意义",
      "score": 11.0,
      "max_score": 15,
      "quality_judgment": {
        "literature_quality": "良好：核心期刊占比约60%，包含田云(2022)、李波(2011)等高被引文献",
        "problem_clarity": "优秀：问题具体明确，聚焦时空变化与影响因素",
        "theory_contribution": "一般：理论框架完整但无实质推进"
      },
      "strengths": ["研究对象典型——河南省是产粮大省代表性很强", "紧扣双碳战略实践价值明确"],
      "weaknesses": ["理论意义薄弱——对EKC曲线等无实质推进"],
      "suggestions": ["可尝试修正EKC曲线模型或提出新机制解释"]
    },
    {
      "name": "文献综述与理论基础",
      "score": 7.5,
      "max_score": 10,
      "quality_judgment": {
        "core_journal_ratio": "较高：约60%为CSSCI/CSCD/北大核心期刊",
        "foreign_top_journals": "一般：多为一般英文期刊，缺乏Q1顶刊",
        "classic_literature": "良好：引用了田云、李波等高被引国内学者工作",
        "recent_literature_ratio": "不足：近五年文献仅34%，建议补充2022-2024年最新研究"
      },
      "strengths": ["文献数量充足（65篇），期刊占比高（94%）", "理论基础明确三大理论"],
      "weaknesses": ["前沿性不足：近五年文献占比偏低", "缺乏英文顶刊文献"],
      "suggestions": ["补充近五年高影响力文献特别是2022-2024年最新研究"]
    }
  ],
  "overall_comment": "论文整体达到良好水平，选题具有现实意义，数据基础扎实...",
  "high_priority": ["稳健性检验方法单一：建议增加多种稳健性检验方法"],
  "medium_priority": ["理论框架与实证结合不紧密"],
  "low_priority": ["摘要与结论存在重复"]
}
```

### 第二部分：详细评价报告（可选参考）

如需输出详细报告，请按以下格式：

```markdown
# 硕士学位论文评审报告

## 一、总体评价
[评价内容]

## 二、各维度详细评价
[7个维度的详细评价]

## 三、修改建议
[高/中/低优先级建议]

## 四、总结
[总结]
```

请开始评价：
""")

    return "".join(lines)


def parse_llm_evaluation(json_str: str) -> Optional[LLMEvaluation]:
    """
    解析LLM返回的JSON评分

    Args:
        json_str: LLM返回的JSON字符串

    Returns:
        LLMEvaluation对象，解析失败返回None
    """
    import json
    import re

    try:
        # 提取JSON部分
        json_str = json_str.strip()

        # 如果包含markdown代码块，提取其中的JSON
        if '```json' in json_str:
            parts = json_str.split('```json')
            for part in parts[1:]:
                if '```' in part:
                    json_str = part.split('```')[0].strip()
                    break

        # 尝试解析
        data = json.loads(json_str)

        # 提取字段
        dimensions = data.get('dimensions', [])

        return LLMEvaluation(
            total_score=data.get('total_score', 0),
            paper_type=data.get('paper_type', '未知'),
            dimensions=dimensions,
            overall_comment=data.get('overall_comment', ''),
            high_priority=data.get('high_priority', []),
            medium_priority=data.get('medium_priority', []),
            low_priority=data.get('low_priority', []),
            raw_json=json_str
        )

    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return None
    except Exception as e:
        print(f"解析评价结果时出错: {e}")
        return None


def generate_final_report(
    modules: ThesisModules,
    stats: PreciseStatistics,
    llm_eval: LLMEvaluation
) -> str:
    """
    根据LLM评价生成最终报告 - 包含质量判断依据
    """
    from datetime import datetime

    lines = []
    date = datetime.now().strftime('%Y-%m-%d')

    # 论文类型权重
    weights = {
        '实证经济学型': {'选题': 10, '综述': 10, '方法': 25, '实证': 30, '创新': 15, '写作': 5, '结论': 5},
        '问卷调查型': {'选题': 10, '综述': 10, '方法': 20, '实证': 30, '创新': 15, '写作': 10, '结论': 5},
        '政策评价型': {'选题': 15, '综述': 10, '方法': 25, '实证': 20, '创新': 15, '写作': 10, '结论': 5},
        '案例分析型': {'选题': 15, '综述': 15, '方法': 15, '实证': 15, '创新': 20, '写作': 15, '结论': 5},
        '混合型': {'选题': 12, '综述': 12, '方法': 23, '实证': 25, '创新': 15, '写作': 8, '结论': 5},
    }

    paper_type = llm_eval.paper_type
    dim_weights = weights.get(paper_type, weights['混合型'])

    # 维度名称映射
    dim_name_map = {
        '选题与研究意义': '选题',
        '文献综述与理论基础': '综述',
        '研究方法与技术路线': '方法',
        '实证分析与结果': '实证',
        '创新性': '创新',
        '写作规范与表达': '写作',
        '结论与建议': '结论'
    }

    lines.append("# 硕士学位论文评审报告\n\n")
    lines.append(f"**论文题目：** {stats.title}\n")
    lines.append(f"**论文类型：** {paper_type} ｜ **评价日期：** {date}\n\n")
    lines.append("---\n\n")

    # 计算等级
    score = llm_eval.total_score
    if score >= 85:
        level = "🟢 优秀"
    elif score >= 70:
        level = "🟡 良好"
    elif score >= 60:
        level = "🔵 合格"
    else:
        level = "🔴 需重修"

    lines.append("## 一、总体评价\n\n")
    lines.append(f"**综合评分：{score:.1f}/100（{level}）**\n\n")

    lines.append("| 评价维度 | 得分 | 权重 |\n")
    lines.append("|----------|------|------|\n")

    for dim in llm_eval.dimensions:
        dim_name = dim.get('name', '')
        short_name = dim_name_map.get(dim_name, dim_name)
        weight = dim_weights.get(short_name, 0)
        score_val = dim.get('score', 0)
        max_val = dim.get('max_score', 15)
        lines.append(f"| {dim_name} | {score_val:.1f}/{max_val} | {weight}% |\n")

    lines.append("\n")
    lines.append(f"**总体评语：** {llm_eval.overall_comment}\n\n")
    lines.append("---\n\n")

    # 二、各维度详细评价（含质量判断依据）
    lines.append("## 二、各维度详细评价\n\n")

    for i, dim in enumerate(llm_eval.dimensions, 1):
        dim_name = dim.get('name', '')
        lines.append(f"### ({i}) {dim_name}\n\n")

        # 质量判断依据
        quality_judgment = dim.get('quality_judgment', {})
        if quality_judgment:
            lines.append("**质量判断依据：**\n")
            for key, value in quality_judgment.items():
                if isinstance(value, str):
                    lines.append(f"- **{key}**：{value}\n")
                elif isinstance(value, dict):
                    lines.append(f"- **{key}**：\n")
                    for sub_key, sub_val in value.items():
                        lines.append(f"  - {sub_key}：{sub_val}\n")
            lines.append("\n")

        strengths = dim.get('strengths', [])
        weaknesses = dim.get('weaknesses', [])

        lines.append("**优点：**\n")
        if strengths:
            for s in strengths:
                lines.append(f"- {s}\n")
        else:
            lines.append("- （优点不明显）\n")

        lines.append("\n**问题：**\n")
        if weaknesses:
            for w in weaknesses:
                lines.append(f"- {w}\n")
        else:
            lines.append("- （未发现明显问题）\n")

        lines.append("\n")

    # 三、修改建议
    lines.append("---\n\n")
    lines.append("## 三、修改建议\n\n")

    lines.append("### 高优先级修改建议（必须修改）\n\n")
    for i, item in enumerate(llm_eval.high_priority, 1):
        lines.append(f"{i}. {item}\n")
    if not llm_eval.high_priority:
        lines.append("（无高优先级问题）\n")
    lines.append("\n")

    lines.append("### 中优先级修改建议\n\n")
    for i, item in enumerate(llm_eval.medium_priority, 1):
        lines.append(f"{i}. {item}\n")
    if not llm_eval.medium_priority:
        lines.append("（无中优先级问题）\n")
    lines.append("\n")

    lines.append("### 低优先级修改建议\n\n")
    for i, item in enumerate(llm_eval.low_priority, 1):
        lines.append(f"{i}. {item}\n")
    if not llm_eval.low_priority:
        lines.append("（无低优先级问题）\n")
    lines.append("\n")

    # 四、总结
    lines.append("---\n\n")
    lines.append("## 四、总结\n\n")
    lines.append(f"该论文以{stats.title}为研究对象，选题具有现实意义，")
    lines.append(f"综合运用{'、'.join(stats.detected_methods[:3]) if stats.detected_methods else '相关研究方法'}进行分析。")
    lines.append(f"文献综述较为系统（{stats.reference_stats.get('total', 0)}篇），")
    lines.append(f"期刊占比{stats.reference_stats.get('journal_ratio', 0):.1%}。")

    if score >= 70:
        lines.append("论文达到良好水平，可以提交答辩。")
    elif score >= 60:
        lines.append("论文达到合格水平，建议在以下方面进一步完善后提交答辩。")
    else:
        lines.append("论文需较大修改，建议针对性完善后再提交答辩。")

    lines.append("\n\n---\n\n")
    lines.append(f"*本评价依据7维度评审体系，Python精准统计 + LLM全权质量判断混合架构*\n")

    return "".join(lines)


# ============================================================================
# 评审结果与流程
# ============================================================================

@dataclass
class ReviewResultV4:
    """评审结果v4"""
    modules: ThesisModules
    statistics: PreciseStatistics
    llm_evaluation: Optional[LLMEvaluation] = None  # LLM评价结果
    evaluation_prompt: str = ""
    final_report: str = ""  # 最终报告

    def save_json(self, output_path: str):
        """保存评审数据为JSON"""
        # LLM评价数据
        llm_data = {}
        if self.llm_evaluation:
            llm_data = self.llm_evaluation.to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': self.statistics.title,
                'paper_type': self.statistics.paper_type,
                'scoring': llm_data,
                'reference_stats': self.statistics.reference_stats,
                'chapters': [
                    {'number': ch.number, 'title': ch.title, 'char_count': ch.char_count}
                    for ch in self.modules.chapters
                ]
            }, f, ensure_ascii=False, indent=2)

    def save_prompt(self, output_path: str):
        """保存评价Prompt"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.evaluation_prompt)

    def save_report(self, output_path: str):
        """保存最终报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.final_report)


class ReviewPipelineV4:
    """
    评审流程v4: Python精准统计 + LLM深度评价

    流程：
    1. 文档解析（Python）
    2. 精准统计（Python）
    3. 生成LLM评价Prompt
    4. 用户调用LLM获取JSON评分
    5. Python解析JSON并生成最终报告
    """

    def __init__(self):
        self.stats_extractor = PreciseStatisticsExtractor()

    def run(self, file_path: str) -> ReviewResultV4:
        """
        执行评审流程（步骤1-3）

        Args:
            file_path: 论文文件路径

        Returns:
            ReviewResultV4包含统计数据和评价Prompt

        Raises:
            FileNotFoundParserError: 文件不存在
            UnsupportedFormatError: 不支持的文件格式
            EmptyDocumentError: 文档为空或解析失败
            PDFParseError: PDF解析失败
            DOCXParseError: DOCX解析失败
        """
        print(f"[1/3] 解析文档: {file_path}")
        try:
            modules = parse_hierarchical(file_path)
        except ParserError as e:
            print(f"❌ 解析失败: {e}")
            raise

        print(f"[2/3] 精准统计...")
        stats = self.stats_extractor.extract(modules)

        print(f"[3/3] 生成LLM评价Prompt...")
        prompt = generate_llm_evaluation_prompt(modules, stats)

        return ReviewResultV4(
            modules=modules,
            statistics=stats,
            evaluation_prompt=prompt
        )

    def generate_report(self, result: ReviewResultV4, llm_json: str) -> str:
        """
        根据LLM返回的JSON生成最终报告

        Args:
            result: 之前的评审结果
            llm_json: LLM返回的JSON字符串

        Returns:
            最终报告字符串
        """
        llm_eval = parse_llm_evaluation(llm_json)

        if llm_eval is None:
            print("⚠️ LLM评分解析失败，将仅生成统计数据报告")
            return self._generate_stats_only_report(result)

        result.llm_evaluation = llm_eval
        report = generate_final_report(result.modules, result.statistics, llm_eval)
        result.final_report = report
        return report

    def _generate_stats_only_report(self, result: ReviewResultV4) -> str:
        """生成仅包含统计数据的报告（当LLM解析失败时）"""
        lines = []
        lines.append("# 硕士学位论文评审报告\n\n")
        lines.append(f"**论文题目**：{result.statistics.title}\n")
        lines.append(f"**论文类型**：{result.statistics.paper_type}\n")
        lines.append("\n---\n\n")
        lines.append("## Python精准统计数据\n\n")
        lines.append(f"- 总字数：约{result.statistics.total_char_count}字\n")
        lines.append(f"- 章节数：{result.statistics.chapter_count}章\n")
        lines.append(f"- 参考文献：{result.statistics.reference_stats.get('total', 0)}篇\n")
        lines.append(f"- 外文文献：{result.statistics.reference_stats.get('foreign', 0)}篇\n")
        lines.append(f"- 期刊占比：{result.statistics.reference_stats.get('journal_ratio', 0):.1%}\n")
        lines.append(f"- 近五年文献：{result.statistics.reference_stats.get('recent_5yr_ratio', 0):.1%}\n")
        if result.statistics.detected_methods:
            lines.append(f"- 识别方法：{'、'.join(result.statistics.detected_methods)}\n")
        lines.append("\n---\n\n")
        lines.append("⚠️ **注意**：LLM评分解析失败，请检查JSON格式是否正确。\n")
        return "".join(lines)

    def _rule_scoring(self, modules: ThesisModules) -> ScoringResult:
        """
        使用Python规则进行评分（仅作参考，不作为最终分数）

        基于关键词匹配等规则进行初步评分，LLM深度评价时应结合全文内容。
        """
        # 构建全文内容
        all_text = ' '.join([ch.content for ch in modules.chapters])

        # 构建info字典
        info = {
            'reference_section': '\n'.join(modules.references),
            'reference_count': len(modules.references),
            'content': all_text,
            'method': self._detect_method(all_text),
            'method_details': {},
            'data': {},
            'has_hypothesis': '假设' in all_text,
            'has_robustness': '稳健性' in all_text or '稳健性检验' in all_text,
            'has_endogeneity': '内生性' in all_text,
            'main_conclusion': modules.chapters[-1].content[:500] if modules.chapters else '',
            'limitations': modules.chapters[-1].content[:500] if modules.chapters else '',  # 字符串，不是布尔值
            'research_question': modules.chapters[0].content[:200] if modules.chapters else ''
        }

        return self.scorer.score(info, all_text)

    def _detect_method(self, text: str) -> str:
        """检测研究方法"""
        extractor = self.stats_extractor
        _, methods = extractor._detect_paper_type(text)
        return ' + '.join(methods) if methods else '未明确识别'

    def save_outputs(self, result: ReviewResultV4, output_dir: str, filename_prefix: str):
        """保存输出文件"""
        output_path = Path(output_dir)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"❌ 无法创建目录（权限不足）: {output_path}")
            return
        except Exception as e:
            print(f"❌ 创建目录失败: {e}")
            return

        # 保存统计数据JSON
        json_path = output_path / f"{filename_prefix}_评审数据.json"
        try:
            result.save_json(str(json_path))
            print(f"✅ 评审数据已保存至: {json_path}")
        except PermissionError:
            print(f"❌ 无法写入文件（权限不足）: {json_path}")
        except Exception as e:
            print(f"❌ 保存评审数据失败: {e}")

        # 保存评价Prompt
        prompt_path = output_path / f"{filename_prefix}_评价Prompt.md"
        try:
            result.save_prompt(str(prompt_path))
            print(f"✅ 评价Prompt已保存至: {prompt_path}")
        except PermissionError:
            print(f"❌ 无法写入文件（权限不足）: {prompt_path}")
        except Exception as e:
            print(f"❌ 保存评价Prompt失败: {e}")

        # 保存最终报告（如有）
        if result.final_report:
            report_path = output_path / f"{filename_prefix}_评审报告.md"
            try:
                result.save_report(str(report_path))
                print(f"✅ 最终报告已保存至: {report_path}")
            except PermissionError:
                print(f"❌ 无法写入文件（权限不足）: {report_path}")
            except Exception as e:
                print(f"❌ 保存最终报告失败: {e}")


def review_pipeline_v4(file_path: str, output_dir: Optional[str] = None) -> ReviewResultV4:
    """
    便捷函数：执行v4评审流程

    Args:
        file_path: 论文文件路径
        output_dir: 可选，输出目录

    Returns:
        ReviewResultV4
    """
    pipeline = ReviewPipelineV4()
    result = pipeline.run(file_path)

    if output_dir:
        filename_prefix = Path(file_path).stem
        pipeline.save_outputs(result, output_dir, filename_prefix)

    return result
