# MCP Server 配置指南

本仓库中部分 skill 依赖 MCP (Model Context Protocol) server。本文档说明每个 MCP server 的用途、安装方式和涉及的 skill。

> **快速路径**：仓库根目录的 `.mcp.json` 已包含所有 MCP server 的声明。Claude Code 打开本仓库时会自动识别。其他 agent 请参考对应文档手动配置。

---

## 总览

| MCP Server | 用途 | 需要 API Key | 涉及的 skill |
|------------|------|:---:|------|
| **firecrawl** | 网页搜索、抓取、爬取 | 是 | firecrawl 全系列（11 个） |
| **chrome-devtools** | 浏览器自动化控制 | 否 | web-access、course-assignment |
| **claude-mem** | 跨会话持久记忆 | 否 | claude-mem 全系列（4 个） |

---

## 1. Firecrawl（网页搜索/抓取）

**用途**：搜索网页、抓取页面内容、爬取整站、结构化数据提取。

**涉及 skill**：
- `firecrawl` — CLI 主 skill
- `firecrawl-agent` — AI 自主研究
- `firecrawl-crawl` — 批量爬取
- `firecrawl-download` — 整站下载
- `firecrawl-interact` — 浏览器交互
- `firecrawl-map` — URL 发现
- `firecrawl-parse` — 文档解析
- `firecrawl-scrape` — 页面抓取
- `firecrawl-build-interact` — 集成开发
- `firecrawl-build-onboarding` — 集成引导

### 安装

**方式一：CLI（推荐，skill 已内置）**

```bash
npx -y firecrawl-cli@latest -y
```

安装后运行 `firecrawl login --browser` 完成认证。

**方式二：MCP Server**

1. 前往 [firecrawl.dev](https://firecrawl.dev) 注册获取 API Key
2. 设置环境变量：
   ```bash
   export FIRECRAWL_API_KEY="fc-xxxxxxxxxxxx"
   ```
3. `.mcp.json` 中已声明配置，Claude Code 会自动读取

### 验证

```bash
firecrawl --status
```

---

## 2. Chrome DevTools（浏览器控制）

**用途**：控制真实 Chrome/Edge 浏览器，执行点击、填写表单、截图、读取动态渲染页面等操作。

**涉及 skill**：
- `web-access` — 通用联网操作（搜索、社交媒体、登录态操作）
- `course-assignment` — 课程作业（学习通等平台操作）

### 安装

Chrome DevTools MCP 通常由 Claude Code 内置提供。如需手动配置：

```bash
npx -y @anthropic-ai/chrome-devtools-mcp@latest
```

确保本地已安装 Chrome 或 Edge 浏览器。

### 验证

在 Claude Code 中执行任意浏览器操作（如截图），确认能正常调用即可。

---

## 3. claude-mem（跨会话记忆）

**用途**：持久化的跨会话记忆存储，支持代码搜索、观察记录、知识语料库。

**涉及 skill**：
- `claude-mem-knowledge-agent` — 知识语料库构建与查询
- `claude-mem-learn-codebase` — 代码库学习
- `claude-mem-mem-search` — 跨会话记忆搜索
- `claude-mem-smart-explore` — 结构化代码探索

### 安装

```bash
npx -y @anthropic-ai/claude-mem@latest
```

### 验证

```bash
# 在 Claude Code 中尝试搜索记忆
# 如果返回结果（即使是空结果），说明配置正确
```

---

## 非 Claude Code Agent 的配置

### Cursor

在 `.cursor/mcp.json` 中添加相同配置：

```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp@latest"],
      "env": {
        "FIRECRAWL_API_KEY": "你的API Key"
      }
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/chrome-devtools-mcp@latest"]
    },
    "claude-mem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/claude-mem@latest"]
    }
  }
}
```

### Codex / Gemini CLI

这些 agent 的 MCP 支持有限。建议：
- **firecrawl**：使用 CLI 方式（`firecrawl` 命令），不依赖 MCP
- **chrome-devtools**：不可用，web-access 和 course-assignment 的浏览器功能降级
- **claude-mem**：不可用，记忆功能降级

### 通用 Agent

仅需 SKILL.md 的 skill（约 40 个）不需要任何 MCP 配置。需要 MCP 的 skill 在 INDEX.md 中标注为 `需MCP`，可根据需要单独配置。

---

## 按需安装

不需要安装所有 MCP server。根据你要使用的 skill 决定：

| 你想用的 skill | 需要安装的 MCP |
|---------------|---------------|
| 文档处理（docx/pdf/pptx/xlsx） | 无 MCP，只需 Node.js/Python |
| 开发流程（superpowers/code-review 等） | 无 MCP |
| 网页搜索/抓取 | firecrawl |
| 浏览器操作/登录 | chrome-devtools |
| 跨会话记忆 | claude-mem |
| PUA 系列 / 写作辅助 | 无 MCP |
