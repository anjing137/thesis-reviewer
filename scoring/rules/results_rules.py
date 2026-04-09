"""
Results and Conclusions Scoring Rules (20 points)
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


class ResultsScoringRules:
    """
    Scoring rules for results/conclusion dimension (20 points)

    Sub-dimensions:
    1. Conclusion Validity (7 points)
    2. Evidence-Support (7 points)
    3. Limitations Acknowledgment (6 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate results and conclusions dimension"""
        self.results = []
        total_score = 0
        max_total = 20

        # Rule 1: Conclusion validity (0-7)
        validity_score, validity_evidence = self._evaluate_validity(info)
        self.results.append(ScoreResult(
            score=validity_score,
            max_score=7,
            passed=validity_score >= 4,
            rule_name="结论有效性",
            evidence=validity_evidence,
            suggestion="建议加强结论的有效性论证" if validity_score < 4 else ""
        ))
        total_score += validity_score

        # Rule 2: Evidence support (0-7)
        evidence_score, evidence_str = self._evaluate_evidence_support(info)
        self.results.append(ScoreResult(
            score=evidence_score,
            max_score=7,
            passed=evidence_score >= 4,
            rule_name="证据支撑",
            evidence=evidence_str,
            suggestion="建议用更多数据支撑结论" if evidence_score < 4 else ""
        ))
        total_score += evidence_score

        # Rule 3: Limitations (0-6)
        limit_score, limit_evidence = self._evaluate_limitations(info)
        self.results.append(ScoreResult(
            score=limit_score,
            max_score=6,
            passed=limit_score >= 3,
            rule_name="局限性说明",
            evidence=limit_evidence,
            suggestion="建议明确讨论研究局限" if limit_score < 3 else ""
        ))
        total_score += limit_score

        return {
            'dimension': '实证分析与结果',
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

    def _evaluate_validity(self, info: Dict) -> Tuple[float, str]:
        """Evaluate if conclusions are valid based on methods used"""
        conclusion = info.get('main_conclusion', '')
        method = info.get('method', '')
        has_robustness = info.get('has_robustness')

        score = 3  # Base score
        evidence = ""

        if not conclusion or conclusion == 'null':
            return 0, "未明确识别到结论"

        # Check conclusion length (too short = suspicious)
        if len(conclusion) > 50:
            score += 1
            evidence += "结论描述较为详细；"
        elif len(conclusion) < 20:
            score -= 1
            evidence += "结论过于简略；"

        # If has robustness check, conclusions more可信
        if has_robustness:
            score += 2
            evidence += "有稳健性检验支撑，结论较可信；"
        else:
            evidence += "无稳健性检验，结论可信度受限；"

        # Check if conclusion matches method
        if method and conclusion:
            if ('OLS' in method.upper() or '回归' in method) and has_robustness is False:
                score -= 1
                evidence += "回归分析无稳健性检验，结论需谨慎；"

        return max(0, min(score, 7)), evidence or "结论有效性评估依据不足"

    def _evaluate_evidence_support(self, info: Dict) -> Tuple[float, str]:
        """Evaluate if conclusions are supported by evidence"""
        conclusion = info.get('main_conclusion', '')
        data = info.get('data', {})

        score = 3  # Base score
        evidence = ""

        # Check if sample size mentioned (supports evidence)
        sample_size = data.get('sample_size', '')
        if sample_size and str(sample_size) != 'null':
            score += 2
            evidence += f"有数据支撑（样本量：{sample_size}）；"

        # Check conclusion specificity
        specific_terms = ['显著', '正向', '负向', '促进', '抑制', '提高', '降低', '相关']
        if conclusion and any(term in conclusion for term in specific_terms):
            score += 2
            evidence += "结论有具体统计支撑；"

        # Check for quantified results
        import re
        if conclusion and re.search(r'\d+\.?\d*%', conclusion):
            score += 1
            evidence += "结论有量化数据；"

        return max(0, min(score, 7)), evidence or "证据支撑评估依据不足"

    def _evaluate_limitations(self, info: Dict) -> Tuple[float, str]:
        """Evaluate if limitations are acknowledged"""
        limitations = info.get('limitations', '')

        if not limitations or limitations == 'null':
            return 2, "未明确讨论研究局限【建议改进】"

        if len(limitations) > 20:
            return 5, f"明确讨论研究局限：{limitations[:50]}；"

        return 3, f"提及研究局限但不够详细：{limitations}；"
