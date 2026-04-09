"""
Report Generator Module
Uses LLM to generate readable review reports from structured data
"""
from dataclasses import dataclass
from typing import Dict, List, Any
from datetime import datetime

from anthropic import Anthropic


REPORT_PROMPT_TEMPLATE = """你是论文评审报告生成专家。请根据以下结构化评审结果，生成一份专业的硕士学位论文评审报告。

【评审信息】
- 论文题目：{title}
- 评审日期：{date}
- 评审机构：硕士论文智能评审系统 v2.3

【评分结果】
总分：{total_score}/{max_score}（{percentage:.1f}%）

各维度评分：
{score_breakdown}

【关键问题汇总】
{major_issues}

【信息抽取结果】
{extracted_info}

请生成以下格式的评审报告：

---
# 硕士学位论文评审报告

## 一、总评
[给出总体评价，包括论文水平定位、主要优缺点]

## 二、各维度详细评审
### 1. 研究问题（{rq_score}/{rq_max}分）
[优点]
[问题]
[证据引用]
[修改建议]

### 2. 方法论严谨性（{method_score}/{method_max}分）
[优点]
[问题]
[证据引用]
[修改建议]

### 3. 结果与结论（{results_score}/{results_max}分）
[优点]
[问题]
[证据引用]
[修改建议]

### 4. 创新性（{innov_score}/{innov_max}分）
[优点]
[问题]
[证据引用]
[修改建议]

### 5. 结构与逻辑（{struct_score}/{struct_max}分）
[优点]
[问题]
[修改建议]

### 6. 表达质量（{writing_score}/{writing_max}分）
[优点]
[问题]
[修改建议]

## 三、必须修改的问题（严重）
[列出所有critical问题，包括证据和修改建议]

## 四、建议修改的问题
[列出所有建议改进项]

## 五、综合评价
[总结性评价，给出是否达到毕业要求的判断]
---

要求：
1. 每个问题必须引用论文原文作为证据（用【】标注）
2. 修改建议要具体可操作
3. 评价客观公正，既要指出问题，也要肯定优点
4. 语言专业、规范
"""


@dataclass
class ReportSection:
    """A section of the report"""
    title: str
    content: str


class ReportGenerator:
    """Generates structured review reports using LLM"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(
        self,
        title: str,
        extracted_info: Dict[str, Any],
        scoring_result: Dict[str, Any]
    ) -> str:
        """
        Generate a complete review report

        Args:
            title: Thesis title
            extracted_info: Information extracted by LLM
            scoring_result: Scoring result from rule-based scorer

        Returns:
            Formatted review report in Markdown
        """
        # Build score breakdown string
        score_breakdown = self._build_score_breakdown(scoring_result)

        # Build major issues string
        major_issues = self._build_major_issues(scoring_result)

        # Build extracted info summary
        info_summary = self._build_info_summary(extracted_info)

        # Get dimension scores
        dims = {d['name']: d for d in scoring_result.get('dimensions', [])}

        # Format prompt
        prompt = REPORT_PROMPT_TEMPLATE.format(
            title=title,
            date=datetime.now().strftime('%Y-%m-%d'),
            total_score=scoring_result.get('total_score', 0),
            max_score=scoring_result.get('max_total', 100),
            percentage=scoring_result.get('total_score', 0) / scoring_result.get('max_total', 100) * 100,
            score_breakdown=score_breakdown,
            major_issues=major_issues,
            extracted_info=info_summary,
            rq_score=dims.get('研究问题', {}).get('score', 0),
            rq_max=dims.get('研究问题', {}).get('max_score', 15),
            method_score=dims.get('方法论严谨性', {}).get('score', 0),
            method_max=dims.get('方法论严谨性', {}).get('max_score', 30),
            results_score=dims.get('结果与结论', {}).get('score', 0),
            results_max=dims.get('结果与结论', {}).get('max_score', 20),
            innov_score=dims.get('创新性', {}).get('score', 0),
            innov_max=dims.get('创新性', {}).get('max_score', 15),
            struct_score=dims.get('结构与逻辑', {}).get('score', 0),
            struct_max=dims.get('结构与逻辑', {}).get('max_score', 10),
            writing_score=dims.get('表达质量', {}).get('score', 0),
            writing_max=dims.get('表达质量', {}).get('max_score', 10)
        )

        # Call LLM
        response = self._call_llm(prompt)

        return response

    def _build_score_breakdown(self, scoring_result: Dict) -> str:
        """Build score breakdown string"""
        lines = []
        for dim in scoring_result.get('dimensions', []):
            grade_emoji = {
                'A': '🟢',
                'B': '🟡',
                'C': '🔵',
                'D': '🔵',
                'F': '🔴'
            }.get(dim.get('grade', ''), '⚪')

            lines.append(
                f"- {dim['name']}: {dim['score']}/{dim['max_score']} {grade_emoji}"
            )
            for sub in dim.get('sub_items', []):
                status = "✅" if sub['passed'] else "❌"
                lines.append(f"  {status} {sub['name']}: {sub['score']}/{sub['max']}")
        return "\n".join(lines)

    def _build_major_issues(self, scoring_result: Dict) -> str:
        """Build major issues string"""
        issues = []
        for dim in scoring_result.get('dimensions', []):
            for issue in dim.get('critical_issues', []):
                if issue:
                    issues.append(f"- [{dim['name']}] {issue}")
        return "\n".join(issues) if issues else "无严重问题"

    def _build_info_summary(self, info: Dict) -> str:
        """Build extracted information summary"""
        parts = []

        if info.get('paper_type'):
            parts.append(f"论文类型：{info['paper_type']}")
        if info.get('research_question'):
            parts.append(f"研究问题：{info['research_question'][:100]}...")
        if info.get('method'):
            parts.append(f"研究方法：{info['method']}")
        if info.get('data', {}).get('sample_size'):
            parts.append(f"样本量：{info['data']['sample_size']}")
        if info.get('main_conclusion'):
            parts.append(f"主要结论：{info['main_conclusion'][:100]}...")

        return "\n".join(parts) if parts else "信息提取结果"

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return response.content[0].text


def generate_report(
    title: str,
    extracted_info: Dict[str, Any],
    scoring_result: Dict[str, Any],
    api_key: str
) -> str:
    """
    Convenience function to generate report

    Args:
        title: Thesis title
        extracted_info: Information extracted by LLM
        scoring_result: Scoring result from rule-based scorer
        api_key: Anthropic API key

    Returns:
        Formatted review report
    """
    generator = ReportGenerator(api_key)
    return generator.generate(title, extracted_info, scoring_result)
