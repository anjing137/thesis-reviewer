"""
Innovation Scoring Rules (15 points)
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


class InnovationScoringRules:
    """
    Scoring rules for innovation dimension (15 points)

    Sub-dimensions:
    1. Topic Innovation (5 points)
    2. Method Innovation (5 points)
    3. Data/Application Innovation (5 points)
    """

    def __init__(self):
        self.results: List[ScoreResult] = []

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate innovation dimension"""
        self.results = []
        total_score = 0
        max_total = 15

        # Rule 1: Topic innovation (0-5)
        topic_score, topic_evidence = self._evaluate_topic_innovation(info)
        self.results.append(ScoreResult(
            score=topic_score,
            max_score=5,
            passed=topic_score >= 3,
            rule_name="选题创新",
            evidence=topic_evidence,
            suggestion="建议寻找更具创新性的研究角度" if topic_score < 3 else ""
        ))
        total_score += topic_score

        # Rule 2: Method innovation (0-5)
        method_score, method_evidence = self._evaluate_method_innovation(info)
        self.results.append(ScoreResult(
            score=method_score,
            max_score=5,
            passed=method_score >= 3,
            rule_name="方法创新",
            evidence=method_evidence,
            suggestion="建议尝试新方法或方法组合" if method_score < 3 else ""
        ))
        total_score += method_score

        # Rule 3: Data/application innovation (0-5)
        data_score, data_evidence = self._evaluate_data_innovation(info)
        self.results.append(ScoreResult(
            score=data_score,
            max_score=5,
            passed=data_score >= 3,
            rule_name="数据/应用创新",
            evidence=data_evidence,
            suggestion="建议使用新数据源或新应用场景" if data_score < 3 else ""
        ))
        total_score += data_score

        return {
            'dimension': '创新性',
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

    def _evaluate_topic_innovation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate topic/research question innovation"""
        research_gap = info.get('research_gap', '')
        innovation_type = info.get('innovation_type', '')

        score = 2  # Base score
        evidence = ""

        # If research gap is clearly stated
        if research_gap and research_gap != 'null' and len(research_gap) > 10:
            score += 2
            evidence += f"明确识别研究gap：{research_gap[:40]}；"

        # If innovation type is specified
        if innovation_type and innovation_type != 'null':
            score += 1
            evidence += f"创新类型：{innovation_type}；"

        # Check for new research context
        data = info.get('data', {})
        region = data.get('region', '')
        if region and ('新' in region or '首次' in region or '新发现' in region):
            score += 1
            evidence += f"新研究场景：{region}；"

        return max(0, min(score, 5)), evidence or "选题创新性评估依据不足"

    def _evaluate_method_innovation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate method innovation"""
        method = info.get('method', '')
        method_details = info.get('method_details', {})

        score = 2  # Base score
        evidence = ""

        if not method or method == 'null':
            return 1, "未明确识别研究方法"

        method_upper = method.upper()

        # Check for advanced methods
        advanced_methods = ['DID', 'IV', 'GMM', 'PSM', 'RD', 'SEM', 'AMOS', 'PLS', 'HLM']
        standard_methods = ['OLS', '回归', 'LOGIT', 'PROBIT']

        if any(m in method_upper for m in advanced_methods):
            score += 2
            evidence += f"使用较先进的方法：{method}；"
        elif any(m in method_upper for m in standard_methods):
            evidence += f"使用常规方法：{method}；"

        # Check for method combination
        specific_methods = method_details.get('specific_methods', [])
        if len(specific_methods) >= 2:
            score += 1
            evidence += f"方法组合使用：{','.join(specific_methods[:2])}；"

        return max(0, min(score, 5)), evidence or "方法创新性一般"

    def _evaluate_data_innovation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate data or application innovation"""
        data = info.get('data', {})
        method = info.get('method', '')

        score = 2  # Base score
        evidence = ""

        # Check for new data source
        source = data.get('source', '')
        if source and source != 'null':
            if any(term in source for term in ['调查', '问卷', '实地', '调研', '田野']):
                score += 2
                evidence += "使用一手调研数据；"
            elif any(term in source for term in ['数据库', '年鉴', '统计']):
                score += 1
                evidence += "使用公开数据；"

        # Check for specific region/application
        region = data.get('region', '')
        if region and region != 'null':
            if len(region) < 10:  # Specific region
                score += 1
                evidence += f"聚焦特定区域：{region}；"

        # Check for new application context
        if method and '新' in method:
            score += 1
            evidence += "新方法应用；"

        return max(0, min(score, 5)), evidence or "数据/应用创新性一般"
