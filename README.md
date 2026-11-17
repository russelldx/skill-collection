# Skill Collection — AI Agent 技能合集

请按任务选择技能，不要全量安装。Skill 提供做事的流程，MCP/CLI 提供工具，两者不能互相替代。

> **核心入口：`session-handoff`**。它用于跨会话交接、专家团角色协作，也支持在 Qoder CLI 的同一会话内派发并行 agent。任务需要跨多个会话、分批推进，或需要把踩过的坑留给后续会话时，默认推荐安装。如果 agent 决定不推荐，必须在清单里说明理由，不能直接跳过。

本仓库现有 **65 个活动入口**，另有 4 个已合并为参考资料的入口和 4 个暂停入口。活动入口中，8 个检索与集成入口是在用户授权后从上游 `firecrawl/cli`、`firecrawl/skills` 新增的；`docx-meta` 元数据清理入口和 `shuorenhua` 中文编辑入口由本地维护。

目前检查了文档、目录结构，并对部分脚本做了回归测试。这不代表所有技能都已在所有平台上运行通过。新增的 8 个 Firecrawl 入口与 `docx-meta` 具体验证了什么，见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

## 快速开始

把本仓库地址，或者 `README.md` 和 [INDEX.md](./INDEX.md)，交给你的 agent，要求它按下面的步骤处理：

1. **先列完整清单，再挑选。** 按 `INDEX.md` 的分类，逐类查看 65 个活动入口。每个入口写一行，标出“推荐安装 / 暂不推荐 / 不适用”，并说明一句理由。不能只挑几个，也不能不作说明就跳过整类。
2. **默认推荐 `session-handoff`。** 只要任务涉及多个会话、交接文档、专家团或并行 agent，就必须把它列为首选。如果不装，必须在清单里说明原因。这是本仓库的核心入口，不能当成可有可无的装饰。
3. 根据任务从 `skills/` 选择技能，不要到归档中查找可安装技能，也不要把合并后的参考资料或暂停入口当成可运行技能。
4. 检查目标环境有哪些运行时、工具和子代理能力，以及已经安装的版本。
5. 核对所选目录的来源和许可，说明要安装的目录及其依赖，获得授权后再安装。如果目标目录已经存在，先比较，不要覆盖。
6. MCP、凭据、全局依赖和 hooks 的配置要单独确认。允许安装技能，不等于允许这些配置操作。

手动安装示例（Git Bash / POSIX shell；先确认目标技能不存在）：

```bash
git clone <仓库地址>
cd skill-collection
# 按需选择一个目录；不要将尖括号占位符直接执行。
cp -r skills/anthropic-frontend-design <你的agent技能目录>/
```

目标目录由宿主决定，例如项目级 `.qoder/skills/` 或用户级 `~/.qoder/skills/`、`~/.claude/skills/`。不要递归复制整个仓库，也不要执行 `skills/*` 全量安装。

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

`sync-skills.py` 的 `EXCLUDED_SKILLS` 列出了不记录同步基线的技能：4 个暂停入口、4 个已经合并的来源（`diagnosing-bugs`、`claude-mem-learn-codebase`、`pua-mama`、`pua-yes`），以及作者要求**不入库**的 `daibi`、`tuomin`。这些目录在两个方向上都不参与同步：不会从本机导入仓库，也不会从仓库导出到本机。

`check` 输出的 `excluded-or-inactive` 中，还会出现两类没有仓库副本的条目。一类是宿主内置的 `deep-research`；另一类是只保存在本机、不在仓库或 GitHub 发布的 `skill-update`，`.gitignore` 中的 `skills/skill-update/` 路径也会阻止它被加入仓库。这些提示都正常，不表示漏了同步，不要为了消掉提示把它们 import 进仓库。

## 按场景选择

