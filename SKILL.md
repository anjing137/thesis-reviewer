---
name: thesis-reviewer
description: "硕士论文智能评审系统 v2.5。Python精准统计 + LLM深度评价架构。Python负责可量化指标（字数、文献数、论文类型），LLM负责深度评价（创新性、逻辑性、方法严谨性）。支持PDF/DOCX解析，5种论文类型，输出包含总体评价+分维度评价+分级建议+总结。"
metadata:
  version: "2.5"
  last_updated: "2026-04-09"
---

# 硕士学位论文智能评审系统 v2.5

**© 2026 河南科技学院经济与管理学院 | 齐安静**

**核心设计原则**：Python负责可量化、LLM负责深度评价——各司其职，输出稳定可解释的评审报告。

---

## 系统架构

```
用户论文（PDF/DOCX）
    ↓
[1] Python解析 → 精准统计（字数、文献数、论文类型）
    ↓
[2] Python生成评价Prompt
    ↓
[3] AI深度评价 → 结构化JSON评分
    ↓
[4] Python解析JSON → 最终评审报告
```

---

## 快速使用

当用户说"评审我的论文"或"评价这篇论文"时：

1. **获取论文路径**：询问用户论文文件路径
2. **运行Python解析**：
   ```bash
   cd /Users/anjing137/Documents/thesis_reviewer  # 项目根目录
   python -c "
   from pipeline_v4 import ReviewPipelineV4
   import json

   pipeline = ReviewPipelineV4()
   result = pipeline.run('论文路径')

   # 保存统计数据
   stats = {
       'title': result.statistics.title,
       'total_char_count': result.statistics.total_char_count,
       'chapter_count': result.statistics.chapter_count,
       'reference_stats': result.statistics.reference_stats,
       'paper_type': result.statistics.paper_type,
       'detected_methods': result.statistics.detected_methods
   }
   print(json.dumps(stats, ensure_ascii=False, indent=2))
   "
   ```
3. **生成评价Prompt**：调用 `generate_llm_evaluation_prompt()` 生成完整Prompt
4. **让用户复制Prompt给LLM评价**
5. **接收LLM的JSON评分**，调用 `generate_report()` 生成最终报告

---

## 核心Python代码

```python
from pipeline_v4 import ReviewPipelineV4, generate_llm_evaluation_prompt, parse_llm_evaluation, generate_final_report

# 1. 解析论文
pipeline = ReviewPipelineV4()
result = pipeline.run("论文.pdf")

# 2. 生成评价Prompt（供AI评价）
prompt = generate_llm_evaluation_prompt(result.modules, result.statistics)
print(prompt)  # 展示给用户

# 3. 解析LLM返回的JSON
llm_json = '用户提供的JSON字符串'
llm_eval = parse_llm_evaluation(llm_json)

# 4. 生成最终报告
report = generate_final_report(result.modules, result.statistics, llm_eval)
print(report)
```

---

## 项目路径

当此仓库被克隆到 `~/.claude/skills/thesis-reviewer/` 时：

| 文件 | 路径 |
|------|------|
| 项目根目录 | `~/.claude/skills/thesis-reviewer/` |
| Python代码 | `~/.claude/skills/thesis-reviewer/thesis_reviewer/` |
| 主流程 | `~/.claude/skills/thesis-reviewer/thesis_reviewer/pipeline_v4.py` |

---

## 版权声明

**© 2026 河南科技学院经济与管理学院 | 齐安静**

本评价报告由智能评审系统生成，评价结论仅供参考，最终评价以答辩委员会意见为准。
