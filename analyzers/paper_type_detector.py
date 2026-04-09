#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Type Detector - 自动检测论文类型

支持五种论文类型：
1. 实证经济学型：计量模型+因果识别
2. 问卷调查型：问卷数据+统计分析
3. 政策评价型：指标体系+政策建议
4. 案例分析型：单/多案例深度分析
5. 混合型：多方法融合
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class PaperType(Enum):
    """论文类型枚举"""
    EMPIRICAL_ECONOMICS = "实证经济学型"  # 计量模型+因果识别
    SURVEY_EMPIRICAL = "问卷调查型"       # 问卷数据+统计分析
    POLICY_EVALUATION = "政策评价型"      # 指标体系+政策建议
    CASE_STUDY = "案例分析型"             # 单/多案例深度分析
    HYBRID = "混合型"                    # 多方法融合
    UNKNOWN = "未知"


@dataclass
class TypeDetectionResult:
    """类型检测结果"""
    paper_type: PaperType
    confidence: float  # 0.0 - 1.0
    matched_keywords: List[str]
    unmatched_keywords: List[str]
    reasoning: str


# 论文类型检测关键词
TYPE_PATTERNS = {
    PaperType.EMPIRICAL_ECONOMICS: {
        'name': '实证经济学型',
        'keywords': [
            'OLS', 'DID', 'IV', '2SLS', 'GMM', 'PSM', 'RD',
            '固定效应', '随机效应', '面板数据', '回归分析',
            '内生性', '工具变量', '双重差分', '断点回归',
            '因果识别', '倾向得分', '匹配', 'Heckman',
            'logit', 'probit', 'tobit', 'logistic'
        ],
        'required_sections': ['变量定义', '模型设定'],
        'score_weights': 1.0  # 每个关键词权重
    },
    PaperType.SURVEY_EMPIRICAL: {
        'name': '问卷调查实证型',
        'keywords': [
            '问卷', '调查', '调查问卷', '信度', '效度',
            '克隆巴赫', 'KMO', 'Bartlett', '因子分析',
            'Cronbach', '因子载荷', '共同方法偏差',
            '结构方程', 'SEM', 'AMOS', 'PLS',
            'Logistic', 'logistic', '二元logistic'
        ],
        'required_sections': ['问卷设计', '样本'],
        'score_weights': 1.0
    },
    PaperType.CASE_STUDY: {
        'name': '案例研究型',
        'keywords': [
            '案例', '案例分析', '多案例', '单案例',
            '定性分析', '访谈', '扎根', '田野调查',
            '三角验证', '过程追踪', '案例选择',
            'AHP', '模糊综合', '层次分析'
        ],
        'required_sections': ['案例选择', '案例分析'],
        'score_weights': 1.0
    },
    PaperType.POLICY_EVALUATION: {
        'name': '政策评价型',
        'keywords': [
            '政策', '对策', '建议', '政府', '监管',
            '实施方案', '可行性', '政策建议', '政策评估',
            '问题分析', '现状分析', '发展对策',
            '优化', '完善', '改进',
            '熵权法', '耦合协调度', '障碍度', '综合指数',
            '指标体系', '测度', '评价模型'
        ],
        'required_sections': ['现状分析', '对策'],
        'score_weights': 0.8  # 政策类关键词更通用，降低权重
    },
    PaperType.HYBRID: {
        'name': '混合型',
        'keywords': [
            # 多方法组合关键词
            '熵权法', '耦合协调度', '障碍度',  # 评价型方法
            '回归分析', '面板数据', '固定效应',  # 计量方法
            '问卷', '信度', '效度',  # 问卷方法
            '案例分析', '案例研究',  # 案例方法
            'GIS', '空间杜宾', '地理探测器',  # 空间分析方法
            '核密度', '基尼系数',  # 分布分析方法
        ],
        'required_sections': [],
        'score_weights': 1.5  # 混合型需要多个关键词组合，权重稍高
    }
}


