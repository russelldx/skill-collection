# Skill Collection — AI Agent 技能合集

> 像游戏 mod 合集一样，一键获取经过验证的 AI agent 技能包。
> 小白全装，老手按需取用。

## 这是什么

本仓库收集了 **63 个 AI agent skill**，覆盖开发流程、文档生成、写作辅助、联网操作、效率工具等多个领域。所有 skill 均经过实际使用验证，可按需安装。

**适用平台**：任何支持 SKILL.md 协议的 AI 编码助手。

## 快速开始

### 推荐方式：让你的 Agent 来决定

把本仓库地址（或 `README.md` + `INDEX.md` 的内容）发给你的 AI 编码助手，让它根据你当前的环境和需求，自动判断该安装哪些 skill、怎么安装。

Agent 会做的事：
1. 读取 `INDEX.md` 中的 63 个 skill 列表和兼容性标注
2. 检测你的环境（有哪些运行时、MCP 配置、是否支持 hooks 等）
3. 推荐适合你环境的 skill 组合
4. 将选中的 skill 复制到正确的 skill 目录

> 你也可以直接把 `INDEX.md` 的全文贴给 agent，附上"帮我挑选适合我环境的 skill 并安装"即可。

### 手动安装（备选）

如果你更习惯自己操作：

```bash
# 1. 克隆仓库
git clone <仓库地址>
cd skill-collection

# 2. 全量安装
cp -r skills/* <你的agent skill目录>/

# 3. 或按需挑选（以文档生成为例）
cp -r skills/anthropic-docx <你的agent skill目录>/
cp -r skills/anthropic-pdf <你的agent skill目录>/
cp -r skills/anthropic-pptx <你的agent skill目录>/
```

> `<你的agent skill目录>` 取决于你使用的 agent，通常是 `~/.claude/skills/`、`~/.cursor/skills/` 等。

## 前置依赖

部分 skill 需要额外依赖才能正常工作：

