"""
Literature Review Scoring Rules (10-15 points)
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


class LiteratureReviewScoringRules:
    """
    Scoring rules for literature review dimension (10-15 points)

    Sub-dimensions:
    1. 文献覆盖度 (4-5 points)
    2. 前沿性 (3-4 points)
    3. 评述深度 (3-4 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate literature review dimension"""
        self.results = []
        total_score = 0
        max_total = 12  # Default, will be scaled

        # Rule 1: 文献覆盖度 (4 points)
        coverage_score, coverage_evidence = self._evaluate_coverage(info)
        self.results.append(ScoreResult(
            score=coverage_score,
            max_score=4,
            passed=coverage_score >= 2,
            rule_name="文献覆盖度",
            evidence=coverage_evidence,
            suggestion="建议增加文献覆盖范围" if coverage_score < 2 else ""
        ))
        total_score += coverage_score

        # Rule 2: 前沿性 (4 points)
        frontier_score, frontier_evidence = self._evaluate_frontier(info)
        self.results.append(ScoreResult(
            score=frontier_score,
            max_score=4,
            passed=frontier_score >= 2,
            rule_name="前沿性",
            evidence=frontier_evidence,
            suggestion="建议增加最新文献引用" if frontier_score < 2 else ""
        ))
        total_score += frontier_score

        # Rule 3: 评述深度 (4 points)
        depth_score, depth_evidence = self._evaluate_depth(info)
        self.results.append(ScoreResult(
            score=depth_score,
            max_score=4,
            passed=depth_score >= 2,
            rule_name="评述深度",
            evidence=depth_evidence,
            suggestion="建议加强文献评述的深度" if depth_score < 2 else ""
        ))
        total_score += depth_score

        return {
            'dimension': '文献综述与理论基础',
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

    def _evaluate_coverage(self, info: Dict) -> tuple:
        """Evaluate literature coverage"""
        ref_section = info.get('reference_section', '')
        ref_count = info.get('reference_count', 0)

        score = 2
        evidence = ""

        if ref_count >= 50:
            score += 2
            evidence += f"参考文献丰富({ref_count}篇)；"
        elif ref_count >= 30:
            score += 1
            evidence += f"参考文献数量达标({ref_count}篇)；"
        else:
            evidence += f"参考文献偏少({ref_count}篇)；"

        # Check for foreign references
        foreign_count = info.get('foreign_count', 0)
        if foreign_count >= 10:
            score += 0.5
            evidence += f"外文文献充足({foreign_count}篇)；"
        elif foreign_count < 5:
            evidence += f"外文文献偏少({foreign_count}篇)；"

        return min(score, 4), evidence or "文献覆盖度一般"

    def _evaluate_frontier(self, info: Dict) -> tuple:
        """Evaluate literature frontier (recent publications)"""
        recent_ratio = info.get('recent_5yr_ratio', 0)

        score = 2
        evidence = ""

        if recent_ratio >= 0.5:
            score += 2
            evidence += f"近五年文献占比高({recent_ratio:.0%})；"
        elif recent_ratio >= 0.3:
            score += 1
            evidence += f"近五年文献占比适中({recent_ratio:.0%})；"
        else:
            evidence += f"近五年文献偏少({recent_ratio:.0%})；"

        # Journal quality
        journal_ratio = info.get('journal_ratio', 0)
        if journal_ratio >= 0.6:
            score += 0.5
            evidence += f"期刊文献占比高({journal_ratio:.0%})；"

        return min(score, 4), evidence or "前沿性评估依据不足"

    def _evaluate_depth(self, info: Dict) -> tuple:
        """Evaluate review depth"""
        # This is inferred from presence of review sections
        content = info.get('content', '')
        score = 2
        evidence = ""

        review_keywords = ['文献综述', '文献回顾', '研究现状', '国内外研究', '评述']
        review_found = sum(1 for kw in review_keywords if kw in content)

        if review_found >= 3:
            score += 1.5
            evidence += "有系统的文献综述；"
        elif review_found >= 1:
            score += 0.5
            evidence += "有基本文献综述；"
        else:
            evidence += "文献综述不够系统；"

        # Check for research gap identification
        gap_keywords = ['研究空白', 'gap', '不足', '尚需', '有待']
        gap_found = sum(1 for kw in gap_keywords if kw in content.lower())
        if gap_found >= 1:
            score += 0.5
            evidence += "识别到研究空白；"

        return min(score, 4), evidence or "评述深度需加强"
