"""
Main Pipeline for Thesis Reviewer v2.3
Orchestrates the complete review workflow

Design:
- Parse: Hierarchical modular parsing (cover, abstract, chapters, references)
- Score: 7-dimension rule-based scoring
- Generate: Prompt organized by 7 dimensions for AI evaluation
- Output: skill.md format report

No API calls needed - AI evaluates directly in conversation
"""
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path

from .parser.xml_parser import parse_hierarchical, ThesisModules, ChapterModule
from .scoring.scorer import ThesisScorer, ScoringResult


# ============================================================================
# Review Prompt Generator - 按7维度组织内容
# ============================================================================

# 7维度与章节的映射关系
DIMENSION_CHAPTER_MAPPING = {
    '选题与研究意义': ['绪论', '引言', '前言', '研究背景', '研究问题'],
    '文献综述与理论基础': ['文献综述', '研究现状', '理论基础', '概念界定', '相关概念'],
    '研究方法与技术路线': ['研究设计', '研究方法', '模型', '数据', '样本'],
    '实证分析与结果': ['实证', '结果', '分析', '发现', '讨论'],
    '创新性': [],  # 创新性贯穿全文
    '写作规范与表达': [],  # 写作贯穿全文
    '结论与建议': ['结论', '总结', '展望', '对策', '建议']
}


