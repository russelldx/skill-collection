# Skill Collection — AI Agent 技能合集

请按任务选择技能，不要全量安装。Skill 提供做事的流程，MCP/CLI 提供工具，两者不能互相替代。

> **中文沟通的默认推荐组合：`shuorenhua + 全局规则`**。不论任务是不是写文章，日常问答、进度说明、代码解释、操作指导和最终总结都是写给用户看的中文回复。安装时必须主动提出这套组合；全局规则写入需明确授权，获准后安装并验证实际加载，不能只安装 skill 就算全局配置完成。

> **核心入口：`session-handoff`**。它用于跨会话交接、专家团角色协作，也支持在 Qoder CLI 的同一会话内派发并行 agent。任务需要跨多个会话、分批推进，或需要把踩过的坑留给后续会话时，默认推荐安装。如果 agent 决定不推荐，必须在清单里说明理由，不能直接跳过。

本仓库现有 **65 个活动入口**，另有 4 个已合并为参考资料的入口和 4 个暂停入口。活动入口中，8 个检索与集成入口是在用户授权后从上游 `firecrawl/cli`、`firecrawl/skills` 新增的；`docx-meta` 元数据入口（默认保留、`--clean` 清理）和 `shuorenhua` 中文编辑入口由本地维护。

目前检查了文档、目录结构，并对部分脚本做了回归测试。这不代表所有技能都已在所有平台上运行通过。新增的 8 个 Firecrawl 入口与 `docx-meta` 具体验证了什么，见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

## 快速开始

**安装或更新，都从 [新手安装向导](INSTALL.md) 开始。** 它会让 AI 助手像安装软件一样带你选用途、看组件说明、检查准备条件，确认后再操作；这是一套对话步骤，不是自动安装程序。原样复制本合集的 Skill，只核对文件和目标位置，不要求跑测试或调用外部服务；已有同名内容仍先比较并备份。

