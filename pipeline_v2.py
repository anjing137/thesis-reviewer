"""
Main Pipeline for Thesis Reviewer v2
Modular design: Python handles rules, AI handles evaluation by module

Design: Python解析(模块化) → Python规则评分 → 模块化AI评价Prompt
"""
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

from .parser.docx_parser import parse_docx, ParsedDocument
from .parser.xml_parser import parse_modular, extract_references, ModularDocument
from .scoring.scorer import score_thesis, ThesisScorer, ScoringResult


# ============================================================================
# Modular AI Evaluation Prompt Generator
# ============================================================================

def generate_modular_review_prompt(
    paper_path: str,
    modular_doc: ModularDocument,
    ref_info: Dict[str, Any],
    scoring_result: ScoringResult
) -> str:
    """
    Generate modular evaluation prompt for AI.

    The AI receives only the modules it needs for each evaluation dimension,
    not the entire document.
    """
    lines = []

    # === Paper Basic Info ===
    lines.append("# 硕士学位论文评价\n\n")
    lines.append("## 一、论文基本信息\n\n")
    lines.append(f"- **论文题目**：{modular_doc.title or '未提取到标题'}\n")
    lines.append(f"- **文件路径**：{paper_path}\n")

    # Calculate total text
    total_chars = sum(m.char_count for m in modular_doc.modules.values())
    lines.append(f"- **正文字数**：约 {total_chars} 字\n")

    # Paper type and reference info
    lines.append(f"- **检测类型**：{scoring_result.paper_type}\n")
    lines.append(f"- **参考文献**：{ref_info['total']} 篇\n")
    lines.append(f"  - 中文文献：{ref_info['chinese']} 篇\n")
    lines.append(f"  - 外文文献：{ref_info['foreign']} 篇\n")
    lines.append(f"  - 期刊文献：{ref_info['journals']} 篇 ({ref_info['journal_ratio']:.1%})\n")
    lines.append(f"  - 近五年文献：{ref_info['recent_5yr']} 篇 ({ref_info['recent_5yr_ratio']:.1%})\n")
    lines.append("\n")

    # === Auto Scoring Results (Python Rule-based) ===
    lines.append("## 二、自动评分结果（Python规则评分，仅供参考）\n\n")
    total_pct = (scoring_result.total_score / scoring_result.max_total * 100) if scoring_result.max_total > 0 else 0
    lines.append(f"**总分**：{scoring_result.total_score}/{scoring_result.max_total} ({total_pct:.1f}%)\n\n")

    grade_icons = {'A': '🟢', 'B': '🟡', 'C': '🔵', 'D': '🔵', 'F': '🔴'}
    for dim in scoring_result.dimensions:
        grade = dim.grade
        icon = grade_icons.get(grade, '⚪')
        lines.append(f"### {dim.name}：{dim.score}/{dim.max_score} {icon}\n\n")
        for sub in dim.sub_items:
            passed = sub.get('passed', False)
            status = "✅" if passed else "❌"
            lines.append(f"- {status} **{sub['name']}**：{sub['score']}/{sub['max']}\n")
            if sub.get('evidence'):
                lines.append(f"  - 证据：{sub['evidence']}\n")
        lines.append("\n")

    # === Key Issues Summary ===
    critical = [s for s in scoring_result.suggestions if s]
    if critical:
        lines.append("## 三、重点问题（基于规则检测）\n\n")
        for i, s in enumerate(critical[:10], 1):
            lines.append(f"{i}. {s}\n")
        lines.append("\n")

    # === Module Content for AI Evaluation ===
    lines.append("## 四、论文内容模块（供AI评价使用）\n\n")

    # For each evaluation dimension, provide the relevant module content

    # 1. Research Question - uses introduction and theory modules
    lines.append("### 研究问题评价 - 相关模块内容\n\n")
    if 'introduction' in modular_doc.modules:
        intro = modular_doc.modules['introduction'].content
        lines.append(f"**引言/研究背景** (前2000字)：\n{intro[:2000]}\n\n")
    if 'related_concepts' in modular_doc.modules:
        concepts = modular_doc.modules['related_concepts'].content
        lines.append(f"**相关概念** (前1000字)：\n{concepts[:1000]}\n\n")

    # 2. Methodology - uses methodology and empirical modules
    lines.append("### 方法论评价 - 相关模块内容\n\n")
    if 'methodology' in modular_doc.modules:
        method = modular_doc.modules['methodology'].content
        lines.append(f"**研究方法** (前15000字)：\n{method[:15000]}\n\n")
    if 'empirical' in modular_doc.modules:
        empirical = modular_doc.modules['empirical'].content
        lines.append(f"**实证分析** (前15000字)：\n{empirical[:15000]}\n\n")

    # 3. Results - uses results module
    lines.append("### 结果与结论评价 - 相关模块内容\n\n")
    if 'results' in modular_doc.modules:
        results = modular_doc.modules['results'].content
        lines.append(f"**结果与讨论** (前15000字)：\n{results[:15000]}\n\n")
    if 'conclusion' in modular_doc.modules:
        conclusion = modular_doc.modules['conclusion'].content
        lines.append(f"**结论** (前1500字)：\n{conclusion[:1500]}\n\n")

    # 4. Innovation - uses multiple modules
    lines.append("### 创新性评价 - 相关模块内容\n\n")
    if 'introduction' in modular_doc.modules:
        lines.append(f"**引言（创新点描述）** (前1500字)：\n{modular_doc.modules['introduction'].content[:1500]}\n\n")

    # 5. Writing Quality - uses body text sample
    lines.append("### 写作质量评价 - 正文示例\n\n")
    if 'empirical' in modular_doc.modules:
        lines.append(f"**实证章节** (前1500字)：\n{modular_doc.modules['empirical'].content[:1500]}\n\n")

    # 6. References - already provided in section 1

    # === Evaluation Requirements ===
    lines.append("""## 五、评价要求

请根据以上论文内容和模块信息，对该硕士学位论文进行深入评价：

### 1. 验证自动评分
- 检查自动评分是否合理
- 根据实际论文内容调整评分

### 2. 重点关注
- **研究问题**：问题是否清晰、有何理论/实践意义
- **方法论**：方法是否匹配研究问题、数据是否可靠
- **创新性**：是否有选题/方法/数据创新
- **参考文献**：数量、质量、时效性是否达标（Python已检测）

### 3. 输出格式

请严格按照以下Markdown格式输出评价报告：

```markdown
# 硕士学位论文评价报告

## 一、基本信息
| 项目 | 内容 |
|---|---|
| 论文题目 | |
| 检测类型 | |
| 自动评分 | XX/100 |

## 二、总评
[100-200字的总体评价]

## 三、分项评价

### 1. 研究问题（XX分）
**优点：**
-
**问题：**
-
**修改建议：**
-

### 2. 方法论严谨性（XX分）
...

[其他维度...]

## 四、严重问题（必须修改）
1.
2.

## 五、修改建议
### 高优先级
1.
### 中优先级
1.

## 六、综合结论
[是否达到硕士学位要求，建议等]
```

请开始评价：
""")

    return "".join(lines)


