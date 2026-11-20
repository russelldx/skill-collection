# Skill 索引

`skills/` 中只有下列 **65 个活动入口**。列在这里，不代表默认安装，也不代表所有执行分支都已验证。请按任务选择，并检查所需工具、运行时和授权。原有另外 8 个入口已合并或暂停，保留内容的存放位置见本文末尾。

第一次使用请看[安装向导](INSTALL.md)；想知道“这个有什么用、要准备什么、怎么开口”，点击各项的“安装与用法”，或查看[全部中文说明卡](SKILL-GUIDE.md)。英文名称链接仍指向技能正文，适合核对具体流程。

## 文档与课程（8 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [anthropic-docx](skills/anthropic-docx/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-docx) | 创建、编辑 Word，填充模板 | 按处理方式准备 Python / Node；模板由用户提供，不保证附带所缺的模板 |
| [docx-meta](skills/docx-meta/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-docx-meta) | 交付 Word 前清理元数据、校正时间线 | Python；只处理 `.docx`；处理前关闭 Word/WPS；清理后再保存会写回元数据 |
| [anthropic-pdf](skills/anthropic-pdf/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-pdf) | 提取、合并、拆分 PDF，处理表单 | Python / PDF 工具，按具体操作检查依赖 |
| [anthropic-pptx](skills/anthropic-pptx/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-pptx) | 生成、编辑演示文稿 | Node / Python / 渲染工具；必须检查渲染结果 |
| [anthropic-xlsx](skills/anthropic-xlsx/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-xlsx) | `.xlsx`、CSV、TSV 通用处理 | Python；通过 Office 重算还需要其他依赖，不能修改真实用户的宏配置 |
| [xls-poi](skills/xls-poi/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-xls-poi) | 分析 BIFF8 / POI 表格、处理模板 | Java + POI；删列流程已暂停，不能拿旧验证器的输出证明处理结果完整保真 |
| [anthropic-slack-gif-creator](skills/anthropic-slack-gif-creator/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-slack-gif-creator) | 制作 Slack 动画 GIF | 按需使用，需 Python 及目录内的依赖 |
| [course-assignment](skills/course-assignment/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-course-assignment) | 取题、实测、撰写和验收文档；生成 docx 后必须完成元数据收尾处理 | 按处理方式准备浏览器、Node / Python；上传和提交须明确授权 |

## 开发流程与设计（13 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [superpowers-brainstorming](skills/superpowers-brainstorming/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-brainstorming) | 澄清复杂或开放性设计 | 按需，明确的小任务或已批准详细方案不重复审批 |
| [superpowers-writing-plans](skills/superpowers-writing-plans/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-writing-plans) | 按可验收的成果拆任务，定义接口和验证重点 | 用于多步骤任务；是否写计划文件，按用户要求处理 |
| [superpowers-executing-plans](skills/superpowers-executing-plans/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-executing-plans) | 直接执行已批准的方案，保留各批次证据并做整体审查 | 遵守已选的执行模式，遇到实质偏差或权限边界时再确认 |
| [superpowers-test-driven-development](skills/superpowers-test-driven-development/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-test-driven-development) | 红→绿→重构 | 使用本技能不等于获得删除既有工作或绕过权限的授权 |
| [superpowers-subagent-driven-development](skills/superpowers-subagent-driven-development/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-subagent-driven-development) | 按任务或同形批次委派，分阶段审查，并做整体审查 | 需要宿主支持子代理；不假定子代理会继承上下文，修复评审最多两轮 |
| [superpowers-dispatching-parallel-agents](skills/superpowers-dispatching-parallel-agents/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-dispatching-parallel-agents) | 把独立任务分开处理 | 按需使用；任务共享文件或互相依赖时，不盲目并行 |
| [superpowers-systematic-debugging](skills/superpowers-systematic-debugging/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-systematic-debugging) | 查找问题根因，诊断性能回归 | 已吸收 diagnosing-bugs 的复现、假设排序和测量方法 |
| [superpowers-using-git-worktrees](skills/superpowers-using-git-worktrees/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-using-git-worktrees) | 隔离开发环境 | 按需使用；安装依赖、提交和清理仍要分别获得相应授权 |
| [superpowers-verification-before-completion](skills/superpowers-verification-before-completion/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-verification-before-completion) | 声称完成前核对证据 | 静态检查不能替代真实功能测试 |
| [superpowers-requesting-code-review](skills/superpowers-requesting-code-review/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-requesting-code-review) | 准备审查所需材料，安排审查时机 | 不会因此自动发布 PR 或评论 |
| [superpowers-receiving-code-review](skills/superpowers-receiving-code-review/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-superpowers-receiving-code-review) | 核实并处理评审意见 | 不直接采纳未经核实的建议 |
| [codebase-design](skills/codebase-design/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-codebase-design) | 讨论深模块、接口和测试接缝 | 用于设计讨论，不强制引入抽象 |
| [domain-modeling](skills/domain-modeling/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-domain-modeling) | 整理领域术语和架构决策 | 按需求维护领域模型 |

