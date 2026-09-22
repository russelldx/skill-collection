# 验证范围与复现方法

本仓库不再使用“63 个 skill 全部可用”或“所有 agent 完全兼容”的结论。全文审查、结构检查、隔离脚本测试和真实平台验收是不同层次；一层通过不能代替另一层。本文中“通过”仅表示对应隔离测试通过，不代表技能在真实环境完成端到端验收。

## 结构验证

```bash
python validate-skills.py
bash validate-skills.sh
```

两条命令调用同一验证器，失败返回非零退出码。检查范围：

- `skills/` 下 55 个活动入口，必需 frontmatter 字段和名称唯一性。
- 不允许参考目录中嵌套 `SKILL.md`；归档入口改为 `REFERENCE.md`。
- `INDEX.md` 对活动技能的完整、无重复覆盖。
- 活动 `SKILL.md` 及根目录说明中的实际本地 Markdown 链接（不验证网页、锚点或代码示例）。
- 本地链接大小写，即使在 Windows 上也能发现 Linux 下失效的引用。
- MCP JSON 可解析，Chrome DevTools 包名正确，没有无效 claude-mem 包声明。

验证器只检查必需 frontmatter 字段，不是完整 YAML 解析器；也不执行技能自然语言指令或验证全部正文承诺。另用隔离安装的 PyYAML 6.0.3 对 55 个活动入口的 frontmatter 做过交叉解析（全部有效，0 错误）；该检查不替代运行时行为。

## 提交时的暂存树校验（只读）

`.githooks/pre-commit` 已替换为只读薄包装：它把 Git 索引中的对象物化到临时目录后用同一验证器校验，只输出提示和错误，**不复制、不暂存、不修改工作区或来源**。本机已将其安装为 `.git/hooks/pre-commit`，旧同步 hook 备份保留为 `.git/hooks/pre-commit.disabled`（勿启用）。行为边界：

- 暂存树违反仓库规范（入口数不符、空 description、失效链接、冲突阶段、非常规文件模式）→ 返回非零，阻止提交。
- 本机安装技能与仓库有无基线/差异只是提示行，不永久阻断无关提交。
- 当前工作区尚未把“整理工作”提交进索引，因此索引仍是旧的 63 入口树，hook 现在会以 19 项错误拦截；将本轮改动整体暂存后应恢复 55/0。这是预期行为，不是 hook 故障。

维护者可另用 `python sync-skills.py check` 只读对比本机安装技能与仓库；任何同步必须用显式 `apply` 命令逐文件复核方向与哈希，工具永远不自动同步、不删除入口。

## 隔离回归

