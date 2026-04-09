"""
Hierarchical Modular Review Pipeline v3
Per-module evaluation with consolidated report generation

Design:
- Python parses: document structure, format checks, reference statistics
- AI evaluates: each module with dedicated prompts, then consolidated
"""
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

from .parser.xml_parser import parse_hierarchical, ThesisModules, ChapterModule
from .parser.docx_parser import parse_docx, ParsedDocument


# ============================================================================
# Per-Module Evaluation Prompts
# ============================================================================

MODULE_PROMPTS = {
    'cover': {
        'dimension': '格式规范',
        'checklist': [
            '论文题目是否居中、字号是否符合要求',
            '作者姓名、学号、年级等信息是否完整',
            '导师信息是否完整',
            '学校、学院名称是否正确',
            '日期是否填写完整'
        ],
        'weight': 0.05
    },

    'abstract_cn': {
        'dimension': '写作质量',
        'checklist': [
            '摘要是否完整概括研究目的、方法、结果和结论',
            '字数是否符合要求（300-500字）',
            '关键词是否3-5个，与研究内容相关',
            '语言是否简练、准确'
        ],
        'weight': 0.05
    },

    'abstract_en': {
        'dimension': '写作质量',
        'checklist': [
            '英文摘要是否与中文摘要内容一致',
            '英文表达是否准确、地道',
            'Keywords是否与中文关键词对应'
        ],
        'weight': 0.03
    },

    'originality': {
        'dimension': '学术规范',
        'checklist': [
            '独创性声明是否完整',
            '作者签名和日期是否完整',
            '授权声明是否完整'
        ],
        'weight': 0.02
    },

    'toc': {
        'dimension': '格式规范',
        'checklist': [
            '目录是否完整（一级、二级标题）',
            '页码是否连续',
            '章节标题是否与正文一致'
        ],
        'weight': 0.03
    },

    'chapter_intro': {
        'dimension': '研究问题',
        'checklist': [
            '研究背景是否充分、有逻辑',
            '研究问题是否明确、具体',
            '研究意义（理论/实践）是否阐述清晰',
            '研究内容是否界定清晰',
            '技术路线是否合理可行'
        ],
        'weight': 0.15
    },

    'chapter_literature': {
        'dimension': '文献综述',
        'checklist': [
            '文献综述是否系统、全面',
            '国内外研究现状评述是否到位',
            '文献引用是否规范（GB/T 7714）',
            '是否清晰指出研究 gap',
            '理论基础是否扎实'
        ],
        'weight': 0.10
    },

    'chapter_method': {
        'dimension': '方法论',
        'checklist': [
            '研究方法选择是否合理',
            '研究设计是否科学',
            '数据来源、样本选择是否清晰',
            '变量定义、测量是否规范',
            '分析方法是否匹配研究问题'
        ],
        'weight': 0.20
    },

    'chapter_empirical': {
        'dimension': '实证分析',
        'checklist': [
            '描述性统计是否完整',
            '模型设定是否合理',
            '回归结果是否可靠',
            '内生性问题是否处理',
            '稳健性检验是否充分',
            '结果解释是否准确'
        ],
        'weight': 0.20
    },

    'chapter_conclusion': {
        'dimension': '结论与创新',
        'checklist': [
            '主要结论是否与研究发现一致',
            '结论是否有针对性、可操作性',
            '研究局限是否诚实讨论',
            '未来展望是否合理',
            '创新点是否明确、有据可依'
        ],
        'weight': 0.12
    },

    'references': {
        'dimension': '参考文献',
        'checklist': [
            '文献数量是否达标（≥30篇）',
            '外文文献比例是否达标（≥30%）',
            '期刊文献比例是否达标（≥50%）',
            '近五年文献比例是否达标（≥30%）',
            '引用格式是否规范'
        ],
        'weight': 0.05
    },

    'acknowledgments': {
        'dimension': '格式规范',
        'checklist': [
            '致谢是否真挚、得体',
            '长度是否适中（300-500字）',
            '格式是否规范'
        ],
        'weight': 0.02
    }
}


@dataclass
class ModuleEvaluation:
    """Evaluation result for a single module"""
    module_name: str
    dimension: str
    score: float
    max_score: float
    findings: List[str]  # What's good
    issues: List[str]  # What's problematic
    suggestions: List[str]  # How to improve
    evidence: str  # Excerpt from the module


