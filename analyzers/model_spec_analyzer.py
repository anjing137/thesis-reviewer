#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model Specification Analyzer - 模型设定分析器

功能：
- 从实证论文中提取变量定义（被解释变量、解释变量、控制变量、中介变量）
- 提取因果链声明
- 提取回归模型公式
- 检测"过度控制"（over-control）问题
- 检测变量角色混淆、遗漏控制变量等问题

仅适用于实证类论文（计量经济学、问卷调查）
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class VariableRole(Enum):
    """变量角色分类"""
    DEPENDENT = "dependent"           # 被解释变量Y
    INDEPENDENT = "independent"       # 核心解释变量X
    MEDIATOR = "mediator"            # 中介变量M
    CONTROL = "control"               # 控制变量
    MODERATOR = "moderator"          # 调节变量
    UNKNOWN = "unknown"


class VariableType(Enum):
    """变量类型分类"""
    CONTINUOUS = "continuous"        # 连续变量
    DISCRETE = "discrete"            # 离散变量
    BINARY = "binary"                # 二值变量
    COUNT = "count"                  # 计数变量
    RATIO = "ratio"                  # 比例变量


@dataclass
class Variable:
    """单个变量定义"""
    name_en: str                      # 英文名 e.g., "innovation"
    name_cn: str                     # 中文名 e.g., "专利申请量"
    role: VariableRole = VariableRole.UNKNOWN
    var_type: VariableType = VariableType.CONTINUOUS
    definition_text: Optional[str] = None
    measurement: Optional[str] = None


@dataclass
class CausalChain:
    """因果链声明"""
    statement: str                    # 完整语句
    cause_var: str                    # 原因变量
    effect_var: str                   # 结果变量
    mediator_vars: List[str] = field(default_factory=list)  # 中介变量列表
    is_direct_effect: bool = False
    line_number: Optional[int] = None


@dataclass
class ModelFormula:
    """回归模型公式"""
    formula_text: str                 # 完整公式文本
    dependent_var: str                # 被解释变量
    independent_vars: List[str] = field(default_factory=list)
    control_vars: List[str] = field(default_factory=list)
    mediator_vars: List[str] = field(default_factory=list)
    model_type: Optional[str] = None  # e.g., "固定效应模型"


@dataclass
class OverControlIssue:
    """过度控制问题"""
    mediator_var: str                 # 被过度控制的中介变量
    causal_chain: str                 # 相关因果链声明
    controlled_in_model: str          # 在哪个模型中被控制
    explanation: str
    severity: str = "high"           # high, medium, low


@dataclass
class EndogeneityCheck:
    """内生性处理检查"""
    has_endogeneity: bool
    method_used: Optional[str]        # e.g., "IV-2SLS", "GMM"
    is_adequate: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class ModelSpecResult:
    """完整的模型设定分析结果"""
    variables: List[Variable] = field(default_factory=list)
    causal_chains: List[CausalChain] = field(default_factory=list)
    formulas: List[ModelFormula] = field(default_factory=list)
    over_control_issues: List[OverControlIssue] = field(default_factory=list)
    endogeneity_check: Optional[EndogeneityCheck] = None

    # 评分（0-100）
    spec_completeness: int = 0
    spec_accuracy: int = 0
    causal_logic: int = 0

    # 元数据
    extraction_confidence: float = 0.0  # 0.0-1.0


