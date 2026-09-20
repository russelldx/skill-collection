# Skill 索引

> 按功能分类，每个 skill 标注描述、使用方式、注意事项、兼容性和来源。
> 兼容性标签：`纯SKILL.md` | `需scripts` | `需hooks` | `需agents` | `需MCP`
>
> **跨Agent 标注说明**：`✓` 完全支持 · `◐` 部分支持（核心可用，增强不可用） · `✗` 不支持
> 目标 agent：CC = Claude Code · Cursor · Codex = Codex/Gemini CLI · 通用 = 任何支持 SKILL.md 的 agent

---

## 一、文档生成（6 个）

处理 Word、PDF、PPT、Excel 等办公文档的创建和编辑。

### anthropic-docx
| 项目 | 内容 |
|------|------|
| **描述** | Word (.docx) 全流程处理：创建、读取、编辑、模板填充 |
| **功能** | Markdown→Word 转换、模板填充（{{token}} 和 reference-doc 模式）、CJK 排版、批量生成 |
| **使用** | 涉及 .docx 文件时自动触发 |
| **注意** | 含 scripts/，需要 Node.js 运行脚本 |
| **兼容性** | `需scripts(Node.js)` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Node.js |
| **来源** | Anthropic 官方 |

### anthropic-pdf
| 项目 | 内容 |
|------|------|
| **描述** | PDF 全流程：读取、提取、合并、拆分、水印、加密 |
| **功能** | 文本/表格提取、多 PDF 合并、按页拆分、添加水印、加密/解密 |
| **使用** | 涉及 PDF 操作时自动触发 |
| **注意** | 含 scripts/，需要 Python |
| **兼容性** | `需scripts(Python)` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Python |
| **来源** | Anthropic 官方 |

### anthropic-pptx
| 项目 | 内容 |
|------|------|
| **描述** | PowerPoint (.pptx) 创建、读取、编辑 |
| **功能** | 幻灯片生成、内容提取、模板编辑、pptxgenjs 集成 |
| **使用** | 涉及 .pptx 文件时自动触发 |
| **注意** | 含 scripts/，需要 Python |
| **兼容性** | `需scripts(Python)` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Python |
| **来源** | Anthropic 官方 |

### anthropic-xlsx
| 项目 | 内容 |
|------|------|
| **描述** | Excel (.xlsx/.csv/.tsv) 通用处理 |
| **功能** | 创建、读取、编辑电子表格；公式处理；格式转换；数据清洗 |
| **使用** | 涉及表格文件时自动触发 |
| **注意** | 含 scripts/，需要 Python。不处理 .xls (BIFF8) 格式 |
| **兼容性** | `需scripts(Python)` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Python |
| **来源** | Anthropic 官方 |

### xls-poi
| 项目 | 内容 |
|------|------|
| **描述** | 专攻 .xls (BIFF8) 格式，补充 anthropic-xlsx 的不足 |
| **功能** | 使用 Java POI 处理旧版 Excel；保留数据验证下拉；删列保持格式 |
| **使用** | 遇到 .xls 后缀文件时触发；或需要保留下拉列表/数据验证时 |
| **注意** | 需要 Java 8 + Apache POI 4.1.2，skill 内含环境脚本 |
| **兼容性** | `需scripts(Java)` |
| **跨Agent** | CC ◐ · Cursor ◐ · Codex ◐ · 通用 ✗ 需Java |
| **来源** | 自创 |

### anthropic-slack-gif-creator
| 项目 | 内容 |
|------|------|
| **描述** | 创建适合 Slack 的动画 GIF |
| **功能** | 约束检查、动画概念设计、生成工具 |
| **使用** | 用户要求制作 Slack GIF 时触发 |
| **注意** | 需要 Python 环境和 requirements.txt 中的依赖 |
| **兼容性** | `需scripts(Python)` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Python |
| **来源** | Anthropic 官方 |

---

## 二、开发流程（16 个）

从构思到发布的完整开发方法论，superpowers 系列为主。

### superpowers-brainstorming
| 项目 | 内容 |
|------|------|
| **描述** | 创意工作前的必用 skill：探索意图、需求和设计 |
| **功能** | 在创建功能/组件/修改行为前，先充分探索用户意图 |
| **使用** | 任何创意工作前自动触发 |
| **注意** | 含 scripts/（Node.js + Shell），核心指令在 SKILL.md |
| **兼容性** | `纯SKILL.md` `需scripts` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ◐ 脚本可选 · 通用 ✓ 核心可用 |
| **来源** | 社区 |