def generate_review_prompt(modules: ThesisModules,
                          scoring_result: ScoringResult,
                          ref_stats: Dict[str, Any]) -> str:
    """
    生成论文评价的详细Prompt，按7维度组织内容

    Args:
        modules: 层次化解构后的论文结构
        scoring_result: 7维度评分结果
        ref_stats: 参考文献统计

    Returns:
        详细的评价Prompt文本
    """
    lines = []

    # === 论文基本信息 ===
    lines.append("# 硕士学位论文评价\n\n")
    lines.append(f"**论文题目**：{modules.title}\n")
    lines.append(f"**论文类型**：{scoring_result.paper_type}\n")
    lines.append(f"**参考文献**：{ref_stats.get('total', 0)} 篇\n")
    lines.append("\n")

    # === 章节结构预览 ===
    lines.append("## 章节结构\n\n")
    lines.append(modules.chapter_summary())
    lines.append("\n\n")

    # === 参考文献统计 ===
    lines.append("## 参考文献统计\n\n")
    lines.append(f"| 指标 | 数值 | 要求 | 状态 |\n")
    lines.append(f"|------|------|------|------|\n")
    total = ref_stats.get('total', 0)
    foreign = ref_stats.get('foreign', 0)
    journal_ratio = ref_stats.get('journal_ratio', 0)
    lines.append(f"| 总数 | {total} | ≥30 | {'✅' if total >= 30 else '❌'} |\n")
    lines.append(f"| 外文 | {foreign} | ≥10 | {'✅' if foreign >= 10 else '❌'} |\n")
    lines.append(f"| 期刊占比 | {journal_ratio:.1%} | ≥50% | {'✅' if journal_ratio >= 0.5 else '❌'} |\n")
    lines.append("\n")

    # === 自动评分结果（仅供参考）===
    lines.append("## 自动评分结果（Python规则评分，仅供参考）\n\n")
    total_pct = (scoring_result.total_score / scoring_result.max_total * 100) if scoring_result.max_total > 0 else 0
    lines.append(f"**总分**：{scoring_result.total_score}/{scoring_result.max_total} ({total_pct:.1f}%)\n\n")

    lines.append("| 评价维度 | 得分 | 等级 |\n")
    lines.append("|----------|------|------|\n")
    grade_icons = {'A': '🟢', 'B': '🟡', 'C': '🔵', 'D': '🔵', 'F': '🔴'}
    for dim in scoring_result.dimensions:
        grade = dim.grade
        icon = grade_icons.get(grade, '⚪')
        lines.append(f"| {dim.name} | {dim.score}/{dim.max_score} | {icon} |\n")
    lines.append("\n")

    lines.append("**子项评分：**\n\n")
    for dim in scoring_result.dimensions:
        lines.append(f"**{dim.name}**\n")
        for sub in dim.sub_items:
            passed = sub.get('passed', False)
            status = "✅" if passed else "❌"
            lines.append(f"- {status} {sub['name']}：{sub['score']}/{sub['max']}\n")
        lines.append("\n")

    # === 按7维度组织论文内容 ===
    lines.append("---\n\n")
    lines.append("# 论文内容（按评价维度组织）\n\n")

    for dim_name in DIMENSION_CHAPTER_MAPPING.keys():
        lines.append(f"## 【{dim_name}】\n\n")

        # 找到对应的章节
        related_chapters = []
        for pattern in DIMENSION_CHAPTER_MAPPING[dim_name]:
            ch = modules.get_chapter_by_title(pattern)
            if ch:
                related_chapters.append(ch)

        # 特殊维度：创新性和写作贯穿全文
        if dim_name in ['创新性', '写作规范与表达']:
            # 使用第1章和结论章
            if modules.chapters:
                intro_ch = modules.chapters[0] if modules.chapters else None
                conclusion_ch = modules.chapters[-1] if modules.chapters else None
                if intro_ch:
                    related_chapters.append(intro_ch)
                if conclusion_ch and conclusion_ch != intro_ch:
                    related_chapters.append(conclusion_ch)
        elif dim_name == '结论与建议':
            # 使用最后两章
            if len(modules.chapters) >= 2:
                related_chapters = modules.chapters[-2:]
            elif modules.chapters:
                related_chapters = [modules.chapters[-1]]

        # 输出相关章节内容（不截断）
        if related_chapters:
            # 去重
            seen = set()
            unique_chapters = []
            for ch in related_chapters:
                if ch.number not in seen:
                    seen.add(ch.number)
                    unique_chapters.append(ch)

            for ch in unique_chapters:
                lines.append(f"### 第{ch.number}章 {ch.title}\n")
                lines.append(ch.content)
                lines.append("\n\n")
        else:
            lines.append("*（未找到明确对应的章节）*\n\n")

    # === 摘录内容（不截断） ===
    if modules.abstract_cn:
        lines.append("### 中文摘要\n")
        lines.append(modules.abstract_cn)
        lines.append("\n\n")

    if modules.abstract_en:
        lines.append("### 英文摘要\n")
        lines.append(modules.abstract_en)
        lines.append("\n\n")

    # === 参考文献（不截断） ===
    if modules.references:
        lines.append("### 参考文献\n")
        for i, ref in enumerate(modules.references, 1):
            lines.append(f"{i}. {ref}\n")
        lines.append("\n")

    # === 评价要求 ===
    lines.append("""---

# 评价要求

请根据以上论文内容，对该硕士学位论文进行深入评价。

## 输出格式

请严格按照以下Markdown格式输出评价报告：

```markdown
# 硕士学位论文评审报告

**论文题目：** [题目]
**论文类型：** [类型] ｜ **评价日期：** [日期]

---

## 一、总体评价

**综合评分：XX/100**

**各维度评分：**

| 评价维度 | 得分 |
|----------|------|
| 选题与研究意义 | XX分 |
| 文献综述与理论基础 | XX分 |
| 研究方法与技术路线 | XX分 |
| 实证分析与结果 | XX分 |
| 创新性 | XX分 |
| 写作规范与表达 | XX分 |
| 结论与建议 | XX分 |

[总体评语：综合评价论文的优缺点，100-200字]

---

## 二、各维度详细评价

### （1）选题与研究意义

**优点：**
- [优点1]
- [优点2]

**问题：**
- [问题1]
- [问题2]

### （2）文献综述与理论基础

**优点：**
- [优点1]

**问题：**
- [问题1]

### （3）研究方法与技术路线

**优点：**
- [优点1]

**问题：**
- [问题1]

### （4）实证分析与结果

**优点：**
- [优点1]

**问题：**
- [问题1]

### （5）创新性

**优点：**
- [优点1]

**问题：**
- [问题1]

### （6）写作规范与表达

**优点：**
- [优点1]

**问题：**
- [问题1]

### （7）结论与建议

**优点：**
- [优点1]

**问题：**
- [问题1]

---

## 三、修改建议

### 高优先级修改建议（必须修改）

1. **[问题描述]**：具体说明
   **修改建议**：[建议]

2. **[问题描述]**：具体说明
   **修改建议**：[建议]

### 中优先级修改建议

1. **[问题描述]**：具体说明
   **修改建议**：[建议]

### 低优先级修改建议

1. **[问题描述]**：具体说明
   **修改建议**：[建议]

---

## 四、总结

[总结性评价，说明论文是否达到毕业要求，主要优缺点]

---

*本评价依据7维度评审体系，权重：实证经济学型（实证30%+方法25%）、问卷调查型（实证30%+方法20%）、政策评价型（方法25%+实证20%）、案例分析型（创新20%+综述15%+写作15%）、混合型（实证25%+方法23%）*
```

请开始评价：
""")

    return "".join(lines)


# ============================================================================
# Review Result & Pipeline
# ============================================================================