@dataclass
class ConsolidatedReport:
    """Consolidated evaluation report"""
    title: str
    paper_type: str
    overall_score: float
    module_evaluations: List[ModuleEvaluation]
    reference_stats: Dict[str, Any]

    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = []

        # Header
        lines.append("# 硕士学位论文评价报告\n")
        lines.append(f"**论文题目**: {self.title}\n")
        lines.append(f"**论文类型**: {self.paper_type}\n")
        lines.append(f"**综合评分**: {self.overall_score}/100\n")

        # Reference stats
        lines.append("\n## 参考文献统计\n")
        lines.append(f"- 总数: {self.reference_stats.get('total', 0)} 篇\n")
        lines.append(f"- 中文: {self.reference_stats.get('chinese', 0)} 篇\n")
        lines.append(f"- 外文: {self.reference_stats.get('foreign', 0)} 篇\n")
        lines.append(f"- 期刊: {self.reference_stats.get('journals', 0)} 篇\n")
        lines.append(f"- 近五年: {self.reference_stats.get('recent_5yr', 0)} 篇\n")

        # Per-module evaluations
        lines.append("\n## 分项评价\n")
        for eval_result in self.module_evaluations:
            lines.append(f"\n### {eval_result.module_name} ({eval_result.dimension})\n")
            lines.append(f"**评分**: {eval_result.score}/{eval_result.max_score}\n")
            lines.append(f"**优点**:\n")
            for f in eval_result.findings:
                lines.append(f"- {f}\n")
            lines.append(f"**问题**:\n")
            for i in eval_result.issues:
                lines.append(f"- {i}\n")
            lines.append(f"**修改建议**:\n")
            for s in eval_result.suggestions:
                lines.append(f"- {s}\n")

        return "".join(lines)


