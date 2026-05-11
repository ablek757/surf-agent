# surf-agent 🏄

> **中文** · [English](./README.en.md)

> **用自然语言驱动一个真实的浏览器。** 你告诉 `surf-agent` 想做什么 ——
> *"找一下下周二 SFO 到 NRT 最便宜的航班"*、
> *"帮我报名那场 talk"*、*"总结一下我的 GitHub 通知"* ——
> LLM Agent 会感知页面、决定下一步点击,通过 Playwright 操作浏览器,
> 直到任务完成。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## ✨ 特性

- **自然语言任务。** 不用 selector,不用 XPath,不用 CSS。描述目标即可。
- **混合感知。** 带编号的 DOM 快照(token 经济)**加上**周期性截图(用于
  布局/视觉推理),让 LLM 兼得两者优点。
- **多种 LLM 后端。** Anthropic Claude、OpenAI(以及 OpenAI 兼容端点)、
  完全本地的 **Ollama** —— 运行时选择。
- **Playwright 驱动。** Chromium / Firefox / WebKit,有头或无头。
- **结构化动作。** 每一轮 LLM 输出一个 typed JSON 动作 ——
  `click`、`type`、`goto`、`scroll`、`wait`、`back`、`screenshot`、`done`。
  在送到浏览器前先用 Pydantic 校验。
- **可组合。** 用 CLI,或在 Python 里 `from surf_agent import SurfAgent`。
- **安全护栏。** 步数硬上限、快照截断、结构化日志。

## 🎯 架构一览

```
                        ┌───────────────────────────┐
   用户任务  ─────────▶│        SurfAgent          │
                        │  (observe → decide → act) │
                        └─────────────┬─────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
    ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
    │ DOM 快照      │         │  LLM provider │         │   Playwright  │
    │ + 截图        │ ───────▶│  (Claude /    │ ───────▶│   浏览器      │
    │ (感知)        │         │   OpenAI /    │         │   (执行)      │
    │               │◀─────── │   Ollama)     │◀─────── │               │
    └───────────────┘         └───────────────┘         └───────────────┘
                                      ▲
                            结构化 JSON 动作 schema
```

每一轮,Agent 会:

1. 把页面快照成一份带编号的可交互元素列表
   (`[0] <button> Sign in`、`[1] <input:text> Search ...`)。
2. 把 DOM(以及每隔几轮的截图)发给 LLM。
3. 收到 `{"thought": "...", "action": {"type": "click", "target_id": 0}}`。
4. 校验动作并通过 Playwright 执行。
5. 重复,直到 LLM 发出 `{"type": "done", "answer": "..."}` 或达到 `max_steps`。

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/ablek757/surf-agent.git
cd surf-agent
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[anthropic]"   # 或 [openai] / [ollama] / [all]
playwright install chromium
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env,填入 ANTHROPIC_API_KEY(或者设置 SURF_AGENT_PROVIDER=ollama)
```

### 3. 运行

```bash
surf-agent run "在 Wikipedia 上搜索 'Playwright (software)',告诉我是谁在维护。" \
    --url https://www.wikipedia.org
```

你会看到浏览器打开,Agent 逐步解说每一步,最后给出答案:

```
✔ Done
Playwright 由 Microsoft 维护。
(7 steps)
```

## 🐍 Python API

```python
import asyncio
from surf_agent import SurfAgent, Config

async def main():
    agent = SurfAgent(Config(provider="anthropic", headless=False))
    result = await agent.run(
        task="在 GitHub 上找到 Playwright 最新的 release,告诉我版本号。",
        start_url="https://github.com/microsoft/playwright/releases",
    )
    print(result.answer)
    print(f"steps: {result.steps_taken}")