| 场景 | 建议入口 |
|------|----------|
| 开发与调试 | `superpowers-systematic-debugging`、`superpowers-test-driven-development`、`superpowers-verification-before-completion` |
| 已有复杂需求 | `superpowers-writing-plans` → `superpowers-executing-plans`；已有明确批准的方案不重复审批 |
| 代码审查 | `code-review`；确有多维审查需求再选 `diegosouzapw-deep-review` |
| 办公文档 | `anthropic-docx/pdf/pptx/xlsx`；旧版 `.xls` 选 `xls-poi`，删列链路暂不启用 |
| Word 元数据清理 | `docx-meta`：删除作者/修订者/自定义属性/缩略图，校正总编辑时间；只处理 `.docx` |
| 公开网页搜索、抓取 | `firecrawl` 及具体子技能，使用前检查 CLI 或 MCP 是否可用 |
| 本机浏览器登录态、书签/历史、站点经验 | `web-access`，不依赖 Chrome DevTools MCP |
| 课程作业 | `course-assignment`（已强制接入 `docx-meta` 收尾）；平台上传、填写答案、提交均须明确授权 |
| 需求 | `gen-prd`（访谈）→ `decompose-prd`（拆解）；`prd-reviewer` 的专用量表需先确认适用 |
| 中文顺句与信息保全 | `shuorenhua`：默认附简短改动摘要；可授权安装 `assets/chinese-writing.md` 到 `~/.qoder/rules/chinese-writing.md`，不复制个人全局配置 |
| 跨会话交接、多会话协作 | `session-handoff`（核心入口，默认推荐）；专家团与 Qoder CLI 并行 agent 模式见其 references |
| 记忆检索 | `claude-mem-mem-search`、`claude-mem-smart-explore`、`claude-mem-knowledge-agent`；与 `session-handoff` 分工不同：一个检索记忆，一个维护交接状态 |
| 安全截图（仅截目标窗口）、按指定路径保存、屏幕取字 | 仓库自带 MCP [`mcps/snipaste-mcp`](./mcps/snipaste-mcp/README.md)（非 skill）；默认只截经覆盖校验的窗口矩形，桌面截图须显式授权；文字提取需 Snipaste PRO |

## 前置依赖

| 能力 | 依赖和边界 |
|------|------------|
| 文档脚本 | 依具体路线需要 Python、Node.js、相应包；PDF/PPT 渲染、Office 重算可能还需外部程序 |
| docx-meta | Python 3；只处理 `.docx`；处理前关闭 Word/WPS；清理后再用 Word/WPS 保存会写回元数据，交付前需重跑 |
| 课程 DOCX 交付 | `course-assignment` 生成器需要 Node.js 与 `docx` 包；元数据收尾强制使用 `docx-meta`；平台提交须明确授权 |
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

```bash
python validate-skills.py
# 或在 Git Bash / POSIX shell 中运行
bash validate-skills.sh
```

验证器会检查活动入口、索引是否完整覆盖、配置，以及实际的本地 Markdown 链接。它不会执行登录、上传、hooks，也不会修改真实文档。具体做过哪些回归测试、还有哪些能力未验证，见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

如果仓库维护者也在本机安装了同名技能，可以用 `python sync-skills.py check` 比较两侧的哈希值；这个操作只读，不会改文件。需要写入时，必须逐文件审阅，通过 `approve` 记录当时两侧的哈希，再明确执行 `apply`（导出要求仓库侧已提交）。提交前的 pre-commit 也只做只读校验，不会自动复制、暂存或删除内容。

不同 agent 对工具名、MCP、hooks、子代理和 shell 的支持并不相同。即使是纯文本指令，也可能引用某个宿主才有的能力。因此，不能因为存在 `SKILL.md` 就承诺跨平台完全兼容。

## 额外内容与来源

`daibi-template/` 是个人文风技能制作指南，不计入上述技能数量。

各目录保留了原有的来源说明和许可证文件，本地修改后的内容可能与上游不同。来源包括 Anthropic、Firecrawl、Superpowers、claude-mem、PUA、社区，以及自创技能（如 `session-handoff`、`course-assignment`、`docx-meta`）。内容没有明确的许可证时，不能默认认为可以任意再分发。

**公开发布阻塞**：`anthropic-docx`、`anthropic-pdf`、`anthropic-pptx`、`anthropic-xlsx` 现有的 `LICENSE.txt` 明确限制复制、衍生和再分发。在本地做过技术审查和修复，不代表已经获得许可。确认适用的权利之前，不应公开分发这些目录，也不应宣称整个合集可以自由复制。其他目录如果只写了来源或许可名称、没有具体条款，也要分别核验。不能通过删除或替换原许可来绕过限制。

## 贡献

新增活动入口时，必须提供 `SKILL.md`、更新 `INDEX.md`，并通过结构验证。如果包含可执行脚本，还要补充隔离回归测试；如果涉及上传、凭据、全局配置或 hooks，要说明哪些操作需要授权，以及允许操作的范围。不要把“静态检查通过”写成“所有功能可用”。
