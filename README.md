# CS PhD Research Agent 🔬

自动化深度调研 Agent —— 针对 CS 等顶尖学术项目申请，帮你从信息碎片中找到最适合的教授和实验室。

申请者在寻找合适的高校（MIT、UC Berkeley 等）和研究实验室时，信息极度碎片化。人工跨越各个院系官网、教授主页及最新论文库去提取录取偏好、研究方向匹配度和近期 Funding 状况，耗时巨大且容易遗漏核心信息。

## 功能

- **教授发现** — 给定目标学校和细分方向，自动搜索相关教授及其主页
- **论文挖掘** — 抓取教授近三年主要论文，提取技术栈
- **实验室趋势分析** — 评估实验室研究方向和 Funding 状况
- **匹配评分** — 解析申请人简历，与教授研究方向做多维度技术匹配打分
- **套磁信生成** — 自动撰写高度个性化的中英双语套磁信草稿
- **结构化报告** — 输出 Markdown 报告 + JSON 数据

## 快速开始

```bash
# 到项目根目录
cd cs-phd-agent/

# 安装依赖
pip install -e .

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入 TAVILY_API_KEY 和 ANTHROPIC_API_KEY

# 运行
cs-phd-agent Stanford MIT --area "natural language processing" --resume ./cv.pdf
```

## 使用示例

```bash
# 带简历（调研 + 匹配评分 + 套磁信）
cs-phd-agent Stanford MIT --area NLP --resume ./cv.pdf

# 仅调研（不评分，不生成套磁信）
cs-phd-agent "UC Berkeley" --area "ML systems"

# 深度模式（更多 Tavily 调用，调研更细致）
cs-phd-agent CMU --area "computer vision" --deep

# 指定输出目录
cs-phd-agent MIT --area robotics --resume ./cv.pdf --output ./my_reports
```

## 架构

```
User Input (universities, area, resume)
    │
    ▼
┌──────────────┐    ┌──────────────────────┐
│ Resume       │    │  Pipeline:            │
│ Parser       │    │  1. Parse resume      │
│ (pdfplumber) │    │  2. Web research      │
└──────┬───────┘    │  3. Claude analysis   │
       │            │  4. Report assembly   │
       ▼            └──────────────────────┘
┌──────────────┐             │
│ Web Research │             ▼
│ (Tavily SDK) │    ┌────────────────┐
│ search→extract│    │  Output:       │
│ →research    │    │  report_*.md   │
└──────┬───────┘    │  report_*.json │
       │            └────────────────┘
       ▼
┌──────────────┐
│ Claude       │
│ 3-step Chain │
│ Extract→     │
│ Score→Email  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Report       │
│ Render       │
│ (Jinja2)     │
└──────────────┘
```

## 项目结构（自项目根目录）

```
cs-phd-agent/
├── pyproject.toml              # 依赖和 CLI 入口
├── .env.example                # 环境变量模板
└── src/cs_phd_agent/
    ├── README.md               # 本文件
    ├── models.py               # Pydantic 数据模型
    ├── config.py               # 环境变量配置
    ├── resume_parser.py        # PDF 简历解析
    ├── researcher.py           # Tavily 网络调研
    ├── analyzer.py             # Claude 推理链
    ├── main.py                 # 管道编排
    ├── report.py               # 报告渲染
    ├── cli.py                  # CLI 入口
    └── templates/
        └── report.md.j2        # Markdown 模板
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `TAVILY_API_KEY` | 是 | Tavily 搜索 API |
| `ANTHROPIC_API_KEY` | 是 | Anthropic API |
| `ANTHROPIC_BASE_URL` | 否 | 自定义 API 地址，默认用 Anthropic |
| `ANTHROPIC_MODEL` | 否 | 模型名，默认 `claude-sonnet-4-20250514` |
| `TOP_K_PROFESSORS` | 否 | 每校最多调研教授数，默认 5 |

## 依赖

- Python ≥ 3.11
- `anthropic` — Claude API
- `tavily-python` — 网络搜索
- `pydantic` — 数据模型
- `pdfplumber` — PDF 解析
- `click` / `rich` — CLI
- `jinja2` — 报告模板
