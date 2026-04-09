"""
Structure and Logic Scoring Rules (10 points)
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


class StructureScoringRules:
    """
    Scoring rules for structure/logic dimension (10 points)

    Sub-dimensions:
    1. Chapter Structure (4 points)
    2. Logic Flow (3 points)
    3. Section Coherence (3 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate structure dimension"""
        self.results = []
        total_score = 0
        max_total = 10

        # Rule 1: Chapter structure (0-4)
        chapter_score, chapter_evidence = self._evaluate_chapter_structure(info)
        self.results.append(ScoreResult(
            score=chapter_score,
            max_score=4,
            passed=chapter_score >= 2,
            rule_name="章节结构",
            evidence=chapter_evidence,
            suggestion="建议完善章节设置" if chapter_score < 2 else ""
        ))
        total_score += chapter_score

        # Rule 2: Logic flow (0-3)
        logic_score, logic_evidence = self._evaluate_logic_flow(info)
        self.results.append(ScoreResult(
            score=logic_score,
            max_score=3,
            passed=logic_score >= 2,
            rule_name="逻辑流程",
            evidence=logic_evidence,
            suggestion="建议加强逻辑衔接" if logic_score < 2 else ""
        ))
        total_score += logic_score

        # Rule 3: Section coherence (0-3)
        coherence_score, coherence_evidence = self._evaluate_section_coherence(info)
        self.results.append(ScoreResult(
            score=coherence_score,
            max_score=3,
            passed=coherence_score >= 2,
            rule_name="部分协调",
            evidence=coherence_evidence,
            suggestion="建议加强章节间过渡" if coherence_score < 2 else ""
        ))
        total_score += coherence_score

        return {
            'dimension': '结构与逻辑',
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

    def _evaluate_chapter_structure(self, info: Dict) -> Tuple[float, str]:
        """Evaluate if chapter structure follows standard format"""
        # This would require parsing the actual document structure
        # For now, use format check results
        format_check = info.get('format_check', {})

        structure = format_check.get('structure', {})
        complete = structure.get('complete', True)

        score = 2
        evidence = ""

        if complete:
            score += 2
            evidence += "论文结构完整；"
        else:
            missing = structure.get('missing_parts', [])
            if missing:
                evidence += f"缺失部分：{','.join(missing[:2])}；"

        return min(score, 4), evidence or "章节结构评估依据不足"

    def _evaluate_logic_flow(self, info: Dict) -> Tuple[float, str]:
        """Evaluate logical flow from intro to conclusion"""
        method = info.get('method', '')
        conclusion = info.get('main_conclusion', '')

        score = 2  # Base score
        evidence = ""

        # If both method and conclusion exist, assume logical flow
        if method and method != 'null' and conclusion and conclusion != 'null':
            score += 1
            evidence += "方法与结论对应；"

        # Check for research question
        rq = info.get('research_question', '')
        if rq and rq != 'null':
            score += 1
            evidence += "有明确研究问题；"

        return min(score, 3), evidence or "逻辑流程评估依据不足"

    def _evaluate_section_coherence(self, info: Dict) -> Tuple[float, str]:
        """Evaluate section-to-section coherence"""
        # Simplified assessment
        conclusion = info.get('main_conclusion', '')

        score = 2  # Base score
        evidence = "章节协调性基本合格"

        if conclusion and len(conclusion) > 30:
            score += 1
            evidence += "，结论内容充实"

        return min(score, 3), evidence
