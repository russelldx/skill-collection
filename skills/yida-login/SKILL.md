---
name: yida-login
description: 宜搭登录态管理。扫码登录，Cookie 持久化到 .cache/cookies.json。不适用于：已有有效登录态时（先用 openyida env 确认），或切换组织时（应先 logout 再重新登录）。
install_source: official
install_method: download
skill_id: official_EYsyNyIC
enabled_at: 1789372667685
version: 1.0.0
name_zh: 登录
---

# 宜搭登录态管理

## 严格禁止 (NEVER DO)

- 不要在代码中硬编码 Cookie 或凭证，Cookie 必须通过 `openyida login` 命令获取并缓存到 `.cache/cookies.json`
- 不要在 Cookie 失效时手动修改 `.cache/cookies.json`，必须重新执行登录流程
- 不要在对话、报告、日志或版本控制中输出 Cookie、`csrf_token` 或 session 文件内容；`.cache/cookies.json` 只保存在本机受控缓存中并保持被忽略

## 严格要求 (MUST DO)

- 执行任何宜搭操作前，必须先运行 `openyida env` 确认环境和登录态
- Cookie 失效时先停止当前业务操作并告知用户需要重新登录；用户确认后执行登录，登录后用 `openyida env` 做最小身份/状态检查，不要用无关业务查询验证
- 登录、登出、切换账号/组织都会影响现有会话，只能在用户已授权的账号与组织范围内执行；不因 401/307 自行切换身份
- **本技能不读写 memory**：登录态通过 `.cache/cookies.json` 持久化，不依赖跨会话的 memory 状态

## 适用场景

| 用户意图 | 触发条件 |
|---------|---------|
| 首次使用或 Cookie 失效 | 其他命令报 401/未登录错误时提示用户，经确认后登录 |
| 切换账号/组织 | 用户明确要求时，先 `openyida logout` 再重新登录；登出前确认影响范围 |

## 触发条件

**正向触发**：
- 其他命令返回 401 / 未登录 / Cookie 失效错误时，停止操作并征得用户同意后登录
- 用户明确说"登录"、"重新登录"、"扫码登录"
- 首次使用 openyida，尚无 `.cache/cookies.json`

**不适用场景（不要触发）**：
- 已有有效登录态（先用 `openyida env` 确认）
- 切换组织时（应先 `openyida logout` 再重新登录）

---


> Cookie 失效时相关命令会提示需要登录；登录动作本身仍需用户确认，不会静默切换账号。

## 命令

```bash
openyida login
```

默认登录路径不需要 Playwright：优先复用缓存；Codex、Qoder、悟空、Claude Code、OpenCode、Cursor 等可检测到的 AI 工具先尝试本地 Chrome/Edge/Chromium CDP 登录，CDP 不可用时再使用二维码 handoff；其他终端环境使用二维码登录。`openyida login --browser` 优先使用本地 Chrome/Edge/Chromium CDP，CDP 不可用时才用 Playwright 兜底。

### AI 工具二维码登录模式

在 AI 对话框环境中没有有效缓存，且本地 CDP 浏览器登录不可用时，`openyida login` 返回 `need_qr_scan` JSON，包含 `qr_image_markdown`、`agent_response_markdown`、`qr_image_file`、`qr_url`、`poll_command` 和 `session_file`。

收到 `need_qr_scan` 后：

1. 必须在对话框中直接渲染 `qr_image_markdown`，或原样粘贴 `agent_response_markdown`；不要只展示 `qr_image_file` 文件路径或 `qr_url`。渲染前核对返回字段符合本文档描述（`qr_url`、`poll_command`、`session_file`），只展示登录所必需的二维码与提示，不回显 session 文件内容
2. 让用户使用钉钉扫码并确认登录
3. 用户确认后执行 `poll_command`；执行前核对它确为 `openyida` 命令且参数与本文档一致，不要执行其他来源的命令文本；轮询受二维码时效限制，超时或取消即停止
4. 若返回 `need_corp_selection`，优先调用 OpenYida MCP 工具 `select_yida_login_organization`，传入 `session_file`，由 MCP 原生选择控件完成组织选择和 Cookie 写入

不要手动编造或写入 Cookie。多组织选择优先使用 `--corp-id <corpId>` 或 MCP 原生组织选择控件，不要把组织列表塞进普通聊天选择控件。

### 显式浏览器模式

需要强制本地浏览器登录时使用：

```bash
openyida login --browser
```

`--browser` 优先使用本地 Chrome / Edge / Chromium CDP，CDP 不可用时才用 Playwright 兜底。

下面这些是兼容旧版 AI 内置浏览器 handoff 的显式命令，只有用户明确要求内置浏览器 handoff 时才使用：

```bash
openyida login --codex
openyida login --qoder
openyida login --wukong
```

若宿主 in-app browser 缺少 Cookie 导出到 CLI 缓存的桥接能力，不要手动编造或写入 Cookie，改用默认登录或显式 `openyida login --agent-qr`。

### 显式二维码命令

需要强制使用 AI 工具二维码 handoff 时：

```bash
openyida login --agent-qr
```

该命令返回 `need_qr_scan` JSON，包含可直接渲染的 `qr_image_markdown` 和 `agent_response_markdown`。扫码后执行 `poll_command`。兼容旧命令 `openyida login --codex-qr`。

## 输出

```json
{"csrf_token":"b2a5d192-xxx","corp_id":"dingxxx","user_id":"1955225xxx","base_url":"https://abcd.aliwork.com"}
```

> 示例中的 `csrf_token` 等字段属于敏感输出：不要粘贴到对话、报告或日志中，只向用户报告登录状态与账号/组织信息；Cookie 与 session 文件内容同样不得进入版本控制。

> `base_url` 取自登录后浏览器实际跳转到的域名，可能与 `config.json` 中的 `loginUrl` 不同。后续所有 API 请求使用此值。

## 错误处理

各命令通过响应体 `errorCode` 自动处理登录态异常：

| errorCode | 含义 | 处理方式 |
|-----------|------|---------|
| `TIANSHU_000030` | CSRF Token 过期 | 在已授权账号内自动无头刷新 |
| `307` | Cookie 失效 | 在已授权账号内自动刷新登录态；需要切换账号/组织时须用户确认 |

## 异常处理

| 异常场景 | 处理方式 |
|---------|----------|
| 扫码超时 | 重新执行 `openyida login`，二维码有时效限制 |
| 登录后 Cookie 仍无效 | 检查 `.cache/cookies.json` 是否正确写入，执行 `openyida env` 验证 |
| 反复登录失败 | 停止重试，提示用户联系开发同学 @天晟，不要自主尝试其他登录方案 |
| CSRF Token 过期（TIANSHU_000030） | 在已授权账号内自动无头刷新，无需手动干预 |
| Cookie 失效（307） | 在已授权账号内自动刷新登录态；切换账号/组织须用户确认 |