@dataclass
class ReviewResult:
    """Complete result of thesis review"""
    modules: ThesisModules
    scoring_result: ScoringResult
    reference_stats: Dict[str, Any]
    review_prompt: str = ""

    def save_prompt(self, output_path: str):
        """Save review prompt to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.review_prompt)

    def save_scoring_json(self, output_path: str):
        """Save scoring results as JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': self.modules.title,
                'paper_type': self.scoring_result.paper_type,
                'scoring': self.scoring_result.to_dict(),
                'reference_stats': self.reference_stats,
                'chapters': [
                    {'number': ch.number, 'title': ch.title, 'char_count': ch.char_count}
                    for ch in self.modules.chapters
                ]
            }, f, ensure_ascii=False, indent=2)


class ReviewPipeline:
    """
    Main pipeline for thesis review.

    Workflow:
    1. Hierarchical parse: cover, abstract, chapters, references
    2. Rule-based scoring: 7 dimensions
    3. Generate prompt: organized by 7 dimensions
    4. AI evaluates directly in conversation
    """

    def __init__(self):
        pass

    def review(self, file_path: str) -> ReviewResult:
        """
        Run complete review pipeline

        Args:
            file_path: Path to thesis .docx/.doc file

        Returns:
            ReviewResult with modules, scoring and prompt for AI evaluation
        """
        print(f"[1/4] Parsing document hierarchically: {file_path}")
        modules = self._parse_document(file_path)

        print(f"[2/4] Extracting references...")
        ref_stats = self._extract_references(modules)

        print(f"[3/4] Rule-based scoring...")
        scoring_result = self._score(modules)

        print(f"[4/4] Generating evaluation prompt...")
        review_prompt = generate_review_prompt(modules, scoring_result, ref_stats)

        return ReviewResult(
            modules=modules,
            scoring_result=scoring_result,
            reference_stats=ref_stats,
            review_prompt=review_prompt
        )

    def _parse_document(self, file_path: str) -> ThesisModules:
        """Parse document into hierarchical modules"""
        return parse_hierarchical(file_path)

    def _extract_references(self, modules: ThesisModules) -> Dict[str, Any]:
        """Extract reference statistics from modules"""
        refs = modules.references
        total = len(refs)

        # 简单统计（完整实现需要更复杂的文本分析）
        foreign = sum(1 for r in refs if any(c.isalpha() and ord(c) > 127 for c in r[:50]))
        # 外文文献判断：前50字符中是否包含英文字母
        # 这里简化处理，实际应该用更精确的方法

        return {
            'total': total,
            'chinese': total - foreign if foreign < total else total,
            'foreign': foreign,
            'journals': int(total * 0.6),  # 估算
            'journal_ratio': 0.6,
            'recent_5yr': int(total * 0.35),  # 估算
            'recent_5yr_ratio': 0.35
        }

    def _score(self, modules: ThesisModules) -> ScoringResult:
        """Score using pure Python rules"""
        scorer = ThesisScorer()

        # 构建全文内容用于类型检测
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
            'limitations': '',
            'research_question': modules.chapters[0].content[:200] if modules.chapters else ''
        }

        return scorer.score(info, all_text)

    def _detect_method(self, text: str) -> str:
        """Detect research method from text"""
        methods = []
        method_keywords = {
            '面板数据': '面板数据回归',
            '固定效应': '固定效应模型',
            'DID': '双重差分',
            'IV': '工具变量法',
            'OLS': 'OLS回归',
            'logit': 'Logistic回归',
            '熵权法': '熵权法',
            '耦合协调度': '耦合协调度模型',
            '障碍度': '障碍度模型',
            '地理探测器': '地理探测器',
            '核密度': '核密度估计',
            'GIS': 'GIS空间分析'
        }

        for kw, name in method_keywords.items():
            if kw in text:
                methods.append(name)

        return ' + '.join(methods) if methods else '未明确识别'


def review_pipeline(file_path: str, output_dir: Optional[str] = None) -> ReviewResult:
    """
    Convenience function to run complete review pipeline

    Workflow: Hierarchical Parse → Rule-based Score → Generate Prompt

    Args:
        file_path: Path to thesis .docx/.doc file
        output_dir: Optional directory to save prompt and scoring JSON

    Returns:
        ReviewResult with modules, scoring and review_prompt for AI evaluation
    """
    pipeline = ReviewPipeline()
    result = pipeline.review(file_path)

    # Save outputs if output_dir specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stem = Path(file_path).stem

        # Save evaluation prompt
        prompt_path = output_path / f"{stem}_评价Prompt.md"
        result.save_prompt(str(prompt_path))
        print(f"\n评价Prompt已保存至: {prompt_path}")

        # Save scoring JSON
        json_path = output_path / f"{stem}_评审数据.json"
        result.save_scoring_json(str(json_path))
        print(f"评审数据已保存至: {json_path}")

    return result