### superpowers-writing-plans
| 项目 | 内容 |
|------|------|
| **描述** | 有规格/需求后、动手写码前，编写实施计划 |
| **功能** | 将需求分解为可执行的多步骤计划文档 |
| **使用** | 有 spec 或需求后触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-executing-plans
| 项目 | 内容 |
|------|------|
| **描述** | 在独立会话中执行已有实施计划，含审查检查点 |
| **功能** | 按计划逐步执行，设置审查节点 |
| **使用** | 有写好的计划需要执行时触发 |
| **注意** | 建议配合 writing-plans 使用；有 sub-agent 的 agent 效果更好 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-test-driven-development
| 项目 | 内容 |
|------|------|
| **描述** | 实现任何功能或修复 bug 前，先写测试 |
| **功能** | TDD 工作流：红→绿→重构 |
| **使用** | 实现功能/修复前触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-subagent-driven-development
| 项目 | 内容 |
|------|------|
| **描述** | 在当前会话中使用 sub-agent 执行独立任务 |
| **功能** | 将实施计划分解给子代理并行执行 |
| **使用** | 有独立任务需要并行处理时触发 |
| **注意** | 需要 agent 支持 sub-agent 调度 |
| **兼容性** | `纯SKILL.md` `需agents` |
| **跨Agent** | CC ✓ · Cursor ◐ 需子代理支持 · Codex ◐ · 通用 ✗ |
| **来源** | 社区 |

### superpowers-dispatching-parallel-agents
| 项目 | 内容 |
|------|------|
| **描述** | 面对 2+ 个独立任务时，分派并行代理 |
| **功能** | 识别可并行的任务并分派子代理 |
| **使用** | 有多个独立任务时触发 |
| **注意** | 需要 agent 支持 sub-agent |
| **兼容性** | `纯SKILL.md` `需agents` |
| **跨Agent** | CC ✓ · Cursor ◐ 需子代理支持 · Codex ◐ · 通用 ✗ |
| **来源** | 社区 |

### superpowers-systematic-debugging
| 项目 | 内容 |
|------|------|
| **描述** | 遇到 bug、测试失败、意外行为时系统化调试 |
| **功能** | 4 阶段流程：调查→模式分析→假设→实施 |
| **使用** | 遇到 bug 或失败时触发 |
| **注意** | 核心原则：永远找根因，不治标 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-using-git-worktrees
| 项目 | 内容 |
|------|------|
| **描述** | 需要隔离工作区时使用 git worktree |
| **功能** | 创建隔离的功能开发环境 |
| **使用** | 开始需要隔离的功能工作时触发 |
| **注意** | 需要 git 环境 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-verification-before-completion
| 项目 | 内容 |
|------|------|
| **描述** | 声称完成前必须验证 |
| **功能** | 运行验证命令、确认输出后才可声明完成 |
| **使用** | 准备声明任务完成前触发 |
| **注意** | 证据先于断言 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-requesting-code-review
| 项目 | 内容 |
|------|------|
| **描述** | 完成任务或主要功能后，请求代码审查 |
| **功能** | 合并前验证工作是否符合要求 |
| **使用** | 完成任务、准备合并前触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-receiving-code-review
| 项目 | 内容 |
|------|------|
| **描述** | 收到代码审查反馈后的处理流程 |
| **功能** | 技术严谨地评估反馈，避免盲目实施 |
| **使用** | 收到 code review 反馈后触发 |
| **注意** | 不盲从，需验证反馈的正确性 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-finishing-a-development-branch
| 项目 | 内容 |
|------|------|
| **描述** | 实现完成、测试通过后的集成决策 |
| **功能** | 提供 merge、PR、cleanup 等选项 |
| **使用** | 开发分支完成并测试通过后触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### superpowers-using-superpowers
| 项目 | 内容 |
|------|------|
| **描述** | 会话开始时建立 skill 使用规范 |
| **功能** | 确保在响应前先检查并调用适用的 skill |
| **使用** | 每次会话开始自动触发 |
| **注意** | 含 hooks/（SessionStart）和 scripts/；hooks 为增强，核心指令在 SKILL.md |
| **兼容性** | `纯SKILL.md` `需hooks` `需scripts` |
| **跨Agent** | CC ✓ · Cursor ◐ 无hooks · Codex ◐ 无hooks · 通用 ◐ 无hooks |
| **来源** | 社区 |