asyncio.run(main())
```

## ⚙️ 配置

所有设置都有对应的环境变量(详见 [`.env.example`](.env.example)):

| 设置             | 环境变量                  | 默认值             | 备注                                   |
| ---------------- | ------------------------ | ------------------ | -------------------------------------- |
| Provider         | `SURF_AGENT_PROVIDER`    | `anthropic`        | `anthropic` / `openai` / `ollama`      |
| Model            | `SURF_AGENT_MODEL`       | 各 provider 默认值 | 例如 `claude-opus-4-7`、`gpt-4o`       |
| Browser          | `SURF_AGENT_BROWSER`     | `chromium`         | `chromium` / `firefox` / `webkit`      |
| Headless         | `SURF_AGENT_HEADLESS`    | `false`            | CI 里设成 `true`                       |
| Max steps        | `SURF_AGENT_MAX_STEPS`   | `25`               | 硬安全上限                             |
| Anthropic key    | `ANTHROPIC_API_KEY`      | —                  | 用 Claude 时必填                       |
| OpenAI key       | `OPENAI_API_KEY`         | —                  | 用 OpenAI 时必填                       |
| Ollama host      | `OLLAMA_HOST`            | `localhost:11434`  | 本地模型用                             |

CLI 参数会覆盖环境变量:`--provider`、`--model`、`--headless/--headed`、
`--max-steps`、`--url`。

## 🧠 动作 schema

LLM 被约束成一个小而 typed 的动作词汇 —— 定义在
[`actions.py`](src/surf_agent/actions.py),由 Pydantic 校验。新增一个动作
只需三行改动:定义 Pydantic 模型 → 加入 `Action` union → 在 `ACTION_GRAMMAR`
里写说明。

```jsonc
// LLM 每轮可能返回的响应示例
{"thought": "需要先登录。",         "action": {"type": "click", "target_id": 4}}
{"thought": "搜索这个主题。",       "action": {"type": "type", "target_id": 0, "text": "playwright", "submit": true}}
{"thought": "拿到答案了。",         "action": {"type": "done", "answer": "由 Microsoft 维护。"}}
```

## 🔬 为什么用混合感知

纯截图 Agent 灵活但开销大(vision token),并且在小而密的 UI 上很脆。
纯 DOM Agent 便宜、精准,但对布局、图表、验证码、视觉上下文是瞎的。
**surf-agent 两者都做:**

- DOM 快照**总是**包含 —— `target_id` 就是从这里来的,点击是确定性的。
- 截图在**第 1 步**(初始定位)以及之后**每 4 步**包含一次。LLM 也可以主动用
  `{"type": "screenshot"}` 索要一张。

调节频率:编辑 [`agent.py`](src/surf_agent/agent.py) 里的 `_loop`。

## 🧪 测试

```bash
pip install -e ".[dev]"
pytest -q
```

自带的测试覆盖动作 schema 的解析,不需要浏览器或 API key。
真实的浏览器测试暂不在范围内 —— 欢迎 PR。

## 🗺️ Roadmap

- [ ] Trace + 回放(导出每一组 `(snapshot, action)`)
- [ ] 在多次运行间保留 cookie / 登录态
- [ ] 多 tab 支持
- [ ] 一组任务并行多 agent
- [ ] Anthropic provider 的真正 prompt caching(系统提示已经是常量 ——
      已经接好 `cache_control`,等 prompt 长过 cache 阈值后自动生效)
- [ ] 更多工具:`download_file`、`extract_table`、`select_option`

## ⚠️ 安全与伦理

- **Agent 会照你说的做。** 在你不掌控的网站上,不要在不清楚后果的情况下使唤它
  (购买、账号改动、违反 ToS)。
- **API key 不要进 git。** `.env` 已被 gitignore,用 `.env.example` 作模板。
- **尊重 robots.txt 和速率限制。** 这是研究级工具,不是隐身爬虫。

## 🤝 贡献

欢迎 PR,请:

1. 先开 issue 描述变更。
2. 给 parser / agent 逻辑加测试(可行的话)。
3. 提交前跑一遍 `ruff check .`。

## 📄 License

[MIT](LICENSE) © surf-agent contributors.
