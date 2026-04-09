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
thesis-reviewer/                    # 整个仓库拷贝到 ~/.claude/skills/
├── SKILL.md                       # Claude Code Skill 配置（AI读取此文件）
├── thesis_reviewer/                # Python 项目代码
│   ├── pipeline_v4.py             # 核心流程（v4混合架构）
│   ├── parser/                    # PDF/DOCX解析
│   ├── scoring/                   # 评分规则
│   └── ...
├── requirements.txt               # Python依赖
└── README.md                     # 本文件
```

---

## 安装部署

### 方式一：直接部署到 Claude Code Skills（推荐）

```bash
# 克隆到 skills 目录
git clone https://github.com/anjing137/thesis-reviewer.git ~/.claude/skills/thesis-reviewer

# 安装依赖
cd ~/.claude/skills/thesis-reviewer
pip install -r requirements.txt
```

### 方式二：克隆到其他位置

```bash
git clone https://github.com/anjing137/thesis-reviewer.git
cd thesis-reviewer
pip install -r requirements.txt
```

---

## 使用方式

在 Claude Code 中直接说：

```
评审我的论文：/path/to/论文.pdf
```

AI 将自动：
1. 调用 Python 解析论文
2. 生成评价 Prompt
3. 进行深度评价
4. 输出结构化评审报告

或手动运行：

```bash
python -c "
from thesis_reviewer.pipeline_v4 import ReviewPipelineV4

pipeline = ReviewPipelineV4()
result = pipeline.run('论文.pdf')
prompt = pipeline.evaluation_prompt
print(prompt[:2000])  # 显示前2000字
"
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