> **superpowers-using-superpowers 降级方案**：无 hooks 时，SKILL.md 中的 skill 使用规范仍然有效，agent 会在会话中遵循。SessionStart hook 仅实现"自动加载"，缺失时需手动在会话开始时装载此 skill。

### codebase-design
| 项目 | 内容 |
|------|------|
| **描述** | 深度模块设计的共享词汇表 |
| **功能** | 设计/改进模块接口、寻找深化机会、决定接缝位置 |
| **使用** | 需要设计讨论时触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

### diagnosing-bugs
| 项目 | 内容 |
|------|------|
| **描述** | 难调试和性能回归的诊断循环 |
| **功能** | 系统化诊断顽固 bug |
| **使用** | 用户说"诊断"/"调试"，或报告某物损坏/抛出/失败/缓慢时触发 |
| **注意** | 含 scripts/（Shell），核心指令在 SKILL.md |
| **兼容性** | `纯SKILL.md` `需scripts` |
| **跨Agent** | CC ✓ · Cursor ◐ Shell可选 · Codex ◐ · 通用 ✓ 核心可用 |
| **来源** | 社区 |

### domain-modeling
| 项目 | 内容 |
|------|------|
| **描述** | 构建和锐化项目的领域模型 |
| **功能** | 确定领域术语、记录架构决策 |
| **使用** | 需要定义领域术语或记录 ADR 时触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 社区 |

---

## 三、代码审查（3 个）

### code-review
| 项目 | 内容 |
|------|------|
| **描述** | 双轴代码审查：标准 + 规格 |
| **功能** | 沿 Standards（是否符合编码标准）和 Spec（是否符合需求）两轴审查 |
| **使用** | 有变更需要审查时触发 |
| **注意** | 使用并行子代理运行两个审查 |
| **兼容性** | `纯SKILL.md` `需agents` |
| **跨Agent** | CC ✓ · Cursor ◐ 需子代理 · Codex ◐ · 通用 ✗ |
| **来源** | 社区 |

### diegosouzapw-deep-review
| 项目 | 内容 |
|------|------|
| **描述** | 综合深度代码审查，覆盖 30+ 维度 |
| **功能** | 架构、代码质量、错误处理、类型、注释、测试、可访问性、本地化、并发、性能、简化、安全、PII 泄漏检测、平台特定审查 |
| **使用** | 审查 PR、合并前、或需要全面代码质量评估时触发 |
| **注意** | 含 agents/（53 个 agent 定义）和 scripts/（Shell） |
| **兼容性** | `需agents` `需scripts` |
| **跨Agent** | CC ◐ · Cursor ◐ · Codex ◐ · 通用 ✗ 需子代理+Shell |
| **来源** | Iron-Ham (GitHub) |

### anthropic-claude-api
| 项目 | 内容 |
|------|------|
| **描述** | Claude API / Anthropic SDK 参考 |
| **功能** | 模型 ID、定价、参数、流式、工具使用、MCP、agents、缓存、token 计数、迁移 |
| **使用** | 涉及 Claude/Anthropic API 开发时触发 |
| **注意** | 含多语言示例（TypeScript、Python、Go、Java 等） |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | Anthropic 官方 |

---

## 四、需求管理（4 个）

### gen-prd
| 项目 | 内容 |
|------|------|
| **描述** | 通过交互式需求分析生成完整 PRD |
| **功能** | 结构化提问、数据流推导、生成需求文档 |
| **使用** | 用户要"生成 PRD/需求文档"时触发 |
| **注意** | 分析现有代码库请用其他工具，不要用此 skill |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 市场 (openclaw) |

### decompose-prd
| 项目 | 内容 |
|------|------|
| **描述** | PRD 分解引擎 |
| **功能** | 将 PRD 分解为 Epics→Features→Tasks 层级 DAG，含依赖图和可执行任务规格 |
| **使用** | 有 PRD 需要分解时触发 |
| **注意** | 支持所有格式（PDF、DOCX、Markdown、Notion、HTML） |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 市场 |

### prd-reviewer
| 项目 | 内容 |
|------|------|
| **描述** | PRD 需求评审评分工具 |
| **功能** | 10 分制严格量化评分，输出总分、各模块得分及详细扣分说明 |
| **使用** | 用户上传 PRD 并要求评审打分时触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 市场 (openclaw) |

### to-prd
| 项目 | 内容 |
|------|------|
| **描述** | 将当前对话转化为 PRD 并发布到 issue tracker |
| **功能** | 综合已有讨论生成 PRD，不需要额外采访 |
| **使用** | 讨论后需要整理 PRD 时触发 |
| **注意** | 需要 issue tracker 配置 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | Matt Pocock 生态 |

