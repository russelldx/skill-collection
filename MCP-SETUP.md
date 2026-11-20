# MCP 安装、配置与使用指南

第一次从 GitHub 下载技能仓库，可先读 [安装向导](./INSTALL.md)；想知道技能怎么选、怎么提问，可读 [技能使用指南](./SKILL-GUIDE.md)。本文只讲五类可选 MCP：它们能做什么、在什么地方配置，以及接通后怎么用。**不需要把五类全部装上。**

## MCP 是什么，和 Skill、CLI 有什么区别

MCP（Model Context Protocol，模型上下文协议）是一套让 AI 助手调用外部工具的通用约定。可以把它理解为“助手与工具之间的接口”，而不是一个装上就拥有全部功能的软件。

- **Skill（技能）**：告诉助手按什么流程办事，例如如何抓取网页、检查截图。复制技能文件不等于安装了工具。
- **MCP 服务**：把抓网页、操作浏览器、查询数据库等能力交给助手调用。服务既可能在本机运行，也可能连接远端系统。
- **宿主 / MCP 客户端**：你正在使用的 AI 软件，例如 Qoder IDE、Qoder CLI、Claude Code。MCP 要接到这个软件里，不能只把 JSON 放进任意文件夹。
- **CLI（命令行工具）**：在终端输入命令来完成操作。Firecrawl 的技能主要走 CLI，MCP 是另一条可选路线，两者不能互相证明“已经配置成功”。

仓库中的 [.mcp.json](./.mcp.json) 是 Firecrawl 与 Chrome DevTools 的项目配置示例，不会替你安装、登录或授权。它也不能证明当前会话中同名 MCP 来自本仓库。本文的配置块是公开示例，**不是你的真实配置或连接结果**。

如果只是原样安装或更新 Skill，不必配置或测试这些 MCP。下文的“如何验证”供你确实配置服务、排障或主动试用时参考，不是复制 Skill 的必做步骤；未测试就不宣称已连通。

## 先选需要的能力

