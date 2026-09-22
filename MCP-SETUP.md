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

### Qoder CLI 与 IDE 的区别（2026-09-22 核对）

当前 CLI 官方文档列出的覆盖顺序为：用户 `~/.qoder/settings.json` → 项目 `.qoder/settings.json` → 项目 `.mcp.json` → 项目 `.qoder/settings.local.json` → 命令行配置。同名服务会被后项覆盖，插件也可提供服务；项目配置需要批准。`~/.qoder/mcp.json` 不在该 CLI 文档的发现列表中。

Qoder CLI 1.0.17 的发布说明明确修复 MCP `${VAR}` 展开；本机检查版本为 1.1.60，但进程中没有 `FIRECRAWL_API_KEY`。占位符不能代替凭据。IDE 文档仅确认 Settings → MCP → My Servers 的配置入口，未证明它会读取本仓库文件或采用相同插值规则。

Firecrawl 官方 Windows 说明使用已定位的 `npx.cmd`；Chrome DevTools 故障排查提供 `cmd /c npx` 包装。Node 的 `.cmd` 启动限制意味着仅换扩展名并非通用修复。按宿主验证，不自动更改 PATH、用户设置或客户端权限。`qodercli mcp list`、`/mcp` 可检查配置和连接，但原始输出未经保证脱敏，不能直接贴入报告。

## 可复现 smoke 检查

`mcp-smoke.py` 需要 Python 3.11+ 和已有 MCP SDK（本轮为 1.27.1），默认只预检指定配置中的一个服务，不安装依赖、不读取用户配置。只有 `--connect` 才启动该服务或连接指定端点；这不是服务代码沙箱，执行前仍须审阅来源。

```bash
python -B mcp-smoke.py --config .mcp.json --server firecrawl
python -B mcp-smoke.py --config .mcp.json --server chrome-devtools
```

安全检查器拒绝 `npx/npm/uvx` 和 shell/batch 启动器，避免隐式下载；因此示例中的 `npx` 会得到 `unsafe_launcher`，这是检查器策略，不是已经证实 Qoder 无法启动。要检验已有安装，显式提供 `--command` 和完整 `--command-args` JSON 数组（例如已核实的 Node 可执行文件及服务 JS 入口），再加 `--connect --require-tool list_pages`。不要照抄其他机器的缓存路径。

协议检查包含 initialize、分页工具清单、结构性 schema 检查、必需工具、有限超时和清理；不是完整 JSON Schema 验证。可选真实调用仅允许 `--call list_pages --arguments '{}'` 或 `list_corpora`，须同时指定 `--connect`。返回结果检查 `isError` 和错误文本，只输出安全元数据；不输出工具内容、令牌、headers 或私有端点。单次 `${NAME}` 展开由检查器完成，不能冒充宿主的插值验证。

启动覆盖的结果标记为 `project_config_with_launch_override`，不能据此宣称原始 `npx` 配置已在宿主加载。测试命令：

```bash
python -B -W error -m unittest discover -s tests -p test_mcp_smoke.py -v
```

### 本轮实测结果

| 证据链 | 结果 | 限制 |
|---|---|---|
| 当前 Chrome DevTools MCP | 列页、自建空白页写入测试文字、读取、截图、关闭均成功 | 原有页面未操作；不等于 web-access Proxy 实测 |
| 已安装 Chrome MCP 1.9.0 + Python SDK | 显式 Node 入口 initialize、29 个工具 schema、必需 `list_pages`、清理通过 | 关闭此次进程的使用统计与 CrUX；未运行 npx，未验证原样配置发现 |
| Firecrawl CLI 1.16.0 | 认证、额度检查、一次官方 MCP 文档抓取成功，退出码 0 | 消耗额度的单页操作；不代表批量抓取或交互已验收 |
| 当前 Firecrawl MCP | 额度查询返回 HTTP 401 | 未继续付费抓取，需用户核对该服务认证；未转移 CLI 凭据 |
| 仓库 Firecrawl 示例 | `missing_environment` | 当前进程无 API Key，未改本机配置 |
| 当前 claude-mem | 哨兵 search / list_corpora 均 `fetch failed`；小型 Python 源文件 outline 无法解析 | 工具可见不等于 worker/AST 可用；未创建语料库、prime 或写入记忆 |

## 官方资料

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [连接已有 Chrome](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md)
- [Firecrawl CLI](https://github.com/firecrawl/cli)
- [claude-mem](https://github.com/thedotmack/claude-mem)
- [Qoder CLI MCP 配置](https://docs.qoder.com/cli/mcp-reference.md)
- [Qoder IDE MCP](https://docs.qoder.com/user-guide/chat/model-context-protocol.md)
- [Qoder CLI 发布说明](https://docs.qoder.com/release-notes/qoder-cli.md)
- [Firecrawl 本地 MCP](https://docs.firecrawl.dev/mcp-server/local)
- [Chrome DevTools 启动排障](https://raw.githubusercontent.com/ChromeDevTools/chrome-devtools-mcp/main/docs/troubleshooting.md)
- [Node.js Windows 子进程限制](https://nodejs.org/api/child_process.html#spawning-bat-and-cmd-files-on-windows)

依赖版本、认证能力和客户端格式可能变化；这些说明不替代目标环境中的实际连接与功能验证。