## 代码审查（2 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [code-review](skills/code-review/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-code-review) | 分别按标准和需求审查 | 区分已提交差异、工作区和未跟踪文件；核对两类审查实际覆盖的范围是否相同 |
| [diegosouzapw-deep-review](skills/diegosouzapw-deep-review/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-diegosouzapw-deep-review) | 从多个方面做专项审查 | 按需使用，需要适配子代理和脚本；不把它作为每次小改动的默认流程 |

## 需求管理（5 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [gen-prd](skills/gen-prd/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-gen-prd) | 访谈并生成需求文档 | 不依赖未提供的领域知识库；用户提供知识库后才能声称知识库驱动 |
| [decompose-prd](skills/decompose-prd/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-decompose-prd) | Epic → Feature → Task 依赖拆解 | 使用正文规则，不引用不存在的附件 |
| [prd-reviewer](skills/prd-reviewer/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-prd-reviewer) | PRD 量化评审 | 先确认专用组织量表适用性，不把 TAPD 等字段强套所有需求 |
| [to-prd](skills/to-prd/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-to-prd) | 把已有讨论整理为 PRD | 发布到外部 tracker 另需授权与有效工具 |
| [to-issues](skills/to-issues/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-to-issues) | 拆分为纵向工单 | 创建或修改远程工单另需授权 |

## 联网与扩展（21 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [web-access](skills/web-access/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-web-access) | 本机登录态、CDP、书签/历史、站点经验 | Node.js 22+；历史另需 sqlite3 CLI；不依赖 Chrome DevTools MCP |
| [firecrawl](skills/firecrawl/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl) | 选择合适的 CLI 操作，查找结构化数据提供方 | 先检查版本和命令支持的能力；MCP 是另一套接口，不能替代对 CLI 的验证 |
| [firecrawl-scrape](skills/firecrawl-scrape/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-scrape) | 提取已知页面，或调用已确认的数据提供方 | 选用 Firecrawl 时使用；调用提供方前，要确认接口支持、契约匹配并获得授权 |
| [firecrawl-crawl](skills/firecrawl-crawl/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-crawl) | 批量提取多个页面或站点内容 | 需要控制范围和额度 |
| [firecrawl-map](skills/firecrawl-map/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-map) | 查找并列出 URL | 不会因此读取每一页正文 |
| [firecrawl-agent](skills/firecrawl-agent/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-agent) | 异步开展结构化研究，查询已有任务 | 等待有时限；检查最终状态、实际数据和额度，不重复提交尚未结束的任务 |
| [firecrawl-interact](skills/firecrawl-interact/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-interact) | 操作云端浏览器 | 支持登录和 profile，但不会自动继承本机登录态 |
| [firecrawl-download](skills/firecrawl-download/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-download) | 把网站内容保存为本地文件 | 按需使用；实验性命令以实际 CLI 版本为准 |
| [firecrawl-parse](skills/firecrawl-parse/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-parse) | 用 Firecrawl 解析文档 | 按需使用；托管模式上传前要明确确认，敏感的本地文档优先在本地处理 |
| [firecrawl-search](skills/firecrawl-search/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-search) | 搜索网页、查找数据提供方和工作流 | 按需使用 Firecrawl CLI；结果额度和反馈退款以实际接口为准 |
| [firecrawl-monitor](skills/firecrawl-monitor/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-monitor) | 监测已知 URL 的变化，通过 webhook/邮件告警 | 按需使用，会安排后续检查任务；目标和范围须先获得授权 |
| [firecrawl-alexandria](skills/firecrawl-alexandria/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-alexandria) | 按契约执行工作流、调用数据提供方 | 需要 Firecrawl 团队开通该能力；不会调用被门控限制的提供方 |
| [firecrawl-developer-index](skills/firecrawl-developer-index/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-developer-index) | 在仓库、issue、PR、README 和文档索引中检索 | 用于编程问题；结果仍要核对版本和出处 |
| [firecrawl-research-index](skills/firecrawl-research-index/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-research-index) | 检索论文索引，针对全文提问 | 以生物医学与 arXiv 为主，不能当成通用网页搜索 |
| [firecrawl-build](skills/firecrawl-build/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-build) | 在产品代码中集成 Firecrawl | 按需使用，会修改应用代码和依赖；先确认端点和密钥来源 |
| [firecrawl-build-scrape](skills/firecrawl-build-scrape/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-build-scrape) | 将 `/scrape` 集成进应用代码 | 用于页面级集成，不替代批量爬取 |
| [firecrawl-build-search](skills/firecrawl-build-search/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-build-search) | 将 `/search` 集成进应用代码 | 从查询开始；需要先有 URL 时接 build-scrape |
| [firecrawl-build-interact](skills/firecrawl-build-interact/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-build-interact) | 将 interact 集成到产品代码 | 按需使用，不等同于直接操作网页 |
| [firecrawl-build-onboarding](skills/firecrawl-build-onboarding/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-firecrawl-build-onboarding) | 在项目中接入 SDK / 凭据，选择端点 | 检查 SDK 是否支持相应契约；不自动升级、全局安装或提交密钥 |
| [find-skills](skills/find-skills/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-find-skills) | 按关键词，或按支持的作者筛选条件查找技能 | 下载和执行须授权；安装量不能代替安全审核，不能全量覆盖定制内容 |
| [yida-login](skills/yida-login/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-yida-login) | 管理宜搭登录态 | 按需使用 OpenYida CLI；先检查已有登录态 |

