"""
Writing Quality Scoring Rules (10 points)
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass
class ScoreResult:
    """Result of a scoring rule"""
    score: float
    max_score: float
    passed: bool
    rule_name: str
    evidence: str
    suggestion: str


class WritingScoringRules:
    """
    Scoring rules for writing quality dimension (10 points)

    Sub-dimensions:
    1. Academic Language (4 points)
    2. Clarity and Conciseness (3 points)
    3. Citation Standard (3 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate writing quality dimension"""
        self.results = []
        total_score = 0
        max_total = 10

        # Rule 1: Academic language (0-4)
        lang_score, lang_evidence = self._evaluate_academic_language(info)
        self.results.append(ScoreResult(
            score=lang_score,
            max_score=4,
            passed=lang_score >= 2,
            rule_name="学术语言",
            evidence=lang_evidence,
            suggestion="建议规范学术表达" if lang_score < 2 else ""
        ))
        total_score += lang_score

        # Rule 2: Clarity (0-3)
        clarity_score, clarity_evidence = self._evaluate_clarity(info)
        self.results.append(ScoreResult(
            score=clarity_score,
            max_score=3,
            passed=clarity_score >= 2,
            rule_name="清晰简洁",
            evidence=clarity_evidence,
            suggestion="建议精简表述" if clarity_score < 2 else ""
        ))
        total_score += clarity_score

        # Rule 3: Citation standard (0-3)
        citation_score, citation_evidence = self._evaluate_citation(info)
        self.results.append(ScoreResult(
            score=citation_score,
            max_score=3,
            passed=citation_score >= 2,
            rule_name="引用规范",
            evidence=citation_evidence,
            suggestion="建议规范引用格式" if citation_score < 2 else ""
        ))
        total_score += citation_score

        return {
            'dimension': '写作规范与表达',
            'dimension_score': total_score,
            'max_score': max_total,
            'sub_items': [
                {
                    'name': r.rule_name,
                    'score': r.score,
                    'max': r.max_score,
                    'passed': r.passed,
                    'evidence': r.evidence,
                    'suggestion': r.suggestion
                }
                for r in self.results
            ],
            'critical_issues': [r for r in self.results if not r.passed],
            'suggestions': [r.suggestion for r in self.results if r.suggestion]
        }

    def _evaluate_academic_language(self, info: Dict) -> Tuple[float, str]:
        """Evaluate academic language usage"""
        # Check format compliance
        format_check = info.get('format_check', {})
        references = format_check.get('references', {})

        score = 3  # Base score
        evidence = "学术语言基本规范"

        # Check reference format
        ref_compliant = references.get('compliant', True)
        if not ref_compliant:
            score -= 1
            evidence += "，参考文献格式需改进"

        return min(score, 4), evidence

    def _evaluate_clarity(self, info: Dict) -> Tuple[float, str]:
        """Evaluate writing clarity and conciseness"""
        conclusion = info.get('main_conclusion', '')
        rq = info.get('research_question', '')

        score = 2  # Base score
        evidence = "表达清晰度基本合格"

        # Check if text is reasonably concise
        if conclusion and 20 < len(conclusion) < 500:
            score += 1
            evidence += "，结论表述适中"

        return min(score, 3), evidence

    def _evaluate_citation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate citation standard"""
        format_check = info.get('format_check', {})
        references = format_check.get('references', {})

        score = 1  # Base score
        evidence = ""

        ref_compliant = references.get('compliant', True)
        if ref_compliant:
            score += 1
            evidence += "参考文献格式规范；"
        else:
            issues = references.get('issues', [])
            if issues:
                evidence += f"存在引用问题：{issues[0]}；"

        # Check if has references
        ref_info = format_check.get('structure', {})
        if ref_info:
            score += 1
            evidence += "包含参考文献部分"

        return min(score, 3), evidence or "引用规范性评估依据不足"