class ModelSpecAnalyzer:
    """
    模型设定分析器

    从实证论文中提取并验证：
    - 变量定义和角色
    - 回归模型公式
    - 因果链声明
    - 过度控制问题
    - 内生性处理
    """

    # 已知中介变量关键词
    KNOWN_MEDIATORS: Set[str] = {
        'rd', '研发投入', '研发支出', '研发强度', '研发费用',
        'patent', '专利', '专利申请', '专利授权',
        'financing', '融资约束', '融资', '资金约束',
        'cash_flow', '现金流', '经营性现金流',
        'roe', 'roa', '盈利能力', '利润', '经营绩效',
        '人力资本', '员工结构', 'employment',
        '风险认知', '认知', 'perception'
    }

    # 常见被解释变量关键词
    COMMON_DEPENDENT_KEYWORDS: Set[str] = {
        'innovation', '创新', '专利', '新产品',
        'performance', '绩效', '业绩', 'roa', 'roe',
        'risk', '风险', 'risk_taking',
        'investment', '投资', '研发',
        'growth', '增长', '营收增长',
        'value', '企业价值', '托宾Q',
        'demand', '需求', '参保意愿', '保险需求',
        'satisfaction', '满意度', '感知'
    }

    # 典型控制变量关键词
    TYPICAL_CONTROL_KEYWORDS: Set[str] = {
        'size', '规模', '公司规模', 'asset', '总资产',
        'age', '年龄', '企业年龄', '成立年限',
        'leverage', '杠杆', '资产负债率', 'debt',
        'tangibility', '有形资产', '固定资产',
        'cash', '现金', '现金持有',
        'growth', '增长', '营收增长',
        'year', '年份', '年度', 'time',
        'industry', '行业', 'industry_fe',
        'roa', '盈利能力', '利润率',
        'gender', '性别', 'age', '年龄',
        'education', '教育', '受教育',
        'income', '收入', '家庭收入'
    }

    # 因果链检测模式
    CAUSAL_PATTERNS: List[re.Pattern] = [
        # H1: X对Y有显著影响
        re.compile(r'[Hh](\d+)\s*[:：]\s*([^:：]+?)\s*(?:对|影响|提升|降低|促进|抑制)?\s*([^:：\n]+?)(?:显著|正向|负向|具有)?'),
        # X通过M影响Y
        re.compile(r'([^\s]+?)\s*(?:通过|经由|借助)\s*([^\s]+?)\s*(?:影响|作用于|促进|抑制)\s*([^\s，。；]+?)'),
    ]

    def __init__(self, content: str = "", is_empirical: bool = True):
        """
        初始化分析器

        Args:
            content: 论文全文内容
            is_empirical: 是否为实证论文
        """
        self.content = content
        self.is_empirical = is_empirical
        self.variables: List[Variable] = []
        self.causal_chains: List[CausalChain] = []
        self.formulas: List[ModelFormula] = []
        self.over_control_issues: List[OverControlIssue] = []

    def analyze(self) -> ModelSpecResult:
        """
        执行完整的模型设定分析

        Returns:
            ModelSpecResult
        """
        result = ModelSpecResult()

        if not self.is_empirical or not self.content:
            result.extraction_confidence = 1.0
            return result

        # 提取信息
        self.variables = self.extract_variables()
        self.causal_chains = self.extract_causal_chains()
        self.formulas = self.extract_model_formulas()

        # 检测问题
        self.over_control_issues = self.detect_over_control()
        endogeneity_check = self.verify_endogeneity_handling()

        # 计算评分
        if self.variables or self.causal_chains:
            result.spec_completeness = self._calculate_completeness()
            result.spec_accuracy = self._calculate_accuracy()
            result.causal_logic = self._calculate_causal_logic()
            result.extraction_confidence = self._calculate_confidence()

        result.variables = self.variables
        result.causal_chains = self.causal_chains
        result.formulas = self.formulas
        result.over_control_issues = self.over_control_issues
        result.endogeneity_check = endogeneity_check

        return result

    def extract_variables(self) -> List[Variable]:
        """从论文中提取变量定义"""
        variables = []

        # 尝试查找变量定义表格
        var_table = self._find_section("变量定义")
        if var_table:
            table_vars = self._parse_variable_table(var_table)
            variables.extend(table_vars)

        # 从文本中提取
        if not variables:
            text_vars = self._extract_variables_from_text()
            variables.extend(text_vars)

        # 分类变量角色
        self._classify_variable_roles(variables)

        return variables

    def _parse_variable_table(self, table_text: str) -> List[Variable]:
        """解析变量定义表格"""
        variables = []

        # 多列格式：| 类型 | 名称 | 符号 | 定义 |
        header_pattern = r'变量类型.*?变量名称|被解释变量.*?解释变量'
        is_multi_col = re.search(header_pattern, table_text)

        if is_multi_col:
            rows = re.findall(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', table_text)
            for row in rows:
                if len(row) < 3:
                    continue

                var_type = row[0].strip()
                var_name = row[1].strip()
                var_symbol = row[2].strip()

                if any(kw in var_name for kw in ['变量', '类型', '名称', '符号']):
                    continue

                role = VariableRole.UNKNOWN
                if '被解释' in var_type or '因变量' in var_type:
                    role = VariableRole.DEPENDENT
                elif '核心' in var_type or '自变量' in var_type or '解释' in var_type:
                    role = VariableRole.INDEPENDENT
                elif '控制' in var_type:
                    role = VariableRole.CONTROL
                elif '中介' in var_type:
                    role = VariableRole.MEDIATOR

                var = Variable(
                    name_en=self._normalize_var_name(var_symbol or var_name),
                    name_cn=var_symbol or var_name,
                    role=role,
                    definition_text=row[3].strip() if len(row) > 3 else ''
                )
                variables.append(var)
        else:
            # 标准双列表格
            rows = re.findall(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', table_text)
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                name_col = row[0].strip()
                def_col = row[1].strip()

                if len(name_col) < 2 or len(def_col) < 2:
                    continue
                if name_col in ['变量', 'Variable', '名称']:
                    continue

                var = Variable(
                    name_en=self._normalize_var_name(name_col),
                    name_cn=name_col,
                    definition_text=def_col
                )
                variables.append(var)

        return variables

    def _extract_variables_from_text(self) -> List[Variable]:
        """从文本中提取变量"""
        variables = []

        patterns = [
            r'([A-Za-z_]\w*)\s*[=:：]\s*([^，,。\n]+)',
            r'([^\s]+?)\s*(?:定义为|定义为|是)\s*([^，,。\n]+)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, self.content)
            for match in matches:
                name = match.group(1).strip()
                definition = match.group(2).strip()

                if len(name) < 2 or len(definition) < 3:
                    continue

                var = Variable(
                    name_en=self._normalize_var_name(name),
                    name_cn=name,
                    definition_text=definition
                )
                variables.append(var)

        return variables

    def _classify_variable_roles(self, variables: List[Variable]) -> None:
        """根据变量名和上下文分类变量角色"""
        # 收集因果链中的变量
        mediator_vars = set()
        for chain in self.causal_chains:
            mediator_vars.update(chain.mediator_vars)

        for var in variables:
            var_name_lower = var.name_en.lower()
            var_name_cn = var.name_cn

            # 检查是否在因果链中声明为中介
            if var.name_en in mediator_vars or any(
                m.lower() in var_name_lower for m in mediator_vars
            ):
                var.role = VariableRole.MEDIATOR
                continue

            # 检查是否为常见被解释变量
            if any(kw in var_name_lower or kw in var_name_cn
                   for kw in self.COMMON_DEPENDENT_KEYWORDS):
                var.role = VariableRole.DEPENDENT
                continue

            # 检查是否为已知中介变量关键词
            if any(kw in var_name_lower for kw in ['研发', '融资', '现金', '认知', '风险']):
                if var.name_en in mediator_vars:
                    var.role = VariableRole.MEDIATOR
                    continue

            # 检查是否为典型控制变量
            if any(kw in var_name_lower for kw in self.TYPICAL_CONTROL_KEYWORDS):
                var.role = VariableRole.CONTROL

    def extract_causal_chains(self) -> List[CausalChain]:
        """从理论/假设部分提取因果链声明"""
        chains = []

        # 从假设部分提取
        hypothesis_section = self._find_section("研究假设")
        if hypothesis_section:
            chains.extend(self._extract_chains_from_text(hypothesis_section))

        # 从理论分析部分提取
        theory_section = self._find_section("理论分析")
        if theory_section:
            chains.extend(self._extract_chains_from_text(theory_section))

        # 去重
        unique_chains = []
        seen = set()
        for chain in chains:
            key = (chain.cause_var, chain.effect_var, tuple(chain.mediator_vars))
            if key not in seen:
                seen.add(key)
                unique_chains.append(chain)

        return unique_chains

    def _extract_chains_from_text(self, text: str) -> List[CausalChain]:
        """从文本中提取因果链"""
        chains = []

        for pattern in self.CAUSAL_PATTERNS:
            matches = pattern.finditer(text)
            for match in matches:
                groups = match.groups()

                if len(groups) >= 2:
                    cause_var = groups[0].strip() if groups[0] else ""
                    effect_var = groups[-1].strip() if groups[-1] else ""

                    if len(cause_var) < 2 or len(effect_var) < 2:
                        continue

                    # 如果有中介变量
                    if len(groups) >= 3 and groups[1]:
                        mediator = groups[1].strip()
                        if mediator and len(mediator) >= 2:
                            chain = CausalChain(
                                statement=match.group(0),
                                cause_var=cause_var,
                                effect_var=effect_var,
                                mediator_vars=[mediator],
                                is_direct_effect=False
                            )
                        else:
                            chain = CausalChain(
                                statement=match.group(0),
                                cause_var=cause_var,
                                effect_var=effect_var,
                                is_direct_effect=True
                            )
                    else:
                        chain = CausalChain(
                            statement=match.group(0),
                            cause_var=cause_var,
                            effect_var=effect_var,
                            is_direct_effect=True
                        )
                    chains.append(chain)

        return chains

    def extract_model_formulas(self) -> List[ModelFormula]:
        """提取回归模型公式"""
        formulas = []

        model_section = self._find_section("模型设定")
        if not model_section:
            model_section = self._find_section("实证分析")
        if not model_section:
            model_section = self.content

        # 匹配回归公式
        eq_patterns = [
            r'([A-Za-z_]\w*)\s*=\s*β₀?\s*[\+]?\s*(?:β\d?[·•]?\s*)?([A-Za-z_]\w*)',
            r'(demand|innovation|performance|risk|growth)\s*=\s*β',
        ]

        for pattern_str in eq_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = pattern.finditer(model_section)

            for match in matches:
                formula = ModelFormula(
                    formula_text=match.group(0),
                    dependent_var=match.group(1) if len(match.groups()) >= 1 else ""
                )
                formulas.append(formula)

        # 提取控制变量
        control_var_pattern = r'(?:控制变量|Control variables?)[:：]\s*([^\n]+)'
        control_matches = re.finditer(control_var_pattern, model_section, re.IGNORECASE)
        for cmatch in control_matches:
            control_text = cmatch.group(1)
            c_vars = re.split(r'[,，、]', control_text)
            for f in formulas:
                for v in c_vars:
                    v_clean = v.strip()
                    if v_clean and len(v_clean) < 20:
                        if v_clean not in f.control_vars:
                            f.control_vars.append(v_clean)

        # 如果找到了变量定义，检查控制变量列表
        if self.variables:
            for var in self.variables:
                if var.role == VariableRole.CONTROL:
                    for f in formulas:
                        if var.name_en not in f.control_vars:
                            f.control_vars.append(var.name_en)

        return formulas

    def detect_over_control(self) -> List[OverControlIssue]:
        """
        检测过度控制问题

        当中介变量被作为控制变量放入模型时，会阻断中介路径，
        导致对直接效应的估计偏误。
        """
        issues = []

        # 找出所有声明的中介变量
        mediators_in_chains = set()
        for chain in self.causal_chains:
            mediators_in_chains.update(chain.mediator_vars)

        if not mediators_in_chains:
            return issues

        # 检查每个公式
        for formula in self.formulas:
            control_vars_lower = [v.lower() for v in formula.control_vars]

            for mediator in mediators_in_chains:
                mediator_lower = mediator.lower()

                # 检查中介变量是否在控制变量中
                if any(mediator_lower in ctrl or ctrl in mediator_lower
                       for ctrl in control_vars_lower):
                    issue = OverControlIssue(
                        mediator_var=mediator,
                        causal_chain=self._get_causal_chain_text(mediator),
                        controlled_in_model=formula.formula_text or "主回归模型",
                        severity="high",
                        explanation=(
                            f"变量'{mediator}'在因果链中作为中介变量被识别，"
                            f"但在研究直接效应时被作为控制变量控制。"
                            f"这会阻断中介路径，导致对直接效应的估计偏误。"
                        )
                    )
                    issues.append(issue)

        return issues

    def _get_causal_chain_text(self, mediator: str) -> str:
        """获取包含特定中介变量的因果链文本"""
        for chain in self.causal_chains:
            if mediator in chain.mediator_vars:
                if chain.mediator_vars:
                    return f"{chain.cause_var} → {chain.mediator_vars[0]} → {chain.effect_var}"
                else:
                    return f"{chain.cause_var} → {chain.effect_var}"
        return ""

    def verify_endogeneity_handling(self) -> EndogeneityCheck:
        """验证内生性问题是否被妥善处理"""
        check = EndogeneityCheck(
            has_endogeneity=False,
            method_used=None,
            is_adequate=True,
            issues=[]
        )

        endogeneity_keywords = {
            'iv': '工具变量法（IV）',
            '2sls': '两阶段最小二乘法（2SLS）',
            'gmm': '广义矩估计（GMM）',
            'did': '双重差分（DID）',
            'rd': '断点回归（RD）',
            '滞后': '滞后变量法',
            'lag': '滞后变量法',
            '内生性': '内生性讨论'
        }

        found_methods = []
        for keyword, method_name in endogeneity_keywords.items():
            if keyword in self.content.lower():
                found_methods.append(method_name)

        if found_methods:
            check.has_endogeneity = True
            check.method_used = '、'.join(found_methods)

            if '内生性讨论' in found_methods and len(found_methods) == 1:
                check.is_adequate = False
                check.issues.append("仅讨论了内生性问题但未采用适当的计量方法处理")

        return check

    def _find_section(self, section_name: str) -> str:
        """查找并提取论文中特定章节的内容"""
        patterns = [
            rf'(?:^|\n)##\s+{re.escape(section_name)}(?:\s*\n|$)',
            rf'(?:^|\n)#\s+{re.escape(section_name)}(?:\s*\n|$)',
            rf'\*\*{re.escape(section_name)}\*\*',
        ]

        section_pos = -1
        section_end = -1

        for pattern in patterns:
            match = re.search(pattern, self.content)
            if match:
                if section_pos == -1 or match.start() < section_pos:
                    section_pos = match.start()
                    section_end = match.end()
                    break

        if section_pos == -1:
            return ""

        # 提取章节内容（到下一个章节为止）
        next_section_pos = section_end
        next_patterns = [
            r'\n#{1,2}\s+[^\n]+',
            r'\n\*\*(?:[^*]|\*(?!\*))*?\*\*',
        ]

        next_section_end = len(self.content)
        for npat in next_patterns:
            nmatch = re.search(npat, self.content[next_section_pos:])
            if nmatch:
                next_section_end = min(next_section_end, next_section_pos + nmatch.start())

        return self.content[next_section_pos:next_section_end].strip()[:5000]

    def _normalize_var_name(self, name: str) -> str:
        """标准化变量名"""
        name = name.strip()
        name = re.sub(r'\s*\([^)]*\)', '', name)
        name = re.sub(r'[（）()【】\[\]]', '', name)
        name = name.strip()

        if re.search(r'[\u4e00-\u9fff]', name):
            mapping = {
                '创新': 'innovation', '专利': 'patent',
                '研发投入': 'rd', '研发支出': 'rd',
                '规模': 'size', '年龄': 'age',
                '融资约束': 'financing', '资产负债率': 'lev',
                '盈利能力': 'roe', '利润': 'profit',
            }
            for cn, en in mapping.items():
                if cn in name:
                    return en

        return name.lower()

    def _calculate_completeness(self) -> int:
        """计算模型设定完整性评分（0-100）"""
        score = 0

        if self.variables:
            score += 25
        if self.causal_chains:
            score += 25
        if self.formulas:
            score += 25

        if '内生性' in self.content or 'endogeneity' in self.content.lower():
            score += 25
        elif '稳健性' in self.content or 'robustness' in self.content.lower():
            score += 12

        return min(score, 100)

    def _calculate_accuracy(self) -> int:
        """计算变量角色准确性评分（0-100）"""
        if not self.variables:
            return 50

        score = 100
        score -= len(self.over_control_issues) * 15

        return max(score, 0)

    def _calculate_causal_logic(self) -> int:
        """计算因果逻辑一致性评分（0-100）"""
        if not self.causal_chains:
            return 50

        score = 100
        high_severity = sum(1 for i in self.over_control_issues if i.severity == 'high')
        score -= high_severity * 30

        return max(score, 0)

    def _calculate_confidence(self) -> float:
        """计算提取置信度（0.0-1.0）"""
        confidence = 0.0

        if self.variables:
            confidence += 0.25
        if self.causal_chains:
            confidence += 0.30
        if self.formulas:
            confidence += 0.20

        if self.over_control_issues:
            confidence -= 0.1 * len(self.over_control_issues)

        return max(0.0, min(1.0, confidence))


def model_spec_to_dict(result: ModelSpecResult) -> Dict:
    """将ModelSpecResult转换为字典"""
    if result is None:
        return {}

    return {
        'variables': [
            {
                'name_en': v.name_en,
                'name_cn': v.name_cn,
                'role': v.role.value if v.role else 'unknown',
                'definition': v.definition_text,
            }
            for v in result.variables
        ],
        'causal_chains': [
            {
                'cause': c.cause_var,
                'effect': c.effect_var,
                'mediators': c.mediator_vars,
                'statement': c.statement,
            }
            for c in result.causal_chains
        ],
        'formulas': [
            {
                'text': f.formula_text,
                'dependent': f.dependent_var,
                'controls': f.control_vars,
                'type': f.model_type,
            }
            for f in result.formulas
        ],
        'over_control_issues': [
            {
                'mediator': i.mediator_var,
                'chain': i.causal_chain,
                'severity': i.severity,
                'explanation': i.explanation,
            }
            for i in result.over_control_issues
        ],
        'endogeneity_check': {
            'has_endogeneity': result.endogeneity_check.has_endogeneity if result.endogeneity_check else False,
            'method': result.endogeneity_check.method_used if result.endogeneity_check else None,
            'adequate': result.endogeneity_check.is_adequate if result.endogeneity_check else True,
        } if result.endogeneity_check else None,
        'scores': {
            'completeness': result.spec_completeness,
            'accuracy': result.spec_accuracy,
            'causal_logic': result.causal_logic,
        },
        'confidence': result.extraction_confidence,
    }