Firecrawl 共 18 个独立入口：主技能 `firecrawl` 1 个、CLI 操作技能 7 个（scrape/crawl/map/agent/interact/download/parse）、检索与数据提供方技能 5 个（search/monitor/alexandria/developer-index/research-index）、build 集成技能 5 个（build/build-scrape/build-search/build-interact/build-onboarding）。来源为上游 `firecrawl/cli` 与 `firecrawl/skills` 两个仓库。

## 写作与交接（5 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [anthropic-doc-coauthoring](skills/anthropic-doc-coauthoring/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-doc-coauthoring) | 共创文档与读者测试 | 不等于文件格式转换 |
| [anthropic-internal-comms](skills/anthropic-internal-comms/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-internal-comms) | 组织沟通模板 | 按需，保留独有模板，不强制公司口吻 |
| [content-research-writer](skills/content-research-writer/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-content-research-writer) | 研究、引用和写作迭代 | 按需，事实须有来源 |
| [shuorenhua](skills/shuorenhua/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-shuorenhua) | 所有面向用户的中文回复自然表达、保留信息；普通回复不附改动摘要 | 默认推荐与全局规则一起安装；MIT 上游的本地定制，不以检测分数验收；全局写入需单独授权并验证加载 |
| [session-handoff](skills/session-handoff/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-session-handoff) | 可接续的交接状态文件（核心入口） | 创建交接体系、改 AGENTS/.gitignore 与全局 hooks 安装须分别授权 |

