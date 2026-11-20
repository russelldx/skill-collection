# 验证范围与复现方法

本仓库不再使用“64 个 skill 全部可用”或“所有 agent 完全兼容”的结论。全文审查、结构检查、隔离脚本测试和真实平台验收分属不同层次；通过其中一层，不能代替另一层的检查。本文中“通过”只表示对应的隔离测试通过，不代表技能已在真实环境中完成端到端验收。

## 结构验证

```bash
python validate-skills.py
bash validate-skills.sh
```

两条命令调用同一验证器，验证失败时返回非零退出码。检查范围：

- `skills/` 下 65 个活动入口（新增 `shuorenhua`）是否具备必需的 frontmatter 字段，名称是否唯一。
- 不允许参考目录中嵌套 `SKILL.md`；归档入口改为 `REFERENCE.md`。
- `INDEX.md` 是否完整列出活动技能，且没有重复。
- 活动 `SKILL.md` 及根目录说明（含 INSTALL、SKILL-GUIDE）中的实际本地 Markdown 链接；默认不验证网页、锚点或代码示例。显式加 `--installation-guide` 时，另检查新手指南的卡片覆盖、必填内容与显式导航锚点。
- 本地链接的大小写，即使在 Windows 上也能发现 Linux 下会失效的引用。
- MCP JSON 能否解析，Chrome DevTools 包名是否正确，是否存在无效的 claude-mem 包声明。

验证器只检查必需的 frontmatter 字段，不是完整的 YAML 解析器；它也不会执行技能中的自然语言指令，或验证正文中的全部承诺。另用隔离安装的 PyYAML 6.0.3 对 55 个活动入口的 frontmatter 做过交叉解析（全部有效，0 错误）；这项检查不能代替对运行时行为的验证。

下文的**逐文件静态审查**、**内容哈希对比**和 **PyYAML 交叉解析**中的「55 个」，指当时实际覆盖的那批入口。不含本轮新装的 8 个 Firecrawl 检索/集成入口，也不含本轮删除的孤儿文件所属入口之外的新增内容。统一抬高这些数字，会把没做过的检查也算进覆盖范围，因此保留原值。新装的 8 个入口目前只经过结构、frontmatter、本地链接与凭据扫描，未做逐文件静态审查和端到端运行验证。本轮唯一被撤下的测试覆盖是 `test_recalc.py`（见上表），不涉及入口计数。表中「同步引擎与 hook 55 项通过」的 55 是 unittest 用例数，与活动入口计数无关。

## 新手安装向导与组件说明验证（2026-11-20）

本次新增 [INSTALL.md](INSTALL.md) 对话式安装向导和 [SKILL-GUIDE.md](SKILL-GUIDE.md)，补齐 [MCP-SETUP.md](MCP-SETUP.md) 五类连接说明，并接入 README 与 INDEX。没有增加自动安装程序、新 Skill 或文档生成器，也没有修改已安装技能、真实 MCP 配置、全局规则或 hooks。

