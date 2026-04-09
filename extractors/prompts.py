"""
LLM Prompts for Information Extraction
"""

INFO_EXTRACTION_PROMPT = """你是论文信息抽取专家。请从以下论文内容中提取结构化信息。

要求：
1. 必须引用原文（用【】标注）
2. 不确定的内容返回null
3. 只抽取信息，不做评价

论文内容：
---
{content}
---

请提取以下信息（JSON格式）：

{{
    "paper_type": "实证经济学型/问卷调查实证型/案例研究型/政策研究型/未知",
    "research_question": "研究问题描述",
    "research_gap": "文献gap描述（如果没有明确提出则写null）",
    "method": "使用的具体方法，如OLS、DID、问卷调查、案例分析等",
    "method_details": {{
        "quantitative": true/false,
        "qualitative": true/false,
        "specific_methods": ["方法1", "方法2"]
    }},
    "data": {{
        "source": "数据来源",
        "sample_size": "样本量（数字或描述）",
        "time_range": "时间范围（如2015-2020）",
        "region": "研究区域"
    }},
    "has_robustness": true/false/null,
    "robustness_details": "稳健性检验具体内容",
    "has_endogeneity": true/false/null,
    "endogeneity_details": "内生性处理具体内容",
    "main_conclusion": "主要结论",
    "innovation_type": "选题创新/方法创新/数据创新/null",
    "limitations": "研究局限（如果明确提出）"
}}

输出要求：
- 如果某项信息在论文中找不到对应内容，写null
- 必须用【】标注引用的原文
- 保持客观，不添加评论
"""

PAPER_TYPE_DETECTION_PROMPT = """你是论文类型分类专家。请根据论文内容判断论文类型。

论文内容：
---
{content}
---

论文类型定义：
1. 实证经济学型：使用计量模型进行因果推断，如OLS、面板数据、时间序列、DID、PSM、IV等
2. 问卷调查实证型：通过问卷收集数据，进行信效度检验、因子分析、结构方程等
3. 案例研究型：对单个或少数案例进行深入分析，采用访谈、文本分析等质性方法
4. 政策研究型：围绕公共政策进行分析，提出政策建议和可行性论证

请返回JSON格式：
{{
    "paper_type": "实证经济学型/问卷调查实证型/案例研究型/政策研究型",
    "confidence": 0.0-1.0,
    "key_indicators": ["判断依据1", "判断依据2"],
    "reasoning": "简要推理过程"
}}

输出要求：
- confidence表示分类置信度（0-1）
- 必须用【】标注引用的原文作为判断依据
"""


METHODOLOGY_EXTRACTION_PROMPT = """你是方法论分析专家。请从论文方法论部分提取详细信息。

论文方法论章节：
---
{content}
---

提取以下信息（JSON格式）：

{{
    "method_name": "主要方法名称",
    "model_type": "回归分析/实验/案例分析/定性分析/混合方法",
    "identification_strategy": "因果识别策略描述，如DID、IV、固定效应等",
    "variables": {{
        "dependent": ["因变量1", "因变量2"],
        "independent": ["自变量1", "自变量2"],
        "control": ["控制变量1", "控制变量2"],
        "mediator": ["中介变量1", "中介变量2"],
        "moderator": ["调节变量1", "调节变量2"]
    }},
    "hypotheses": ["假设1", "假设2"],
    "causal_chains": [
        {{
            "cause": "原因变量",
            "effect": "结果变量",
            "mediator": "中介变量（如有）",
            "statement": "原文因果声明"
        }}
    ],
    "estimation_method": "具体估计方法，如固定效应、OLS等",
    "tests_performed": ["检验1", "检验2"],
    "software": "使用的软件（如SPSS、Stata、R等）",
    "over_control_issues": [
        {{
            "mediator_var": "被过度控制的中介变量",
            "explanation": "解释为何是过度控制",
            "severity": "high/medium/low"
        }}
    ],
    "missing_info": ["缺失的关键信息列表"]
}}

要求：
- 必须引用原文
- 不确定则写null
- over_control_issues: 检测中介变量是否被错误地作为控制变量处理（过度控制）
"""


FORMAT_CHECKING_PROMPT = """你是格式规范审查专家。请根据河南科技学院硕士论文格式要求检查论文格式。

格式要求摘要：
1. 结构：封面、扉页、摘要（中英文）、目录、引言、正文、结论、参考文献、致谢
2. 字数：学术型≥3万字，专业型≥2万字
3. 标题层级：第一章、1.1、1.1.1格式
4. 图表编号：图1-1、表1-1格式
5. 参考文献：符合GB/T 7714-2015

论文内容：
---
{content}
---

请检查以下项目，对每项给出通过/不通过/建议改进：

1. 结构完整性：是否包含所有必要部分
2. 标题层级：是否规范使用层级标题
3. 图表编号：是否连续规范
4. 参考文献格式：是否统一规范
5. 字体字号：是否按要求设置
6. 页眉页脚：是否正确设置

输出格式（JSON）：
{{
    "structure": {{
        "complete": true/false,
        "missing_parts": ["缺失部分列表"],
        "extra_parts": ["多余部分"]
    }},
    "title_hierarchy": {{
        "compliant": true/false,
        "issues": ["问题列表"]
    }},
    "figure_table": {{
        "compliant": true/false,
        "issues": ["问题列表"]
    }},
    "references": {{
        "compliant": true/false,
        "issues": ["问题列表"]
    }},
    "overall_score": 0-10,
    "critical_issues": ["严重问题（必须修改）"],
    "minor_issues": ["轻微问题（建议修改）"]
}}
"""

# 论文类型关键词（用于辅助判断论文类型）
PAPER_TYPE_KEYWORDS = {
    "实证经济学型": [
        "计量模型", "回归分析", "OLS", "固定效应", "随机效应", "面板数据",
        "时间序列", "VAR", "VEC", "GARCH", "DID", "PSM", "IV", "工具变量",
        "双重差分", "倾向得分匹配", "自然实验", "准实验"
    ],
    "问卷调查实证型": [
        "问卷调查", "问卷", "量表", "李克特", "信度", "效度", "因子分析",
        "Cronbach", "KMO", "结构方程", "SEM", "探索性因子", "验证性因子",
        "方差分析", "ANOVA", "t检验"
    ],
    "案例研究型": [
        "案例研究", "案例分析", "单案例", "多案例", "案例描述", "深度访谈",
        "扎根理论", "质性研究", "叙事分析", "文本分析", "历史分析"
    ],
    "政策研究型": [
        "政策研究", "政策分析", "政策建议", "公共政策", "政府", "制度",
        "法规", "规范性文件", "对策研究", "可行性分析", "影响评估"
    ]
}