`shuorenhua + 全局规则` 是中文沟通的默认推荐组合，不限于写作任务。安装时主动说明全局配置的目标位置和影响范围，单独取得授权后写入并验证实际加载；未配置或未验证时明确说明，不能只安装 skill 就宣称全局生效。普通回复不附改动摘要，用户要求改写已有文字且确有改动时才默认附上；用户只要正文则省略。具体步骤见 [README](README.md#中文回复的全局规则安装时必查)。

`session-handoff` 是本仓库的核心入口：任何跨会话、分批推进或需要把踩坑留给后续会话的任务，默认推荐安装；跳过时应在推荐清单里写明理由。

## API 与记忆（5 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [anthropic-claude-api](skills/anthropic-claude-api/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-claude-api) | Claude API / Anthropic SDK 参考 | 只在明确涉及该供应商 API 的任务中触发，不接管普通总结或其他供应商的代码 |
| [anthropic-mcp-builder](skills/anthropic-mcp-builder/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-mcp-builder) | 设计、评测 MCP 服务端 | 按所用语言选择运行时 / SDK |
| [claude-mem-mem-search](skills/claude-mem-mem-search/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-claude-mem-mem-search) | 分三层过滤和检索，必要时读取原始工具证据 | 使用第四层前，必须确认实际提供了 get_tool_uses；没有工具或 ID 时，不编造证据 |
| [claude-mem-smart-explore](skills/claude-mem-smart-explore/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-claude-mem-smart-explore) | 通过 AST 探索当前源码 | 需要相应的 MCP 工具；显式全文模式必须限制范围和预算 |
| [claude-mem-knowledge-agent](skills/claude-mem-knowledge-agent/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-claude-mem-knowledge-agent) | 建立专题语料库，持续问答 | 按需使用，需要相应的语料库工具；不能假定所有版本都有这些工具 |

## 视觉设计（6 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [anthropic-algorithmic-art](skills/anthropic-algorithmic-art/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-algorithmic-art) | 种子驱动的算法艺术 | 按需，p5.js 环境 |
| [anthropic-brand-guidelines](skills/anthropic-brand-guidelines/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-brand-guidelines) | Anthropic 品牌规则 | 按需，仅用户需要该品牌时应用 |
| [anthropic-canvas-design](skills/anthropic-canvas-design/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-canvas-design) | 静态画布构图 | 按需，交付格式由用户决定 |
| [anthropic-frontend-design](skills/anthropic-frontend-design/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-frontend-design) | 前端视觉设计 | 实现后需要浏览器实测，不仅检查构建 |
| [anthropic-theme-factory](skills/anthropic-theme-factory/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-theme-factory) | 主题资产与排版配色 | 按需，不覆盖用户明确的品牌要求 |
| [anthropic-web-artifacts-builder](skills/anthropic-web-artifacts-builder/SKILL.md) · [安装与用法](SKILL-GUIDE.md#skill-anthropic-web-artifacts-builder) | 多组件 HTML artifact 构建 | 按需，Node / shell；依赖安装另需授权 |

## 已合并的 4 个入口

这些文件是参考资料，不作为独立技能安装。

| 原入口 | 内容位置 / 替代入口 |
|--------|--------------------|
| diagnosing-bugs | [诊断参考](skills/superpowers-systematic-debugging/references/diagnosing-bugs/REFERENCE.md)，主入口为 systematic-debugging |
| claude-mem-learn-codebase | [全文阅读参考](skills/claude-mem-smart-explore/references/learn-codebase/REFERENCE.md)，主入口为 smart-explore |
| pua-mama | [文风参考](archive/disabled/pua-pua/references/styles/pua-mama/REFERENCE.md)，核心暂停期间不启用 |
| pua-yes | [文风参考](archive/disabled/pua-pua/references/styles/pua-yes/REFERENCE.md)，不以普通 yes 触发 |

## 暂停的 4 个入口

这些目录不在 `skills/` 中，主文件改名为 `REFERENCE.md`。不安装、不注册其 hooks；修复代码并不等于已完成重新启用验收。

| 原入口 | 归档 | 暂停原因 |
|--------|------|----------|
| superpowers-using-superpowers | [参考](archive/disabled/superpowers-using-superpowers/REFERENCE.md) | 过度强制触发和错误的权限优先级声明 |
| superpowers-finishing-a-development-branch | [参考](archive/disabled/superpowers-finishing-a-development-branch/REFERENCE.md) | worktree 目标及来源识别、清理顺序尚需端到端验收 |
| pua-pua | [参考](archive/disabled/pua-pua/REFERENCE.md) | 自动触发、遥测与宿主适配需完整审查 |
| pua-pua-loop | [参考](archive/disabled/pua-pua-loop/REFERENCE.md) | 验收、取消、隔离与运行边界需完整审查 |

详细工具配置见 [MCP-SETUP.md](MCP-SETUP.md)，测试范围见 [TEST-SUMMARY.md](TEST-SUMMARY.md)。本索引不提供未经实测的跨 agent 兼容数量保证。