- 说明卡：按当前 65 项 Skill 正文及必要参考撰写，八类共 65 张卡；MCP 为 Firecrawl、Chrome DevTools、Snipaste、claude-mem、DBX 五张卡。每张含七项说明，分别说明用途、适用对象、准备条件、配置、用法、验证和注意事项。主会话完整通读实稿；MCP 的版本敏感说明另查官方来源，具体来源及未确认项列在该指南中。
- 结构检查：`python -B validate-skills.py --installation-guide` 返回 65 个活动入口、0 错误。检查卡片与实际入口一一对应、重复或过期 ID、七字段非空、路径大小写和显式导航锚点；六个 MCP JSON 示例均可解析。默认验证和 hook 不强制要求安装文档，只有显式开关才启用这些附加规则。
- 校验器回归：41 项通过，原有 17 项保留，新增 24 项。新规则先写失败测试再实现；独立审查又发现 HTML 注释中的卡片、字段和锚点被误计，以及同行重复字段漏检，补充反例后逐项修复。内联代码示例不会被当成重复字段，可见代码内容也不会被注释过滤误删。
- 审查取舍：采纳隐藏内容与重复字段的修复；未采纳“每个字段只能一段”的额外限制。批准范围要求七字段各出现一次且内容非空，并未禁止补充分段说明；README 已明确允许复杂步骤另分段展开，并有正例测试保护。
- 最终完整隔离回归：修复审查发现后，运行下方 `unittest discover` 命令，177 项全部通过，0 失败、0 跳过，用时 792.482 秒；包含验证器 41 项、同步引擎 55 项、MCP smoke 25 项、交接 56 项。此前分组执行的 113 项和 56 项也通过，但不把重复运行累加成新的覆盖数。
- 只读对话推演：由未参与正文编写的代理，仅依据安装向导与 README，走查不懂选推荐、拒绝全局规则、缺密钥、只选 CLI、本机登录态、非 Windows 选择 Snipaste、数据库归属未知、已有定制技能和取消九种情景，未发现指令冲突。这是文本推演，不是真实新手安装或用户体验测试。
- 后续流程简化：按用户要求，安装与更新共用对话入口，先选择和确认，获准后才操作。原样复制 Skill 只核对文件完整性与目标位置，不要求运行功能测试、回归套件或新会话试题；卡片的“如何验证”保留为按需参考。此调整仅改读者文档，未改校验器或技能脚本；上面的 177 项仍指该版本代码的隔离回归，不代表运行了实际安装。
- 已有功能限制：卡片明确提示 `superpowers-executing-plans/scripts/task-start` 的兄弟目录名与本仓库前缀不符，以及 SDD 的 INDEX 两轮描述与参考文件五轮上限不一致。未为编写指南修改这些 Skill，也未将相应执行分支记为可用。

复现本次完整隔离套件：

```bash
PYTHONUTF8=1 python -B validate-skills.py --installation-guide
PYTHONUTF8=1 bash validate-skills.sh --installation-guide
PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_*.py'
```

未执行真实安装、MCP 服务调用、登录、截图、上传、数据库操作或收费请求。本机没有可用的 Markdown 渲染器，未做渲染预览；文档结构与来源核对不能证明五类服务已经连通，也不能证明 65 项技能全部可用。Git 差异核对和限定文件的凭据特征检查不替代完整安全审计；本轮不包含用户导出文本或个人配置。

## shuorenhua 中文表达验证（2026-11-17）

本次新增 `shuorenhua`，活动入口 64→65；历史的 55/63/64 入口记录不改写成新覆盖范围。上游来源和 MIT 许可见该 skill。只提交独立的中文规则模板，不收录个人全局配置。

- 静态检查：补齐 `~/.qoder/rules/chinese-writing.md` 的 `trigger: always_on`，修正“功能词必须逐字保留”与“默认只能删除语法赘词”的限制；检查新稿、只要正文、标注和修订模式下，哪些情况应附摘要、哪些不应附。
- 真实启动：Qoder CLI 1.1.90，用临时工作目录，在无工具、无 MCP、非持久化模式下启动新进程，未在提问中提供 skill 名称；返回 `shuorenhua` 并按已加载规则改写测试句，保留了批准条件、日期、完整性、效率目的、未开始状态，以及不支持自动提交这一否定。
- 真实 skill 调用：另一次临时 CLI 运行只开放 `Skill` 工具；stream-json 中记录了 `Skill(shuorenhua)`。四个独立用例分别验证完整信息与默认摘要、只要正文、只标问题、程序代码块及未具名来源保护；逐项核对原文与输出后，保护片段和输出模式检查通过。
- 实际例子：“用于复核”改为“用来复核”，保留“不支持自动提交”；“以提升效率”改为“来提高效率”，保留“完整工作链路”。代码、注释和字符串逐字未变，未具名专家的归因与“可能”仍在正文中。
- 交接入口：中文约定放入 `session-handoff/SKILL.md` 核心；模板中的一行只作提示。`handoff.py init` 不读该 Markdown 模板，`context` 也不保证收录附加节。因此，不能因为模板已写入文件，就宣称这些约定会自动继承。
- 新稿补测：初次的摘要标签检查通过，但逐句审阅发现，输出擅加了“本周五”“维护完成后即恢复正常”，还在未改原文时附了评价；补充断言后这三项失败。收紧新稿对时间、承诺和原样输出的限制后，用同题及新增的试用反馈/未来功能说明复测。正文保留了限定、状态和原样文本，8 项片段及模式检查通过。组合测试仍附了总体说明，不能据此承诺任意请求都能严格只输出正文。
- 仓库回归：`PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_*.py' -v`，140 项通过，0 失败、0 跳过（含交接 43 项、MCP smoke 25 项、结构验证器 17 项、同步引擎 55 项）。交接脚本另单独运行 43 项也通过，不叠加为新的用例数。