---

## 五、联网操作（14 个）

网页抓取、搜索、浏览器交互。

### web-access
| 项目 | 内容 |
|------|------|
| **描述** | 所有联网操作的统一入口 |
| **功能** | 搜索、网页抓取、登录后操作、网络交互、社交媒体（小红书、微博等） |
| **使用** | 用户要求搜索、查看网页、登录网站、操作网页界面时触发 |
| **注意** | 需要 Chrome DevTools MCP；含 scripts/（Node.js） |
| **兼容性** | `需MCP(chrome-devtools)` `需scripts(Node.js)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | 一泽Eze |

### firecrawl
| 项目 | 内容 |
|------|------|
| **描述** | Firecrawl CLI 的搜索、抓取、交互 |
| **功能** | 搜索、抓取网页、研究主题、下载站点 |
| **使用** | 需要联网获取信息时触发 |
| **注意** | 需要 Firecrawl MCP server 和 API key |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-scrape
| 项目 | 内容 |
|------|------|
| **描述** | 从 URL 提取干净的 markdown |
| **功能** | 抓取单个页面，支持 JS 渲染的 SPA |
| **使用** | 用户提供 URL 需要获取内容时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-crawl
| 项目 | 内容 |
|------|------|
| **描述** | 批量提取整个网站或站点section的内容 |
| **功能** | 跟随链接批量抓取多页 |
| **使用** | 用户说"crawl"/"获取所有页面"/"批量提取"时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-map
| 项目 | 内容 |
|------|------|
| **描述** | 发现并列出网站下所有 URL |
| **功能** | 站点地图枚举，可选搜索过滤 |
| **使用** | 需要找到特定页面或了解站点结构时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-search
| 项目 | 内容 |
|------|------|
| **描述** | 网页搜索 |
| **功能** | 搜索并返回相关网页 |
| **使用** | 需要搜索信息时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-agent
| 项目 | 内容 |
|------|------|
| **描述** | AI 驱动的自主数据提取 |
| **功能** | 导航复杂站点，返回结构化 JSON |
| **使用** | 需要结构化数据（价格、产品列表等）时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-interact
| 项目 | 内容 |
|------|------|
| **描述** | 控制实时浏览器会话与页面交互 |
| **功能** | 点击按钮、填写表单、导航流程、提取数据 |
| **使用** | 需要登录、提交表单、点击等交互时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-download
| 项目 | 内容 |
|------|------|
| **描述** | 下载整个网站为本地文件 |
| **功能** | 批量保存页面为 markdown、截图等格式 |
| **使用** | 需要离线保存文档时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-parse
| 项目 | 内容 |
|------|------|
| **描述** | 高效提取本地文件内容 |
| **功能** | 处理 PDF、DOCX、HTML 等转为 markdown |
| **使用** | 需要读取本地文档时触发 |
| **注意** | 需要 Firecrawl MCP |
| **兼容性** | `需MCP(firecrawl)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |
| **来源** | Firecrawl 官方 |

### firecrawl-build-interact
| 项目 | 内容 |
|------|------|
| **描述** | 将 Firecrawl /interact 集成到产品代码 |
| **功能** | 动态页面和浏览器操作的开发指导 |
| **使用** | 需要在代码中集成 Firecrawl 交互功能时触发 |
| **注意** | 面向开发者的集成指南，纯文档 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | Firecrawl 官方 |

### firecrawl-build-onboarding
| 项目 | 内容 |
|------|------|
| **描述** | Firecrawl 凭证和 SDK 配置 |
| **功能** | 帮助设置 FIRECRAWL_API_KEY、.env 配置 |
| **使用** | 首次配置 Firecrawl 时触发 |
| **注意** | 入门指南 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | Firecrawl 官方 |

### find-skills
| 项目 | 内容 |
|------|------|
| **描述** | 帮助发现和安装 agent skill |
| **功能** | 搜索可用的 skill 扩展 |
| **使用** | 用户问"怎么做 X"/"有没有 skill 能..."时触发 |
| **注意** | 需要 npx/skills CLI |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 市场 |

