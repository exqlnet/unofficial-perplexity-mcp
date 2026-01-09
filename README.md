# Perplexity Unofficial MCP（基于 Cookies）

> 非官方实现：本项目通过浏览器 Cookies 调用 Perplexity 的 Web 接口，**稳定性与合规性不做保证**。请确保你的使用方式符合你所在组织的安全要求与 Perplexity 的服务条款。

本项目目标是把非官方 `perplexity-ai`（Python SDK，Cookies 方式）包装成一个 **MCP STDIO Server**，并提供 **`npx` 启动方式**，让 MCP 客户端（Claude Desktop / Cursor / VS Code 等）能像使用官方 Perplexity MCP 一样使用它。

## 你会得到什么

- 一个 **Python MCP Server**（STDIO + JSON-RPC 2.0），工具命名对齐官方：
  - `perplexity_ask`
  - `perplexity_research`
  - `perplexity_reason`
  - `perplexity_search`
- 一个 **npx 启动器**：`perplexity-unofficial-mcp`（Node 只负责启动 uv + Python，并透传 stdio）
- 一份可直接用于 MCP 客户端的**快速配置 JSON**

## 前置条件

- Node.js >= 18（用于 `npx` 启动）
- Python >= 3.10
- `uv` 已安装（https://docs.astral.sh/uv/）
- 非官方 SDK 依赖：
  - 默认通过 `pyproject.toml` 里的 **git pin 依赖**安装（见 `perplexity-api @ git+https://...@<commit>`）
  - 因此运行环境通常需要可用的 `git` 与网络访问（受限网络环境可考虑自行改为 vendoring）
- 你已在浏览器登录 Perplexity，并能获取 Cookies

> 重要：STDIO 模式下 stdout 只能输出 MCP 协议消息。本项目所有日志都输出到 stderr，启动器使用 `uv -q` 尽量抑制 uv 自身输出。

## Cookies 获取与配置

### 获取 Cookies（建议方式）

1. 在浏览器登录 `perplexity.ai`
2. 打开开发者工具 → Application/Storage → Cookies → `https://www.perplexity.ai`
3. 找到并复制你当前会话的 Cookies（常见包含）：
   - `next-auth.csrf-token`
   - `next-auth.session-token`

### 通过 JSON 传入 Cookies（已确认方式）

本项目默认使用环境变量 `PERPLEXITY_COOKIES_JSON` 注入 Cookies，格式为 JSON 字符串：

```json
{"next-auth.csrf-token":"<你的值>","next-auth.session-token":"<你的值>"}
```

注意：在 MCP 客户端配置文件（JSON）里写环境变量时，字符串内部的引号需要转义（见下方示例）。

可选（兼容）：如果你不想在配置里写长字符串，也可用 `PERPLEXITY_COOKIES_PATH` 指向一个 JSON 文件（内容同上）。

## npx 启动方式

### 发布到 npm 后使用（推荐）

发布成功后可直接使用：

- `npx -y --package @exqlnet/unofficial-perplexity-mcp perplexity-unofficial-mcp`

> 如果你的 MCP 客户端对 stdout 噪音非常敏感，可尝试将 `-y` 改为 `-yq`（更安静）。

### 本地目录包使用（开发调试）

在本地开发阶段，你也可以通过 `npx --package file:<ABS_PATH_TO_REPO>` 运行本地包（见下方配置示例）。

## MCP 快速配置（JSON）

以下示例中请将 `<ABS_PATH_TO_REPO>` 替换为本仓库 `unofficial-perplexity-mcp/` 的**绝对路径**。

### Cursor / Claude Desktop / Windsurf（mcpServers 格式）

#### 方式 A：使用已发布的 npm 包（一键使用）

```json
{
  "mcpServers": {
    "perplexity_unofficial": {
      "command": "npx",
      "args": ["-y", "--package", "@exqlnet/unofficial-perplexity-mcp", "perplexity-unofficial-mcp"],
      "env": {
        "PERPLEXITY_COOKIES_JSON": "{\"next-auth.csrf-token\":\"<csrf>\",\"next-auth.session-token\":\"<session>\"}"
      }
    }
  }
}
```

#### 方式 B：使用本地目录包（开发调试）

