# MCP Server 配置指南

Skill 是流程说明，MCP 和 CLI 是执行接口。仓库中的 [.mcp.json](./.mcp.json) 只提供 Firecrawl 与 Chrome DevTools 的项目配置示例，不自动完成安装、登录或授权，也不验证你当前会话中同名 MCP 的来源。

## 总览

| 能力 | 使用方式 | 涉及技能 |
|------|----------|----------|
| Firecrawl | 本仓库主要介绍 CLI 的用法，MCP 可选；服务认证和额度需按当前账户检查 | 10 个 `firecrawl*` 技能 |
| 浏览器控制 | Chrome DevTools MCP；连接现有浏览器与使用独立 profile 是两种不同模式 | 可供 `course-assignment` 等流程选用 |
| 本机 CDP / 书签 / 历史 | `web-access` 自带 Node.js CDP Proxy，不要求 Chrome DevTools MCP | `web-access` |
| 持久记忆 / 结构化探索 | 使用官方 claude-mem 插件及其 MCP，不能用虚构的 npm 包代替 | 3 个活动 `claude-mem-*` 技能 |
| 数据库操作（可选） | 后端开发有需要时，推荐 [DBX](https://github.com/t8y2/dbx) 及其 MCP 包 `@dbx-app/mcp-server`（README 含中文说明）；连接与权限由 DBX 应用管理，凭据不写入配置文件 | 仓库暂无依赖技能，按需自取 |
| 安全截图与屏幕取字 | 本仓库自带 [`mcps/snipaste-mcp`](./mcps/snipaste-mcp/README.md)。这是本地 Node.js stdio 服务，通过 Snipaste 命令行截图；默认只截目标窗口，桌面截图须显式授权 | 仓库暂无依赖技能，按需自取 |

只配置当前任务需要的服务。修改客户端配置、安装插件或全局包、登录账户都须获得授权；不要把密钥直接写进版本控制文件。

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

`FIRECRAWL_API_KEY` 通过客户端支持的安全环境变量或凭据配置提供。`${...}` 的展开方式取决于客户端，不能假定这个 JSON 在所有宿主中都能原样使用；如果宿主不支持，就按宿主文档配置，不要在仓库中写入真实值。

MCP 验证分三步：确认服务已连接 → 确认工具列表存在 → 对用户允许的公开页面做一次只读调用。搜索或抓取成功，不代表 `interact` 的点击、登录、填表也已通过验证。

Firecrawl `interact` 支持登录流程和 profile 持久化，但不会自动继承用户本机浏览器登录态。`parse` 在托管模式下会上传本地文件，也可能消耗额度，须事先确认文件范围与上传授权；处理敏感本地文档时，优先使用本地工具。

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

默认启动的独立浏览器 profile 不会自动带上日常登录态。需要连接已有 Chrome 时，可在用户授权后选择一种方式：

- `--autoConnect`：官方文档要求 Chrome 144+，用户先启动 Chrome、启用远程调试并允许连接；连接的是浏览器选定的默认 profile。
- `--browser-url=http://127.0.0.1:9222`：仅连接用户已明确开放且确认归属的调试端点；实际端口以环境为准，不擅自启动、关闭或替换日常浏览器。

通过 MCP 列出页面，在自己创建的测试标签页中读取/截图，完成后再关闭该标签页。不要操作或关闭用户原有页面。如果 profile 被占用，先确定是谁在使用，不能直接终止浏览器进程或删除锁文件。

## Snipaste MCP（本仓库自带）

`mcps/snipaste-mcp` 是仓库内唯一自带实现的 MCP 服务，不是第三方包，也不在 `skills/` 同步基线内。它封装了 Snipaste 的命令行参数，提供 `snip_capture`、`snip_view`、`snip_windows`、`snip_ocr`、`snip_status` 五个工具，用来安全截图、读取屏幕文字（PRO）和进行窗口自检。完整说明见 [mcps/snipaste-mcp/README.md](./mcps/snipaste-mcp/README.md)。

**默认安全策略（务必保留）**：截图严禁包含用户桌面与其它隐私窗口。`snip_capture` 默认 `target: "window"`，只截一个经覆盖校验的目标窗口矩形，截完自动还原窗口。`fullscreen`/`active_screen`/`last` 一律拒绝，除非调用方显式传入 `allow_desktop: true`；这个开关仅限用户明确要求桌面截图时使用。没有合适的应用窗口时，用 `snip_view` 打开临时浏览器窗口，渲染后再截图。窗口级校验失败时，宁可不返回图片，也不会降级成整屏截图。窗口控制与 `snip_view` 仅支持 Windows，其它平台会明确报错，提示不支持。

依赖：Snipaste 2.x（便携版即可，不要求在 `PATH` 中）与 Node.js 18+；`snip_view` 需要本机装有 Edge 或 Chrome。安装与配置：

```bash
cd mcps/snipaste-mcp
npm ci            # 依 package-lock.json 安装；node_modules 已被 .gitignore 排除
npm test          # 对真实 Snipaste 跑端到端检查，截图写入临时目录后清理
```

```json
{
  "mcpServers": {
    "snipaste": {
      "command": "node",
      "args": ["<仓库路径>/mcps/snipaste-mcp/src/server.js"]
    }
  }
}
```

定位顺序：`SNIPASTE_PATH` → 常见安装目录 → `PATH` → 上次缓存 → 正在运行的进程 → `Desktop`/`Downloads`/`Documents`/`Programs` 的浅层扫描。首次找到后，会将路径写入用户配置目录，之后冷启动也不用再次扫描。Snipaste 未运行时会自动启动，首次截图约 2.5 s，后续约 0.3 s。

免费版支持哪些功能，以 Snipaste 官方对照表为准：活动窗口截图、阴影、`--block` 与 `-o ocr_clipboard`（文字提取）属于 PRO 功能，免费版既不报错，也不输出结果。其中 `-o ocr_clipboard` 还会让 Snipaste 之后不再响应截图请求，因此 `snip_ocr` 超时后会先重启 Snipaste，再返回明确错误。注册 MCP 和安装依赖都须获得用户授权，配置文件里不要写死他人磁盘路径。

`web-access` 自带本地 CDP Proxy，保留了使用本机登录态的方式、书签/历史检索和站点经验。需要 Node.js 22+；查询 History 数据库另需 sqlite3 CLI。浏览器调试授权、站点风控和操作权限仍须分别确认。

显式指定浏览器后，如果检测失败，并不等于所有 CDP 路线都不可用。应按脚本反馈核对 profile、调试端口与选择方式；未获授权时，不要更改浏览器偏好。

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

使用官方安装文件中的 Node 入口 `plugin/scripts/mcp-server.cjs`。**先找到并确认本机实际文件路径和 worker 状态，再添加配置**；不要猜测用户名、安装目录，也不要复制其他机器的绝对路径。

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

上面的路径是占位符，不能直接运行。即使 MCP 服务能启动，也不保证当前版本提供所有 AST 或语料库工具；需要分别验证 `mem-search`、`smart-explore`、`knowledge-agent` 所需的工具。全文阅读模式已并入 `smart-explore`，不再安装独立 `learn-codebase` 入口。

## 跨客户端适配

Claude Code、Qoder、Cursor、Codex、Gemini CLI 等宿主应分别按其当前文档配置 MCP。不要假定它们都读取项目 `.mcp.json`、都支持相同环境变量插值或工具名称，也不要笼统宣称某客户端不可用。Chrome DevTools 官方文档包含 Gemini CLI 配置示例。

Windows 环境下，若客户端不能直接解析 `npx`，按该客户端文档使用命令包装或可执行文件路径；不要在没有错误证据时修改全局 PATH 或系统设置。

### Qoder CLI 与 IDE 的区别（2026-09-22 核对）

当前 CLI 官方文档列出的覆盖顺序为：用户 `~/.qoder/settings.json` → 项目 `.qoder/settings.json` → 项目 `.mcp.json` → 项目 `.qoder/settings.local.json` → 命令行配置。同名服务会被后项覆盖，插件也可提供服务；项目配置需要批准。`~/.qoder/mcp.json` 不在该 CLI 文档的发现列表中。

Qoder CLI 1.0.17 的发布说明明确指出，已修复 MCP `${VAR}` 展开问题；本机检查时的版本为 1.1.60，但进程中没有 `FIRECRAWL_API_KEY`。占位符不能代替凭据。IDE 文档仅确认了 Settings → MCP → My Servers 这个配置入口，未证明它会读取本仓库文件或采用相同插值规则。

Firecrawl 官方 Windows 说明使用已定位的 `npx.cmd`；Chrome DevTools 故障排查提供了用 `cmd /c npx` 包装命令的方式。Node 对 `.cmd` 的启动有限制，单靠更换扩展名并不能解决所有情况。需要在具体宿主中验证，不自动更改 PATH、用户设置或客户端权限。`qodercli mcp list`、`/mcp` 可检查配置和连接，但原始输出不保证已脱敏，不能直接贴入报告。

## 可复现 smoke 检查

`mcp-smoke.py` 需要 Python 3.11+ 和已有 MCP SDK（本轮为 1.27.1），默认只预检指定配置中的一个服务，不安装依赖，也不读取用户配置。只有指定 `--connect` 时，才会启动该服务或连接指定端点；这个检查器不是服务代码沙箱，执行前仍须审阅来源。

```bash
python -B mcp-smoke.py --config .mcp.json --server firecrawl
python -B mcp-smoke.py --config .mcp.json --server chrome-devtools
```

安全检查器拒绝 `npx/npm/uvx` 和 shell/batch 启动器，以免隐式下载；因此示例中的 `npx` 会得到 `unsafe_launcher`。这是检查器的策略，不能据此认定 Qoder 无法启动该服务。要检验已有安装，需显式提供 `--command` 和完整的 `--command-args` JSON 数组（例如已核实的 Node 可执行文件及服务 JS 入口），再加 `--connect --require-tool list_pages`。不要照抄其他机器的缓存路径。

协议检查包括 initialize、分页获取工具清单、检查 schema 结构和必需工具，并包含有限超时和清理；它不做完整的 JSON Schema 验证。可选的真实调用仅允许 `--call list_pages --arguments '{}'` 或 `list_corpora`，须同时指定 `--connect`。检查器会核对返回结果中的 `isError` 和错误文本，只输出安全元数据；不输出工具内容、令牌、headers 或私有端点。检查器只做一次 `${NAME}` 展开，不能把它当作对宿主插值的验证。

覆盖启动配置后的结果标记为 `project_config_with_launch_override`，不能据此宣称原始 `npx` 配置已在宿主加载。测试命令：

```bash
python -B -W error -m unittest discover -s tests -p test_mcp_smoke.py -v
```

### 本轮实测结果

| 证据链 | 结果 | 限制 |
|---|---|---|
| 当前 Chrome DevTools MCP | 列出页面、在自建空白页写入测试文字、读取、截图、关闭均成功 | 未操作原有页面；这不等于已经实测 web-access Proxy |
| 已安装 Chrome MCP 1.9.0 + Python SDK | 使用显式 Node 入口，initialize、29 个工具 schema、必需 `list_pages` 和清理均通过检查 | 关闭此次进程的使用统计与 CrUX；未运行 npx，未验证宿主能否发现原样配置 |
| Firecrawl CLI 1.16.0 | 认证、额度检查和一次官方 MCP 文档抓取均成功，退出码 0 | 这是消耗额度的单页操作；不代表批量抓取或交互已验收 |
| 当前 Firecrawl MCP | 原先查询额度时返回 HTTP 401；2026-09-22 用户提供 Key 并设置用户级 `FIRECRAWL_API_KEY` 后，隔离安装 firecrawl-mcp 3.25.2 并实测：initialize 成功、29 个工具、`firecrawl_credit_usage` 返回 999/1000（isError=false） | 客户端需重启才能继承新环境变量（2026-09-22 晚复核：用户级变量已设置，但当前进程树仍未继承，仍返回 401）；未做付费抓取，scrape/search/interact 各自功能仍未逐项验收 |
| 仓库 Firecrawl 示例 | 环境变量就绪后，预检结果从 `missing_environment` 变为 `unsafe_launcher`（检查器按策略拒绝 npx，并非宿主启动缺陷）；移除变量后复现 `missing_environment` | 仅证明示例中的 `${FIRECRAWL_API_KEY}` 展开可解析，未证明本客户端已加载该示例 |
| 当前 claude-mem（2026-09-22 晚修复后） | worker 健康端点正常，自动启动链路也已恢复（停止 worker 后，全新 MCP 进程自动拉起了 worker，日志为 `Worker started successfully`）；`list_corpora` 正常返回；`smart_outline`（含非 ASCII 路径）、`smart_search`（扫描 469 文件/6416 符号）、`smart_unfold` 均返回正确结果 | 修复前启动的 MCP 进程在进程内缓存了失败的解析结果，AST 工具需重启客户端或开启新会话后才能生效；记忆库为空，检索无结果符合预期 |

阻塞根因与处置（2026-09-22 诊断与修复，含晚间 claude-mem 修复）：

- Firecrawl MCP 401 根因：用户级 `~/.qoder/settings.json` 中该条目为 `npx -y firecrawl-mcp@latest`，未配置环境变量（env 键为空），且用户环境中不存在 `FIRECRAWL_API_KEY`，因此服务端调用时没有凭据。**已修复**：将 Key 写入用户级环境变量（不进入任何配置文件），隔离安装包并实测认证通过（见上表）；未复制 CLI 凭据、未改客户端配置。移除方法：`[Environment]::SetEnvironmentVariable('FIRECRAWL_API_KEY',$null,'User')`。
- claude-mem worker/AST 不可用（2026-09-22 晚定位并修复，三项根因叠加）：
  1. **插件缓存副本缺 `node_modules`**（不完整安装）→ worker 一启动就崩溃（`Cannot find module 'zod/v3'`），所以 MCP 每次自动启动 worker 都会失败。用同版本 marketplace 副本的依赖目录补齐（两侧 `package.json`、`bun.lock`、`scripts/` 逐字节一致，仅缺依赖）。
  2. **`tree-sitter-cli` 安装脚本下载中断**，留下 0 字节的 `tree-sitter.exe` → AST 工具全部报“Could not parse”。重新运行包内的 `install.js`，重新下载平台二进制（v0.26.9）后修复。
  3. **Windows 命名缺口**：bundle 定位 CLI 时查找无扩展名的 `tree-sitter`（POSIX 布局），Windows 包只提供 `tree-sitter.exe`。在包目录内以硬链接补齐该名称。
  验证：实测确认自动启动链路已恢复（停止 worker → 全新 MCP 进程自动拉起）；worker 类工具（检索、语料库列表）通过 HTTP 调用，修复后立即生效；AST 工具在全新进程中逐项通过验证。限制：修复前已启动的 MCP 进程在进程内缓存了失败结果，AST 工具需重启客户端或开启新会话才能生效；记忆库为空时，检索无结果符合预期（数据由宿主会话写入）。

## 官方资料

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [连接已有 Chrome](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md)
- [Firecrawl CLI](https://github.com/firecrawl/cli)
- [claude-mem](https://github.com/thedotmack/claude-mem)
- [DBX MCP Server](https://github.com/t8y2/dbx/tree/main/packages/mcp-server)
- [Qoder CLI MCP 配置](https://docs.qoder.com/cli/mcp-reference.md)
- [Qoder IDE MCP](https://docs.qoder.com/user-guide/chat/model-context-protocol.md)
- [Qoder CLI 发布说明](https://docs.qoder.com/release-notes/qoder-cli.md)
- [Firecrawl 本地 MCP](https://docs.firecrawl.dev/mcp-server/local)
- [Chrome DevTools 启动排障](https://raw.githubusercontent.com/ChromeDevTools/chrome-devtools-mcp/main/docs/troubleshooting.md)
- [Node.js Windows 子进程限制](https://nodejs.org/api/child_process.html#spawning-bat-and-cmd-files-on-windows)

依赖版本、认证能力和客户端格式可能变化；这些说明不替代目标环境中的实际连接与功能验证。
