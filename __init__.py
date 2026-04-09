"""
Thesis Reviewer - 硕士论文智能评审系统 v2.5

Design: Python精准统计 + LLM深度评价

v2.5 Workflow (推荐):
1. Python解析文档（PDF/DOCX → 结构化文本）
2. Python精准统计（字数、文献数、论文类型）
3. 生成评价Prompt
4. LLM深度评价（在对话中进行）

Usage:
    # v2.5 推荐用法
    from thesis_reviewer import review_pipeline_v4

    result = review_pipeline_v4('thesis.pdf', './output/')
    print(result.statistics)       # Python精准统计数据
    print(result.evaluation_prompt)  # LLM评价用的Prompt
"""

from .pipeline_v4 import ReviewPipelineV4, review_pipeline_v4, ReviewResultV4

# 向后兼容v2
from .pipeline import ReviewPipeline, review_pipeline, ReviewResult

__all__ = [
    # v2.5 新架构
    'ReviewPipelineV4',
    'review_pipeline_v4',
    'ReviewResultV4',
    # v2 向后兼容
    'ReviewPipeline',
    'review_pipeline',
    'ReviewResult',
]
__version__ = '2.5.0'
