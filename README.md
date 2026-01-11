# Perplexity Unofficial MCP（基于 Cookies）

> 非官方实现：本项目通过浏览器 Cookies 调用 Perplexity 的 Web 接口，**稳定性与合规性不做保证**。请确保你的使用方式符合你所在组织的安全要求与 Perplexity 的服务条款。

本项目目标是把非官方 `perplexity-ai`（Python SDK，Cookies 方式）包装成一个 **MCP STDIO Server**，让 MCP 客户端（Claude Desktop / Cursor / VS Code 等）能像使用官方 Perplexity MCP 一样使用它。

## 你会得到什么

- 一个 **Python MCP Server**（STDIO + JSON-RPC 2.0），工具命名对齐官方：
  - `perplexity_ask`
  - `perplexity_research`
  - `perplexity_reason`
  - `perplexity_search`
- 一份可直接用于 MCP 客户端的**快速配置 JSON**

## 前置条件

- Python >= 3.10
- `uv` 已安装（https://docs.astral.sh/uv/）
- 非官方 SDK 依赖：
  - 默认通过 `pyproject.toml` 里的 **git pin 依赖**安装（见 `perplexity-api @ git+https://...@<commit>`）
  - 因此运行环境通常需要可用的 `git` 与网络访问（受限网络环境可考虑自行改为 vendoring）
- 你已在浏览器登录 Perplexity，并能获取 Cookies

> 重要：STDIO 模式下 stdout 只能输出 MCP 协议消息。本项目所有日志都输出到 stderr。建议使用 `uv -q` 并设置 `UV_NO_PROGRESS=1` 来尽量抑制 uv 自身输出。

## Cookies 获取与配置

### 获取 Cookies（建议方式）

1. 在浏览器登录 `perplexity.ai`
2. 打开开发者工具 → Application/Storage → Cookies → `https://www.perplexity.ai`
3. 找到并复制你当前会话的 Cookies（常见包含）：
   - `next-auth.csrf-token`
   - `next-auth.session-token`

### 通过两个环境变量传入 Cookies（推荐方式）

本项目默认使用两个环境变量注入 Cookies：

- `PERPLEXITY_CSRF_TOKEN`：对应 `next-auth.csrf-token`
- `PERPLEXITY_SESSION_TOKEN`：对应 `next-auth.session-token`

注意：不要把 token 写进仓库或公开渠道；建议通过本机环境变量或密钥管理注入。

## 安装与启动（推荐：uv）

本项目不再提供或依赖 `npx` 启动方式。推荐使用 `uv` 直接运行（由 `uv` 负责依赖解析与运行）。

如果你需要把它接入 MCP 客户端，推荐使用“从 GitHub 仓库地址启动”的形式（无需本地 clone）。

## MCP 快速配置（JSON）

以下示例默认使用主分支 `main`。生产/团队环境建议 pin 到 tag 或 commit 以保证可复现。

### Cursor / Claude Desktop / Windsurf（mcpServers 格式）

#### 方式：使用 uv 从 GitHub 启动（推荐）

```json
{
  "mcpServers": {
    "perplexity_unofficial": {
      "command": "uv",
      "args": [
        "-q",
        "tool",
        "run",
        "--from",
        "git+https://github.com/exqlnet/unofficial-perplexity-mcp.git@main",
        "perplexity-unofficial-mcp"
      ],
      "env": {
        "PERPLEXITY_CSRF_TOKEN": "<csrf>",
        "PERPLEXITY_SESSION_TOKEN": "<session>",
        "UV_NO_PROGRESS": "1",
        "UV_COLOR": "never"
      }
    }
  }
}
```

### VS Code（.vscode/mcp.json，servers 格式）

#### 方式：使用 uv 从 GitHub 启动（推荐）

```json
{
  "servers": {
    "perplexity_unofficial": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "-q",
        "tool",
        "run",
        "--from",
        "git+https://github.com/exqlnet/unofficial-perplexity-mcp.git@main",
        "perplexity-unofficial-mcp"
      ],
      "env": {
        "PERPLEXITY_CSRF_TOKEN": "<csrf>",
        "PERPLEXITY_SESSION_TOKEN": "<session>",
        "UV_NO_PROGRESS": "1",
        "UV_COLOR": "never"
      }
    }
  }
}
```

