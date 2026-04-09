"""
Reference and Academic Standards Scoring Rules (5 points)
References dimension for thesis review
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import re


@dataclass
class ScoreResult:
    """Result of a scoring rule"""
    score: float
    max_score: float
    passed: bool
    rule_name: str
    evidence: str
    suggestion: str


class ReferenceScoringRules:
    """
    Scoring rules for references and academic standards dimension (5 points)

    Sub-dimensions:
    1. Reference Quantity (1.5 points) - minimum 30 references required
    2. Foreign References (1.5 points) - minimum 10 foreign references
    3. Journal Ratio (1 point) - at least 50% should be journal articles
    4. Recent References (1 point) - at least 30% from recent 5 years
    """

    MIN_REFERENCES = 30       # 硕士要求至少30篇
    MIN_FOREIGN = 10          # 外文文献至少10篇
    MIN_JOURNAL_RATIO = 0.5   # 期刊占比至少50%
    MIN_RECENT_RATIO = 0.3    # 近五年文献至少30%

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate references dimension"""
        self.results = []
        total_score = 0
        max_total = 5

        # Get reference info from extracted data
        ref_info = info.get('reference_info', {})
        ref_section = info.get('reference_section', '')

        # Rule 1: Reference quantity (0-1.5)
        quantity_score, quantity_evidence = self._evaluate_quantity(ref_info, ref_section)
        self.results.append(ScoreResult(
            score=quantity_score,
            max_score=1.5,
            passed=quantity_score >= 1.0,
            rule_name="文献数量",
            evidence=quantity_evidence,
            suggestion="建议增加参考文献数量至30篇以上" if quantity_score < 1.0 else ""
        ))
        total_score += quantity_score

        # Rule 2: Foreign references (0-1.5)
        foreign_score, foreign_evidence = self._evaluate_foreign(ref_info, ref_section)
        self.results.append(ScoreResult(
            score=foreign_score,
            max_score=1.5,
            passed=foreign_score >= 1.0,
            rule_name="外文文献",
            evidence=foreign_evidence,
            suggestion="建议增加外文文献至10篇以上" if foreign_score < 1.0 else ""
        ))
        total_score += foreign_score

        # Rule 3: Journal ratio (0-1)
        journal_score, journal_evidence = self._evaluate_journal_ratio(ref_info)
        self.results.append(ScoreResult(
            score=journal_score,
            max_score=1.0,
            passed=journal_score >= 0.6,
            rule_name="期刊占比",
            evidence=journal_evidence,
            suggestion="建议增加期刊文献占比至50%以上" if journal_score < 0.6 else ""
        ))
        total_score += journal_score

        # Rule 4: Recent references (0-1)
        recent_score, recent_evidence = self._evaluate_recent_ratio(ref_info)
        self.results.append(ScoreResult(
            score=recent_score,
            max_score=1.0,
            passed=recent_score >= 0.6,
            rule_name="近五年文献",
            evidence=recent_evidence,
            suggestion="建议增加近五年文献占比" if recent_score < 0.6 else ""
        ))
        total_score += recent_score

        return {
            'dimension': '参考文献与规范',
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

    def _evaluate_quantity(self, ref_info: Dict, ref_section: str) -> Tuple[float, str]:
        """Evaluate total reference quantity"""
        # Try to get count from ref_info
        total = ref_info.get('total', 0)

        # If not available, try to count from section
        if total == 0 and ref_section:
            total = self._count_references(ref_section)

        if total == 0:
            return 0.0, "未检测到参考文献"

        score = 0.0
        evidence = f"参考文献总数：{total}篇"

        if total >= self.MIN_REFERENCES:
            score = 1.5
            evidence += "（满足要求≥30篇）"
        elif total >= 25:
            score = 1.0
            evidence += "（基本满足，差5篇）"
        elif total >= 20:
            score = 0.5
            evidence += "（不足，差10篇）"
        else:
            score = 0.0
            evidence += f"（严重不足，需增加至少{self.MIN_REFERENCES - total}篇）"

        return score, evidence

    def _evaluate_foreign(self, ref_info: Dict, ref_section: str) -> Tuple[float, str]:
        """Evaluate foreign reference quantity"""
        foreign = ref_info.get('foreign', 0)

        if foreign == 0 and ref_section:
            foreign = self._count_foreign_references(ref_section)

        if foreign == 0:
            return 0.0, "未检测到外文参考文献"

        score = 0.0
        evidence = f"外文文献：{foreign}篇"

        if foreign >= self.MIN_FOREIGN:
            score = 1.5
            evidence += "（满足要求≥10篇）"
        elif foreign >= 8:
            score = 1.0
            evidence += "（基本满足）"
        elif foreign >= 5:
            score = 0.5
            evidence += "（不足）"
        else:
            score = 0.0
            evidence += f"（严重不足，需增加{self.MIN_FOREIGN - foreign}篇）"

        return score, evidence

    def _evaluate_journal_ratio(self, ref_info: Dict) -> Tuple[float, str]:
        """Evaluate journal article ratio"""
        journal_ratio = ref_info.get('journal_ratio', 0.0)
        total = ref_info.get('total', 0)

        if total == 0:
            return 0.5, "无法评估期刊占比"

        evidence = f"期刊文献占比：{journal_ratio:.0%}"

        if journal_ratio >= self.MIN_JOURNAL_RATIO:
            score = 1.0
            evidence += "（满足要求≥50%）"
        elif journal_ratio >= 0.4:
            score = 0.6
            evidence += "（基本满足）"
        else:
            score = 0.3
            evidence += "（不足）"

        return score, evidence

    def _evaluate_recent_ratio(self, ref_info: Dict) -> Tuple[float, str]:
        """Evaluate recent references ratio (within 5 years)"""
        recent_ratio = ref_info.get('recent_5yr_ratio', 0.0)
        total = ref_info.get('total', 0)

        if total == 0:
            return 0.5, "无法评估文献时效性"

        evidence = f"近五年文献占比：{recent_ratio:.0%}"

        if recent_ratio >= self.MIN_RECENT_RATIO:
            score = 1.0
            evidence += "（满足要求≥30%）"
        elif recent_ratio >= 0.2:
            score = 0.6
            evidence += "（基本满足）"
        else:
            score = 0.3
            evidence += "（建议增加近期文献）"

        return score, evidence

    def _count_references(self, ref_section: str) -> int:
        """Count references in reference section"""
        if not ref_section:
            return 0

        # Count by common patterns
        # Pattern 1: [1] format
        bracket_count = len(re.findall(r'\[\d+\]', ref_section))
        # Pattern 2: (作者, 年份) format
        paren_count = len(re.findall(r'\([A-Z][a-z]+,?\s*\d{4}\)', ref_section))
        # Pattern 3: Lines starting with capital letter or '[' (author name format)
        lines = ref_section.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        # Count lines that start with capital letter or '['
        valid_starts = sum(1 for line in non_empty_lines
                          if (line and line[0].isupper()) or line.startswith('['))

        return max(bracket_count, paren_count, valid_starts, len(non_empty_lines))

    def _count_foreign_references(self, ref_section: str) -> int:
        """Count foreign references"""
        if not ref_section:
            return 0

        # Foreign reference patterns
        patterns = [
            r'[A-Z][a-z]+,\s*[A-Z]\.',  # Smith, J.
            r'[A-Z][a-z]+\s+[A-Z][a-z]+,',  # John Smith,
            r'et\s+al\.?',
            r'Journal\s+of', r'Review\s+of',
            r'Economics?', r'Management', r'Finance',
        ]

        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, ref_section, re.IGNORECASE))

        return count