### yida-login
| 项目 | 内容 |
|------|------|
| **描述** | 宜搭登录态管理 |
| **功能** | 扫码登录、Cookie 持久化 |
| **使用** | 使用 openyida 相关命令时自动触发 |
| **注意** | 需要安装 openyida CLI 工具 |
| **兼容性** | `需CLI(openyida)` |
| **跨Agent** | CC ◐ 需CLI · Cursor ◐ 需CLI · Codex ◐ 需CLI · 通用 ✗ |
| **来源** | OpenYida 官方 |

---

## 六、写作辅助（2 个）

### content-research-writer
| 项目 | 内容 |
|------|------|
| **描述** | 高质量内容写作助手 |
| **功能** | 研究、添加引用、改进 hook、迭代大纲、实时反馈 |
| **使用** | 需要写作帮助时触发 |
| **注意** | 无特殊依赖 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | 市场 |

### session-handoff
| 项目 | 内容 |
|------|------|
| **描述** | 会话交接/对接文档范式 |
| **功能** | 跨会话任务进度保留、AGENTS.md 管理、专家团模式 |
| **使用** | 任务跨多会话/需分批推进时触发 |
| **注意** | 含 hooks/（PostToolUse+Stop）和 scripts/（Python）；**hooks 为可选增强**，核心功能无需 hooks |
| **兼容性** | `纯SKILL.md` `需hooks` `需scripts(Python)` |
| **跨Agent** | CC ✓ · Cursor ◐ 无hooks，手动运行脚本 · Codex ◐ 无hooks · 通用 ◐ 无hooks |
| **来源** | 自创 |

> **session-handoff 降级方案**：无 hooks 的 agent 核心功能仍可用（创建/更新交接文档），只需在会话开始/结束时手动运行 `python scripts/handoff.py validate` 和 `python scripts/handoff.py status`。详见 `test-env/SESSION-HANDOFF-COMPATIBILITY.md`。

---

## 七、效率工具（12 个）

### claude-mem 系列（4 个）

需要 claude-mem MCP server。

| Skill | 描述 | 使用场景 |
|-------|------|---------|
| **claude-mem-knowledge-agent** | 构建和查询 AI 知识库 | 创建"大脑"、查询工作模式 |
| **claude-mem-learn-codebase** | 完整阅读代码库所有源文件 | 开始新项目时"学习代码库" |
| **claude-mem-mem-search** | 搜索跨会话持久化记忆 | "上次我们怎么做的？" |
| **claude-mem-smart-explore** | Token 优化的结构化代码搜索 | 用 tree-sitter AST 解析探索代码 |

以上 4 个 skill 兼容性相同：

| 项目 | 内容 |
|------|------|
| **兼容性** | `需MCP(claude-mem)` |
| **跨Agent** | CC ◐ 需MCP · Cursor ◐ 需MCP · Codex ◐ 需MCP · 通用 ✗ |

### anthropic 视觉设计系列（4 个）

| Skill | 描述 | 使用场景 | 跨Agent |
|-------|------|---------|---------|
| **anthropic-algorithmic-art** | 用 p5.js 创建算法艺术 | 生成艺术、流场、粒子系统 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-brand-guidelines** | 应用 Anthropic 品牌色彩和排版 | 需要 Anthropic 风格时 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-canvas-design** | 在 .png/.pdf 中创建视觉艺术 | 海报、设计、视觉作品 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-frontend-design** | 独特、有意图的视觉设计指导 | 构建新 UI 或重塑现有 UI | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |

### 其他效率工具

| Skill | 描述 | 使用场景 | 跨Agent |
|-------|------|---------|---------|
| **anthropic-doc-coauthoring** | 文档协作工作流 | 写文档、提案、技术规格 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-internal-comms** | 内部沟通写作 | 状态报告、领导更新、FAQ | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-mcp-builder** | 创建 MCP server | 构建 MCP 集成 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✗ 需Python |
| **anthropic-theme-factory** | 主题样式工具包 | 给 artifact 应用主题 | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **anthropic-web-artifacts-builder** | 复杂 HTML artifact 构建 | React + Tailwind + shadcn/ui | CC ✓ · Cursor ◐ 需Shell · Codex ◐ · 通用 ✗ 需Shell |
| **course-assignment** | 大学课程作业通用流程 | 完成作业/大作业/实验报告 | CC ◐ 需Node+chrome-devtools · Cursor ◐ 需Node+MCP · Codex ◐ · 通用 ✗ |
| **to-issues** | 将计划分解为可领取的 issue | 任务分解发布到 issue tracker | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |

---

## 八、驱动风格（4 个）