class HierarchicalReviewPipeline:
    """
    Hierarchical review pipeline that:
    1. Parses thesis into modules (cover, chapters, references, etc.)
    2. Generates per-module evaluation prompts
    3. Consolidates into final report
    """

    def __init__(self):
        pass

    def review(self, file_path: str) -> ConsolidatedReport:
        """Run hierarchical review"""
        print(f"[1/4] Parsing document hierarchically...")
        modules = self._parse_document(file_path)

        print(f"[2/4] Extracting references...")
        ref_stats = self._extract_references(file_path)

        print(f"[3/4] Generating module evaluation prompts...")
        evaluations = self._generate_module_evaluations(modules, ref_stats)

        print(f"[4/4] Consolidating report...")
        report = self._consolidate_report(modules, evaluations, ref_stats)

        return report

    def _parse_document(self, file_path: str) -> ThesisModules:
        """Parse using hierarchical parser"""
        return parse_hierarchical(file_path)

    def _extract_references(self, file_path: str) -> Dict[str, Any]:
        """Extract reference statistics"""
        # Use existing reference extraction logic
        from .parser.xml_parser import extract_references
        ref_info = extract_references(file_path)
        return {
            'total': ref_info['total'],
            'chinese': ref_info['chinese'],
            'foreign': ref_info['foreign'],
            'journals': ref_info['journals'],
            'journal_ratio': ref_info['journal_ratio'],
            'recent_5yr': ref_info['recent_5yr'],
            'recent_5yr_ratio': ref_info['recent_5yr_ratio'],
        }

    def _generate_module_evaluations(self, modules: ThesisModules,
                                     ref_stats: Dict) -> List[ModuleEvaluation]:
        """Generate evaluation for each module"""
        evaluations = []

        # Cover page
        if modules.cover:
            evaluations.append(ModuleEvaluation(
                module_name="封面",
                dimension="格式规范",
                score=0,  # AI will fill in
                max_score=10,
                findings=[],
                issues=[],
                suggestions=[],
                evidence=modules.cover[:500]
            ))

        # Abstract
        if modules.abstract_cn:
            evaluations.append(ModuleEvaluation(
                module_name="中文摘要",
                dimension="写作质量",
                score=0,
                max_score=10,
                findings=[],
                issues=[],
                suggestions=[],
                evidence=modules.abstract_cn[:1000]
            ))

        if modules.abstract_en:
            evaluations.append(ModuleEvaluation(
                module_name="英文摘要",
                dimension="写作质量",
                score=0,
                max_score=10,
                findings=[],
                issues=[],
                suggestions=[],
                evidence=modules.abstract_en[:1000]
            ))

        # Chapters - identify type and generate appropriate evaluation
        for chapter in modules.chapters:
            eval_result = self._evaluate_chapter(chapter)
            if eval_result:
                evaluations.append(eval_result)

        # References
        if modules.references:
            ref_text = '\n'.join(modules.references[:20])  # First 20 refs
            evaluations.append(ModuleEvaluation(
                module_name="参考文献",
                dimension="参考文献规范",
                score=0,
                max_score=10,
                findings=[],
                issues=[],
                suggestions=[],
                evidence=ref_text
            ))

        # Acknowledgments
        if modules.acknowledgments:
            evaluations.append(ModuleEvaluation(
                module_name="致谢",
                dimension="格式规范",
                score=0,
                max_score=10,
                findings=[],
                issues=[],
                suggestions=[],
                evidence=modules.acknowledgments[:500]
            ))

        return evaluations

    def _evaluate_chapter(self, chapter: ChapterModule) -> Optional[ModuleEvaluation]:
        """Determine chapter type and generate evaluation prompt"""
        title = chapter.title.lower()

        # Determine chapter type
        if any(kw in title for kw in ['引言', '绪论', '背景', '前言', '研究背景']):
            dim = '研究问题'
            checklist = MODULE_PROMPTS['chapter_intro']['checklist']
        elif any(kw in title for kw in ['文献', '综述', '研究现状', '理论基础', '概念']):
            dim = '文献综述'
            checklist = MODULE_PROMPTS['chapter_literature']['checklist']
        elif any(kw in title for kw in ['方法', '研究设计', '模型', '数据']):
            dim = '方法论'
            checklist = MODULE_PROMPTS['chapter_method']['checklist']
        elif any(kw in title for kw in ['实证', '结果', '分析', '发现', '讨论']):
            dim = '实证分析'
            checklist = MODULE_PROMPTS['chapter_empirical']['checklist']
        elif any(kw in title for kw in ['结论', '总结', '展望', '创新']):
            dim = '结论与创新'
            checklist = MODULE_PROMPTS['chapter_conclusion']['checklist']
        else:
            dim = '论文内容'
            checklist = ['内容是否完整', '逻辑是否清晰', '表达是否规范']

        # Limit content to prevent token overflow
        evidence = chapter.content[:8000]

        return ModuleEvaluation(
            module_name=f"第{chapter.number}章 {chapter.title}",
            dimension=dim,
            score=0,
            max_score=10,
            findings=[],
            issues=[],
            suggestions=[],
            evidence=evidence
        )

    def _consolidate_report(self, modules: ThesisModules,
                           evaluations: List[ModuleEvaluation],
                           ref_stats: Dict) -> ConsolidatedReport:
        """Consolidate evaluations into final report"""
        # Detect paper type
        paper_type = self._detect_paper_type(modules)

        # Calculate overall score (placeholder - AI will refine)
        overall_score = self._calculate_preliminary_score(evaluations, ref_stats)

        return ConsolidatedReport(
            title=modules.title,
            paper_type=paper_type,
            overall_score=overall_score,
            module_evaluations=evaluations,
            reference_stats=ref_stats
        )

    def _detect_paper_type(self, modules: ThesisModules) -> str:
        """Detect paper type based on content"""
        all_text = ' '.join([ch.content for ch in modules.chapters])

        # Check for empirical economics indicators
        empirical_keywords = ['回归', 'OLS', 'DID', 'IV', '面板', '固定效应', 'PSM']
        survey_keywords = ['问卷', '调查', 'logistic', 'logit', '量表', '信度', '效度']
        case_keywords = ['案例', '访谈', '扎根', '定性']
        policy_keywords = ['政策', '对策', '建议', '路径', '策略']

        empirical_count = sum(1 for kw in empirical_keywords if kw in all_text)
        survey_count = sum(1 for kw in survey_keywords if kw in all_text)
        case_count = sum(1 for kw in case_keywords if kw in all_text)
        policy_count = sum(1 for kw in policy_keywords if kw in all_text)

        max_count = max(empirical_count, survey_count, case_count, policy_count)

        if empirical_count == max_count:
            return '实证经济学型'
        elif survey_count == max_count:
            return '问卷调查实证型'
        elif case_count == max_count:
            return '案例研究型'
        else:
            return '政策研究型'

    def _calculate_preliminary_score(self, evaluations: List[ModuleEvaluation],
                                    ref_stats: Dict) -> float:
        """Calculate preliminary score (Python rule-based part)"""
        # This is a simplified scoring - AI will refine
        score = 50.0  # Base score

        # Reference bonuses/penalties
        if ref_stats['total'] >= 30:
            score += 5
        if ref_stats['foreign'] >= 10:
            score += 3
        if ref_stats['journal_ratio'] >= 0.5:
            score += 2

        return min(score, 100)