def save_review_prompt_v2(
    paper_path: str,
    modular_doc: ModularDocument,
    ref_info: Dict[str, Any],
    scoring_result: ScoringResult,
    output_dir: str
) -> str:
    """Save evaluation prompt to file"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stem = Path(paper_path).stem
    prompt_file = output_path / f"{stem}_评价Prompt.md"

    prompt = generate_modular_review_prompt(paper_path, modular_doc, ref_info, scoring_result)

    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    return str(prompt_file)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ReviewResult:
    """Complete result of thesis review"""
    modular_doc: ModularDocument
    ref_info: Dict[str, Any]
    scoring_result: ScoringResult
    review_prompt: str = ""

    def save_prompt(self, output_path: str):
        """Save review prompt to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.review_prompt)

    def save_scoring_json(self, output_path: str):
        """Save scoring results as JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': self.modular_doc.title,
                'paper_type': self.scoring_result.paper_type,
                'scoring': self.scoring_result.to_dict(),
                'references': {
                    'total': self.ref_info['total'],
                    'chinese': self.ref_info['chinese'],
                    'foreign': self.ref_info['foreign'],
                    'journals': self.ref_info['journals'],
                    'journal_ratio': self.ref_info['journal_ratio'],
                    'recent_5yr': self.ref_info['recent_5yr'],
                    'recent_5yr_ratio': self.ref_info['recent_5yr_ratio'],
                }
            }, f, ensure_ascii=False, indent=2)


# ============================================================================
# Main Pipeline
# ============================================================================

class ReviewPipeline:
    """
    Main pipeline for thesis review v2.

    Workflow: Modular Parse → Rule Scoring → Modular AI Prompt
    - Python handles: parsing, reference extraction, format checking, rule scoring
    - AI evaluates: research quality, methodology, innovation, writing
    """

    def __init__(self):
        pass

    def review(self, file_path: str) -> ReviewResult:
        """
        Run complete review pipeline

        Args:
            file_path: Path to thesis .doc/.docx file

        Returns:
            ReviewResult with modular document, reference info, scoring and prompt
        """
        print(f"[1/4] Parsing document (modular): {file_path}")
        modular_doc = self._parse_document(file_path)

        print(f"[2/4] Extracting references...")
        ref_info = self._extract_references(file_path)

        print(f"[3/4] Rule-based scoring...")
        scoring_result = self._score(modular_doc, ref_info)

        print(f"[4/4] Generating evaluation prompt...")
        review_prompt = generate_modular_review_prompt(
            file_path, modular_doc, ref_info, scoring_result
        )

        return ReviewResult(
            modular_doc=modular_doc,
            ref_info=ref_info,
            scoring_result=scoring_result,
            review_prompt=review_prompt
        )

    def _parse_document(self, file_path: str) -> ModularDocument:
        """Parse document using modular XML parser"""
        return parse_modular(file_path)

    def _extract_references(self, file_path: str) -> Dict[str, Any]:
        """Extract reference information"""
        return extract_references(file_path)

    def _score(self, modular_doc: ModularDocument, ref_info: Dict[str, Any]) -> ScoringResult:
        """Score using pure Python rules with modular content"""
        scorer = ThesisScorer()

        # Helper to get module content safely
        def get_content(name: str) -> str:
            mod = modular_doc.modules.get(name)
            return mod.content if mod else ''

        # Build info dict from modular document
        info = {
            'paper_type': modular_doc.modules.get('paper_type', ''),
            'reference_section': '',
            'reference_info': {
                'total': ref_info['total'],
                'foreign': ref_info['foreign'],
                'journal_ratio': ref_info['journal_ratio'],
                'recent_5yr_ratio': ref_info['recent_5yr_ratio'],
            },
            'intro_text': get_content('introduction'),
            'method_text': get_content('methodology'),
            'results_text': get_content('results') or get_content('empirical'),
            'conclusion_text': get_content('conclusion'),
        }

        # Combine all text for keyword detection
        all_text = modular_doc.get_all_text()

        # Add keyword-based detection
        info['has_hypothesis'] = '假设' in all_text
        info['has_robustness'] = '稳健性' in all_text or '稳健性检验' in all_text or '敏感性分析' in all_text
        info['has_endogeneity'] = '内生性' in all_text or '工具变量' in all_text or 'IV' in all_text
        info['has_literature_review'] = '文献综述' in all_text or '文献回顾' in all_text

        return scorer.score(info, all_text)


from .parser.xml_parser import DocumentModule, ModularDocument


def review_pipeline_v2(file_path: str, output_dir: Optional[str] = None) -> ReviewResult:
    """
    Convenience function to run complete review pipeline v2

    Args:
        file_path: Path to thesis .doc/.docx file
        output_dir: Optional directory to save prompt and scoring JSON

    Returns:
        ReviewResult with modular document, reference info, scoring and prompt
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
        json_path = output_path / f"{stem}_评分结果.json"
        result.save_scoring_json(str(json_path))
        print(f"评分结果已保存至: {json_path}")

    return result
