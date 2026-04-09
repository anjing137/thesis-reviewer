"""
Conclusion and Recommendation Scoring Rules (5-10 points)
"""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ScoreResult:
    """Result of a scoring rule"""
    score: float
    max_score: float
    passed: bool
    rule_name: str
    evidence: str
    suggestion: str


class ConclusionScoringRules:
    """
    Scoring rules for conclusion dimension (5-10 points)

    Sub-dimensions:
    1. 结论明确性 (2-3 points)
    2. 建议可操作性 (2-3 points)
    3. 局限性说明 (1-2 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate conclusion dimension"""
        self.results = []
        total_score = 0
        max_total = 5  # Default, will be scaled

        # Rule 1: 结论明确性 (2 points)
        clarity_score, clarity_evidence = self._evaluate_clarity(info)
        self.results.append(ScoreResult(
            score=clarity_score,
            max_score=2,
            passed=clarity_score >= 1,
            rule_name="结论明确性",
            evidence=clarity_evidence,
            suggestion="建议更清晰地表述研究结论" if clarity_score < 1 else ""
        ))
        total_score += clarity_score

        # Rule 2: 建议可操作性 (2 points)
        actionable_score, actionable_evidence = self._evaluate_actionable(info)
        self.results.append(ScoreResult(
            score=actionable_score,
            max_score=2,
            passed=actionable_score >= 1,
            rule_name="建议可操作性",
            evidence=actionable_evidence,
            suggestion="建议提出更具可操作性的政策建议" if actionable_score < 1 else ""
        ))
        total_score += actionable_score

        # Rule 3: 局限性说明 (1 point)
        limitation_score, limitation_evidence = self._evaluate_limitation(info)
        self.results.append(ScoreResult(
            score=limitation_score,
            max_score=1,
            passed=limitation_score >= 0.5,
            rule_name="局限性说明",
            evidence=limitation_evidence,
            suggestion="建议加强研究局限性的讨论" if limitation_score < 0.5 else ""
        ))
        total_score += limitation_score

        return {
            'dimension': '结论与建议',
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

    def _evaluate_clarity(self, info: Dict) -> tuple:
        """Evaluate conclusion clarity"""
        conclusion = info.get('main_conclusion', '')
        score = 1
        evidence = ""

        if conclusion and len(conclusion) > 50:
            score += 1
            evidence += "结论表述详细；"
        elif conclusion and len(conclusion) > 20:
            evidence += "有基本结论表述；"
        else:
            evidence += "结论表述不够清晰；"

        return min(score, 2), evidence or "结论明确性一般"

    def _evaluate_actionable(self, info: Dict) -> tuple:
        """Evaluate policy recommendation actionability"""
        conclusion = info.get('main_conclusion', '')
        score = 1
        evidence = ""

        actionable_keywords = ['建议', '对策', '政策', '措施', '启示', '启示']
        found = sum(1 for kw in actionable_keywords if kw in conclusion)

        if found >= 2:
            score += 1
            evidence += "包含具体政策建议；"
        elif found >= 1:
            evidence += "有一般性建议；"
        else:
            evidence += "缺乏政策建议；"

        return min(score, 2), evidence or "建议可操作性需加强"

    def _evaluate_limitation(self, info: Dict) -> tuple:
        """Evaluate limitation discussion"""
        limitations = info.get('limitations', '')
        score = 0.5
        evidence = ""

        if limitations and limitations != 'null' and len(limitations) > 20:
            score += 0.5
            evidence += "讨论了研究局限；"
        else:
            evidence += "研究局限性讨论不足；"

        return min(score, 1), evidence or "局限性说明需加强"
