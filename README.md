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

### 1. 克隆仓库

```bash
git clone https://github.com/anjing137/thesis-reviewer.git
cd thesis-reviewer
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行评审

```bash
python -c "
from thesis_reviewer.pipeline_v4 import ReviewPipelineV4
import os

pipeline = ReviewPipelineV4()
result = pipeline.run('你的论文.pdf')

os.makedirs('output', exist_ok=True)
pipeline.save_outputs(result, 'output', '论文评审')
print('评审Prompt已保存')
"
```

### 4. LLM评价

1. 查看 `output/论文评审_评价Prompt.md`
2. 将内容发送给 LLM（如 ChatGPT、Claude）
3. 获取 LLM 返回的 JSON 评价结果

### 5. 生成最终报告

```python
# 继续上面的Python环境，粘贴LLM返回的JSON
llm_json = '''粘贴JSON'''
report = pipeline.generate_report(result, llm_json)
print(report)
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