## 工具说明（与官方对齐）

### perplexity_ask

- 入参：`query`（字符串），可选 `backend_uuid`
- 行为：
  - 为避免调用方误传导致行为不可预测：本 MCP **已禁用外部 `mode` / `model` 入参**
  - 服务端会按内部默认策略选择模式（例如有 Cookies 时倾向使用 pro，并默认使用 `gpt-5.2`）
  - 请避免频繁调用；尽量将多个子问题合并到一次 query / 一次 perplexity_search 中查清楚
- 出参：`content`（文本）+ `structuredContent.response`（文本）+ 可选 `structuredContent.chunks` + 可选 `structuredContent.backend_uuid`

#### 续问（同一对话线程继续问）

- 每次调用若上游返回 `backend_uuid`，本 MCP 会在 `structuredContent.backend_uuid` 回传。
- 下一次调用时，把该值作为入参 `backend_uuid` 传回，即可让 Perplexity 以同一对话上下文续问。
- 注意：该能力依赖网页端私有接口与服务端策略，`backend_uuid` 可能缺失、过期或被忽略；本项目不保证稳定。

### perplexity_research

- 入参：`query`（字符串），可选 `backend_uuid`、`strip_thinking`
- 行为：
  - 默认 deep research（专用语义）
  - 本 MCP 已禁用外部 `mode` / `model` 入参
  - 注意：这是重型调用，耗时更长；仅在必要时使用，优先 ask/search

### perplexity_reason

- 入参：`query`（字符串），可选 `backend_uuid`、`strip_thinking`
- 行为：
  - 默认 reasoning（专用语义）
  - 本 MCP 已禁用外部 `mode` / `model` 入参

### perplexity_search

- 入参：`query`（字符串），可选 `backend_uuid`
- 行为：
  - 当前实现返回“回答文本”（并尽量在 `structuredContent.chunks` 附带结构化片段）
  - 本 MCP 已禁用外部 `mode` / `model` 入参；服务端会按内部默认策略选择模式
  - 请避免频繁调用；尽量把要查的点写进一次 query（例如用编号列出多个子问题），一次 search 查清楚

> 说明：官方 `perplexity_search` 语义是“返回搜索结果列表”；非官方 SDK 不一定稳定提供同等结构，因此本实现优先保证可用性与对齐接口形状。

> 重要：本 MCP 不再支持 `messages[]` 入参；如果你的调用方仍传 `messages`，会返回工具级错误并提示改用 `query`。
> 重要：本 MCP 不再支持 `mode` / `model` 入参；如果你的调用方仍传 `mode` / `model`，会返回工具级错误并提示移除该字段。

## 排错

- 启动报错 `未找到 uv`：安装 uv 后重试。
- 提示 Cookies 无效/请求失败：通常是会话过期，重新获取 Cookies 并更新 `PERPLEXITY_CSRF_TOKEN` / `PERPLEXITY_SESSION_TOKEN`。
- MCP 客户端初始化失败：检查是否有任何非协议输出写入 stdout；本项目日志写入 stderr，且推荐使用 `uv -q` 并设置 `UV_NO_PROGRESS=1`，仍失败时请检查你的外层启动命令是否会向 stdout 输出额外内容。
- GitHub 拉取失败：检查网络与 git 可用性；受限环境可改为本地 clone 后再使用本地方式启动（见下文开发说明）。

## 开发说明

### 直接运行（不走 uv）

在仓库目录下：

- 使用 `PYTHONPATH=src python3 -m perplexity_unofficial_mcp.cli`（适合不安装依赖时做协议层开发）
- 使用 `uv -q run --no-editable perplexity-unofficial-mcp`（会按 `pyproject.toml` 安装依赖）

## 安全提示

- 不要把真实 Cookies 提交到 git、截图或粘贴到公开渠道。
- 建议通过密钥管理（或本机环境变量注入）提供 `PERPLEXITY_CSRF_TOKEN` / `PERPLEXITY_SESSION_TOKEN`。