以上是有限样本实测，不是 AI 检测评分，不保证任意文本或任意模型都无信息损失。脚本只核对实际输出的关键片段与模式，含义是否完整仍需逐句审阅。

### 全部中文回复与默认安装组合补测（2026-11-18）

- 安装入口：README、INDEX、shuorenhua 与 session-handoff 均说明默认推荐 `shuorenhua + 全局规则`；全局写入仍需明确授权，按当前宿主适配路径，并分别报告 skill 安装、规则写入、实际加载验证的状态。六个改动文件的独立只读审查未发现授权或摘要规则冲突；没有在其他宿主执行安装。
- 真实回复：用 Qoder CLI 1.1.90 在临时目录启动新进程，禁用工具和 MCP，不持久化会话，也不在提问中粘贴规则。组合题覆盖进度说明、代码解释和改写；只有改写部分附了改动摘要，但首次进度正文擅加了“跑完测试后提交并同步”的承诺，不能把这次输出整体计为通过。
- 同题复测：补充“未提供的后续安排须单列为建议，不能放进可直接发送的正文中替用户承诺”后，进度正文只写代码已修改、测试未跑、尚未提交；后续安排另列，并明确以用户确认安排为前提。代码解释保留乘法及字符串/列表重复行为；改写保留管理员批准条件、复核用途、提高效率的目的和自动提交尚未启用的状态。
- 只要正文：另一次新进程保留“周五”“预计两小时”“尚未安排补偿”“仅影响试用用户、不影响付费用户”，没有改动摘要，没有补“本周五”或恢复保证。该项在上述进度规则补充前完成。
- 本地检查：结构验证为 65 个入口、0 错误；`test_repository_validation.py` 的 17 项测试通过。四个相关 skill 文件的仓库与安装副本逐字节相同，实际全局规则也与模板相同；第二次同步因仓库文件尚未提交而被脚本拒绝，未关闭检查或自动提交，随后仅在本轮编辑的两处文本中应用相同修订。shuorenhua 的两个文件因此为 `equal-unbound`，已有同步基线待后续提交时复核，另外两个文件为 `equal`。

本轮验证的是这些样本在本机配置下的实际输出，不是所有模型都能遵守规则的保证；未导出宿主完整加载清单，也未验证其他 agent 的全局加载。未改动 AGENTS.md、全局 hooks 或权限设置。

## 提交时的暂存树校验（只读）

`.githooks/pre-commit` 已替换为只读的简单包装脚本：它先把 Git 索引中的对象写入临时目录，再用同一验证器校验。脚本只输出提示和错误，**不复制、不暂存、不修改工作区或来源**。本机已将其安装为 `.git/hooks/pre-commit`，旧同步 hook 的备份保留为 `.git/hooks/pre-commit.disabled`（勿启用）。行为边界：

- 暂存树违反仓库规范（入口数不符、空 description、失效链接、冲突阶段、非常规文件模式）→ 返回非零，阻止提交。
- 本机安装技能与仓库之间是否有基线、是否有差异，都只作为提示显示，不会永久阻断无关提交。
- 当前活动入口数为 65。历史的 `docx-meta` 批次从 63 增至 64 时，hook 实测 exit 0 并输出 `Active entries: 64; errors: 0`；这不是新增 `shuorenhua` 后的验证结果。历史提交 `d6ed444` 的索引曾是 63 入口旧树（hook 会以 19 项错误拦截）；修复提交 `96139fa` 后已恢复。索引含未暂存修改时，hook 只校验索引副本，不受工作区影响。

维护者也可以用 `python sync-skills.py check` 只读对比本机安装技能与仓库。任何同步都必须使用显式 `apply` 命令，逐文件复核方向与哈希；工具永远不自动同步，也不删除入口。导出到本机前，需先审阅差异，并用 `approve` 记录哈希绑定（方向与双侧哈希任一变化即失效）。

