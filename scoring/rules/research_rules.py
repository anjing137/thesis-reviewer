"""
Research Question Scoring Rules
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


class ResearchScoringRules:
    """Scoring rules for research question dimension (15 points)"""

    SUB_ITEMS = [
        ('clarity', '问题清晰度', 5),
        ('significance', '理论意义', 5),
        ('feasibility', '实践价值', 5),
    ]

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate research question dimension

        Args:
            info: Extracted information dict

        Returns:
            Dict with scores and details
        """
        self.results = []
        total_score = 0
        max_total = 15

        # Rule 1: Problem clarity (0-5)
        clarity_score, clarity_evidence = self._evaluate_clarity(info)
        self.results.append(ScoreResult(
            score=clarity_score,
            max_score=5,
            passed=clarity_score >= 3,
            rule_name="问题清晰度",
            evidence=clarity_evidence,
            suggestion="建议明确定义核心概念，表述具体研究问题" if clarity_score < 3 else ""
        ))
        total_score += clarity_score

        # Rule 2: Theoretical significance (0-5)
        sig_score, sig_evidence = self._evaluate_significance(info)
        self.results.append(ScoreResult(
            score=sig_score,
            max_score=5,
            passed=sig_score >= 3,
            rule_name="理论意义",
            evidence=sig_evidence,
            suggestion="建议加强文献对话，明确理论贡献" if sig_score < 3 else ""
        ))
        total_score += sig_score

        # Rule 3: Practical value (0-5)
        prac_score, prac_evidence = self._evaluate_practicality(info)
        self.results.append(ScoreResult(
            score=prac_score,
            max_score=5,
            passed=prac_score >= 3,
            rule_name="实践价值",
            evidence=prac_evidence,
            suggestion="建议加强实践意义的论证" if prac_score < 3 else ""
        ))
        total_score += prac_score

        return {
            'dimension': '选题与研究意义',
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
        """Evaluate research question clarity"""
        rq = info.get('research_question', '')
        score = 0
        evidence = ""

        if not rq or rq == 'null':
            return 0, "未明确识别到研究问题"

        # Check if specific
        if len(rq) > 20:
            score += 2
            evidence += f"研究问题描述较长({len(rq)}字)，相对具体；"

        # Check if contains specific terms
        specific_terms = ['影响', '关系', '效应', '机制', '策略', '分析']
        if any(term in rq for term in specific_terms):
            score += 2
            evidence += "问题包含具体研究动词；"
        else:
            evidence += "问题表述较为宽泛；"

        # Check for research gap
        gap = info.get('research_gap', '')
        if gap and gap != 'null' and len(gap) > 10:
            score += 1
            evidence += f"识别到研究gap：{gap[:50]}；"
        else:
            evidence += "未明确识别研究gap；"

        return min(score, 5), evidence

    def _evaluate_significance(self, info: Dict) -> tuple:
        """Evaluate theoretical significance"""
        # This is inferred from the content
        method = info.get('method', '')
        data = info.get('data', {})

        score = 2  # Base score
        evidence = ""

        # If using quantitative methods, assume some theoretical contribution
        if info.get('method_details', {}).get('quantitative'):
            score += 1
            evidence += "采用定量研究方法；"

        # If sample size is reasonable
        sample = data.get('sample_size', '')
        if isinstance(sample, str) and any(char.isdigit() for char in sample):
            # Extract numbers
            import re
            numbers = re.findall(r'\d+', sample)
            if numbers:
                num = int(numbers[0])
                if num >= 200:
                    score += 1
                    evidence += f"样本量较大({num})；"
                elif num < 50:
                    score -= 1
                    evidence += f"样本量较小({num})；"

        # If identified innovation type
        innovation = info.get('innovation_type', '')
        if innovation and innovation != 'null':
            score += 1
            evidence += f"创新类型：{innovation}；"

        return max(0, min(score, 5)), evidence or "理论意义评估依据不足"

    def _evaluate_practicality(self, info: Dict) -> tuple:
        """Evaluate practical value"""
        conclusion = info.get('main_conclusion', '')
        score = 2  # Base score
        evidence = ""

        if conclusion and len(conclusion) > 30:
            score += 2
            evidence += "有明确结论；"

        # Check for policy suggestions in conclusion
        if conclusion and any(term in conclusion for term in ['建议', '对策', '启示', '政策']):
            score += 1
            evidence += "包含政策建议；"

        return max(0, min(score, 5)), evidence or "实践价值评估依据不足"