PUA 系列，调节 agent 的工作风格和积极性。来自 [pua-skill](https://pua-skill.pages.dev) 项目。

> **警告**：PUA 系列会显著改变 agent 的交互风格。安装前请了解各模式特点。

### pua-pua
| 项目 | 内容 |
|------|------|
| **描述** | PUA 核心模式 — 高绩效文化驱动 |
| **功能** | 14 种大厂味道、方法论路由、P8 顶层设计思维、7 项工作清单 |
| **使用** | 用户请求 PUA 模式、或表现出挫败/重复失败/被动时触发 |
| **注意** | 含 hooks/（7 种事件）、scripts/（Shell）、agents/（7 个 agent）；**hooks 为增强**，核心指令在 SKILL.md |
| **兼容性** | `需hooks` `需scripts` `需agents` |
| **跨Agent** | CC ✓ · Cursor ◐ 无hooks · Codex ◐ 无hooks · 通用 ◐ 无hooks |
| **来源** | pua-skill 项目 (MIT) |

> **pua-pua 降级方案**：无 hooks 时，核心 PUA 行为仍由 SKILL.md 指令驱动。hooks 仅提供自动化增强（失败检测、挫折拦截等），缺失不影响主功能。

### pua-mama
| 项目 | 内容 |
|------|------|
| **描述** | 妈妈唠叨模式 — 中国式妈妈驱动 |
| **功能** | 底层行为不变，旁白变成妈妈碎碎念 |
| **使用** | `/pua:mama` 或说"妈妈模式"时触发 |
| **注意** | 是旁白风格切换，不改变核心行为 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | pua-skill 项目 (MIT) |

### pua-pua-loop
| 项目 | 内容 |
|------|------|
| **描述** | 自动迭代开发循环 |
| **功能** | 自主迭代直到验证完成，含 Oracle 隔离验证 |
| **使用** | `/pua:pua-loop` 或说"自动循环"时触发 |
| **注意** | 会持续运行直到完成 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | pua-skill 项目 (MIT) |

### pua-yes
| 项目 | 内容 |
|------|------|
| **描述** | 夸夸模式 — ENFP 型领导 |
| **功能** | 共情+鼓励+偶尔吐槽，底层行为不变 |
| **使用** | `/pua:yes` 或说"夸夸模式"时触发 |
| **注意** | 是旁白风格切换，不改变核心行为 |
| **兼容性** | `纯SKILL.md` |
| **跨Agent** | CC ✓ · Cursor ✓ · Codex ✓ · 通用 ✓ |
| **来源** | pua-skill 项目 (MIT) |

---

## 快速选择指南

### 按场景推荐

| 场景 | 推荐 skill |
|------|-----------|
| **新手入门，想要完整开发流程** | superpowers-* 全系列 |
| **需要生成办公文档** | anthropic-docx/pdf/pptx/xlsx |
| **处理旧版 Excel (.xls)** | xls-poi |
| **需要联网获取信息** | web-access 或 firecrawl 系列 |
| **写 PRD / 需求分析** | gen-prd + decompose-prd + prd-reviewer |
| **代码审查** | code-review 或 diegosouzapw-deep-review |
| **跨会话任务管理** | session-handoff |
| **大学作业** | course-assignment |
| **想让 agent 更积极** | pua-pua（完整版）或 pua-yes（温和版） |
| **制作个人文风 skill** | 参考 daibi-template/ |

### 按兼容性选择

| 你的环境 | 推荐 |
|---------|------|
| **纯 SKILL.md，无额外依赖** | 大部分 skill 都可用 |
| **有 Node.js** | + anthropic-docx、web-access 等 |
| **有 Python** | + anthropic-pdf/pptx/xlsx、session-handoff 等 |
| **有 Firecrawl MCP** | + firecrawl 全系列 |
| **有 chrome-devtools MCP** | + web-access |
| **agent 支持 hooks** | + pua-pua、session-handoff、superpowers-using-superpowers |

### 按 Agent 选择

| 你的 Agent | 完全兼容 | 部分兼容（需配置） | 不兼容 |
|-----------|---------|-------------------|--------|
| **Claude Code** | 全部 63 个 | — | — |
| **Cursor** | ~45 个纯 SKILL.md | ~15 个需脚本/MCP | ~3 个 hooks 降级可用 |
| **Codex / Gemini CLI** | ~45 个纯 SKILL.md | ~12 个需脚本/MCP | ~6 个需 hooks/shell |
| **通用 SKILL.md agent** | ~40 个纯 SKILL.md | — | ~23 个需运行时/MCP/hooks |