| 你想知道什么 | 从哪里看 |
|---|---|
| 不知道该选什么，想一步步安装 | [安装向导](INSTALL.md#start) |
| 每个 Skill 能做什么、怎么配置、怎么用 | [65 项中文说明卡](SKILL-GUIDE.md) |
| MCP 和账号怎么配置、怎么检查连接 | [MCP 配置指南](MCP-SETUP.md) |
| 已经熟悉，只想快速查名字 | [简明索引](INDEX.md) |

把本仓库地址或本地目录交给你的 AI 助手，再复制这段话：

> 请按本仓库的 INSTALL.md 发起安装或更新对话，先不要执行安装。确认我使用的助手、系统和用途，展示用途分类，再只展开与我有关的组件。每项用中文说明用途、准备条件、配置步骤、使用示例和注意事项；不要只列英文名字。我不清楚时帮我推荐，但不要默认全装。动手前列出实际路径、依赖、已有内容差异和设置影响，等我确认；全局规则、MCP、凭据、全局依赖与 hooks 分别确认。原样安装不用跑测试，只核对文件和目标位置；最后说明安装结果与尚未配置的项目，给每项一句可以直接使用的请求，不宣称未测试的功能已验证。

- **先选用途，再看细项。** 全部分类都能查看；默认只展开所选分类，其他分类说明暂不安装。选择“查看全部”时再按分类展开完整清单，不一开始就让新手读满 65 项。
- **中文沟通主动推荐 `shuorenhua + 全局规则`。** 推荐不等于已授权；拒绝全局规则仍可单独安装 Skill，不能因此声称所有对话自动生效。
- **跨会话、分批推进或协作时推荐 `session-handoff`。** 没有选择时说明理由；不为简单任务强行建交接体系。
- **只安装确认的活动入口。** 先核对来源、许可和依赖；已有同名内容先比较并保留，更新前明确备份和合并方式。归档与合并参考不是独立安装选项。
- **缺少账号或软件可以稍后配置。** 不要求把密钥发到聊天中，不复制维护者的个人配置；没有验证的能力如实标注。用户拒绝某项后不反复劝装。

熟悉操作的用户可以手动复制选定的 `skills/<目录名>/`，目标由宿主决定，例如 Qoder 的项目级 `.qoder/skills/` 或用户级 `~/.qoder/skills/`。复制前确认目标不存在或已经明确同意更新，保留配套文件与目录结构；不要递归复制整个仓库，也不要执行 `skills/*` 全量安装。各宿主的加载位置、同名优先级和启用方法须按当前官方说明确认，不照搬其他机器的路径。

### 中文回复的全局规则（安装时必查）

`shuorenhua` 的 [简短规则模板](skills/shuorenhua/assets/chinese-writing.md) 应与 skill 一起作为默认推荐项。规则覆盖所有面向用户的中文回复，不限于成稿、演示或润色：说清事情，保留独立信息，不擅自删减或编造事实。普通回复不附改动摘要；用户要求改写已有文字且确有改动时才默认附上，说“只要正文”则省略。

- **确认位置和授权。** Qoder CLI 使用 `~/.qoder/rules/chinese-writing.md`，以 `trigger: always_on` 常驻加载，不是根目录 `rules.md`。其他 agent 先按当前宿主文档确认用户级入口和格式，不照搬这条路径或 frontmatter。说明具体目标和影响所有项目的范围，得到明确的全局写入授权后再操作。
- **合并，不覆盖。** 读取已有规则，只新增或合并中文表达部分，保留其他约定；没有文件时才创建。遇到冲突先确认，不把整个 skill 塞入全局上下文，也不因配置规则擅自修改权限或安装 hooks。修改 AGENTS.md 仍需明确授权该文件。
- **检查是否真的加载。** 用宿主的加载清单或新会话验证，并检查普通问答和进度说明是否保留信息、是否误附改动摘要。只看到文件存在，或让当前会话照着刚给的规则回答，不算全局加载验证；模型自称已加载也不能单独作证。
- **分别报告结果。** 写清“skill 已安装”“全局规则已写入”“加载已验证”各自是否完成。用户拒绝、宿主不支持或无法验证时如实说明，不默认启用，也不把局部成功报成全部完成。

## 活动入口与归档

| 状态 | 数量 | 位置 / 含义 |
|------|------|-------------|
| 活动 | 65 | `skills/<name>/SKILL.md`，按需安装；个别执行分支仍有明确限制 |
| 已合并 | 4 | 原内容保留为主技能的 `references/**/REFERENCE.md`，不再单独自动触发 |
| 暂停 | 4 | `archive/disabled/<name>/REFERENCE.md`，仅供审阅，不安装、不运行 hooks 或启动循环 |

合并关系：

- `diagnosing-bugs` → `superpowers-systematic-debugging` 的诊断参考。
- `claude-mem-learn-codebase` → `claude-mem-smart-explore` 的显式、有范围和预算的全文阅读模式。
- `pua-mama`、`pua-yes` → 已归档 PUA 核心的文风参考，随核心暂停。

暂停项：`superpowers-using-superpowers`、`superpowers-finishing-a-development-branch`、`pua-pua`、`pua-pua-loop`。归档保留来源和代码，不代表缺陷已全部修复或已获重新启用授权。

`sync-skills.py` 的 `EXCLUDED_SKILLS` 列出了不记录同步基线的技能：4 个暂停入口、4 个已经合并的来源（`diagnosing-bugs`、`claude-mem-learn-codebase`、`pua-mama`、`pua-yes`）、作者要求**不入库**的 `daibi`、`tuomin`，以及用户决定本地保留、不入库的英文写作工具 `ai-check`、`humanize`。这些目录在两个方向上都不参与同步：不会从本机导入仓库，也不会从仓库导出到本机。

`check` 输出的 `excluded-or-inactive` 中，还会出现两类没有仓库副本的条目。一类是宿主内置的 `deep-research`；另一类是只保存在本机、不在仓库或 GitHub 发布的 `skill-update`，`.gitignore` 中的 `skills/skill-update/` 路径也会阻止它被加入仓库。这些提示都正常，不表示漏了同步，不要为了消掉提示把它们 import 进仓库。

## 按场景选择

| 场景 | 建议入口 |
|------|----------|
| 开发与调试 | `superpowers-systematic-debugging`、`superpowers-test-driven-development`、`superpowers-verification-before-completion` |
| 已有复杂需求 | `superpowers-writing-plans` → `superpowers-executing-plans`；已有明确批准的方案不重复审批 |
| 代码审查 | `code-review`；确有多维审查需求再选 `diegosouzapw-deep-review` |
| 办公文档 | `anthropic-docx/pdf/pptx/xlsx`；旧版 `.xls` 选 `xls-poi`，删列链路暂不启用 |
| Word 元数据维护 | `docx-meta`：默认保留作者/修订者/所有者/程序名和自定义属性，只维护总编辑时间；交付清理需显式 `--clean`；两种模式都不自动前移创建时间，总时长超出实际跨度时压到跨度以内；只处理 `.docx` |
| 公开网页搜索、抓取 | `firecrawl` 及具体子技能，使用前检查 CLI 或 MCP 是否可用 |
| 本机浏览器登录态、书签/历史、站点经验 | `web-access`，不依赖 Chrome DevTools MCP |
| 课程作业 | `course-assignment`（已强制以 `docx-meta --clean` 收尾）；平台上传、填写答案、提交均须明确授权 |
| 需求 | `gen-prd`（访谈）→ `decompose-prd`（拆解）；`prd-reviewer` 的专用量表需先确认适用 |
| 所有面向用户的中文回复 | 默认推荐 `shuorenhua + 全局规则`；普通回复不附改动摘要，仅改写已有文字时默认附上。主动确认全局写入授权，按宿主安装并验证加载，不复制个人全局配置 |
| 跨会话交接、多会话协作 | `session-handoff`（核心入口，默认推荐）；专家团与 Qoder CLI 并行 agent 模式见其 references |
| 记忆检索 | `claude-mem-mem-search`、`claude-mem-smart-explore`、`claude-mem-knowledge-agent`；与 `session-handoff` 分工不同：一个检索记忆，一个维护交接状态 |
| 安全截图（仅截目标窗口）、按指定路径保存、屏幕取字 | 仓库自带 MCP [`mcps/snipaste-mcp`](./mcps/snipaste-mcp/README.md)（非 skill）；默认只截经覆盖校验的窗口矩形，桌面截图须显式授权；文字提取需 Snipaste PRO |

## 前置依赖

| 能力 | 依赖和边界 |
|------|------------|
| 文档脚本 | 依具体路线需要 Python、Node.js、相应包；PDF/PPT 渲染、Office 重算可能还需外部程序 |
| docx-meta | Python 3；只处理 `.docx`；默认原样保留属性，交付清理需显式 `--clean`；处理前关闭 Word/WPS；清理后再用 Word/WPS 保存会写回元数据，交付前需重跑 |
| 课程 DOCX 交付 | `course-assignment` 生成器需要 Node.js 与 `docx` 包；元数据收尾强制使用 `docx-meta --clean`；平台提交须明确授权 |
| POI 表格处理 | Java + Apache POI；显式配置本机 classpath，不能照搬个人磁盘路径 |
| web-access | Node.js 22+、可授权连接的 Chromium 系浏览器；历史检索另需 sqlite3 CLI，书签读取不需要 sqlite3 |
| Firecrawl 18 个技能 | 主要使用 Firecrawl CLI；MCP 为可选工具接口，CLI 安装/登录成功不证明 MCP 正常 |
| Chrome DevTools MCP | 可选浏览器工具；默认独立 profile 不自动继承日常登录态，连接已有浏览器须配置并授权 |
| claude-mem 3 个活动技能 | 官方安装及所需 MCP 工具；不同版本的 AST/知识库工具可用性需要逐项检查 |
| yida-login | OpenYida CLI；Cookie 是敏感信息，不能提交到仓库 |
| snipaste-mcp（仓库自带 MCP） | Node.js 18+ 与 Snipaste 2.x，便携版可用；窗口安全截图与 `snip_view` 仅支持 Windows（`snip_view` 另需 Edge 或 Chrome），截桌面须显式 `allow_desktop`；阴影、文字提取属 PRO 功能，免费版静默不产出 |
| hooks / 子代理 | 宿主支持和权限需分别确认；安装技能不会自动授权注册 hooks |

根目录的 [.mcp.json](./.mcp.json) 提供了 Firecrawl 和 Chrome DevTools 的项目配置示例。客户端能识别这个文件，不代表服务已经安装、获得授权、成功启动或实际操作成功。换用其他客户端时，需要按该客户端的文档调整配置格式和环境变量的展开方式。仓库自带的 [mcps/snipaste-mcp](./mcps/snipaste-mcp/README.md) 是唯一需要在本地执行 `npm ci` 的 MCP；它不在 `.mcp.json` 示例中，也不计入 65 个活动 skill 入口。

具体配置步骤，以及每一层该怎样验证，见 [MCP-SETUP.md](./MCP-SETUP.md)。本仓库没有可直接套用的个人 claude-mem 路径，也不包含任何 API Key。

## 验证与兼容性

以下命令供仓库维护和排错使用，普通用户原样安装或更新 Skill 不需要运行。

```bash
python -B validate-skills.py --installation-guide
# 或在 Git Bash / POSIX shell 中运行
bash validate-skills.sh --installation-guide
```

验证器会检查活动入口、索引是否完整覆盖、配置，以及实际的本地 Markdown 链接。`--installation-guide` 另查说明卡是否漏项、重复或缺少内容，以及安装文档中的导航锚点；不带这个选项仍按原有范围检查。它不会执行登录、上传、hooks，也不会修改真实文档。文档结构通过不代表配置步骤或所有功能已经实测，具体覆盖见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

如果仓库维护者也在本机安装了同名技能，可以用 `python sync-skills.py check` 比较两侧的哈希值；这个操作只读，不会改文件。需要写入时，必须逐文件审阅，通过 `approve` 记录当时两侧的哈希，再明确执行 `apply`（导出要求仓库侧已提交）。提交前的 pre-commit 也只做只读校验，不会自动复制、暂存或删除内容。

不同 agent 对工具名、MCP、hooks、子代理和 shell 的支持并不相同。即使是纯文本指令，也可能引用某个宿主才有的能力。因此，不能因为存在 `SKILL.md` 就承诺跨平台完全兼容。

## 额外内容与来源

`daibi-template/` 是个人文风技能制作指南，不计入上述技能数量。

各目录保留了原有的来源说明和许可证文件，本地修改后的内容可能与上游不同。来源包括 Anthropic、Firecrawl、Superpowers、claude-mem、PUA、社区，以及自创技能（如 `session-handoff`、`course-assignment`、`docx-meta`）。内容没有明确的许可证时，不能默认认为可以任意再分发。

**许可状态（2026-11-20 更新）**：上游 `anthropics/skills` 已于 2026-11-06 将 Office 技能转为 Apache 2.0（#2146）；本仓库同步至上游 `e4bb5d9` 后核实，14 个带 `LICENSE.txt` 的 anthropic 入口（含 docx/pdf/pptx/xlsx）均为 Apache 2.0，原先「限制复制、衍生和再分发」的公开发布阻塞对这些目录已解除。`anthropic-doc-coauthoring` 没有 LICENSE.txt，仍按来源核验。其他目录如果只写了来源或许可名称、没有具体条款，也要分别核验；不能默认整个合集可以自由复制，也不能通过删除或替换原许可来绕过限制。

## 贡献

新增活动入口时，必须提供 `SKILL.md`、更新 `INDEX.md`，并在 [SKILL-GUIDE.md](SKILL-GUIDE.md) 补上用途、准备条件、配置、使用例子、验证与限制。新增或调整公开 MCP 接入方式时，同步 [MCP-SETUP.md](MCP-SETUP.md)，再运行 `python -B validate-skills.py --installation-guide`。说明卡采用独立的显式锚点，七个字段分别标注且冒号后有内容，复杂步骤可另分段展开；校验只确认完整性，事实仍需对照技能正文和官方资料核实。如果包含可执行脚本，还要补充隔离回归测试；涉及上传、凭据、全局配置或 hooks 时，说明哪些操作需要授权及允许范围。不要把“静态检查通过”写成“所有功能可用”。