```json
{
  "mcpServers": {
    "perplexity_unofficial": {
      "command": "npx",
      "args": [
        "-y",
        "--package",
        "file:<ABS_PATH_TO_REPO>",
        "perplexity-unofficial-mcp"
      ],
      "env": {
        "PERPLEXITY_COOKIES_JSON": "{\"next-auth.csrf-token\":\"<csrf>\",\"next-auth.session-token\":\"<session>\"}"
      }
    }
  }
}
```

### VS Code（.vscode/mcp.json，servers 格式）

#### 方式 A：使用已发布的 npm 包（一键使用）

```json
{
  "servers": {
    "perplexity_unofficial": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "--package", "@exqlnet/unofficial-perplexity-mcp", "perplexity-unofficial-mcp"],
      "env": {
        "PERPLEXITY_COOKIES_JSON": "{\"next-auth.csrf-token\":\"<csrf>\",\"next-auth.session-token\":\"<session>\"}"
      }
    }
  }
}
```

#### 方式 B：使用本地目录包（开发调试）

```json
{
  "servers": {
    "perplexity_unofficial": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "--package",
        "file:<ABS_PATH_TO_REPO>",
        "perplexity-unofficial-mcp"
      ],
      "env": {
        "PERPLEXITY_COOKIES_JSON": "{\"next-auth.csrf-token\":\"<csrf>\",\"next-auth.session-token\":\"<session>\"}"
      }
    }
  }
}
```

## 工具说明（与官方对齐）

### perplexity_ask

- 入参：`messages: [{ role, content }, ...]`
- 行为：默认映射为非官方 SDK 的 `mode="pro"`（更接近官方 `sonar-pro` 的语义）
- 出参：`content`（文本）+ `structuredContent.response`（文本）+ 可选 `structuredContent.chunks`

### perplexity_research

- 入参：`messages`，可选 `strip_thinking`
- 行为：映射为 `mode="deep research"`

### perplexity_reason

- 入参：`messages`，可选 `strip_thinking`
- 行为：映射为 `mode="reasoning"`

### perplexity_search

- 入参：`query`（并兼容官方字段 `max_results/max_tokens_per_page/country`，当前实现会忽略这些字段）
- 行为：当前实现返回“回答文本”（并尽量在 `structuredContent.chunks` 附带结构化片段）

> 说明：官方 `perplexity_search` 语义是“返回搜索结果列表”；非官方 SDK 不一定稳定提供同等结构，因此本实现优先保证可用性与对齐接口形状。

## 排错

- 启动报错 `未找到 uv`：安装 uv 后重试，或设置 `UV_BIN` 指向 uv 的可执行文件路径。
- 提示 Cookies 无效/请求失败：通常是会话过期，重新获取 Cookies 并更新 `PERPLEXITY_COOKIES_JSON`。
- MCP 客户端初始化失败：检查是否有任何非协议输出写入 stdout；本项目日志写入 stderr，且启动器使用 `uv -q`，仍失败时请检查你的外层启动命令是否会向 stdout 输出额外内容。

## 维护者：发布到 npm（GitHub Actions）

本仓库使用 tag 触发发布：推送 `vX.Y.Z` 后，GitHub Actions 会自动 `npm publish`。

### 必需条件

- GitHub 仓库已配置 Secret：`NPM_TOKEN`
- `NPM_TOKEN` 必须满足 npm 的 2FA 策略要求：
  - 如果你的账号/组织启用了“发布必须 2FA”，请使用 **Automation token**，或 **Granular access token** 并启用“bypass 2FA”权限。
  - 否则 Actions 会报错：`E403 ... Two-factor authentication ... bypass 2fa enabled is required`

### 发布步骤

1. 同步版本号（必须一致）：
   - `package.json`
   - `pyproject.toml`
   - `src/perplexity_unofficial_mcp/version.py`
2. 合并到 `main` 后创建并推送 tag：`vX.Y.Z`
3. 在 GitHub Actions 查看 `Release` 工作流是否成功

## 开发说明

### 直接运行（不走 npx）

在仓库目录下：

- 使用 `PYTHONPATH=src python3 -m perplexity_unofficial_mcp.cli`（适合不安装依赖时做协议层开发）
- 使用 `uv run perplexity-unofficial-mcp`（会按 `pyproject.toml` 安装依赖）

## 安全提示

- 不要把真实 Cookies 提交到 git、截图或粘贴到公开渠道。
- 建议通过密钥管理（或本机环境变量注入）提供 `PERPLEXITY_COOKIES_JSON`。
