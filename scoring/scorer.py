"""
Main Scoring Engine
Pure Python rule-based scoring (NO LLM involvement)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from .rules.research_rules import ResearchScoringRules
from .rules.methodology_rules import MethodologyScoringRules
from .rules.results_rules import ResultsScoringRules
from .rules.innovation_rules import InnovationScoringRules
from .rules.writing_rules import WritingScoringRules
from .rules.literature_review_rules import LiteratureReviewScoringRules
from .rules.conclusion_rules import ConclusionScoringRules

# Import analyzers for paper type detection
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzers.paper_type_detector import (
    PaperType, detect_paper_type, paper_type_to_dimensions,
    paper_type_to_methodology_subdims
)


# 维度名称映射（英文key → 中文显示名）
DIMENSION_NAME_MAP = {
    'topic_significance': '选题与研究意义',
    'literature_review': '文献综述与理论基础',
    'methodology': '研究方法与技术路线',
    'empirical_analysis': '实证分析与结果',
    'innovation': '创新性',
    'writing': '写作规范与表达',
    'conclusion': '结论与建议'
}


@dataclass
class DimensionScore:
    """Score for a single dimension"""
    name: str
    score: float
    max_score: float
    sub_items: List[Dict] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0

    @property
    def grade(self) -> str:
        p = self.percentage
        if p >= 90:
            return "A"
        elif p >= 80:
            return "B"
        elif p >= 70:
            return "C"
        elif p >= 60:
            return "D"
        else:
            return "F"


@dataclass
class ScoringResult:
    """Complete scoring result"""
    dimensions: List[DimensionScore]
    total_score: float
    max_total: int
    critical_count: int
    paper_type: str = "未知"
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'dimensions': [
                {
                    'name': d.name,
                    'score': d.score,
                    'max_score': d.max_score,
                    'percentage': d.percentage,
                    'grade': d.grade,
                    'sub_items': d.sub_items,
                    'critical_issues': d.critical_issues,
                    'suggestions': d.suggestions
                }
                for d in self.dimensions
            ],
            'total_score': self.total_score,
            'max_total': self.max_total,
            'percentage': (self.total_score / self.max_total * 100) if self.max_total > 0 else 0,
            'critical_count': self.critical_count,
            'paper_type': self.paper_type,
            'suggestions': self.suggestions
        }


class ThesisScorer:
    """
    Main scoring engine using pure Python rules.

    Scoring Dimensions (100 points total, varies by paper type):
    1. 选题与研究意义 (10-15 points)
    2. 文献综述与理论基础 (10-15 points)
    3. 研究方法与技术路线 (15-25 points)
    4. 实证分析与结果 (20-30 points)
    5. 创新性 (15-20 points)
    6. 写作规范与表达 (5-15 points)
    7. 结论与建议 (5-10 points)

    NO LLM is used for scoring - this ensures reproducibility and consistency.
    """

    def __init__(self):
        # rules字典使用英文key，与paper_type_to_dimensions的key一致
        self.rules = {
            'topic_significance': ResearchScoringRules(),
            'literature_review': LiteratureReviewScoringRules(),
            'methodology': MethodologyScoringRules(),
            'empirical_analysis': ResultsScoringRules(),
            'innovation': InnovationScoringRules(),
            'writing': WritingScoringRules(),
            'conclusion': ConclusionScoringRules()
        }

    def score(self, info: Dict[str, Any], content: str = "") -> ScoringResult:
        """
        Calculate scores using rule-based evaluation

        Args:
            info: Extracted information from LLM extraction
            content: Raw paper content for type detection

        Returns:
            ScoringResult with all dimension scores
        """
        # Detect paper type
        paper_type = PaperType.UNKNOWN
        if content:
            detection = detect_paper_type(content)
            paper_type = detection.paper_type

        # Get dimension weights for this paper type (from paper_type_detector)
        dim_weights = paper_type_to_dimensions(paper_type)

        dimensions = []
        total_score = 0
        all_critical = []
        all_suggestions = []

        # Evaluate each dimension
        for dim_key, rules in self.rules.items():
            max_score = dim_weights.get(dim_key, 0)
            if max_score == 0:
                continue

            result = rules.evaluate(info)

            # Get the dimension display name
            dim_name = DIMENSION_NAME_MAP.get(dim_key, result.get('dimension', dim_key))

            # Scale score if rule returns different max
            original_max = result.get('max_score', 0)
            scaled_score = result['dimension_score']

            if original_max != max_score and original_max > 0:
                # Scale the dimension score
                scale_factor = max_score / original_max
                scaled_score = min(result['dimension_score'] * scale_factor, max_score)

            dim_score = DimensionScore(
                name=dim_name,
                score=scaled_score,
                max_score=max_score,
                sub_items=result.get('sub_items', []),
                critical_issues=[str(r) for r in result.get('critical_issues', [])],
                suggestions=result.get('suggestions', [])
            )

            dimensions.append(dim_score)
            total_score += scaled_score
            all_critical.extend(dim_score.critical_issues)
            all_suggestions.extend(dim_score.suggestions)

        return ScoringResult(
            dimensions=dimensions,
            total_score=total_score,
            max_total=100,
            critical_count=len(all_critical),
            paper_type=paper_type.value,
            suggestions=list(set(all_suggestions))
        )

    def get_scoring_summary(self, result: ScoringResult) -> str:
        """Generate a text summary of scoring results"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"论文评分结果（论文类型：{result.paper_type}）")
        lines.append("=" * 60)

        for dim in result.dimensions:
            grade_symbol = {
                'A': '🟢',
                'B': '🟡',
                'C': '🔵',
                'D': '🔵',
                'F': '🔴'
            }.get(dim.grade, '⚪')

            lines.append(f"\n{dim.name}: {dim.score}/{dim.max_score} ({dim.percentage:.1f}%) {grade_symbol}")

            for sub in dim.sub_items:
                status = "✅" if sub['passed'] else "❌"
                lines.append(f"  {status} {sub['name']}: {sub['score']}/{sub['max']}")

        lines.append(f"\n{'=' * 60}")
        lines.append(f"总分: {result.total_score}/{result.max_total} ({(result.total_score/result.max_total*100):.1f}%)")
        lines.append(f"严重问题数: {result.critical_count}")
        lines.append("=" * 60)

        return "\n".join(lines)


def score_thesis(info: Dict[str, Any], content: str = "") -> ScoringResult:
    """
    Convenience function to score thesis

    Args:
        info: Extracted information dict
        content: Raw paper content for type detection

    Returns:
        ScoringResult with all scores
    """
    scorer = ThesisScorer()
    return scorer.score(info, content)