| 依赖 | 涉及 skill | 安装方式 |
|------|-----------|---------|
| **Node.js** | anthropic-docx、anthropic-xlsx、web-access、course-assignment 等含 scripts/ 的 skill | [nodejs.org](https://nodejs.org) |
| **Python 3** | anthropic-slack-gif-creator | `pip install -r requirements.txt` |
| **Java 8 + POI** | xls-poi | skill 内含 `scripts/poi_env.sh` |
| **Firecrawl MCP** | firecrawl 全系列 | 见下方 MCP 配置说明 |
| **Chrome DevTools MCP** | web-access、course-assignment | 见下方 MCP 配置说明 |
| **claude-mem MCP** | claude-mem 全系列 | 见下方 MCP 配置说明 |
| **OpenYida CLI** | yida-login | 需安装 openyida 命令行工具 |

> 不含 scripts/、不需要 MCP 的 skill（大部分纯 SKILL.md）可直接使用，无额外依赖。

### MCP 配置说明

本仓库已在根目录提供 **`.mcp.json`**，Claude Code 打开仓库时会自动识别所需的 MCP server。

详细安装步骤、API Key 获取方式、各 agent 的配置方法见 **[MCP-SETUP.md](./MCP-SETUP.md)**。

三个 MCP server 概要：

| MCP Server | 用途 | 需要 API Key | 涉及 skill 数 |
|------------|------|:---:|:---:|
| **Firecrawl** | 网页搜索/抓取/爬取 | 是（[firecrawl.dev](https://firecrawl.dev) 免费注册） | 11 个 |
| **Chrome DevTools** | 浏览器自动化控制 | 否 | 2 个 |
| **claude-mem** | 跨会话持久记忆 | 否 | 4 个 |

> **按需安装**：不需要全部配置。约 40 个纯 SKILL.md skill 无需任何 MCP。详见 MCP-SETUP.md 中的按需安装表。

## 合集内容

详细列表见 [INDEX.md](./INDEX.md)，按功能分为 8 大类：

| 分类 | 数量 | 说明 |
|------|------|------|
| 文档生成 | 6 | Word、PDF、PPT、Excel 等文件处理 |
| 开发流程 | 16 | 从构思到发布的完整开发方法论 |
| 代码审查 | 3 | 代码质量、深度审查 |
| 需求管理 | 4 | PRD 生成、分解、评审 |
| 联网操作 | 14 | 网页抓取、搜索、浏览器交互 |
| 写作辅助 | 2 | 内容研究、会话交接 |
| 效率工具 | 12 | 调试、诊断、知识管理 |
| 驱动风格 | 4 | PUA 系列，调节 agent 工作风格 |

## 额外内容

### daibi 模板（个人文风 skill 制作指南）

`daibi-template/` 目录包含制作个人文风 skill 的完整指南和模板：

- `GUIDE.md` — 从零制作个人文风 skill 的步骤
- `SKILL-TEMPLATE.md` — 可填写的模板文件

这不是一个现成的 skill，而是教你**如何制作一个模仿你自己文风的 skill**。

## 兼容性说明

| 标签 | 含义 |
|------|------|
| `纯SKILL.md` | 任何支持 SKILL.md 的 agent 可直接使用 |
| `需scripts` | 含可执行脚本，需要对应运行时（Node/Python/Java） |
| `需hooks` | 含 hook 配置，需要 agent 支持 hook 系统 |
| `需agents` | 使用 sub-agent 系统，需要 agent 支持子代理调度 |
| `需MCP` | 需要配置对应的 MCP server |

各 skill 的具体兼容性标注见 [INDEX.md](./INDEX.md)。

### 跨 Agent 兼容矩阵

| Agent | 能力覆盖 | 完全兼容 | 部分兼容 | 降级可用 |
|-------|---------|---------|---------|---------|
| **Claude Code** | SKILL.md + scripts + hooks + sub-agents + MCP | **63 个** | — | — |
| **Cursor** | SKILL.md + scripts + MCP | ~45 个纯 SKILL.md | ~15 个需脚本/MCP 配置 | ~3 个 hooks skill 核心功能可用 |
| **Codex / Gemini CLI** | SKILL.md + scripts（shell 受限） | ~45 个纯 SKILL.md | ~12 个需脚本/MCP | ~6 个需 hooks/shell 降级 |
| **通用 SKILL.md agent** | 仅 SKILL.md 指令 | ~40 个纯 SKILL.md | — | ~23 个需运行时/MCP/hooks |

> **标签说明**：`✓` 完全支持 · `◐` 部分支持（核心功能可用，增强功能不可用） · `✗` 不支持
>
> **Hooks 降级**：本合集含 hooks 的 3 个 skill（session-handoff、pua-pua、superpowers-using-superpowers）均将 hooks 作为可选增强，核心指令写在 SKILL.md 中，无 hooks 的 agent 仍可正常使用核心功能。详见 [INDEX.md](./INDEX.md) 中各 skill 的降级方案说明。

## 来源归属

| 来源 | 数量 | 说明 |
|------|------|------|
| Anthropic 官方 | 15 | anthropic-* 系列 |
| 市场/社区 | 27 | 来自 marketplace、GitHub 等 |
| superpowers 系列 | 13 | 社区开发方法论合集 |
| PUA 系列 | 4 | [pua-skill](https://pua-skill.pages.dev) 项目 |
| 自创 | 4 | session-handoff、course-assignment、xls-poi、daibi 模板 |

## 注意事项

1. **不要安装你已有的同名 skill** — 会覆盖现有版本
2. **含 scripts/ 的 skill** — 首次使用前检查脚本依赖
3. **含 hooks/ 的 skill** — 需要通过 skill 提供的安装脚本部署 hook
4. **MCP 相关 skill** — 需先在 agent 配置中添加对应 MCP server
5. **PUA 系列** — 会显著改变 agent 的交互风格，建议先了解再安装

## License

各 skill 保留原有 license。anthropic-* 系列见各自 LICENSE.txt；pua-* 系列为 MIT；其他无明确声明的遵循仓库默认条款。

## 贡献

欢迎提交 PR 添加你的 skill！要求：
- 必须有 SKILL.md 主文件
- 必须在 INDEX.md 中添加对应条目
- 如有特殊依赖，需在 README 前置依赖表中说明
