# 硕士论文智能评审系统

**版本：v2.5**

**© 2026 河南科技学院经济与管理学院 | 齐安静**

---

## 系统简介

硕士论文智能评审系统是一款基于 Python + LLM 混合架构的论文评审工具。

**核心设计原则**：Python 负责可量化指标，LLM 负责深度评价——各司其职，输出稳定可解释的评审报告。

---

## 目录结构

```
thesis-reviewer/
├── README.md                    # 本文件
├── thesis_reviewer/            # Python项目代码
│   ├── pipeline_v4.py          # 核心流程（v4混合架构）
│   ├── parser/                 # PDF/DOCX解析
│   ├── scoring/                # 评分规则
│   └── ...
├── skills/
│   └── thesis-reviewer/
│       ├── SKILL.md           # Claude Code Skill配置
│       ├── agents/             # 各维度评审Agent
│       └── README.md          # 版权声明
```

---

## 快速开始

### 方式一：在Claude Code中使用（推荐）

1. 克隆本仓库到本地
2. 将 `skills/thesis-reviewer/` 目录拷贝到 Claude Code 的 skills 目录：
   ```bash
   cp -r skills/thesis-reviewer ~/.claude/skills/
   ```
3. 在Claude Code中运行：
   ```
   /thesis-reviewer
   ```

### 方式二：Python脚本直接调用

```python
from thesis_reviewer.pipeline_v4 import ReviewPipelineV4

pipeline = ReviewPipelineV4()
result = pipeline.run("论文.pdf")
```

---

## 版权声明

**© 2026 河南科技学院经济与管理学院 | 齐安静**

本系统及文档受版权法保护。未经授权，任何单位或个人不得复制、修改、传播本系统的代码或文档。

**引用方式**：
```
硕士论文智能评审系统 v2.5
河南科技学院经济与管理学院
齐安静
2026
```

---

## 免责声明

本评价报告由智能评审系统生成，评价结论仅供参考，最终评价以答辩委员会意见为准。
