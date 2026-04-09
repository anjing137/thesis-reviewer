"""
Methodology Scoring Rules (Variable points based on paper type)

Paper type specific sub-dimensions:
- 实证经济学型 (30 points): 内生性处理、识别策略、稳健性检验、过度控制检测、模型规范性
- 问卷调查实证型 (25 points): 问卷设计、信效度检验、统计方法
- 案例研究型 (20 points): 案例选择、证据三角验证、过程追踪
- 政策研究型 (15 points): 政策逻辑、数据支撑、可行性论证
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
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


# Paper type specific sub-dimensions
METHODOLOGY_SUB_DIMS = {
    '实证经济学型': [
        ('数据质量', 6),
        ('方法规范性', 8),
        ('稳健性检验', 8),
        ('内生性处理', 8)
    ],
    '问卷调查型': [
        ('问卷设计', 6),
        ('样本代表性', 6),
        ('信效度检验', 8),
        ('统计方法', 6)
    ],
    '政策评价型': [
        ('指标体系', 6),
        ('测度方法', 6),
        ('障碍度分析', 6),
        ('实证逻辑', 6)
    ],
    '案例分析型': [
        ('案例典型性', 7),
        ('理论应用', 7),
        ('分析深度', 6)
    ],
    '混合型': [
        ('方法明确度', 5),
        ('方法匹配度', 8),
        ('多方法融合', 6),
        ('实证逻辑', 6)
    ],
    '未知': [
        ('方法匹配度', 6),
        ('数据质量', 6),
        ('模型规范性', 6),
        ('稳健性检验', 6)
    ]
}


class MethodologyScoringRules:
    """
    Scoring rules for methodology dimension

    The sub-dimensions vary based on paper type:
    - 实证经济学型: Emphasizes endogeneity handling, identification strategy
    - 问卷调查实证型: Emphasizes questionnaire design, reliability/validity
    - 案例研究型: Emphasizes case selection, triangulation
    - 政策研究型: Emphasizes policy logic, feasibility
    """

    def __init__(self):
        self.results: List[ScoreResult] = []
        self.paper_type: str = '未知'

    def evaluate(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate methodology dimension

        Args:
            info: Extracted information dict from LLM
            info can contain:
                - paper_type: str (detected paper type)
                - method: str (research method)
                - method_details: dict
                - data: dict
                - has_robustness: bool
                - has_endogeneity: bool
                - over_control_issues: list (from model analyzer)
                - model_spec: dict (model specification details)

        Returns:
            Dict with scores and details
        """
        self.results = []
        total_score = 0

        # Determine paper type
        self.paper_type = info.get('paper_type', '未知')
        sub_dims = METHODOLOGY_SUB_DIMS.get(self.paper_type, METHODOLOGY_SUB_DIMS['未知'])
        max_total = sum(max_score for _, max_score in sub_dims)

        # Get common info
        method = info.get('method', '').upper()
        method_details = info.get('method_details', {})
        data = info.get('data', {})
        has_robustness = info.get('has_robustness')
        has_endogeneity = info.get('has_endogeneity')
        over_control_issues = info.get('over_control_issues', [])

        # Evaluate based on paper type
        if self.paper_type == '实证经济学型':
            total_score = self._evaluate_empirical_economics(
                method, method_details, data, has_robustness, has_endogeneity, over_control_issues, info
            )
        elif self.paper_type == '问卷调查型':
            total_score = self._evaluate_survey(
                method, method_details, data, has_robustness, info
            )
        elif self.paper_type == '政策评价型':
            total_score = self._evaluate_policy_evaluation(
                method, method_details, data, info
            )
        elif self.paper_type == '案例分析型':
            total_score = self._evaluate_case_study(
                method, method_details, info
            )
        elif self.paper_type == '混合型':
            total_score = self._evaluate_hybrid(
                method, method_details, data, info
            )
        else:
            # Generic evaluation
            total_score = self._evaluate_generic(
                method, method_details, data, has_robustness, has_endogeneity, info
            )

        return {
            'dimension': '研究方法与技术路线',
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

    def _add_result(self, rule_name: str, score: float, max_score: float,
                   passed: bool, evidence: str, suggestion: str = ""):
        """Helper to add a result"""
        self.results.append(ScoreResult(
            score=score,
            max_score=max_score,
            passed=passed,
            rule_name=rule_name,
            evidence=evidence,
            suggestion=suggestion
        ))

    def _evaluate_empirical_economics(
        self, method: str, method_details: Dict, data: Dict,
        has_robustness: Optional[bool], has_endogeneity: Optional[bool],
        over_control_issues: List, info: Dict
    ) -> float:
        """Evaluate 实证经济学型 methodology (30 points)"""
        total = 0

        # 1. 内生性处理 (6 points)
        endo_score, endo_evidence = self._evaluate_endogeneity(method, has_endogeneity, info)
        self._add_result(
            '内生性处理', endo_score, 6,
            endo_score >= 4,
            endo_evidence,
            "必须处理内生性问题" if endo_score < 3 else ("建议进一步处理内生性" if endo_score < 4 else "")
        )
        total += endo_score

        # 2. 识别策略 (6 points)
        strategy_score, strategy_evidence = self._evaluate_identification_strategy(method, method_details)
        self._add_result(
            '识别策略', strategy_score, 6,
            strategy_score >= 4,
            strategy_evidence,
            "识别策略不明确" if strategy_score < 4 else ""
        )
        total += strategy_score

        # 3. 稳健性检验 (6 points)
        robust_score, robust_evidence = self._evaluate_robustness(has_robustness, info)
        self._add_result(
            '稳健性检验', robust_score, 6,
            robust_score >= 4,
            robust_evidence,
            "必须增加稳健性检验" if robust_score < 4 else ""
        )
        total += robust_score

        # 4. 过度控制检测 (6 points)
        overcontrol_score, overcontrol_evidence = self._evaluate_overcontrol(over_control_issues, method_details)
        self._add_result(
            '过度控制检测', overcontrol_score, 6,
            overcontrol_score >= 4,
            overcontrol_evidence,
            "存在过度控制问题" if overcontrol_score < 4 else ""
        )
        total += overcontrol_score

        # 5. 模型规范性 (6 points)
        model_score, model_evidence = self._evaluate_model_spec(method, method_details)
        self._add_result(
            '模型规范性', model_score, 6,
            model_score >= 4,
            model_evidence,
            "建议完善模型设定" if model_score < 4 else ""
        )
        total += model_score

        return total

    def _evaluate_survey(
        self, method: str, method_details: Dict, data: Dict,
        has_robustness: Optional[bool], info: Dict
    ) -> float:
        """Evaluate 问卷调查实证型 methodology (25 points)"""
        total = 0

        # 1. 问卷设计 (8 points)
        design_score, design_evidence = self._evaluate_questionnaire_design(info)
        self._add_result(
            '问卷设计', design_score, 8,
            design_score >= 5,
            design_evidence,
            "问卷设计需改进" if design_score < 5 else ""
        )
        total += design_score

        # 2. 信效度检验 (9 points)
        reliability_score, reliability_evidence = self._evaluate_reliability_validity(info)
        self._add_result(
            '信效度检验', reliability_score, 9,
            reliability_score >= 6,
            reliability_evidence,
            "必须进行信效度检验" if reliability_score < 6 else ""
        )
        total += reliability_score

        # 3. 统计方法 (8 points)
        stats_score, stats_evidence = self._evaluate_statistical_method(method, method_details)
        self._add_result(
            '统计方法', stats_score, 8,
            stats_score >= 5,
            stats_evidence,
            "统计方法需完善" if stats_score < 5 else ""
        )
        total += stats_score

        return total

    def _evaluate_case_study(
        self, method: str, method_details: Dict, info: Dict
    ) -> float:
        """Evaluate 案例研究型 methodology (20 points)"""
        total = 0

        # 1. 案例选择 (7 points)
        case_score, case_evidence = self._evaluate_case_selection(info)
        self._add_result(
            '案例选择', case_score, 7,
            case_score >= 4,
            case_evidence,
            "案例选择依据不充分" if case_score < 4 else ""
        )
        total += case_score

        # 2. 证据三角验证 (7 points)
        triangulation_score, triangulation_evidence = self._evaluate_triangulation(info)
        self._add_result(
            '证据三角验证', triangulation_score, 7,
            triangulation_score >= 4,
            triangulation_evidence,
            "缺乏三角验证" if triangulation_score < 4 else ""
        )
        total += triangulation_score

        # 3. 过程追踪 (6 points)
        process_score, process_evidence = self._evaluate_process_tracking(info)
        self._add_result(
            '过程追踪', process_score, 6,
            process_score >= 4,
            process_evidence,
            "过程追踪不完整" if process_score < 4 else ""
        )
        total += process_score

        return total

    def _evaluate_policy_evaluation(
        self, method: str, method_details: Dict, data: Dict, info: Dict
    ) -> float:
        """Evaluate 政策评价型 methodology (25 points)"""
        total = 0

        # 1. 指标体系 (6 points)
        indicator_score, indicator_evidence = self._evaluate_indicator_system(info)
        self._add_result(
            '指标体系', indicator_score, 6,
            indicator_score >= 4,
            indicator_evidence,
            "指标体系构建需完善" if indicator_score < 4 else ""
        )
        total += indicator_score

        # 2. 测度方法 (6 points)
        measurement_score, measurement_evidence = self._evaluate_measurement_method(method, method_details)
        self._add_result(
            '测度方法', measurement_score, 6,
            measurement_score >= 4,
            measurement_evidence,
            "测度方法选择需论证" if measurement_score < 4 else ""
        )
        total += measurement_score

        # 3. 障碍度分析 (6 points)
        barrier_score, barrier_evidence = self._evaluate_barrier_analysis(info)
        self._add_result(
            '障碍度分析', barrier_score, 6,
            barrier_score >= 4,
            barrier_evidence,
            "障碍度分析不够深入" if barrier_score < 4 else ""
        )
        total += barrier_score

        # 4. 实证逻辑 (6 points)
        logic_score, logic_evidence = self._evaluate实证_logic(info)
        self._add_result(
            '实证逻辑', logic_score, 6,
            logic_score >= 4,
            logic_evidence,
            "实证逻辑需加强" if logic_score < 4 else ""
        )
        total += logic_score

        return total

    def _evaluate_hybrid(
        self, method: str, method_details: Dict, data: Dict, info: Dict
    ) -> float:
        """Evaluate 混合型 methodology (25 points)"""
        total = 0

        # 1. 方法明确度 (5 points)
        clarity_score, clarity_evidence = self._evaluate_method_clarity(method, method_details)
        self._add_result(
            '方法明确度', clarity_score, 5,
            clarity_score >= 3,
            clarity_evidence,
            "方法描述需更清晰" if clarity_score < 3 else ""
        )
        total += clarity_score

        # 2. 方法匹配度 (8 points)
        match_score, match_evidence = self._evaluate_method_match(method, method_details)
        self._add_result(
            '方法匹配度', match_score, 8,
            match_score >= 5,
            match_evidence,
            "方法与研究问题匹配度不足" if match_score < 5 else ""
        )
        total += match_score

        # 3. 多方法融合 (6 points)
        fusion_score, fusion_evidence = self._evaluate_method_fusion(method_details)
        self._add_result(
            '多方法融合', fusion_score, 6,
            fusion_score >= 4,
            fusion_evidence,
            "多方法融合逻辑需加强" if fusion_score < 4 else ""
        )
        total += fusion_score

        # 4. 实证逻辑 (6 points)
        logic_score, logic_evidence = self._evaluate实证_logic(info)
        self._add_result(
            '实证逻辑', logic_score, 6,
            logic_score >= 4,
            logic_evidence,
            "实证逻辑需加强" if logic_score < 4 else ""
        )
        total += logic_score

        return total

    # ---- Helper methods for new evaluation types ----

    def _evaluate_indicator_system(self, info: Dict) -> tuple:
        """Evaluate indicator system construction"""
        score = 3.0
        evidence = ""

        method_details = info.get('method_details', {})
        indicators = method_details.get('indicators', [])

        if indicators and len(indicators) > 0:
            score += 1.5
            evidence += f"构建了指标体系({len(indicators)}个指标)；"
        else:
            evidence += "未明确指标体系；"

        # Check for entropy weight method
        content = info.get('content', '')
        if '熵权' in content or '熵值法' in content:
            score += 1.0
            evidence += "使用熵权法确定权重；"

        return min(score, 6), evidence or "指标体系评估依据不足"

    def _evaluate_measurement_method(self, method: str, method_details: Dict) -> tuple:
        """Evaluate measurement/tasure method"""
        score = 3.0
        evidence = ""

        method_upper = method.upper()
        if '熵权' in method or '熵值法' in method:
            score += 2.0
            evidence += "使用熵权法进行测度；"
        elif '耦合' in method or '协调度' in method:
            score += 1.5
            evidence += "使用耦合协调度模型；"
        elif '障碍度' in method:
            score += 1.5
            evidence += "包含障碍度分析；"

        return min(score, 6), evidence or "测度方法评估依据不足"

    def _evaluate_barrier_analysis(self, info: Dict) -> tuple:
        """Evaluate barrier degree analysis"""
        score = 3.0
        evidence = ""

        content = info.get('content', '')
        if '障碍度' in content or '障碍因子' in content:
            score += 2.0
            evidence += "进行了障碍度分析；"
        else:
            evidence += "未进行障碍度分析；"

        # Check for obstacle factor identification
        if '障碍因子' in content or '障碍因素' in content:
            score += 1.0
            evidence += "识别了障碍因子；"

        return min(score, 6), evidence or "障碍度分析需加强"

    def _evaluate实证_logic(self, info: Dict) -> tuple:
        """Evaluate empirical logic chain"""
        score = 3.0
        evidence = ""

        conclusion = info.get('main_conclusion', '')
        if conclusion and len(conclusion) > 50:
            score += 1.5
            evidence += "结论表述详细；"

        limitations = info.get('limitations', '')
        if limitations and limitations != 'null':
            score += 1.5
            evidence += "讨论了研究局限；"

        return min(score, 6), evidence or "实证逻辑评估依据不足"

    def _evaluate_method_clarity(self, method: str, method_details: Dict) -> tuple:
        """Evaluate method description clarity"""
        score = 2.5
        evidence = ""

        if method and method != 'null' and len(method) > 5:
            score += 1.5
            evidence += f"方法描述清晰：{method[:30]}；"
        else:
            evidence += "方法描述不够清晰；"

        return min(score, 5), evidence or "方法明确度不足"

    def _evaluate_method_fusion(self, method_details: Dict) -> tuple:
        """Evaluate multi-method fusion logic"""
        score = 3.0
        evidence = ""

        # Check for multiple methods
        content = str(method_details)
        method_count = 0
        methods = ['回归', '熵权', '耦合', '障碍度', 'GIS', '空间', '核密度', '基尼']
        for m in methods:
            if m in content:
                method_count += 1

        if method_count >= 3:
            score += 2.0
            evidence += f"使用了{method_count}种方法进行融合；"
        elif method_count >= 2:
            score += 1.0
            evidence += f"使用了{2}种方法；"
        else:
            evidence += "方法组合较为单一；"

        return min(score, 6), evidence or "多方法融合评估依据不足"

    def _evaluate_generic(
        self, method: str, method_details: Dict, data: Dict,
        has_robustness: Optional[bool], has_endogeneity: Optional[bool], info: Dict
    ) -> float:
        """Generic evaluation for unknown paper type"""
        total = 0
        max_per = 6

        # Method match
        match_score, match_evidence = self._evaluate_method_match(method, method_details)
        self._add_result(
            '方法匹配度', match_score, max_per,
            match_score >= 4,
            match_evidence,
            "方法匹配度不足" if match_score < 4 else ""
        )
        total += match_score

        # Data quality
        data_score, data_evidence = self._evaluate_data_quality(data)
        self._add_result(
            '数据质量', data_score, max_per,
            data_score >= 4,
            data_evidence,
            "数据质量需提高" if data_score < 4 else ""
        )
        total += data_score

        # Model specification
        model_score, model_evidence = self._evaluate_model_spec(method, method_details)
        self._add_result(
            '模型规范性', model_score, max_per,
            model_score >= 4,
            model_evidence,
            "模型规范性不足" if model_score < 4 else ""
        )
        total += model_score

        # Robustness
        robust_score, robust_evidence = self._evaluate_robustness(has_robustness, info)
        self._add_result(
            '稳健性检验', robust_score, max_per,
            robust_score >= 4,
            robust_evidence,
            "缺乏稳健性检验" if robust_score < 4 else ""
        )
        total += robust_score

        # Results interpretation
        results_score, results_evidence = self._evaluate_results_interpretation(info)
        self._add_result(
            '结果解释', results_score, max_per,
            results_score >= 4,
            results_evidence,
            "结果解释不充分" if results_score < 4 else ""
        )
        total += results_score

        return total

    # ---- Sub-evaluation methods ----

    def _evaluate_endogeneity(self, method: str, has_endogeneity: Optional[bool], info: Dict) -> Tuple[float, str]:
        """Evaluate endogeneity handling"""
        method_upper = method.upper()

        endogeneity_methods = ['DID', 'IV', '2SLS', 'GMM', 'FIXED', 'RANDOM', 'PANEL']
        has_endogeneity_method = any(m in method_upper for m in endogeneity_methods)

        if has_endogeneity_method:
            return 5.5, f"使用{method}方法，可处理内生性问题"

        if 'OLS' in method_upper or '回归' in method:
            if has_endogeneity is False:
                return 2.0, "OLS回归未处理内生性问题【潜在严重问题】"
            return 1.0, "OLS回归，可能存在内生性问题但未处理"

        if has_endogeneity is True:
            return 4.0, "已识别内生性但处理方式不明确"

        if has_endogeneity is False:
            return 4.0, "方法选择合理，内生性问题关注充分"

        return 3.0, "内生性处理情况不明确"

    def _evaluate_identification_strategy(self, method: str, method_details: Dict) -> Tuple[float, str]:
        """Evaluate identification strategy"""
        score = 3
        evidence = ""

        method_upper = method.upper()

        # DID has clear identification
        if 'DID' in method_upper:
            score += 2.5
            evidence += "使用DID方法，识别策略清晰；"

        # IV/2SLS has instrument variables
        elif 'IV' in method_upper or '2SLS' in method_upper:
            score += 2.5
            evidence += "使用工具变量法；"

        # Panel fixed effects
        elif 'FIXED' in method_upper or 'RANDOM' in method_upper:
            score += 2.0
            evidence += "使用固定效应/随机效应模型；"

        # Check for identification strategy statement in details
        id_strategy = method_details.get('identification_strategy', '')
        if id_strategy and id_strategy != 'null':
            score += 0.5
            evidence += f"识别策略：{id_strategy[:30]}；"

        return min(score, 6), evidence or "识别策略不明确"

    def _evaluate_overcontrol(self, over_control_issues: List, method_details: Dict) -> Tuple[float, str]:
        """Evaluate over-control detection"""
        if not over_control_issues:
            return 5.5, "未检测到过度控制问题"

        issue_count = len(over_control_issues)
        severity = 'high' if any(i.get('severity') == 'high' for i in over_control_issues) else 'medium'

        if issue_count >= 2 or severity == 'high':
            score = 2.0
            evidence = f"发现{issue_count}处过度控制问题【严重】；"
        else:
            score = 3.5
            evidence = f"发现{issue_count}处潜在过度控制问题；"

        return score, evidence

    def _evaluate_robustness(self, has_robustness: Optional[bool], info: Dict) -> Tuple[float, str]:
        """Evaluate robustness checks"""
        if has_robustness is None:
            return 1.0, "未明确是否进行稳健性检验"

        if not has_robustness:
            return 0.0, "未进行稳健性检验【严重问题】"

        details = info.get('robustness_details', '')
        score = 3.0

        robustness_keywords = ['替换', '子样本', '滞后', '工具变量', 'bootstrap', '稳健性', '敏感性']
        check_count = sum(1 for kw in robustness_keywords if kw.lower() in details.lower())

        if check_count >= 3:
            score = 6.0
            evidence = f"进行{check_count}种稳健性检验；"
        elif check_count == 2:
            score = 5.0
            evidence = "进行2种稳健性检验；"
        elif check_count == 1:
            score = 4.0
            evidence = "进行基本稳健性检验；"
        else:
            score = 3.0
            evidence = "提及稳健性但细节不足；"

        return score, evidence

    def _evaluate_model_spec(self, method: str, method_details: Dict) -> Tuple[float, str]:
        """Evaluate model specification"""
        score = 3.0
        evidence = ""

        if not method_details:
            return 2.0, "缺乏详细的模型设定信息"

        variables = method_details.get('variables', {})
        if variables:
            dep = variables.get('dependent', [])
            indep = variables.get('independent', [])
            if dep and indep:
                score += 2.0
                evidence += f"变量定义清晰（因变量：{len(dep)}个，自变量：{len(indep)}个）；"

        hypotheses = method_details.get('hypotheses', [])
        if hypotheses:
            score += 1.0
            evidence += f"提出{len(hypotheses)}个假设；"

        return min(score, 6), evidence or "模型规范性一般"

    def _evaluate_questionnaire_design(self, info: Dict) -> Tuple[float, str]:
        """Evaluate questionnaire design"""
        score = 4.0
        evidence = ""

        # Check for questionnaire-related info
        method_details = info.get('method_details', {})
        questionnaire = method_details.get('questionnaire', {})

        if not questionnaire:
            # Try to infer from method
            method = info.get('method', '').lower()
            if '问卷' in method or '调查' in method:
                score = 4.0
                evidence = "使用问卷调查法；"
            else:
                return 2.0, "未明确问卷设计"
        else:
            # Check dimensions
            dimensions = questionnaire.get('dimensions', 0)
            items = questionnaire.get('items', 0)
            if dimensions > 0 and items > 0:
                score += 2.0
                evidence += f"问卷包含{dimensions}个维度，{items}个题项；"

            pretest = questionnaire.get('pretest', False)
            if pretest:
                score += 1.0
                evidence += "进行预调研；"

        return min(score, 8), evidence or "问卷设计基本合理"

    def _evaluate_reliability_validity(self, info: Dict) -> Tuple[float, str]:
        """Evaluate reliability and validity tests"""
        score = 3.0
        evidence = ""

        method_details = info.get('method_details', {})
        reliability = method_details.get('reliability', {})

        if not reliability:
            # Check for common indicators in text
            format_check = info.get('format_check', {})
            # This is a simplified check - real implementation would parse actual values
            return 4.5, "进行信效度检验但具体数值不明确"

        # Cronbach's alpha
        alpha = reliability.get('cronbach_alpha')
        if alpha is not None:
            if alpha >= 0.8:
                score += 3.0
                evidence += f"克隆巴赫α={alpha:.3f}，信度很高；"
            elif alpha >= 0.7:
                score += 2.5
                evidence += f"克隆巴赫α={alpha:.3f}，信度较好；"
            elif alpha >= 0.6:
                score += 1.5
                evidence += f"克隆巴赫α={alpha:.3f}，信度一般；"
            else:
                score += 0.5
                evidence += f"克隆巴赫α={alpha:.3f}【偏低】；"

        # KMO
        kmo = reliability.get('kmo')
        if kmo is not None:
            if kmo >= 0.8:
                score += 3.0
                evidence += f"KMO={kmo:.3f}，效度很好；"
            elif kmo >= 0.7:
                score += 2.0
                evidence += f"KMO={kmo:.3f}，效度较好；"
            elif kmo >= 0.6:
                score += 1.0
                evidence += f"KMO={kmo:.3f}，效度一般；"
            else:
                score += 0.0
                evidence += f"KMO={kmo:.3f}【偏低】；"

        # Bartlett test
        bartlett = reliability.get('bartlett_sig') or reliability.get('bartlett', 0)
        if bartlett and bartlett < 0.05:
            score += 1.0
            evidence += "Bartlett检验显著；"

        return min(score, 9), evidence or "信效度评估依据不足"

    def _evaluate_statistical_method(self, method: str, method_details: Dict) -> Tuple[float, str]:
        """Evaluate statistical method"""
        score = 4.0
        evidence = ""

        method_upper = method.upper()

        logistic_methods = ['LOGIT', 'LOGISTIC', 'BINARY']
        if any(m in method_upper for m in logistic_methods):
            score += 2.0
            evidence += "使用二元Logistic回归；"
        elif 'OLS' in method_upper or '回归' in method:
            score += 1.5
            evidence += "使用OLS回归；"
        elif 'SEM' in method_upper or 'STRUCTURAL' in method_upper:
            score += 2.0
            evidence += "使用结构方程模型；"

        # Check for specific tests
        tests = method_details.get('tests_performed', [])
        if tests:
            score += 1.0
            evidence += f"进行{len(tests)}种统计检验；"

        return min(score, 8), evidence or "统计方法基本合理"

    def _evaluate_case_selection(self, info: Dict) -> Tuple[float, str]:
        """Evaluate case selection"""
        score = 3.5
        evidence = ""

        method_details = info.get('method_details', {})

        # Check for case selection criteria
        selection = method_details.get('case_selection', '')
        if selection and selection != 'null':
            score += 2.0
            evidence += f"案例选择依据：{selection[:40]}；"

        # Check for number of cases
        case_count = method_details.get('case_count', 0)
        if case_count > 0:
            score += 1.0
            evidence += f"选取{case_count}个案例；"

        # Check for case characteristics
        characteristics = method_details.get('case_characteristics', [])
        if characteristics:
            score += 0.5
            evidence += f"案例具有{len(characteristics)}个特征；"

        return min(score, 7), evidence or "案例选择依据需明确"

    def _evaluate_triangulation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate triangulation (multiple sources of evidence)"""
        score = 3.5
        evidence = ""

        method_details = info.get('method_details', {})
        evidence_sources = method_details.get('evidence_sources', [])

        if evidence_sources:
            count = len(evidence_sources) if isinstance(evidence_sources, list) else 1
            score += min(count * 1.0, 3.0)
            evidence += f"使用{count}种证据来源；"
        else:
            # Check for keywords
            evidence_keywords = ['访谈', '问卷', '数据', '文献', '档案', '观察']
            found = [kw for kw in evidence_keywords if kw in str(info)]
            if found:
                score += 2.0
                evidence += f"发现{len(found)}种证据来源；"

        return min(score, 7), evidence or "证据来源单一，缺乏三角验证"

    def _evaluate_process_tracking(self, info: Dict) -> Tuple[float, str]:
        """Evaluate process tracking"""
        score = 3.0
        evidence = "过程追踪基本合理"

        method_details = info.get('method_details', {})
        process = method_details.get('process_tracking', '')

        if process and process != 'null':
            score += 2.0
            evidence = f"过程追踪：{process[:40]}；"

        timeline = method_details.get('timeline', '')
        if timeline:
            score += 1.0
            evidence += "有时间线追踪；"

        return min(score, 6), evidence

    def _evaluate_policy_logic(self, info: Dict) -> Tuple[float, str]:
        """Evaluate policy logic"""
        score = 3.0
        evidence = ""

        conclusion = info.get('main_conclusion', '')

        # Check for logical flow indicators
        logic_terms = ['因此', '所以', '从而', '可见', '表明']
        logic_count = sum(1 for term in logic_terms if term in conclusion)

        if logic_count >= 2:
            score += 1.5
            evidence += "政策逻辑较清晰；"
        elif logic_count >= 1:
            score += 0.5
            evidence += "政策逻辑基本成立；"

        # Check for problem definition
        rq = info.get('research_question', '')
        if rq and len(rq) > 20:
            score += 0.5
            evidence += "问题界定清晰；"

        return min(score, 5), evidence or "政策逻辑需加强"

    def _evaluate_data_support(self, data: Dict, info: Dict) -> Tuple[float, str]:
        """Evaluate data support for policy"""
        score = 2.5
        evidence = ""

        if not data:
            return 2.0, "缺乏数据支撑"

        sample_size = data.get('sample_size', '')
        if sample_size:
            import re
            numbers = re.findall(r'\d+', str(sample_size))
            if numbers:
                num = int(numbers[0])
                if num >= 500:
                    score += 2.0
                    evidence += f"样本量充足({num})；"
                elif num >= 200:
                    score += 1.0
                    evidence += f"样本量适中({num})；"
                else:
                    evidence += f"样本量较小({num})；"

        source = data.get('source', '')
        if source and source != 'null':
            score += 0.5
            evidence += f"数据来源：{source[:20]}；"

        return min(score, 5), evidence or "数据支撑不足"

    def _evaluate_feasibility(self, info: Dict) -> Tuple[float, str]:
        """Evaluate feasibility analysis"""
        score = 3.0
        evidence = ""

        conclusion = info.get('main_conclusion', '')

        # Check for feasibility-related content
        feasibility_terms = ['可行性', '可操作性', '实施', '落地', '推广']
        found_terms = [t for t in feasibility_terms if t in conclusion]

        if found_terms:
            score += 1.5
            evidence += f"包含可行性讨论；"
        else:
            evidence += "缺乏可行性论证；"

        # Check for limitations
        limitations = info.get('limitations', '')
        if limitations and limitations != 'null':
            score += 0.5
            evidence += "讨论了研究局限；"

        return min(score, 5), evidence or "可行性论证不足"

    def _evaluate_method_match(self, method: str, method_details: Dict) -> Tuple[float, str]:
        """Evaluate method-problem match"""
        score = 3.0
        evidence = ""

        if not method or method == 'null':
            return 1.0, "未识别到具体研究方法"

        method_upper = method.upper()

        quantitative = ['OLS', 'DID', 'IV', '2SLS', 'GMM', 'PSM', 'LOGIT', 'PROBIT']
        qualitative = ['案例', '访谈', '德尔菲', '扎根']

        if any(m in method_upper for m in quantitative):
            score += 2.0
            evidence += "使用定量方法；"
        elif any(m in method for m in qualitative):
            score += 2.0
            evidence += "使用定性方法；"

        return min(score, 6), evidence or "方法匹配度一般"

    def _evaluate_data_quality(self, data: Dict) -> Tuple[float, str]:
        """Evaluate data quality"""
        score = 3.0
        evidence = ""

        if not data:
            return 1.0, "未获取到数据信息"

        sample_size = data.get('sample_size', '')
        if sample_size:
            import re
            numbers = re.findall(r'\d+', str(sample_size))
            if numbers:
                num = int(numbers[0])
                if num >= 500:
                    score += 2.0
                    evidence += f"样本量充足({num})；"
                elif num >= 200:
                    score += 1.0
                    evidence += f"样本量适中({num})；"
                else:
                    evidence += f"样本量偏小({num})；"

        source = data.get('source', '')
        if source and source != 'null':
            score += 1.0
            evidence += f"数据来源：{source[:30]}；"

        return max(0, min(score, 6)), evidence or "数据质量评估依据不足"

    def _evaluate_results_interpretation(self, info: Dict) -> Tuple[float, str]:
        """Evaluate results interpretation"""
        score = 3.0
        evidence = ""

        conclusion = info.get('main_conclusion', '')

        if conclusion and len(conclusion) > 50:
            score += 2.0
            evidence += "结论表述详细；"

        limitations = info.get('limitations', '')
        if limitations and limitations != 'null' and len(limitations) > 20:
            score += 1.0
            evidence += "讨论了研究局限；"

        return min(score, 6), evidence or "结果解释需深化"
