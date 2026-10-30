# Skill Collection — AI Agent 技能合集

按任务选择技能，而不是全量安装。Skill 提供工作流程，MCP/CLI 提供工具；两者不能互相替代。

> **核心入口：`session-handoff`** — 跨会话交接、专家团角色协作、Qoder CLI 会话内并行 agent 派发。任何跨多会话、分批推进或需要把踩坑留给后续会话的任务，默认推荐安装；如果 agent 决定不推荐它，必须在清单里写明理由，不能静默跳过。

本仓库现有 **64 个活动入口**，另有 4 个合并参考和 4 个暂停入口。活动入口包含按用户授权从上游 `firecrawl/cli`、`firecrawl/skills` 新增的 8 个检索与集成入口，以及本地维护的 `docx-meta` 元数据清理入口。检查范围为文档、结构和部分脚本回归，不代表所有技能在所有平台上运行通过；新增的 8 个 Firecrawl 入口与 `docx-meta` 的验证范围见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

## 快速开始

将本仓库地址或 `README.md` + [INDEX.md](./INDEX.md) 交给你的 agent，并要求它：

1. **先给出完整清单，再做减法。** 按 `INDEX.md` 的分类逐类过一遍 64 个活动入口，每个入口一行，标出“推荐安装 / 暂不推荐 / 不适用”和一句理由；不允许只挑几个就结束，也不允许静默跳过整类。
2. **默认推荐 `session-handoff`。** 多会话任务、需要交接文档、使用专家团或并行 agent 的任务，必须把它列为首选；跳过时必须在清单中写明“为什么不装”。它是本仓库的核心入口，不是可选装饰。
3. 根据任务从 `skills/` 选择需要的技能，不扫描归档作为可安装技能；不把合并参考或暂停入口当成可运行技能。
4. 检查目标环境的运行时、工具、子代理能力及已安装版本。
5. 核对所选目录的来源和许可；说明待安装目录和依赖，得到授权后安装；目标目录已存在时先比较，不覆盖。
6. 单独确认 MCP、凭据、全局依赖和 hooks 的配置，不能把安装技能视为授权这些操作。

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
| 活动 | 64 | `skills/<name>/SKILL.md`，按需安装；个别执行分支仍有明确限制 |
| 已合并 | 4 | 原内容保留为主技能的 `references/**/REFERENCE.md`，不再单独自动触发 |
| 暂停 | 4 | `archive/disabled/<name>/REFERENCE.md`，仅供审阅，不安装、不运行 hooks 或启动循环 |

合并关系：

- `diagnosing-bugs` → `superpowers-systematic-debugging` 的诊断参考。
- `claude-mem-learn-codebase` → `claude-mem-smart-explore` 的显式、有范围和预算的全文阅读模式。
- `pua-mama`、`pua-yes` → 已归档 PUA 核心的文风参考，随核心暂停。

暂停项：`superpowers-using-superpowers`、`superpowers-finishing-a-development-branch`、`pua-pua`、`pua-pua-loop`。归档保留来源和代码，不代表缺陷已全部修复或已获重新启用授权。

`sync-skills.py` 的 `EXCLUDED_SKILLS` 列出不进入同步基线的名称：4 个暂停入口、4 个已合并来源（`diagnosing-bugs`、`claude-mem-learn-codebase`、`pua-mama`、`pua-yes`），以及按作者要求**不入库**的 `daibi`、`tuomin`。排除是双向的：工具既不把这些目录从本机回流到仓库，也不把仓库改动导出到本机。`check` 输出里的 `excluded-or-inactive` 还会出现两类根本没有仓库副本的条目：宿主内置的 `deep-research`，以及只作为本地 skill 存在、仓库与 GitHub 都不发布的 `skill-update`（由 `.gitignore` 的 `skills/skill-update/` 守卫路径兜底）。这些都是预期状态，不是漏同步，不要为了消掉提示行把它们 import 进仓库。

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

根目录 [.mcp.json](./.mcp.json) 提供 Firecrawl 和 Chrome DevTools 的项目配置示例。文件被客户端识别不等于服务安装、授权、启动或实际操作成功；其他客户端的配置格式和环境变量展开方式需按其文档适配。仓库自带的 [mcps/snipaste-mcp](./mcps/snipaste-mcp/README.md) 是唯一需要本地 `npm ci` 的 MCP，不包含在 `.mcp.json` 示例中，也不属于 64 个活动 skill 入口。

详细配置与分层验证见 [MCP-SETUP.md](./MCP-SETUP.md)。本仓库不含可直接套用的个人 claude-mem 路径或任何 API Key。

## 验证与兼容性

```bash
python validate-skills.py
# 或在 Git Bash / POSIX shell 中运行
bash validate-skills.sh
```

验证器检查活动入口、索引覆盖、配置及实际本地 Markdown 链接，不执行登录、上传、hooks 或真实文档修改。具体回归与未验证能力见 [TEST-SUMMARY.md](./TEST-SUMMARY.md)。

仓库维护者若同时在本机安装着同名技能，可用 `python sync-skills.py check` 只读对比两侧哈希；写入必须逐文件审阅、经 `approve` 记录当时双侧哈希后由显式 `apply` 执行（导出要求仓库侧已提交），提交前的 pre-commit 只做只读校验，不会自动复制、暂存或删除内容。

不同 agent 对工具名、MCP、hooks、子代理和 shell 的支持不同。纯文本指令也可能引用宿主特有能力，不能仅凭 `SKILL.md` 存在承诺跨平台完全兼容。

## 额外内容与来源

`daibi-template/` 是个人文风技能制作指南，不计入上述技能数量。

各目录保留原有来源与许可证文件；本地修改可能与上游不同。来源包括 Anthropic、Firecrawl、Superpowers、claude-mem、PUA、社区和自创技能（如 `session-handoff`、`course-assignment`、`docx-meta`）。没有明确许可证的内容，不应推定获得任意再分发授权。

**公开发布阻塞**：`anthropic-docx`、`anthropic-pdf`、`anthropic-pptx`、`anthropic-xlsx` 的现有 `LICENSE.txt` 明确限制复制、衍生和再分发；本地技术审查与修复不代表取得许可。未确认适用权利前，不应公开分发这些目录或宣称整个合集可自由复制。其他仅有来源或许可名称、缺少具体条款的目录也需分别核验；不删除或替换原许可来绕过限制。

## 贡献

新增活动入口须有 `SKILL.md`、更新 `INDEX.md` 并通过结构验证。涉及可执行脚本时补充隔离回归；涉及上传、凭据、全局配置或 hooks 时明确授权边界。不要把“静态检查通过”写成“所有功能可用”。
