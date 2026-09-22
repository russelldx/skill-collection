# Skill Collection — AI Agent 技能合集

按任务选择技能，而不是全量安装。Skill 提供工作流程，MCP/CLI 提供工具；两者不能互相替代。

本仓库保留原有 **63 个 skill 的内容**，整理为 **55 个活动入口、4 个合并参考、4 个暂停入口**。检查范围为文档、结构和部分脚本回归，不代表所有技能在所有平台上运行通过。

## 快速开始

将本仓库地址或 `README.md` + [INDEX.md](./INDEX.md) 交给你的 agent，让它：

1. 根据任务从 `skills/` 选择需要的技能，不扫描归档作为可安装技能。
2. 检查目标环境的运行时、工具、子代理能力及已安装版本。
3. 核对所选目录的来源和许可；说明待安装目录和依赖，得到授权后安装；目标目录已存在时先比较，不覆盖。
4. 单独确认 MCP、凭据、全局依赖和 hooks 的配置，不能把安装技能视为授权这些操作。

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
| 活动 | 55 | `skills/<name>/SKILL.md`，按需安装；个别执行分支仍有明确限制 |
| 已合并 | 4 | 原内容保留为主技能的 `references/**/REFERENCE.md`，不再单独自动触发 |
| 暂停 | 4 | `archive/disabled/<name>/REFERENCE.md`，仅供审阅，不安装、不运行 hooks 或启动循环 |

合并关系：

- `diagnosing-bugs` → `superpowers-systematic-debugging` 的诊断参考。
- `claude-mem-learn-codebase` → `claude-mem-smart-explore` 的显式、有范围和预算的全文阅读模式。
- `pua-mama`、`pua-yes` → 已归档 PUA 核心的文风参考，随核心暂停。

暂停项：`superpowers-using-superpowers`、`superpowers-finishing-a-development-branch`、`pua-pua`、`pua-pua-loop`。归档保留来源和代码，不代表缺陷已全部修复或已获重新启用授权。

## 按场景选择

| 场景 | 建议入口 |
|------|----------|
| 开发与调试 | `superpowers-systematic-debugging`、`superpowers-test-driven-development`、`superpowers-verification-before-completion` |
| 已有复杂需求 | `superpowers-writing-plans` → `superpowers-executing-plans`；已有明确批准的方案不重复审批 |
| 代码审查 | `code-review`；确有多维审查需求再选 `diegosouzapw-deep-review` |
| 办公文档 | `anthropic-docx/pdf/pptx/xlsx`；旧版 `.xls` 选 `xls-poi`，删列链路暂不启用 |
| 公开网页搜索、抓取 | `firecrawl` 及具体子技能，使用前检查 CLI 或 MCP 是否可用 |
| 本机浏览器登录态、书签/历史、站点经验 | `web-access`，不依赖 Chrome DevTools MCP |
| 课程作业 | `course-assignment`；平台上传、填写答案、提交均须明确授权 |
| 需求 | `gen-prd`（访谈）→ `decompose-prd`（拆解）；`prd-reviewer` 的专用量表需先确认适用 |
| 记忆与交接 | `claude-mem-mem-search`、`claude-mem-smart-explore`、`claude-mem-knowledge-agent`；需要交接文件时选 `session-handoff` |

## 前置依赖

| 能力 | 依赖和边界 |
|------|------------|
| 文档脚本 | 依具体路线需要 Python、Node.js、相应包；PDF/PPT 渲染、Office 重算可能还需外部程序 |
| POI 表格处理 | Java + Apache POI；显式配置本机 classpath，不能照搬个人磁盘路径 |
| web-access | Node.js 22+、可授权连接的 Chromium 系浏览器；历史检索另需 sqlite3 CLI，书签读取不需要 sqlite3 |
| Firecrawl 10 个技能 | 主要使用 Firecrawl CLI；MCP 为可选工具接口，CLI 安装/登录成功不证明 MCP 正常 |
| Chrome DevTools MCP | 可选浏览器工具；默认独立 profile 不自动继承日常登录态，连接已有浏览器须配置并授权 |
| claude-mem 3 个活动技能 | 官方安装及所需 MCP 工具；不同版本的 AST/知识库工具可用性需要逐项检查 |
| yida-login | OpenYida CLI；Cookie 是敏感信息，不能提交到仓库 |
| hooks / 子代理 | 宿主支持和权限需分别确认；安装技能不会自动授权注册 hooks |

根目录 [.mcp.json](./.mcp.json) 提供 Firecrawl 和 Chrome DevTools 的项目配置示例。文件被客户端识别不等于服务安装、授权、启动或实际操作成功；其他客户端的配置格式和环境变量展开方式需按其文档适配。

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

各目录保留原有来源与许可证文件；本地修改可能与上游不同。来源包括 Anthropic、Firecrawl、Superpowers、claude-mem、PUA、社区和自创技能。没有明确许可证的内容，不应推定获得任意再分发授权。

**公开发布阻塞**：`anthropic-docx`、`anthropic-pdf`、`anthropic-pptx`、`anthropic-xlsx` 的现有 `LICENSE.txt` 明确限制复制、衍生和再分发；本地技术审查与修复不代表取得许可。未确认适用权利前，不应公开分发这些目录或宣称整个合集可自由复制。其他仅有来源或许可名称、缺少具体条款的目录也需分别核验；不删除或替换原许可来绕过限制。

## 贡献

新增活动入口须有 `SKILL.md`、更新 `INDEX.md` 并通过结构验证。涉及可执行脚本时补充隔离回归；涉及上传、凭据、全局配置或 hooks 时明确授权边界。不要把“静态检查通过”写成“所有功能可用”。