| 能力 | 选择与边界 | 涉及技能 |
|------|------------|----------|
| [网页搜索与抓取 · Firecrawl](#mcp-firecrawl) | CLI 为主、MCP 可选；云端 MCP 需服务密钥，CLI 部分基础操作支持受限免密钥模式 | 18 个 `firecrawl*` 技能 |
| [浏览器调试与操作 · Chrome DevTools MCP](#mcp-chrome-devtools) | 可用独立浏览器资料，也可经授权连接已有 Chrome | 可供 `course-assignment` 等流程选用 |
| [窗口截图与屏幕取字 · Snipaste MCP](#mcp-snipaste) | 仓库自带本地实现；默认只截指定窗口，OCR 需要 PRO | 仓库暂无依赖技能，按需选用 |
| [跨会话记忆与代码探索 · claude-mem](#mcp-claude-mem) | 插件负责采集等集成；单独接 MCP 不等于自动记录宿主会话 | 3 个活动 `claude-mem-*` 技能 |
| [数据库查询 · DBX](#mcp-dbx) | 先在 DBX 中准备获授权的数据源，再以只读、最小权限接入 MCP | 仓库暂无依赖技能，按需选用 |

`web-access` **不是第六类 MCP**，它和独立浏览器、云端 browser 的区别见[浏览器方案怎么选](#browser-options)。

<a id="setup-first-steps"></a>
## 配置前先做这几步

1. **确定宿主和范围。** 确认你用的是 IDE 还是 CLI，以及只给当前项目使用还是所有项目共用。具体入口见[跨客户端适配](#client-settings)。不要把一个客户端的文件路径套到另一个客户端上。
2. **按所选章节准备依赖。** Node.js 是运行这些 Node 工具的环境；npm 是包管理器，npx 会在需要时下载并运行包。可在终端用 `node --version`、`npm --version` 查看已有版本；缺少依赖再按官方说明安装，不必先执行所有安装命令。
3. **分清必填值和可选值。** 本文 JSON 中的 `command` 是启动程序，`args` 是分开的参数，`env` 是传给服务进程的环境变量。`<仓库绝对路径>` 等必须换成你自己的实际路径；JSON 内 Windows 路径可用 `/`，若用反斜杠则要写成 `\\`。只合并所需服务条目，不覆盖已有配置，也不要粘贴 Markdown 的围栏标记。
4. **由你自己填写秘密。** API Key 就是服务密钥，作用类似给程序用的密码。真实密钥、数据库密码和访问令牌只放在宿主支持的受保护凭据或环境变量入口；不要发到聊天、截图、日志、GitHub 或仓库文件里。`${变量名}` 只是引用占位符，宿主必须支持展开，而且它启动的进程必须能收到该变量。没有凭据可以先跳过该服务，稍后再配。
5. **保存后在宿主中启用或重新加载。** 本文的 stdio 示例由客户端启动本地子进程，不需要再手动开一个终端长期运行同一服务。首次使用 npx 可能下载软件；安装插件、启动进程、配置写入和账户授权都要由你确认，不能让助手顺带代办。
6. **把验证分开看。** “已连接”只说明接口接通；有工具列表说明能发现工具；对获授权的测试对象成功调用，才说明那一项功能可用。截图、联网、付费调用、采集会话或访问数据库都有各自影响，不作为默认无副作用检查。

本文于 **2026-11-20 核对公开文档和仓库代码**，没有替读者安装或运行 MCP。下文版本要求对应所引来源；`@latest` 会变化，安装时应再核实目标版本的要求。文末的历史本机记录另列日期，不代表你已配置完成。

<a id="mcp-firecrawl"></a>
## 网页搜索与抓取 · Firecrawl

**能做什么**：搜索网页、读取页面正文、收集网站中的链接或多页内容；交互浏览和文件解析另有授权及部署限制。仓库技能主要通过 Firecrawl CLI 使用这些能力，MCP 不是必装前提。

**适合谁**：需要让助手整理公开网页、查资料或提取网站数据的人。只做本地文件编辑，或现有搜索工具已经够用时，可以不配。

**准备什么**：按当前官方 CLI 包要求及本地 MCP 文档准备 Node.js 22+、npm/npx。云端 MCP 还需 Firecrawl 账户、API Key（服务密钥）和可用额度；密钥由你在服务的账户页面取得，没有就稍后再配。CLI 的部分基础操作支持受限免密钥模式，覆盖范围和额度以所用版本及服务状态为准，不能据此跳过 MCP 认证。自托管路线还需管理员提供的 API 地址及所需认证。

**怎么配置**：先选 CLI 或 MCP。CLI 命令在终端执行，浏览器登录由你完成；MCP 则在所用 AI 软件的 MCP 设置中加入下方 JSON，并通过安全入口提供必填的 `FIRECRAWL_API_KEY`。不要把 CLI 登录成功当成 MCP 自动拿到了同一密钥。

**怎么用**：连接后，在宿主的 Agent 聊天中说：“用 Firecrawl 读取我给出的这个公开文档页面，列出安装步骤；只读这一页，不登录、不批量抓取。”提交前把页面链接和允许的范围一起给出；批量任务另定页数和额度预算。

**如何验证**：先在宿主中看连接状态和工具列表，再经你同意，对一个公开页面做一次只读抓取并检查是否返回目标正文。CLI 用 `firecrawl --status` 看认证及额度状态，但这不是 MCP 验证；只报告是否通过，不回显凭据。

**注意事项**：云端抓取也可能计费；登录、填表、文件上传和创建持续监控都需另行确认。`interact` 不会自动继承本机浏览器登录态；抓取成功不代表交互功能已验证。不要为配置 CLI 顺带安装整套技能或修改其他客户端。

### 仓库中的 18 个技能入口

`firecrawl`、`firecrawl-agent`、`firecrawl-alexandria`、`firecrawl-build`、`firecrawl-build-interact`、`firecrawl-build-onboarding`、`firecrawl-build-scrape`、`firecrawl-build-search`、`firecrawl-crawl`、`firecrawl-developer-index`、`firecrawl-download`、`firecrawl-interact`、`firecrawl-map`、`firecrawl-monitor`、`firecrawl-parse`、`firecrawl-research-index`、`firecrawl-scrape`、`firecrawl-search`，共 **18 个**。这是技能入口数，不是 MCP 工具数。

### CLI 路线

确认用户同意全局安装后，官方 CLI 的安装命令为：

```bash
npm install -g firecrawl-cli@latest
firecrawl login --method browser
firecrawl --status
```

CLI 不随技能目录捆绑。登录操作由用户在浏览器中完成；`--status` 只验证 CLI 的状态，不是 MCP 验证。不要为了设置 CLI 顺带安装整个技能集合或更改其他客户端配置。

### MCP 路线

在宿主的 MCP 配置入口合并以下示例。这里的“本地”是指 MCP 进程在本机运行，**不表示网页处理一定在本机完成**；默认仍请求 Firecrawl 云端 API。官方本地文档此次使用固定版本 `firecrawl-mcp@3.40.0`，下方保留仓库的 `@latest` 写法；需要可复现安装时，应先核对并固定你选用的版本。

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

Firecrawl `interact` 支持登录流程和 profile 持久化，但不会自动继承用户本机浏览器登录态。CLI `parse` 的云端处理会上传选定文件，也可能消耗额度，须先确认文件范围与上传授权。不要据此推断所有 MCP 部署都能直接读本地路径：当前官方本地文档说明，本地 MCP 的 `firecrawl_parse` 直接处理本地文件需配置自托管的 `FIRECRAWL_API_URL`；仅连接云端 API 的本地 MCP 不支持通过该工具直接上传本地文件，托管 MCP 使用另一套签名上传流程。敏感本地文档优先用本地工具。

依据：[Firecrawl CLI](https://github.com/firecrawl/cli)、[本地 MCP 配置与限制](https://docs.firecrawl.dev/mcp-server/local)。

<a id="mcp-chrome-devtools"></a>
## 浏览器调试与操作 · Chrome DevTools MCP

**能做什么**：让助手读取网页、截图、检查控制台和网络请求，也可分析性能、点击或填写页面。它控制的是所连接的 Chrome，不是纯文本网页抓取器。

**适合谁**：需要调试网页、检查页面显示或在浏览器中完成获授权操作的人。只想查普通公开资料，不一定需要启用浏览器控制。

**准备什么**：Google Chrome 当前稳定版或更新版本、npm/npx，以及满足目标包要求的 Node.js LTS。此次官方 `package.json` 的范围为 `^20.19.0 || ^22.12.0 || >=23`；不是任意 Node.js 20 或 22 都可以。基础本地模式不需要 API Key；只有连接已有 Chrome 的 `--autoConnect` 模式另要求 Chrome 144+。

**怎么配置**：在宿主的 MCP 设置中加入下方 `chrome-devtools` 条目；默认配置没有必须填写的密钥或调试端口。先用与日常浏览器分开的资料目录；只有确实要复用已有会话，才按下方步骤选择 `--autoConnect` 或填写已核实的调试端点。

**怎么用**：在 Agent 聊天中说：“请新建一个测试标签页，打开我提供的测试网址，检查控制台报错；不要操作已有标签页，完成后只关闭你创建的标签页。”需要登录、提交表单或上传文件时，再单独确认。

**如何验证**：先看宿主显示已连接且有工具列表；允许启动测试浏览器后，再让助手调用 `list_pages`，在自己新建的测试标签页读取文字或截图，并检查结果。只连上 MCP 不代表浏览器已启动或页面操作成功。

**注意事项**：连接已有 profile（浏览器资料目录）可能让助手访问其中所有窗口及登录状态。默认 MCP profile 与日常资料分开，但会跨次保留，并非一次性隐私模式。官方默认开启使用统计，性能工具还可能向 CrUX 发送页面 URL，关闭方式见下方；不要把调试端口开放到公网。

### 基础配置

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

默认启动的独立浏览器 profile 不会自动带上日常登录态，但同一频道的 MCP 会复用它。若要用关闭后清理的一次性 profile，可在 `args` 末尾增加 `--isolated`；若不希望发送使用统计或 CrUX 请求，可增加 `--no-usage-statistics`、`--no-performance-crux`。这些是该服务的启动参数，不是给所有客户端通用的设置键。

### 连接已有 Chrome（可选）

确实需要复用浏览器状态时，在用户授权后选择一种方式，不要同时套用两种连接参数：

- `--autoConnect`：官方文档要求 Chrome 144+。用户先启动 Chrome，在 `chrome://inspect/#remote-debugging` 启用远程调试，并在浏览器对话框中允许连接；将参数加到上述 `args` 中。连接的是 Chrome 选定的默认 profile，可能覆盖其全部打开窗口。
- `--browser-url=http://127.0.0.1:9222`：将参数加到 `args` 中，仅连接用户已明确开放且确认归属的调试端点；`9222` 是示例，实际端口以环境为准。手动启动调试端口的方式要求使用非日常默认的用户数据目录，不能为了让命令成功擅自关闭或替换日常浏览器。

通过 MCP 列出页面，在自己创建的测试标签页中读取/截图，完成后再关闭该标签页。不要操作或关闭用户原有页面。如果 profile 被占用，先确定是谁在使用，不能直接终止浏览器进程或删除锁文件。官方只保证 Google Chrome 和 Chrome for Testing 的支持，不能据此承诺任意 Chromium 浏览器兼容。

依据：[官方说明与运行要求](https://github.com/ChromeDevTools/chrome-devtools-mcp)、[连接模式与 profile](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md)。

<a id="mcp-snipaste"></a>
## 窗口截图与屏幕取字 · Snipaste MCP

**能做什么**：截取你指定的应用窗口，或在临时浏览器窗口中显示文件、URL、HTML 后截图；还能列出可见窗口。屏幕取字（OCR）需要 Snipaste PRO。

**适合谁**：Windows 用户需要让助手检查应用画面、网页效果或提取窗口文字时使用。只做浏览器内部调试，可先考虑 Chrome DevTools，不必同时安装。

**准备什么**：本仓库的 `mcps/snipaste-mcp` 目录、Snipaste 2.x 和 Node.js 18+；`snip_view` 另需 Edge 或 Chrome。窗口截图与窗口控制当前仅支持 Windows。基础截图没有 API Key 必填项；没有 Snipaste 或不允许截图，可以先不启用。

**怎么配置**：在终端进入你下载仓库中的 `mcps/snipaste-mcp` 目录，经你同意后用 `npm ci` 安装本地依赖；然后在宿主 MCP 设置中加入下方 JSON。必填的是你自己的 `src/server.js` 绝对路径，不能照抄他人路径；自动定位失败时，再给该条目的 `env` 配置 `SNIPASTE_PATH`，值为实际 Snipaste 可执行文件路径。

**怎么用**：在聊天中说：“先列出这个测试应用的窗口，等我确认目标后，只截这个窗口，不截桌面。”用 `snip_windows` 确认候选后，助手应以 `app`、`title` 或 `pid` 指定目标；显示本地测试 HTML 可选 `snip_view`，不借用日常浏览器登录态。

**如何验证**：先看宿主是否连接成功、是否列出五个工具；允许环境探测后，可用 `snip_status` 查看是否找到 Snipaste 和支持窗口控制。它会返回路径、前台窗口信息，且可能缓存定位结果，不要公开原始输出。真正验证图片要另外同意截图范围；`npm test` 是会调用真实 Snipaste 的端到端测试，不作为默认检查。

**注意事项**：默认窗口截图会置前、最大化并尝试恢复窗口，异常中断时可能来不及恢复；截图也会保存到磁盘。OCR 会读取并覆盖剪贴板，超时恢复可能重启 Snipaste；不要让剪贴板保留密钥再试 OCR。桌面截图只有你明确要求时才允许，遮挡校验失败不能改成整屏截图来绕过。

### 实现与安全策略

`mcps/snipaste-mcp` 是仓库内唯一自带实现的 MCP 服务，不是第三方包，也不在 `skills/` 同步基线内。它封装了 Snipaste 的命令行参数，提供 `snip_capture`、`snip_view`、`snip_windows`、`snip_ocr`、`snip_status` 五个工具，用来安全截图、读取屏幕文字（PRO）和进行窗口自检。完整说明见 [mcps/snipaste-mcp/README.md](./mcps/snipaste-mcp/README.md)。

**默认安全策略（务必保留）**：截图严禁包含用户桌面与其它隐私窗口。`snip_capture` 默认 `target: "window"`，只截一个经覆盖校验的目标窗口矩形，截完自动还原窗口。`fullscreen`/`active_screen`/`last` 一律拒绝，除非调用方显式传入 `allow_desktop: true`；这个开关仅限用户明确要求桌面截图时使用。没有合适的应用窗口时，用 `snip_view` 打开临时浏览器窗口，渲染后再截图。窗口级校验失败时，宁可不返回图片，也不会降级成整屏截图。窗口控制与 `snip_view` 仅支持 Windows，其它平台会明确报错，提示不支持。

### 安装依赖与注册

依赖：Snipaste 2.x（便携版即可，不要求在 `PATH` 中）与 Node.js 18+；`snip_view` 需要本机装有 Edge 或 Chrome。以下命令在终端执行，先把路径换成你下载的仓库目录：

```bash
cd "<仓库绝对路径>/mcps/snipaste-mcp"
npm ci            # 依 package-lock.json 安装；node_modules 已被 .gitignore 排除
```

再在宿主中注册服务。下方 `<仓库路径>` 必须换成同一个仓库的绝对路径；没有可用的 Node 命令时，应核实宿主使用的 Node 可执行文件，而不是猜安装目录。

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

定位顺序：`SNIPASTE_PATH` → 常见安装目录 → `PATH` → 上次缓存 → 正在运行的进程 → `Desktop`/`Downloads`/`Documents`/`Programs` 的浅层扫描。首次找到后，会将路径写入用户配置目录；`snip_status` 也会触发这条定位链路。真正截图时，如果 Snipaste 未运行，服务会自动启动它。README 给出的首次约 2.5 s、后续约 0.3 s 是说明中的估计，窗口控制还有额外开销，不是对你机器的实测承诺。

免费版支持哪些功能，以 Snipaste 官方对照表为准：Snipaste 自带的活动窗口参数、阴影、`--block` 与 `-o ocr_clipboard`（文字提取）属于 PRO 功能，免费版会忽略相关参数。因此本 MCP 用窗口控制配合 `--area` 实现窗口截图，**免费版也能按本 MCP 的窗口流程截图**。免费版的 `-o ocr_clipboard` 还可能让 Snipaste 不再响应后续截图请求，因此 `snip_ocr` 超时后会尝试重启 Snipaste，再返回明确错误；错误中可能带有剪贴板残留文字，不要直接公开日志。

### 可选的真实端到端验收

只有你同意真实截图、测试窗口和进程操作后，才在上述目录单独执行：

```bash
npm test
```

当前 `package.json` 将它指向 `test/e2e.mjs`：会启动 MCP、重启真实 Snipaste、创建专用 WinForms 窗口、测试窗口截图和遮挡拒绝，并用临时 Edge/Chrome profile 渲染 HTML、截图，再清理测试窗口和临时目录。它不是纯静态检查，也不等于 OCR 等所有功能都已验收；普通截图返回的图片文件不能因测试会清理就视为自动删除。

**临时端口也属于需确认的影响。** 此次核对的 `src/viewer.js` 和 `test/e2e.mjs` 使用本地文件渲染，未见显式开启 HTTP/CDP 监听端口的代码；若另外用本地 HTTP 测试页或其他验收脚本临时监听端口，应事先说明端口、用途和清理方式，不能把它当作无副作用的默认验证。本次没有运行端到端测试。

依据：[仓库 README](./mcps/snipaste-mcp/README.md)、[工具注册与安全检查](./mcps/snipaste-mcp/src/server.js)、[截图与状态实现](./mcps/snipaste-mcp/src/snipaste.js)、[临时浏览器实现](./mcps/snipaste-mcp/src/viewer.js)、[端到端测试](./mcps/snipaste-mcp/test/e2e.mjs)。

<a id="mcp-claude-mem"></a>
## 跨会话记忆与代码探索 · claude-mem

**能做什么**：检索已经保存的工作记录，帮助回顾之前的处理过程；配套版本还可提供代码结构探索和知识库工具。自动记录新会话依赖宿主集成，不是 MCP 连接自身就具备的行为。

**适合谁**：需要跨会话回顾工作，并愿意明确管理记录范围、保存位置和处理方式的人。只需要当前对话上下文，或不愿采集工作内容时，可以不安装采集插件。

**准备什么**：官方 claude-mem 安装文件、受支持的宿主与配套版本。此次上游 README/包要求 Node.js 20.x 的 20.19+，或 22.12+；当前安装文档还列出 Bun 1.2.16+、uv、内置 SQLite，以及使用新式 hooks 时的 Claude Code 2.1.139+。旧版要求可能不同，安装前按选定版本复核，不把本机曾用的插件版本当成所有人的固定要求。

**怎么配置**：Claude Code 用户可按下方插件市场命令安装，但须先单独同意 hooks（会话事件触发脚本）、worker（后台处理服务）和持久记录。其他 MCP 客户端可接官方 `plugin/scripts/mcp-server.cjs`；必填项是已确认的实际绝对路径，还要有配套、可用的 worker。若记录处理需要模型服务密钥，由你在官方安全入口配置；缺少凭据可稍后启用采集。

**怎么用**：在 Agent 聊天中说：“只在这个项目已保存的记录里找上次修复登录问题的做法，给出来源；找不到就说明没有记录。”代码探索可说：“只查看我授权的测试项目，列出主要模块。”不要让助手为填满记忆库擅自读取其他项目。

**如何验证**：先确认 MCP 连接及实际工具列表，再对已获授权的记录做一次检索；空库返回无结果不等于故障。若还要验证自动记录，需另行同意一段不含敏感信息的测试会话，核对 hooks、worker 和下一会话能否检索到记录。只连通 MCP、只看到工具名，不能证明会话已自动采集。

**注意事项**：插件安装可能下载额外运行时、启动后台服务并记录工具活动；摘要处理还可能向你选择的模型服务发送内容。安装前分别确认采集范围、存储、模型提供方、云同步和遥测选项；不能把“安装技能”视为这些操作的同意。三个仓库技能须与插件实际能力配套，不要盲目固定为 13.4.0 或用最新技能覆盖旧插件。

### 安装入口与版本核对

`@anthropic-ai/claude-mem` 不是官方安装入口，因此没有放进通用 `.mcp.json`。官方现有 `claude-mem` 包，但 `npm install -g claude-mem` 只装 SDK/库，不能替代插件 hooks 和 worker 的设置。

Context7 此次提供的部分系统要求摘录仍写 Node.js 20+、Bun 1.0+，与直接读取的上游 `README.md`、`package.json` 和 `docs/public/installation.mdx` 不同。上文采用后者的明确要求；这只是 **2026-11-20 的文档核对**，不是运行兼容性测试。macOS 27 的签名 launcher 在当前安装文档中另要求 Bun 1.4.1+，其他平台也应看目标版本说明。

### Claude Code

经用户授权后，在支持插件的 Claude Code 中执行官方命令：

```text
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```

这两条是 **Claude Code 对话中的插件命令**，不是普通终端命令。插件安装会设置相应集成，可能下载运行时、启动 worker、注册 hooks 并产生持久记录；同意这些影响后才安装，之后按官方提示重启或开启新会话，验证实际启用状态。不要把“插件已安装”直接写成“历史记录已生成”。

### 其他 MCP 客户端

1. 如果尚未安装 claude-mem，先按[官方安装说明](https://github.com/thedotmack/claude-mem/blob/main/docs/public/installation.mdx)核对目标宿主是否受支持。官方另有 `npx claude-mem install` 安装入口，但它可能下载运行时、修改宿主集成及用户 PATH、启动 worker、引导账户或模型提供方设置，不能当成纯检查命令，也不要为了 MCP 检索顺带给所有宿主装采集 hooks。
2. 使用官方安装文件中的 Node 入口 `plugin/scripts/mcp-server.cjs`。**先找到并确认本机实际文件路径和 worker 状态，再添加配置**；不要猜测用户名、安装目录，也不要复制其他机器的绝对路径。只复制这个脚本并不构成完整安装。
3. 在目标客户端的 MCP 设置中合并以下示例。按所装版本的官方方法检查 worker 健康状态和实际端口，不盲连某个默认端口；同意启动后台 worker 与同意采集宿主会话要分开确认。

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

上面的路径是占位符，不能直接运行。即使 MCP 服务能启动，也不保证当前版本提供所有 AST（代码语法结构）或语料库工具；需要分别验证 `mem-search`、`smart-explore`、`knowledge-agent` 所需的工具。**仅接这个 MCP，不会自动让任意宿主记录会话。** 自动记录还需要该宿主受支持且已获同意的 hooks 或其他集成。

本仓库的全文阅读模式已并入 `smart-explore`，不再安装独立 `learn-codebase` 入口；这是仓库入口安排，不代表所有上游版本都没有同名功能。

依据：[claude-mem 官方仓库](https://github.com/thedotmack/claude-mem)、[安装要求](https://github.com/thedotmack/claude-mem/blob/main/docs/public/installation.mdx)、[MCP 搜索架构与入口](https://github.com/thedotmack/claude-mem/blob/main/docs/public/architecture/search-architecture.mdx)，以及 Context7 的 `/thedotmack/claude-mem` 文档摘录。

<a id="mcp-dbx"></a>
## 数据库查询 · DBX

**能做什么**：通过 DBX 管理的连接查看数据库、表结构和查询结果；某些模式也能写数据或在 DBX 界面展示结果。本指南从只读查询开始，不默认开放写入、删除、建表或连接管理。

**适合谁**：有数据库任务，并已取得数据所有者授权的开发者或分析人员。仓库目前没有必须依赖 DBX 的技能；不知道要查哪一个库、没有获授权的数据源时，可以先不装。

**准备什么**：按[DBX 官方仓库](https://github.com/t8y2/dbx)的安装说明准备 DBX 应用，并由你或管理员提供一个获授权的测试数据库连接。优先使用仅能读取必要库表的数据库账户。npm/npx 路线按当前官方要求需 Node.js 18.18.0+ 和受支持的系统/CPU；本地接入不要求 Firecrawl 等其他服务的 API Key。

**怎么配置**：先在 DBX 应用中添加并验证测试连接，主机、端口、数据库、认证信息或本地文件路径按该数据库类型填写；密码由你自己输入，不交给聊天或仓库保存。再到 DBX 的 `Settings → MCP` 选择 `Read only`（只读），在 `Allowed connections` 中只允许该测试连接，最后在 AI 宿主加入下方 `@dbx-app/mcp-server` 配置。

**怎么用**：在 Agent 聊天中说：“只使用我授权的测试数据库连接，查看指定测试表的字段；先不要读取记录。”确认结构后再说：“只读这张测试表的指定列，最多返回 10 条，不访问其他库，不修改任何数据。”连接名、表名和列名由你按测试库实际情况提供。

**如何验证**：分三层检查：宿主显示已连接并列出工具；经授权列出允许的连接，确认只出现预期测试连接；再对指定测试库做结构读取，必要时做一次小范围只读查询。初始化成功或能看到工具列表，**不等于已经能连数据库、通过认证或获准查表**。

**注意事项**：数据库自身的只读账户、DBX 的只读模式和连接允许列表要同时收紧，不能只靠提示词说“不要写”。表结构、连接备注和查询结果也可能含敏感信息；不要把密码写进连接备注。连接不存在或权限不足时先停下核对，不让助手改权限、添加真实业务连接或改用生产库试错。

### 第一步：在 DBX 中准备获授权的数据源

1. 从官方仓库指向的渠道选择适合自己系统的 DBX 安装方式。DBX 应用与 MCP 包是两个部分，安装技能不会把它们一起装好。此次没有确认 DBX 应用与 MCP 包的最低兼容版本，安装时核对各自的发布说明。
2. 在 DBX 中保存一个你有权使用的测试连接，并用应用确认能连接。SQL 数据库通常需要主机、端口、库名和认证信息；SQLite 等本地数据库需要文件路径，具体以连接表单为准。没有连接或凭据就到此暂停，不把真实业务数据当默认样例。
3. 在 `Settings → MCP` 设置 `Read only`，并用 `Allowed connections` 仅允许测试连接；同时让数据库账户只有必要库表的读取权限。如果你所装版本没有这些界面，先按对应版本官方说明核对，不猜配置开关，也不直接开放全部连接。

### 第二步：在 AI 宿主接入 MCP

本地 stdio 路线的官方 npx 示例如下，无需先全局安装：

```json
{
  "mcpServers": {
    "dbx": {
      "command": "npx",
      "args": ["-y", "@dbx-app/mcp-server"]
    }
  }
}
```

这条配置没有数据库密码必填项，因为连接由 DBX 管理；**不表示数据库不需要认证**。首次启动可能下载包和对应平台的原生二进制，须先同意。当前包不要使用 `--no-optional`，平台二进制由 npm 的可选依赖提供；支持的平台及原生离线安装见官方包说明。

如果你明确选择全局安装，也可在终端执行官方命令，再把宿主中该服务的 `command` 改为 `dbx-mcp-server`，不再保留 npx 的 `args`；两条路线选一条即可：

```bash
npm install -g @dbx-app/mcp-server
```

普通本地安装由 MCP 读取 DBX 的连接存储，不需要在 MCP JSON 中再填主机和密码。便携版或非默认数据位置可设置 `DBX_DATA_DIR`，值是**包含 `dbx.db` 的目录**，不是数据库文件本身；只在已核实位置后填写，不要复制他人的磁盘路径或打开连接存储来公开其中内容。

### 第三步：只验证所授权的测试库

- 保存配置，在宿主中启用或重新加载 DBX。先确认服务连接和工具清单，再按用户允许范围调用 `dbx_list_connections`，核对能看到的连接是否符合预期；不要把完整连接清单或备注直接贴到报告里。
- 只对选定测试连接使用 `dbx_list_tables`、`dbx_describe_table` 读取元数据。若要验证查询，再用 `dbx_execute_query` 做已确认列、限定行数的只读操作，不执行写入语句。具体参数以实际工具 schema 为准，不能把此时能发现的工具视为全部已验收。
- 当前原生模式下，受支持的本地连接查询不要求 DBX 窗口一直打开；`dbx_open_table`、`dbx_execute_and_show` 则要求 DBX 桌面应用运行。Agent/JDBC 数据库还需配套 agent、驱动与 JRE，不能承诺装一个 MCP 包就覆盖所有数据库。

DBX Web/Docker 及 HTTP 接入是另一条部署路线，需由管理员提供真实服务地址和认证方式；`DBX_WEB_PASSWORD` 是 Web 登录密码，本地桌面模式不用它。本指南不替用户部署服务、开放端口或配置远端凭据，需要时再按[官方 MCP 包说明](https://github.com/t8y2/dbx/tree/main/packages/mcp-server)选择。

<a id="browser-options"></a>
## 浏览器方案怎么选

下面是浏览器使用方式的区别，**不是要额外安装的第六类 MCP**。CDP 是 Chromium 浏览器提供的调试接口；登录态属于具体浏览器资料，不能在这些路线之间默认通用。

| 方案 | 浏览器及登录态在哪里 | 什么时候选 |
|------|--------------------|------------|
| `web-access` 技能 + 自带 CDP Proxy | 使用你明确选定的本机日常浏览器，可使用其中已有登录态；不是 MCP | 需要本机登录态、本人书签/历史或站点经验 |
| Chrome DevTools 的独立浏览器模式 | 使用与日常资料分开的 profile；默认保留，`--isolated` 才是一次性 | 页面调试、截图、测试，不需要借用日常登录态 |
| Chrome DevTools 连接已有 Chrome | 经调试授权接到选定的已有 profile | 明确要在手动操作和助手之间共享网页状态 |
| Firecrawl `interact` 等云端 browser | 浏览器在服务端；即使有持久 profile，也不是本机浏览器资料 | 已选择云端网页交互，并同意内容处理、登录及额度范围 |
| Snipaste `snip_view` 临时窗口 | 本机临时 Edge/Chrome profile，用完关闭；不继承日常登录态 | 只需把文件、URL 或 HTML 渲染成截图 |

`web-access` 自带本地 Node.js CDP Proxy，不要求 Chrome DevTools MCP。它保留了使用本机登录态、书签/历史检索和站点经验的路线；需要 Node.js 22+，查询 History 数据库另需 sqlite3 CLI，详见[技能说明](./skills/web-access/SKILL.md)。它的前置脚本在没有可用服务时可能启动后台 Proxy，不能当作纯版本检查默认执行。

首次使用要确认具体浏览器及其用户数据目录，并按技能说明完成浏览器调试授权。浏览器调试授权、站点风控和实际操作权限仍须分别确认；没有明确请求，不读个人历史、不操作已有标签页。已有健康 Proxy 应优先复用，不要因普通任务结束而停止它。

显式指定浏览器后，如果检测失败，并不等于所有 CDP 路线都不可用。应按脚本反馈核对 profile、调试端口与选择方式；未获授权时，不要更改浏览器偏好，也不要自动换到另一个浏览器或云端服务。

<a id="client-settings"></a>
## 跨客户端适配

Claude Code、Qoder、Cursor、Codex、Gemini CLI 等宿主应分别按其当前文档配置 MCP。不要假定它们都读取项目 `.mcp.json`、都支持相同环境变量插值或工具名称，也不要笼统宣称某客户端不可用。Chrome DevTools 官方文档包含 Gemini CLI 配置示例。

Windows 环境下，若客户端不能直接解析 `npx`，按该客户端文档使用命令包装或可执行文件路径；不要在没有错误证据时修改全局 PATH 或系统设置。

### Qoder IDE：在界面里添加

按[当前官方 IDE 文档](https://docs.qoder.com/user-guide/chat/model-context-protocol.md)：

1. 打开 **Qoder IDE Settings → MCP → My Servers → + Add**。
2. 在出现的 JSON 编辑文件中，只合并你选择的服务条目。stdio 需要命令和参数；服务若需要密钥，由你通过当前宿主支持的安全方式提供，不能把真实值存入公开仓库。
3. 保存后回到 My Servers，连接图标表示接通，展开条目可查看工具。失败时先核对实际错误、依赖和必填值，不默认使用会改变环境的“Quick Fix”。
4. 在 Chat 中切换到 **Agent** 模式，按各章节的自然语言示例提问；调用前核对工具、输入、目标范围并确认，不为方便而允许所有后续操作。

该文档未明确说明 IDE 会读取本仓库 `.mcp.json`，也未证明它采用与 CLI 相同的 `${VAR}` 展开规则。不能只因仓库有文件就跳过 IDE 的配置与验证。

### Qoder CLI：先确认配置作用范围

按[当前 CLI 文档](https://docs.qoder.com/cli/mcp-reference.md)，同名服务的覆盖顺序为：用户 `~/.qoder/settings.json` → 项目 `.qoder/settings.json` → 项目 `.mcp.json` → 项目 `.qoder/settings.local.json` → 命令行配置。后项覆盖前项，插件也可提供服务；项目配置需要批准，本地项目设置只在受信任目录加载。`~/.qoder/mcp.json` 不在该 CLI 文档的发现列表中。

在确认的配置范围内合并条目并按提示批准所需服务，不要为了省事启用全部项目 MCP 或跳过权限确认。会话中可用 `/mcp` 看连接状态，修改后用 `/mcp reload` 重新发现服务和工具；这可能启动配置的服务，执行前仍应知道将加载什么。官方当前命令行写法是 `qoder mcp list`；历史安装使用过 `qodercli mcp list`，应以你实际安装的可执行命令及其帮助为准，不保证两个名称互通。

[Qoder CLI 1.0.17 发布说明](https://docs.qoder.com/release-notes/qoder-cli.md)明确记录修复了 MCP `${VAR}` 环境变量展开问题。但占位符不能代替凭据，也不能证明新设置已被当前进程继承；凭据由你配置后，可能需要完整重启宿主，再验证所选服务的认证。不要用打印密钥的方式排错，连接清单和原始日志也不保证已脱敏。

### Windows 启动差异

Firecrawl 官方 Windows 说明使用已定位的 `npx.cmd`；Chrome DevTools 故障排查提供了用 `cmd /c npx` 包装命令的方式。Node 对 `.cmd` 的启动有限制，单靠更换扩展名并不能解决所有情况。只在出现相应启动错误、且宿主支持时考虑官方包装方式，例如：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

这是 Windows 的替代启动配置，不是要求再添加第二个 Chrome 服务。需要在具体宿主中验证，不自动更改 PATH、用户设置、浏览器权限或系统安全策略。

<a id="connection-checks"></a>
## 可复现 smoke 检查（进阶，可跳过）

smoke 是最小连通性检查，不是完整功能验收。新手可先用宿主界面的连接状态和获授权的单次测试，不必为了看工具列表安装一套测试环境。

仓库的 `mcp-smoke.py` 需要 Python 3.11+ 和已有 Python MCP SDK，默认只预检指定配置中的一个服务，不安装依赖，也不自动发现或读取用户级配置。但它会读取你用 `--config` 指定的整个 JSON 文件；不要把真实凭据配置当作无敏感内容的测试夹具。下面是针对仓库公开示例的命令，**本次文档维护没有执行它们，也没有读取真实 `.mcp.json`**。

只有指定 `--connect` 时，检查器才会启动该服务或连接指定端点；它不是服务代码沙箱，初始化本身也可能触发服务副作用，执行前仍须审阅来源并获准。历史测试曾用 SDK 1.27.1，不是所有用户必须安装的固定版本。

```bash
python -B mcp-smoke.py --config .mcp.json --server firecrawl
python -B mcp-smoke.py --config .mcp.json --server chrome-devtools
```

安全检查器拒绝 `npx/npm/uvx` 和 shell/batch 启动器，以免隐式下载；因此示例中的 `npx` 会得到 `unsafe_launcher`。这是检查器的策略，不能据此认定 Qoder 无法启动该服务。要检验已有安装，需显式提供 `--command` 和完整的 `--command-args` JSON 数组（例如已核实的 Node 可执行文件及服务 JS 入口），再加 `--connect --require-tool list_pages`。不要照抄其他机器的缓存路径。

协议检查包括 initialize、分页获取工具清单、检查 schema 结构和必需工具，并包含有限超时和清理；它不做完整的 JSON Schema 验证。可选的真实调用仅允许 `--call list_pages --arguments '{}'` 或 `list_corpora`，须同时指定 `--connect`。检查器会核对返回结果中的 `isError` 和错误文本，只输出安全元数据；不输出工具内容、令牌、headers 或私有端点。检查器只做一次 `${NAME}` 展开，不能把它当作对宿主插值的验证。

覆盖启动配置后的结果标记为 `project_config_with_launch_override`，不能据此宣称原始 `npx` 配置已在宿主加载。DBX 不能靠此检查器的工具列表检查就算查库通过；Snipaste 的真实截图也不在上述真实调用允许列表中，不能为验收而顺手调用。

如需维护检查器本身，其单元测试命令如下；这不是五类 MCP 的安装命令，也不是全部真实服务的验收结果：

```bash
python -B -W error -m unittest discover -s tests -p test_mcp_smoke.py -v
```

<a id="historical-results"></a>
## 历史本机排查记录（2026-09-22，不是安装完成证明）

以下沿用原文保存的 **2026-09-22 本机实测与修复记录，含当晚复核**，仅供理解故障和证据边界。本次 2026-11-20 只核对文档与代码，未重新执行这些操作。表中的账户、安装版本、连接结果、工具数和数据量只属于当时环境，不能套用到读者机器，也不能证明本仓库示例已经在你的宿主加载。

| 当时的证据链 | 历史结果 | 限制 |
|---|---|---|
| Qoder CLI 1.1.60 | 检查时的进程中没有 `FIRECRAWL_API_KEY` | 不代表读者的 Qoder 版本或凭据状态；CLI 与 IDE 配置机制仍需分别核对 |
| Chrome DevTools MCP | 列出页面、在自建空白页写入测试文字、读取、截图、关闭均成功 | 未操作原有页面；不等于已经实测 web-access Proxy |
| 已安装 Chrome MCP 1.9.0 + Python SDK 1.27.1 | 使用显式 Node 入口，initialize、29 个工具 schema、必需 `list_pages` 和清理均通过检查 | 关闭该次进程的使用统计与 CrUX；未运行 npx，未验证宿主能否发现原样配置 |
| Firecrawl CLI 1.16.0 | 认证、额度检查和一次官方 MCP 文档抓取均成功，退出码 0 | 这是消耗额度的单页操作；不代表批量抓取或交互已验收 |
| Firecrawl MCP | 原先查询额度时返回 HTTP 401；用户提供 Key 并设置用户级 `FIRECRAWL_API_KEY` 后，隔离安装 firecrawl-mcp 3.25.2 并实测：initialize 成功、29 个工具、`firecrawl_credit_usage` 返回 999/1000（isError=false） | 当晚复核：用户级变量已设置，但当时的进程树仍未继承，仍返回 401，需重启客户端；该次 MCP 测试未做付费抓取，scrape/search/interact 仍未逐项验收 |
| 仓库 Firecrawl 示例 | 环境变量就绪后，预检结果从 `missing_environment` 变为 `unsafe_launcher`（检查器按策略拒绝 npx，并非宿主启动缺陷）；移除变量后复现 `missing_environment` | 仅证明检查器可解析示例中的 `${FIRECRAWL_API_KEY}`，未证明当时客户端已加载该示例 |
| claude-mem（当晚修复后） | worker 健康端点正常，自动启动链路已恢复（停止 worker 后，全新 MCP 进程自动拉起了 worker，日志为 `Worker started successfully`）；`list_corpora` 正常返回；`smart_outline`（含非 ASCII 路径）、`smart_search`（扫描 469 文件/6416 符号）、`smart_unfold` 均返回正确结果 | 修复前启动的 MCP 进程缓存了失败的解析结果，AST 工具需重启客户端或开启新会话后才能生效；记忆库为空，检索无结果符合预期；未证明任意宿主会自动写入会话记录 |

### 当时的阻塞根因与处置

以下是 2026-09-22 的诊断与处置经过，**不是建议读者照抄的安装或修复脚本**。现在遇到相似错误，应先核对自己所用版本的官方排障说明；不要直接复制依赖、创建硬链接、删除变量或重启既有服务。

- Firecrawl MCP 401 根因：当时用户级 `~/.qoder/settings.json` 中该条目为 `npx -y firecrawl-mcp@latest`，未配置环境变量（env 键为空），且用户环境中不存在 `FIRECRAWL_API_KEY`，因此服务端调用时没有凭据。**当时的处置**：将 Key 写入用户级环境变量（不进入任何配置文件），隔离安装包并实测认证通过（见上表）；未复制 CLI 凭据、未改客户端配置。此记录不表示本次编辑读取或修改了任何真实配置，也不是要求读者采用用户级全局变量。
- claude-mem worker/AST 不可用（2026-09-22 晚定位并修复，三项根因叠加）：
  1. **插件缓存副本缺 `node_modules`**（不完整安装）→ worker 一启动就崩溃（`Cannot find module 'zod/v3'`），所以 MCP 每次自动启动 worker 都会失败。用同版本 marketplace 副本的依赖目录补齐（两侧 `package.json`、`bun.lock`、`scripts/` 逐字节一致，仅缺依赖）。
  2. **`tree-sitter-cli` 安装脚本下载中断**，留下 0 字节的 `tree-sitter.exe` → AST 工具全部报“Could not parse”。重新运行包内的 `install.js`，重新下载平台二进制（v0.26.9）后修复。
  3. **Windows 命名缺口**：bundle 定位 CLI 时查找无扩展名的 `tree-sitter`（POSIX 布局），Windows 包只提供 `tree-sitter.exe`。在包目录内以硬链接补齐该名称。
  当时的验证：实测确认自动启动链路已恢复（停止 worker → 全新 MCP 进程自动拉起）；worker 类工具（检索、语料库列表）通过 HTTP 调用，修复后立即生效；AST 工具在全新进程中逐项通过验证。限制：修复前已启动的 MCP 进程在进程内缓存了失败结果，AST 工具需重启客户端或开启新会话才能生效；记忆库为空时，检索无结果符合预期。新数据是否由宿主会话写入，取决于该宿主是否安装并启用了获授权的采集集成，不能从这次 MCP 验证推断。

<a id="official-sources"></a>
## 官方资料与核对范围

公开资料核对日期：**2026-11-20**，依据下列官方文档、软件包要求及仓库实现。版本要求不是兼容性实测结果，安装时以所选版本为准。

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
- [Chrome DevTools 包与 Node.js 版本声明](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/package.json)
- [Firecrawl CLI 包与 Node.js 版本声明](https://github.com/firecrawl/cli/blob/main/package.json)
- [claude-mem 安装要求](https://github.com/thedotmack/claude-mem/blob/main/docs/public/installation.mdx)
- [claude-mem 包版本要求](https://github.com/thedotmack/claude-mem/blob/main/package.json)
- [claude-mem MCP 搜索架构](https://github.com/thedotmack/claude-mem/blob/main/docs/public/architecture/search-architecture.mdx)
- [DBX MCP 包版本要求](https://github.com/t8y2/dbx/blob/main/packages/mcp-server/package.json)

仓库实现依据：[Snipaste README](./mcps/snipaste-mcp/README.md)、[运行要求](./mcps/snipaste-mcp/package.json)、[工具入口](./mcps/snipaste-mcp/src/server.js)、[状态与截图](./mcps/snipaste-mcp/src/snipaste.js)、[临时浏览器](./mcps/snipaste-mcp/src/viewer.js)、[端到端测试](./mcps/snipaste-mcp/test/e2e.mjs)、[web-access 技能](./skills/web-access/SKILL.md)、[smoke 检查器](./mcp-smoke.py)。

仍需在读者环境确认：宿主对配置及环境变量的实际支持、选定版本的最低依赖、DBX 应用与 MCP 的版本配套、可用工具、认证和权限，以及每项真实功能是否成功。不要把文档中的示例、工具清单或历史结果当成这些验证已经完成。