def generate_module_review_prompts(modules: ThesisModules,
                                   evaluations: List[ModuleEvaluation],
                                   ref_stats: Dict) -> str:
    """
    Generate comprehensive prompt for AI to evaluate each module.
    Returns a structured prompt document.
    """
    lines = []

    # Header
    lines.append("# 硕士学位论文分模块评价\n\n")
    lines.append(f"**论文题目**: {modules.title}\n\n")
    lines.append("---\n\n")

    # Reference statistics
    lines.append("## 参考文献统计\n\n")
    lines.append(f"| 指标 | 数值 | 要求 | 状态 |\n")
    lines.append(f"|------|------|------|------|\n")
    lines.append(f"| 总数 | {ref_stats['total']} | ≥30 | {'✅' if ref_stats['total'] >= 30 else '❌'} |\n")
    lines.append(f"| 外文 | {ref_stats['foreign']} | ≥10 | {'✅' if ref_stats['foreign'] >= 10 else '❌'} |\n")
    lines.append(f"| 期刊占比 | {ref_stats['journal_ratio']:.1%} | ≥50% | {'✅' if ref_stats['journal_ratio'] >= 0.5 else '❌'} |\n")
    lines.append(f"| 近五年占比 | {ref_stats['recent_5yr_ratio']:.1%} | ≥30% | {'✅' if ref_stats['recent_5yr_ratio'] >= 0.3 else '❌'} |\n")
    lines.append("\n---\n\n")

    # Chapters overview
    lines.append("## 章节结构\n\n")
    lines.append(modules.chapter_summary())
    lines.append("\n\n---\n\n")

    # Per-module evaluation requests
    lines.append("## 分模块评价\n\n")

    for i, eval_result in enumerate(evaluations, 1):
        lines.append(f"### {i}. {eval_result.module_name}\n")
        lines.append(f"**评价维度**: {eval_result.dimension}\n\n")

        lines.append("**原文内容**:\n")
        lines.append("```\n")
        lines.append(eval_result.evidence[:3000])
        if len(eval_result.evidence) > 3000:
            lines.append("\n... [内容已截断]\n")
        lines.append("```\n\n")

        lines.append("**评价要点**:\n")
        # Get checklist based on dimension
        checklist_key = None
        for key in MODULE_PROMPTS:
            if MODULE_PROMPTS[key]['dimension'] == eval_result.dimension:
                checklist_key = key
                break

        if checklist_key:
            for item in MODULE_PROMPTS[checklist_key]['checklist']:
                lines.append(f"- [ ] {item}\n")
        else:
            lines.append("- [ ] 内容是否完整\n")
            lines.append("- [ ] 逻辑是否清晰\n")
            lines.append("- [ ] 表达是否规范\n")

        lines.append("\n---\n\n")

    # Summary section
    lines.append("""## 综合评价要求

请根据以上分模块内容，对论文进行全面评价：

### 1. 格式规范检查
- [ ] 封面格式是否规范
- [ ] 摘要格式是否规范
- [ ] 目录是否完整
- [ ] 章节标题层级是否统一
- [ ] 图表编号是否规范
- [ ] 参考文献格式是否统一

### 2. 各维度评价
请对每个模块的以下方面进行评价：
- **优点**：该部分的亮点
- **问题**：存在的具体问题
- **修改建议**：具体的修改方案

### 3. 输出格式

请严格按照以下格式输出评价报告：

```markdown
# 硕士学位论文评价报告

## 基本信息
| 项目 | 内容 |
|---|---|
| 论文题目 | |
| 论文类型 | |
| 综合评分 | XX/100 |

## 格式规范检查
| 检查项 | 状态 | 问题 |
|---|---|---|
| 封面 | ✅/❌ | |
| 摘要 | ✅/❌ | |
| ... | ... | ... |

## 分项评价

### 第X章 [章标题]
**优点**:
-
**问题**:
-
**修改建议**:
-

[其他章节...]

## 综合结论
[是否达到毕业要求，建议等]
```

请开始评价：
""")

    return "".join(lines)


def review_hierarchical(file_path: str, output_dir: Optional[str] = None) -> ConsolidatedReport:
    """
    Run hierarchical review pipeline.
    Returns consolidated report.
    """
    pipeline = HierarchicalReviewPipeline()
    modules = pipeline._parse_document(file_path)
    ref_stats = pipeline._extract_references(file_path)
    evaluations = pipeline._generate_module_evaluations(modules, ref_stats)
    report = pipeline._consolidate_report(modules, evaluations, ref_stats)

    # Generate prompt
    prompt = generate_module_review_prompts(modules, evaluations, ref_stats)

    # Save outputs
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        stem = Path(file_path).stem

        # Save evaluation prompt
        prompt_path = output_path / f"{stem}_分模块Prompt.md"
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"分模块Prompt已保存至: {prompt_path}")

        # Save consolidated report
        report_path = output_path / f"{stem}_评审报告.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report.to_markdown())
        print(f"评审报告已保存至: {report_path}")

        # Save JSON
        json_path = output_path / f"{stem}_评审数据.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': modules.title,
                'paper_type': report.paper_type,
                'reference_stats': ref_stats,
                'chapters': [
                    {'number': ch.number, 'title': ch.title, 'char_count': ch.char_count}
                    for ch in modules.chapters
                ]
            }, f, ensure_ascii=False, indent=2)
        print(f"评审数据已保存至: {json_path}")

    return report