在仓库根目录执行（Git Bash / POSIX shell）：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_repository_validation.py' -v
PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_skill_sync.py' -v
PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_mcp_smoke.py' -v
node --test skills/web-access/scripts/audit-safety.test.mjs
PYTHONUTF8=1 python -B skills/anthropic-xlsx/scripts/test_recalc.py
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_verify_media.py
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_gen_docx.py
PYTHONUTF8=1 python -B skills/xls-poi/scripts/test_paused.py
```

| 测试 | 本轮结果 | 实际覆盖 |
|------|----------|----------|
| 仓库验证器 | 17 项通过 | frontmatter 必填字段、链接大小写/相对路径、代码示例排除、索引、归档、MCP 包操作数及缺失命令 |
| 同步引擎与 hook | 48 项通过 | 临时 Git fixture：无变化/双方变化/无基线/刻意分叉/来源缺失与竞争/链接与越界拒绝/归档复活拒绝/敏感文件排除/部分暂存/并发修改/失败回退；每次比较执行前后文件与索引哈希；含真实 Bash 包装执行 |
| MCP smoke 检查器 | 25 项通过 | 注入内存流与假会话：初始化、分页、超时、清理、isError、结构校验、启动器拒绝、证据标签；不外连 |
| web-access 浏览器安全 | 12 项通过 | 注入假发现结果：严格选择、身份未确认拒绝复用、启动后身份复核、禁止备用探测、Proxy 复用与授权诊断；不启动浏览器或监听端口 |
| LibreOffice 重算 | 8 项通过 | 模拟外部进程，验证临时 profile、完成标记、失败/超时清理和 Windows 拒绝执行；**未真实重算** |
| DOCX 图片校验 | 4 项通过 | 比较媒体内容字节、发现缺图、错误输入及非零退出码 |
| 课程 DOCX 生成 | 3 项通过，无跳过 | 缺依赖预检查，以及使用现有 docx 包真实生成包含表格和图片的 DOCX，再校验媒体 |
| POI 删列停用 | 4 项通过 | 真实编译运行拒绝入口，确认输入/输出不变；其他命令只验证参数转发，不代表 POI 工作簿功能已验收 |

测试在临时目录中生成样本并清理，不使用真实用户文件。运行前需要现有 Python/openpyxl、Node.js、Java 和 Bash；DOCX 生成测试在缺少现有 docx 包时会明确跳过，不能把跳过记作通过。

此前会话曾发现：提交 `d6ed444` 的树因错误的同步 hook 用旧版本覆盖，未包含审计修复。其暂存对象（64 个 Git blob）仍存在于本地对象库；本轮已保存恢复前快照，并精确恢复 7 个安全相关脚本（重算、POI 拒绝入口、浏览器、DOCX 生成），上述测试即这些恢复的回归规格。其余参考文档候选的合入仍待逐项复核，未恢复不等于已丢失。

## 文档级静态审计（两批均已完成，修复已写入）

- 55 个活动入口全部完成逐文件静态审查：文档与联网类 28 个（65 项发现，`test-env/recovery-20260922/review-docweb.json`），流程与自创类 27 个（51 项发现，`review-workflows.json`）；两份 JSON 不随仓库发布。
- 审查发现已按范围修复（本轮共更新 80 余个 Markdown/参考文件与 7 个恢复脚本）。主要类别：
  - 授权边界：远程 issue/PRD 发布与标签需显式授权、全局 hooks 安装需独立授权、登录/登出/切组织需授权、凭据不得出现在聊天/日志/命令行、提交/安装/发布/发送不再默认执行。
  - 暂停一致性：`xls-poi` 删列/校验链标注 PAUSED，与脚本 exit 2 及 `poi_env.sh` 守卫一致；`POI_CLASSPATH` 要求写清。
  - 失效引用清理：不存在的 `/setup-*` 命令、未绑定的参考/模板文件、失效路径与锚点（如 `./visual-companion.md`、`./code-reviewer.md`）。
  - 隐藏强制行为：不再强制接管所有联网、不再自动链式调用缺失技能、不再自动提交设计文档、worktree 只读检测后才请求安装授权。
  - 平台假设：移除个人 Node 路径硬编码、uuidgen 依赖改为可移植方案、`claude -p` 段标注宿主专属。
- 仍留有的低优先级项（未修复）：`content-research-writer`、`superpowers-dispatching-parallel-agents`、`superpowers-receiving-code-review`、`superpowers-verification-before-completion` 等 5 项宿主措辞/不可验证引用类小问题；不影响授权与安全边界。
- 静态审查与文档修复不等于执行验证；修复后的技能未逐一在真实环境端到端执行。

## 许可与再分发

`anthropic-docx`、`anthropic-pdf`、`anthropic-pptx`、`anthropic-xlsx` 的现有 `LICENSE.txt` 明确限制复制、衍生与再分发；本地技术审查和修复不构成许可。未确认适用权利前，不应公开分发这些目录，也不应以仓库公开代替许可评估。其他只有来源名称、缺少完整许可条款的目录同样需要分别核验。

## MCP 分层验收（2026-09-22）

两条证据链分开记录；完整安全证据（版本、哈希、结果）见 `test-env/recovery-20260922/mcp-evidence.json`（不随仓库发布）。

| 项目 | 状态 |
|------|------|
| 项目 `.mcp.json` 示例 | 未证明在目标宿主被发现/启动；firecrawl 缺环境变量、chrome-devtools 被检查器按策略拒绝 npx（非宿主启动缺陷） |
| 已安装 Chrome MCP 1.9.0 | 经显式 Node 启动覆盖，协议初始化、29 个工具、`list_pages` 通过；未执行工具调用、未下载包 |
| 宿主 Chrome DevTools 工具 | 自建测试页创建/读取/截图/关闭通过；未操作用户原有页面 |
| Firecrawl CLI 1.16.0 | 认证、额度、一次官方公开文档抓取通过（可能消耗额度） |
| Firecrawl MCP | 额度调用 HTTP 401，未执行抓取；CLI 成功不能替代 MCP 认证 |
| claude-mem | 检索与语料库列表 worker fetch failed；AST 小样本未解析；未写入、未重启 worker |

`.mcp.json` 保持为示例文件（含 `${FIRECRAWL_API_KEY}` 展开写法）；未为本轮验收修改任何全局 MCP 配置、凭据或登录状态。

## 真实环境中仍需验证

| 路线 | 必须另行验证的内容 |
|------|------------------|
| 文档生成 | 本机依赖、实际文件打开、渲染质量、公式结果、格式和数据验证保留 |
| LibreOffice 重算 | 外部程序可用、临时 profile 隔离，以及重算输出的实际正确性；当前 Windows 明确拒绝，本机无 soffice |
| POI 删列 | 暂停；拒绝入口已验证，但工作簿保真能力不重新启用 |
| Chrome DevTools / web-access | 调试授权、浏览器/profile 归属、真实页面读取与交互；本轮只验证了注入式安全边界 |
| Firecrawl | MCP 认证修复后的 search/scrape/interact 各自功能与计费能力 |
| claude-mem | worker 和各项 MCP 工具在安装版本中的实际可用性 |
| 课程平台 | 题目和截止信息准确，提交状态有平台证据；上传/提交另需用户授权 |
| hooks / 循环 | 新只读 hook 已验证“阻断非法暂存树、不修改文件”；归档流程未启用，宿主事件与停止条件各平台未全部覆盖 |

此轮不因验证需要而上传本地文档、安装全局依赖、改动真实宏配置、注册额外 hooks 或执行课程提交。历史 `test-env/` 内容未随仓库发布，不能作为读者可复现的当前验收证据。

## 本机安装技能差异（只读对比，未写入）

对 55 个活动入口与 `~/.qoder/skills`、`~/.agents/skills` 做内容哈希对比（排除元数据与缓存；完整数据在 `test-env/recovery-20260922/local-compare.json`，不随仓库发布）。审计修复写入仓库后，当前 **45 个入口**与本机旧安装存在差异（修复前为 16 个）；仓库侧为已审阅版本，本机仍是旧副本。

- 建议优先同步（含 fail-closed 与授权边界修复）：`web-access`（2 个安全脚本 + 测试）、`xls-poi`（拒绝入口 3 文件 + 参考 + 测试）、`anthropic-xlsx`（recalc.py + 测试）、`course-assignment`（gen_docx.cjs + 校验脚本）。
- 文档级差异：firecrawl 系列、anthropic 系列、web-access、find-skills、yida-login、gen-prd、superpowers 系列等的措辞/链接/授权边界更新，可按需同步。
- 本机还装有 8 个已合并/暂停入口与 `daibi`、`tuomin`；本轮未删除、未改动任何本机文件。

写入本机 `~/.qoder/skills` / `~/.agents/skills` 必须逐项获得授权后另行执行；可用 `python sync-skills.py check` 查看逐文件哈希与状态，再用显式 `apply` 命令同步。本报告不代表已完成同步。
