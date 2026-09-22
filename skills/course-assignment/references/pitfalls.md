# 通用踩坑记录（跨科目复用）

按场景分组。每条：现象 → 根因/结论 → 处理。新坑随做随记并标日期。

## 学习通 / 超星平台（2026-09 实测）

- 登录报"手机号或密码错误" → 首次失败就停，请用户核对账号（曾遇用户口述笔误），**连续重试会触发账号锁定**
- 图片 CDN `p.ananas.chaoxing.com` 防盗链：curl 直接下载得到 HTML 而非图片 → 在浏览器新标签打开原图 URL，再 take_screenshot 保存
- 题面文本在 DOM 中完整存在，`evaluate_script` 提取即可，不必截图 OCR
- **红线**：作业提交动作（上传/粘贴/点击提交）必须等用户明确允许；子 agent 一律禁止碰提交平台
- **截止不等于提交证据**：没有用户明确确认或平台成功回执/可核对状态时，保持 `submission_status: UNKNOWN`；截止已过也不能默认已提交、勾选关闭提交待办或按已提交归档，交付完成与提交状态分开记录。2026-09-09 口径中只保留"不再反复追问等放行"，去掉按截止推断已提交的部分

## 浏览器 / 自动化

- Chrome 136+ 对**默认配置目录**忽略 `--remote-debugging-port`（不生成 DevToolsActivePort）→ 用独立 `--user-data-dir` + 固定端口
- web-access skill 的 CDP proxy 兜底模式连 `ws://.../devtools/browser`（无 UUID 路径）被新版 Chrome（152）拒绝（non-101 握手）→ 直接用 chrome-devtools MCP
- **chrome-devtools MCP 若只配 `npx chrome-devtools-mcp@latest`（无 `--browserUrl`），它是自己拉起 Chrome**，持久 profile 在 `~/.cache/chrome-devtools-mcp/chrome-profile`，登录态存在这里（2026-09-09 实测该库有 chaoxing/saucedemo Cookie）。手工起的 9222 独立调试实例 + 自定义 `--user-data-dir` 那套只是 MCP 起不来时的兜底，别默认去复现（当时那个 profile 已无监听、无 Cookie）
- React 应用（如 saucedemo）里 `el.value=` 直接赋值不触发组件状态更新，提交会误报"必填" → 用 fill_form 等真实输入方式
- 页面同时存在多个表单时 `document.forms[0]` 不一定是目标表单（曾误提交左栏登录表单）→ 用 `Array.from(document.forms).find(fm => fm.querySelector('[name=...]'))` 按字段定位
- chrome-devtools `evaluate_script` 的 args 只接受字符串数组（uid），非 uid 参数直接内嵌进函数体

## Windows 中文环境 / docx

- validate.py 报 GBK codec 错误（读 UTF-8 XML）→ 环境变量 `PYTHONUTF8=1`
- soffice.py 在 Windows 直接崩溃（依赖 Unix socket）→ 本机无 LibreOffice/pandoc/pdftoppm 时，**没有 docx→图 的渲染链路**，视觉校验降级为结构检查+直读源图，并如实声明
- **不要用 Word COM 自动导 PDF**（2026-09-05 两次踩坑）：① COM 实例退出失败残留不可见 WINWORD（`MainWindowHandle=0`）死锁输出目录的 docx/pdf，还留 `~$` 锁文件；② 强杀后下次 COM 启动弹不可见"恢复/安全模式"对话框，`ExportAsFixedFormat` 永不返回 → 需要 PDF 时让用户在 WPS/Word 里手动"另存为"
- 重新生成 docx 报 `EBUSY` → 先 `Get-Process wps,WINWORD` 看 `MainWindowHandle`：**非 0 是用户自己开着文档**，请用户关闭，绝不强杀用户正在编辑的进程；为 0 的不可见实例才是自动化残留，可安全清理并删 `~$` 锁文件
- **用户在 WPS/Word 里打开并另存过交付 docx 后，该文件即不再可信**（2026-09-05 实测）：体积和段落数会变（855950B/440 段 → 528841B/434 段，图片被重压缩），且 `word/styles.xml` 里 `w:uiPriority` 元素顺序被改坏，严格校验由 PASSED 变 FAILED。所以**内容源 md 是唯一权威**，最终版一律 `node gen_docx.cjs` 重新生成，绝不在用户另存过的 docx 上增量改
- PowerShell 5.1 把 UTF-8 **无 BOM** 的 .ps1 按 GBK 解码，硬编码中文路径变乱码 → 脚本只用 ASCII 内容，或用 pwsh 7
- Git Bash 会展开双引号里 PowerShell 命令的 `$var`/`$_` → 把命令写进 .ps1 用 `-File` 执行，或改用无 `$` 的写法
- 全局 npm 包（docx）不在本地 node_modules → 先运行本 skill 实际路径下 `scripts/gen_docx.cjs --check-deps`；生成器会检查本地/NODE_PATH 与已有 `npm root -g`。也可由用户指定实际的 NODE_PATH；不要复制个人机器路径，不自动安装

## 文档撰写

- 中文 markdown 上 Edit 工具多行 old_string 偶发 0 匹配（疑似行尾差异）→ 拆单行编辑
- 全篇数字/日期前后不一致是最高频缺陷（用例数、通过数、日期范围）→ 定稿前 grep 所有数字与日期统一核对
- 证据截图里出现的账号/标识符，正文"测试环境/材料"一节必须能对上 → 嵌入截图前做一次交叉检查
- 课程作业用学生口吻；被指出"太专业"时，砍咨询腔术语，保留方法、数据与模板结构
