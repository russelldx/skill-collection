# MCP Server 配置指南

Skill 是流程说明，MCP 和 CLI 是执行接口。仓库中的 [.mcp.json](./.mcp.json) 只提供 Firecrawl 与 Chrome DevTools 的项目配置示例，不自动完成安装、登录或授权，也不验证你当前会话中同名 MCP 的来源。

## 总览

| 能力 | 使用方式 | 涉及技能 |
|------|----------|----------|
| Firecrawl | CLI 为本仓库主要说明方式，MCP 可选；服务认证和额度按当前账户检查 | 10 个 `firecrawl*` 技能 |
| 浏览器控制 | Chrome DevTools MCP；连接现有浏览器和独立 profile 是不同模式 | 可供 `course-assignment` 等流程选用 |
| 本机 CDP / 书签 / 历史 | `web-access` 自带 Node.js CDP Proxy，不要求 Chrome DevTools MCP | `web-access` |
| 持久记忆 / 结构化探索 | 官方 claude-mem 插件及其 MCP，不能使用虚构 npm 包代替 | 3 个活动 `claude-mem-*` 技能 |

只配置当前任务需要的服务。修改客户端配置、安装插件或全局包、登录账户均须授权；不要把密钥直接写进版本控制文件。

## Firecrawl

仓库包含 `firecrawl`、`firecrawl-agent`、`firecrawl-crawl`、`firecrawl-download`、`firecrawl-interact`、`firecrawl-map`、`firecrawl-parse`、`firecrawl-scrape`、`firecrawl-build-interact`、`firecrawl-build-onboarding`，共 **10 个**。

### CLI 路线

确认用户同意全局安装后，官方 CLI 的安装命令为：

```bash
npm install -g firecrawl-cli@latest
firecrawl login --browser
firecrawl --status
```

CLI 不随技能目录捆绑。登录操作由用户在浏览器中完成；`--status` 只验证 CLI 的状态，不是 MCP 验证。不要为了设置 CLI 顺带安装整个技能集合或更改其他客户端配置。

### MCP 路线

项目示例：

```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp@latest"],
      "env": { "FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}" }
    }
  }
}
```

`FIRECRAWL_API_KEY` 由客户端支持的安全环境变量或凭据配置提供。`${...}` 的展开方式取决于客户端，不可把这个 JSON 原样推广到所有宿主；不支持时按宿主文档配置，不在仓库写真实值。

MCP 验证分三步：确认服务已连接 → 确认工具列表存在 → 对用户允许的公开页面进行一次只读调用。搜索或抓取成功不能证明 `interact` 的点击、登录、填表已经验证。

Firecrawl `interact` 支持登录流程和 profile 持久化，但不会自动继承用户本机浏览器登录态。`parse` 在托管模式下会上传本地文件并可能消耗额度，须事先确认文件范围与上传授权；敏感本地文档优先使用本地工具。

## Chrome DevTools MCP

正确的 npm 包是 **`chrome-devtools-mcp`**，不是 `@anthropic-ai/chrome-devtools-mcp`。该 MCP 需要配置，不能假定已被宿主内置。

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

默认启动的独立浏览器 profile 不自动拥有日常登录态。需要连接已有 Chrome 时，可在用户授权后选择一种方式：

- `--autoConnect`：官方文档要求 Chrome 144+，用户先启动 Chrome、启用远程调试并允许连接；连接的是浏览器选定的默认 profile。
- `--browser-url=http://127.0.0.1:9222`：仅连接用户已明确开放且确认归属的调试端点；实际端口以环境为准，不擅自启动、关闭或替换日常浏览器。

通过 MCP 列出页面，在自己创建的测试标签页完成读取/截图，再关闭该标签页。不要操作或关闭用户原有页面。若出现 profile 占用，先确定归属，不能直接杀浏览器或删除锁文件。

## web-access 不需要此 MCP

`web-access` 自带本地 CDP Proxy，保留本机登录态路线、书签/历史检索和站点经验。需要 Node.js 22+；查询 History 数据库另需 sqlite3 CLI。浏览器调试授权、站点风控和操作权限仍须独立确认。

显式指定浏览器时的检测失败，不等于所有 CDP 路线不可用；按脚本反馈核对 profile、调试端口与选择方式，不在未获授权时更改浏览器偏好。

## claude-mem

`@anthropic-ai/claude-mem` 不是有效安装入口，因此没有放进通用 `.mcp.json`。

### Claude Code

经用户授权后，在支持插件的 Claude Code 中执行官方命令：

```text
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```

插件安装可能涉及 worker、hooks 和持久记录，安装前说明影响，安装后验证实际启用状态。

### 其他 MCP 客户端

使用官方安装产物中的 Node 入口 `plugin/scripts/mcp-server.cjs`。**先找到并确认本机实际文件路径和 worker 状态，再添加配置**；不要猜测用户名、安装目录或复制其他机器的绝对路径。

```json
{
  "mcpServers": {
    "mcp-search": {
      "command": "node",
      "args": ["<已核实的绝对路径>/plugin/scripts/mcp-server.cjs"]
    }
  }
}
```

上面的路径是占位符，不能直接运行。MCP 服务能启动也不保证当前版本提供所有 AST 或语料库工具；分别验证 `mem-search`、`smart-explore`、`knowledge-agent` 所需工具。全文阅读模式已并入 `smart-explore`，不再安装独立 `learn-codebase` 入口。

## 跨客户端适配

Claude Code、Qoder、Cursor、Codex、Gemini CLI 等宿主应分别按其当前文档配置 MCP。不要假定它们都读取项目 `.mcp.json`、都支持相同环境变量插值或工具名称，也不要笼统宣称某客户端不可用。Chrome DevTools 官方文档包含 Gemini CLI 配置示例。

Windows 环境下，若客户端不能直接解析 `npx`，按该客户端文档使用命令包装或可执行文件路径；不要在没有错误证据时修改全局 PATH 或系统设置。

## 官方资料

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [连接已有 Chrome](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md)
- [Firecrawl CLI](https://github.com/firecrawl/cli)
- [claude-mem](https://github.com/thedotmack/claude-mem)

依赖版本、认证能力和客户端格式可能变化；这些说明不替代目标环境中的实际连接与功能验证。