class PaperTypeDetector:
    """论文类型检测器"""

    def __init__(self, content: str = ""):
        """
        初始化检测器

        Args:
            content: 论文全文内容
        """
        self.content = content
        self.lower_content = content.lower() if content else ""

    def detect(self) -> TypeDetectionResult:
        """
        检测论文类型

        Returns:
            TypeDetectionResult 包含检测结果和置信度
        """
        if not self.content:
            return TypeDetectionResult(
                paper_type=PaperType.UNKNOWN,
                confidence=0.0,
                matched_keywords=[],
                unmatched_keywords=[],
                reasoning="未提供论文内容"
            )

        # 计算各类型得分
        scores = {}
        matched = {}
        unmatched = {}

        for ptype, pattern in TYPE_PATTERNS.items():
            score, m, u = self._calculate_type_score(ptype, pattern)
            scores[ptype] = score
            matched[ptype] = m
            unmatched[ptype] = u

        # 找出最高分类型
        best_type = max(scores.items(), key=lambda x: x[1])
        best_ptype = best_type[0]
        best_score = best_type[1]

        # 计算置信度（最高分 / 所有分之和，归一化到0-1）
        total_score = sum(scores.values())
        if total_score > 0:
            confidence = best_score / total_score
        else:
            confidence = 0.0

        # 检查必需章节
        required_satisfied = self._check_required_sections(best_ptype)

        # 如果必需章节不满足，降低置信度
        if not required_satisfied:
            confidence *= 0.7

        reasoning = self._generate_reasoning(best_ptype, best_score, matched[best_ptype], required_satisfied)

        return TypeDetectionResult(
            paper_type=best_ptype,
            confidence=min(confidence, 1.0),
            matched_keywords=matched[best_ptype],
            unmatched_keywords=unmatched[best_ptype],
            reasoning=reasoning
        )

    def _calculate_type_score(self, ptype: PaperType, pattern: Dict) -> tuple:
        """
        计算某类型的匹配得分

        Returns:
            (score, matched_keywords, unmatched_keywords)
        """
        score = 0.0
        matched = []
        unmatched = []

        keywords = pattern['keywords']
        weights = pattern.get('score_weights', 1.0)

        for kw in keywords:
            if kw.lower() in self.lower_content:
                score += weights
                matched.append(kw)
            else:
                unmatched.append(kw)

        return score, matched, unmatched

    def _check_required_sections(self, ptype: PaperType) -> bool:
        """检查必需章节是否满足"""
        if ptype == PaperType.UNKNOWN:
            return True

        pattern = TYPE_PATTERNS.get(ptype)
        if not pattern:
            return True

        required = pattern.get('required_sections', [])
        if not required:
            return True

        # 检查章节标题
        section_patterns = [
            r'#{1,3}\s*[^\n]+'  # Markdown标题
        ]

        found_sections = set()
        for sec in required:
            for pat in section_patterns:
                matches = re.findall(pat, self.content)
                for m in matches:
                    if sec in m:
                        found_sections.add(sec)
                        break

        # 至少满足一半的必需章节
        return len(found_sections) >= len(required) / 2

    def _generate_reasoning(self, ptype: PaperType, score: float,
                           matched: List[str], required_satisfied: bool) -> str:
        """生成推理说明"""
        parts = []

        parts.append(f"论文类型判定为【{ptype.value}】")

        if matched:
            parts.append(f"匹配关键词：{', '.join(matched[:5])}")
            if len(matched) > 5:
                parts.append(f"等共{len(matched)}个")

        if required_satisfied:
            parts.append("必需章节满足")
        else:
            parts.append("部分必需章节缺失")

        parts.append(f"匹配得分：{score:.1f}")

        return "；".join(parts)


def detect_paper_type(content: str) -> TypeDetectionResult:
    """
    便捷函数：检测论文类型

    Args:
        content: 论文全文内容

    Returns:
        TypeDetectionResult
    """
    detector = PaperTypeDetector(content)
    return detector.detect()


def paper_type_to_dimensions(ptype: PaperType) -> Dict[str, int]:
    """
    根据论文类型返回评分维度权重

    Args:
        ptype: 论文类型

    Returns:
        各维度权重字典
    """
    # 各类型权重配置（与skill.md v2.3一致）
    DIMENSION_WEIGHTS = {
        PaperType.EMPIRICAL_ECONOMICS: {
            'topic_significance': 10,    # 选题与研究意义
            'literature_review': 10,     # 文献综述与理论基础
            'methodology': 25,           # 研究方法与技术路线
            'empirical_analysis': 30,    # 实证分析与结果
            'innovation': 15,            # 创新性
            'writing': 5,                # 写作规范与表达
            'conclusion': 5             # 结论与建议
        },
        PaperType.SURVEY_EMPIRICAL: {
            'topic_significance': 10,
            'literature_review': 10,
            'methodology': 20,
            'empirical_analysis': 30,
            'innovation': 15,
            'writing': 10,
            'conclusion': 5
        },
        PaperType.POLICY_EVALUATION: {
            'topic_significance': 15,
            'literature_review': 10,
            'methodology': 25,
            'empirical_analysis': 20,
            'innovation': 15,
            'writing': 10,
            'conclusion': 5
        },
        PaperType.CASE_STUDY: {
            'topic_significance': 15,
            'literature_review': 15,
            'methodology': 15,
            'empirical_analysis': 15,
            'innovation': 20,
            'writing': 15,
            'conclusion': 5
        },
        PaperType.HYBRID: {
            'topic_significance': 12,
            'literature_review': 12,
            'methodology': 23,
            'empirical_analysis': 25,
            'innovation': 15,
            'writing': 8,
            'conclusion': 5
        },
        PaperType.UNKNOWN: {
            'topic_significance': 12,
            'literature_review': 12,
            'methodology': 23,
            'empirical_analysis': 25,
            'innovation': 15,
            'writing': 8,
            'conclusion': 5
        }
    }

    return DIMENSION_WEIGHTS.get(ptype, DIMENSION_WEIGHTS[PaperType.UNKNOWN])


def paper_type_to_methodology_subdims(ptype: PaperType) -> List[tuple]:
    """
    根据论文类型返回方法论的子维度

    Args:
        ptype: 论文类型

    Returns:
        [(子维度名, 满分), ...]
    """
    SUB_DIMENSIONS = {
        PaperType.EMPIRICAL_ECONOMICS: [
            ('数据质量', 6),
            ('方法规范性', 8),
            ('稳健性检验', 8),
            ('内生性处理', 8)
        ],
        PaperType.SURVEY_EMPIRICAL: [
            ('问卷设计', 6),
            ('样本代表性', 6),
            ('信效度检验', 8),
            ('统计方法', 6)
        ],
        PaperType.POLICY_EVALUATION: [
            ('数据质量', 5),
            ('指标体系', 5),
            ('评价结果', 5),
            ('障碍度分析', 5)
        ],
        PaperType.CASE_STUDY: [
            ('案例典型性', 7),
            ('理论应用', 7),
            ('分析深度', 6)
        ],
        PaperType.HYBRID: [
            ('方法明确度', 5),
            ('方法匹配度', 8),
            ('多方法融合', 5),
            ('实证逻辑', 5)
        ],
        PaperType.UNKNOWN: [
            ('方法匹配度', 6),
            ('数据质量', 6),
            ('模型规范性', 6),
            ('稳健性检验', 6)
        ]
    }

    return SUB_DIMENSIONS.get(ptype, SUB_DIMENSIONS[PaperType.UNKNOWN])