## 隔离回归

在仓库根目录执行（Git Bash / POSIX shell）：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_repository_validation.py' -v
PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_skill_sync.py' -v
PYTHONUTF8=1 python -B -m unittest discover -s tests -p 'test_mcp_smoke.py' -v
node --test skills/web-access/scripts/*.test.mjs
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_verify_media.py
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_gen_docx.py
PYTHONUTF8=1 python -B skills/docx-meta/scripts/test_docx_meta.py
PYTHONUTF8=1 python -B skills/xls-poi/scripts/test_paused.py
```

| 测试 | 本轮结果 | 实际覆盖 |
|------|----------|----------|
| 仓库验证器 | 17 项通过 | frontmatter 必填字段、链接大小写/相对路径、代码示例排除、索引、归档、MCP 包操作数及缺失命令 |
| 同步引擎与 hook | 55 项通过 | 临时 Git fixture：无变化/双方变化/无基线/刻意分叉/来源缺失与竞争/链接与越界拒绝/归档复活拒绝/敏感文件排除/部分暂存/并发修改/失败回退，以及审阅导出时绑定哈希与方向、容忍 `core.autocrlf` 检出时产生的字节差异；每次都比较执行前后的文件与索引哈希；也包含真实执行 Bash 包装脚本的测试。包装器用例原先把活动入口数写死为 55，修改默认值就会失败；现在根据 `hook.__defaults__[0]` 确定 fixture 数量与断言。pre-commit 不运行本套件，所以入口数变更后须手工运行一次 |
| LibreOffice 重算 | 无自动化覆盖 | 原 mock 回归 `test_recalc.py` 对重构后的 `recalc.py` 跑出 1 项失败 + 8 项错误（`recalc.signal` 已不存在），已删除；`recalc.py` 本体仍在，重算只在"真实环境中仍需验证"一节记录 |
| MCP smoke 检查器 | 25 项通过 | 注入内存流与假会话：初始化、分页、超时、清理、isError、结构校验、启动器拒绝、证据标签；不外连 |
| web-access 上游套件 | 227 项通过、3 项跳过（11-20，v2.6.0） | 8 个上游测试文件：浏览器发现/探测、CDP 连接与代理、check-deps 身份复核与偏好、page-frames、proxy-maintenance、user-data 迁移；夹具在临时目录生成，不启动真实浏览器或监听端口。测试夹具的 `--import` 裸路径在 Windows 报 `ERR_UNSUPPORTED_ESM_URL_SCHEME`，已本地补 `pathToFileURL`（5 处，属本地定制）。旧 `audit-safety.test.mjs` 已退休（见下节） |
| DOCX 图片校验 | 4 项通过 | 比较媒体内容字节、发现缺图、错误输入及非零退出码 |
| 课程 DOCX 生成 | 3 项通过，无跳过 | 缺依赖预检查，以及使用现有 docx 包真实生成包含表格和图片的 DOCX，再校验媒体 |
| DOCX 元数据清理 | 仓库侧与安装侧各 26 项通过 | 保留原清理/注册/时间线/作者覆盖测试；新增初次基线、WPS 清零/缺失恢复、绝对覆盖与手动追加、原生累计值去重、增删改文本、重复文字小改动、重复运行与空闲时间不计入、纯排版不编造耗时、改名续接、页数覆盖、只读预演、损坏/锁定基线拒绝；通过注入文件替换失败，验证基线不前移；也验证基线保存失败时，不丢失修改时间锚点。样本与状态均在临时目录 |
| POI 删列停用 | 4 项通过 | 真实编译运行拒绝入口，确认输入/输出不变；其他命令只验证参数转发，不代表 POI 工作簿功能已验收 |

测试在临时目录中生成样本并清理，不使用真实用户文件。运行前需要现有 Python/openpyxl、Node.js、Java 和 Bash；DOCX 生成测试在缺少现有 docx 包时会明确跳过，不能把跳过记作通过。

### docx-meta 累计模式的 Windows 属性验收（2026-11-01）

对一份独立的临时 DOCX，先设置 90 分钟并建立基线，模拟编辑器把包内 TotalTime 清零，再显式追加 15 分钟。Windows Shell `System.Document.TotalEditingTime` 读取为 105 分钟，详细属性显示 `01:45:00`。随后模拟等长替换一个英文词并再次清零，自动估算的增量为 1 分钟，累计得到 106，普通重跑仍为 106；Shell 显示 `01:46:00`。回归测试验证了原正文/媒体保留，基线位于 DOCX 包外。

这证明当前 Windows 属性处理程序能显示包内数值，但不是 Word/WPS GUI 的真实编辑保存测试，也不证明估算分钟数就是实际耗时。未修改任何用户交付文档或实验三的项目 wrapper。

### docx-meta 累计模式维护时发现的独立失败（2026-11-01）

`node --test skills/web-access/scripts/audit-safety.test.mjs` 的以下 10 项在本次实现之前即失败，web-access 没有修改；不将其计为通过，也不在元数据任务中顺手修复：

- `checker keeps explicit mismatch strict even if a separate port could be available`
- `checker asks before persistence and leaves temporary selection available`
- `wrong-browser proxy reuse refuses without spawning or killing a process`
- `proxy explicit mismatch does not fall back or claim a proven toggle failure`
- `proxy rejects a changed pinned browser with precise, permission-bound guidance`
- `proxy retains its pin when browser disappears`
- `safe diagnostics replace batch-kill and global-install advice in both entry points`
- `explicit selection refuses reuse when browser identity is unknown`
- `checker verifies browser identity again after proxy startup`
- `ambiguous browser selection never probes the fallback port`

对于上游重构后已删除的回归测试与文档，本轮按"先提交删除、再退休同步基线"处理，不在仓库里留下必然失败或自我矛盾的条目。`anthropic-xlsx/scripts/test_recalc.py` 对重构后的 `recalc.py` 跑出 1 项失败 + 8 项错误，因此连同其命令行一起撤下（见上表）。同时删除了 `anthropic-pptx`/`anthropic-xlsx` 的 `scripts/office/{pack,unpack}.py` 与 `helpers/{merge_runs,simplify_redlines}.py`：相关能力已并入 `helpers/__init__.py` 的 `safe_extract`/`rezip`，新 `SKILL.md` 改用 `zipfile.extractall` 与 `zip -Xr` 一行命令。另外也删除了 `anthropic-pptx/editing.md`、`pptxgenjs.md`：内容已合并进精简后的 `SKILL.md`，而且 `editing.md` 仍在指导读者调用上游已不存在的 `pack.py`/`unpack.py`。`anthropic-docx` 保留自己的一份 `pack.py`/`unpack.py`，不受影响。被删文件均可从提交 `d3f170b` 取回；如需把 Smart Quotes、Multi-Item Content、Template Adaptation 或 pptxgenjs 图表示例重新讲清楚，应显式提出，再将内容补回 `SKILL.md`，而不是保留过期副本。

此前会话曾发现：错误的同步 hook 用旧版本覆盖了提交 `d6ed444` 的树，导致其中未包含审计修复。其暂存对象（64 个 Git blob）仍存在于本地对象库。本轮已保存恢复前快照，并精确恢复了 7 个安全相关脚本（重算、POI 拒绝入口、浏览器、DOCX 生成），上述测试就是检查这些恢复结果的回归规格。其余候选参考文档能否合入，仍需逐项复核；未恢复不等于已丢失。

### web-access v2.6.0 更新与审计测试退休（2026-11-20）

web-access 合并更新至上游 `d173a75`（v2.6.0，浏览器发现重做、用户数据迁出 Skill 目录到 `~/.web-access/`、iframe 能力）。本地 `audit-safety.test.mjs` 针对 v2.5.4 内部 API，10-23 那轮就已 10/12 失败（见上节），本轮对 v2.6.0 全 12 项失败，均为 API 过期而非安全回归；其断言面（严格身份不匹配、复用不杀进程、持久化前询问、身份未知拒绝复用等）已由上游 `check-deps.test.mjs` 等 8 个测试文件覆盖，故退休该文件，回归命令行改为 `node --test skills/web-access/scripts/*.test.mjs`。被删文件可从提交 `b3d20f7` 之前的历史取回。

上游测试夹具在 Windows 有一处平台 bug：`spawn(node, ['--import', <裸绝对路径>, ...])` 报 `ERR_UNSUPPORTED_ESM_URL_SCHEME`。本地对 5 个测试文件补 `pathToFileURL(...).href`（browser-discovery/browser-probe/cdp-proxy/check-deps/proxy-maintenance），补丁后全套 227 过 0 败 3 跳过。这 5 处是本地定制，下次上游更新这些测试文件时要重新带上。

上节「anthropic-docx 保留自己的一份 pack.py/unpack.py」已被 11-20 anthropic 更新取代：docx 也迁移到上游新修补管线（zipfile + merge_runs + zip），pack/unpack/helpers 旧脚本一并退休，见提交 `1e910cf`。

## 文档级静态审计（两批均已完成，修复已写入）

- 55 个活动入口已全部完成逐文件静态审查：文档与联网类 28 个（65 项发现，`test-env/recovery-20260922/review-docweb.json`），流程与自创类 27 个（51 项发现，`review-workflows.json`）；两份 JSON 不随仓库发布。
- 审查发现的问题已按范围修复（本轮共更新 80 余个 Markdown/参考文件与 7 个恢复脚本）。主要类别：
  - 授权边界：发布远程 issue/PRD 及设置标签需显式授权；安装全局 hooks 需独立授权；登录/登出/切组织需授权；凭据不得出现在聊天/日志/命令行；提交/安装/发布/发送不再默认执行。
  - 暂停一致性：`xls-poi` 删列/校验链标注 PAUSED，与脚本 exit 2 及 `poi_env.sh` 守卫一致；`POI_CLASSPATH` 的要求必须写清。
  - 失效引用清理：不存在的 `/setup-*` 命令、未绑定的参考/模板文件、失效路径与锚点（如 `./visual-companion.md`、`./code-reviewer.md`）。
  - 隐藏强制行为：不再强制接管所有联网、不再自动链式调用缺失技能、不再自动提交设计文档；worktree 只有完成只读检测后，才请求安装授权。
  - 平台假设：移除硬编码的个人 Node 路径，将 uuidgen 依赖改为可移植方案，并将 `claude -p` 段标注为宿主专属。
- 仍留有的低优先级项（未修复）：`content-research-writer`、`superpowers-dispatching-parallel-agents`、`superpowers-receiving-code-review`、`superpowers-verification-before-completion` 等 5 项涉及宿主措辞/不可验证引用的小问题；不影响授权与安全边界。
- 静态审查与文档修复不等于执行验证；修复后的技能未逐一在真实环境端到端执行。

## 许可与再分发

`anthropic-docx`、`anthropic-pdf`、`anthropic-pptx`、`anthropic-xlsx` 的现有 `LICENSE.txt` 明确限制复制、衍生与再分发；本地技术审查和修复不构成许可。未确认适用权利前，不应公开分发这些目录，也不应以仓库公开代替许可评估。其他只有来源名称、缺少完整许可条款的目录同样需要分别核验。

## MCP 分层验收（2026-09-22）

两条证据链分开记录；完整安全证据（版本、哈希、结果）见 `test-env/recovery-20260922/mcp-evidence.json`（不随仓库发布）。

| 项目 | 状态 |
|------|------|
| 项目 `.mcp.json` 示例 | 未证明在目标宿主被发现/启动；环境变量就绪后 firecrawl 预检由 `missing_environment` 变为检查器策略拒绝 npx，chrome-devtools 同样被策略拒绝 |
| 已安装 Chrome MCP 1.9.0 | 经显式 Node 启动覆盖，协议初始化、29 个工具、`list_pages` 通过；未执行工具调用、未下载包 |
| 宿主 Chrome DevTools 工具 | 自建测试页创建/读取/截图/关闭通过；未操作用户原有页面 |
| Firecrawl CLI 1.16.0 | 认证、额度、一次官方公开文档抓取通过（可能消耗额度） |
| Firecrawl MCP | 2026-09-22 用户提供 Key 并设置用户级 `FIRECRAWL_API_KEY` 后，隔离安装 firecrawl-mcp 3.25.2 实测通过：29 工具、`firecrawl_credit_usage` 返回 999/1000（isError=false）；原 401 解除，客户端重启后对其生效 |
| claude-mem | 检索与语料库列表 worker fetch failed；AST 小样本未解析；未写入、未重启 worker |

`.mcp.json` 仍是示例文件（含 `${FIRECRAWL_API_KEY}` 展开写法）。本轮唯一的本机配置变更，是按用户提供的 Key 设置用户级环境变量 `FIRECRAWL_API_KEY`；未写入任何配置文件，也未改客户端 MCP 条目或登录状态。移除方法见 MCP-SETUP.md 实测结果 一节。

## 真实环境中仍需验证

| 路线 | 必须另行验证的内容 |
|------|------------------|
| 文档生成 | 本机依赖、实际文件打开、渲染质量、公式结果、格式和数据验证保留 |
| LibreOffice 重算 | 外部程序可用、临时 profile 隔离，以及重算输出的实际正确性；当前 Windows 明确拒绝，本机无 soffice；针对重构后 `recalc.py` 的 mock 回归已撤下，此路线当前无任何自动化覆盖 |
| POI 删列 | 暂停；拒绝入口已验证，但工作簿保真能力不重新启用 |
| Chrome DevTools / web-access | 调试授权、浏览器/profile 归属、真实页面读取与交互；本轮只验证了注入式安全边界 |
| Firecrawl | MCP 认证修复后的 search/scrape/interact 各自功能与计费能力 |
| claude-mem | worker 和各项 MCP 工具在安装版本中的实际可用性 |
| 课程平台 | 题目和截止信息准确，提交状态有平台证据；上传/提交另需用户授权 |
| hooks / 循环 | 新只读 hook 已验证“阻断非法暂存树、不修改文件”；归档流程未启用，宿主事件与停止条件各平台未全部覆盖 |

此轮不因验证需要而上传本地文档、安装全局依赖、改动真实宏配置、注册额外 hooks 或执行课程提交。历史 `test-env/` 内容未随仓库发布，不能作为读者可复现的当前验收证据。

## 本机安装技能同步（2026-09-22 执行，经用户授权）

对 55 个活动入口与 `~/.qoder/skills`、`~/.agents/skills` 做了内容哈希对比（排除元数据与缓存；完整数据在 `test-env/recovery-20260922/local-compare.json`，不随仓库发布）。审计修复写入仓库后，曾有 45 个入口与本机旧安装存在差异（修复前为 16 个）。

经用户授权后，用 `sync-skills.py` 的显式流程执行了一次性同步（驱动脚本 `test-env/sync-local.py`：逐文件 `bind` → `approve` 登记审阅哈希 → `apply --direction export`）。每次写入前，都先做全量预检，并将每个文件备份到 `.git/skill-sync/<hash>/backups/`；失败时回滚，且不改动基线。

- 结果：**81 个文件导出写入本机**（含 web-access 安全脚本与测试、xls-poi 拒绝入口与参考、anthropic-xlsx 重算脚本、course-assignment DOCX 生成/校验脚本，以及 firecrawl、anthropic、superpowers、session-handoff 等系列的文档更新），101 个相同文件登记共同基线，0 跳过、0 失败；593 个受管文件全部有共同基线，无遗留的导出许可。
- 复评（同步后重跑 `test-env/local-compare.py`）：**55 个入口中 54 个完全一致**；唯一剩余差异为 `session-handoff/hooks/`（该目录含可执行 hook，按设计不参与自动同步，其 README 差异保留，待人工处置）。
- 未改动：8 个已合并/暂停入口、`daibi`、`tuomin`、安装锁文件与任何全局 hooks；未删除任何本机文件。
- 真实环境缺陷修复：本机 Git 的 `core.autocrlf=true` 使干净检出的文本文件为 CRLF 工作区 + LF blob。旧实现按裸字节判"未暂存修改"，导致导出时对 17+ 个已提交文件误报失败。现在只在 autocrlf=true 且文件为文本时，接受这种规范化等价（autocrlf 关闭时同字节仍判脏）。回归见 `tests/test_skill_sync.py` 的 `test_export_accepts_committed_autocrlf_worktree_bytes`。

导出授权机制：`approve FILE --repo-hash H --source-hash H` 把当时的双侧哈希登记为一次性许可。如果仓库侧未提交、来源或仓库内容在写入前变化，或目标有并发修改等，都会拒绝写入；成功后清除许可并更新基线。可随时用 `python sync-skills.py check` 只读复核。
