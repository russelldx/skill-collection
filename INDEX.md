# Skill 索引

仅下列 **55 个活动入口** 位于 `skills/`。保留不代表默认安装或所有分支已验证；按任务选择并检查工具、运行时和授权。原有另外 8 个入口已合并或暂停，内容保留在本文末尾的位置。

## 文档与课程（7 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [anthropic-docx](skills/anthropic-docx/SKILL.md) | Word 创建、编辑、模板填充 | 按路线需要 Python / Node；模板由用户提供，不承诺捆绑缺失模板 |
| [anthropic-pdf](skills/anthropic-pdf/SKILL.md) | PDF 提取、合并、拆分与表单 | Python / PDF 工具，按操作检查依赖 |
| [anthropic-pptx](skills/anthropic-pptx/SKILL.md) | 演示文稿生成与编辑 | Node / Python / 渲染工具；必须检查渲染结果 |
| [anthropic-xlsx](skills/anthropic-xlsx/SKILL.md) | `.xlsx`、CSV、TSV 通用处理 | Python；Office 重算另需依赖，不能修改真实用户宏配置 |
| [xls-poi](skills/xls-poi/SKILL.md) | BIFF8 / POI 表格分析与模板处理 | Java + POI；删列执行链路暂停，不能以旧验证器输出证明完整保真 |
| [anthropic-slack-gif-creator](skills/anthropic-slack-gif-creator/SKILL.md) | Slack 动画 GIF | 按需，Python 及目录内依赖 |
| [course-assignment](skills/course-assignment/SKILL.md) | 取题、实测、撰写、文档验收 | 按路线需要浏览器、Node / Python；上传和提交须明确授权 |

## 开发流程与设计（13 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [superpowers-brainstorming](skills/superpowers-brainstorming/SKILL.md) | 澄清复杂或开放性设计 | 按需，明确的小任务或已批准详细方案不重复审批 |
| [superpowers-writing-plans](skills/superpowers-writing-plans/SKILL.md) | 按可验收成果划任务、定义接口与验证重点 | 多步骤任务，是否写计划文件遵循用户要求 |
| [superpowers-executing-plans](skills/superpowers-executing-plans/SKILL.md) | 直接执行已批准方案，保留批次证据与整体审查 | 尊重执行模式，遇到实质偏差或权限边界再确认 |
| [superpowers-test-driven-development](skills/superpowers-test-driven-development/SKILL.md) | 红→绿→重构 | 不授予删除既有工作或绕过权限的授权 |
| [superpowers-subagent-driven-development](skills/superpowers-subagent-driven-development/SKILL.md) | 按任务或同形批次委派，分阶段及整体审查 | 需宿主子代理能力；不假定继承上下文，修复评审最多两轮 |
| [superpowers-dispatching-parallel-agents](skills/superpowers-dispatching-parallel-agents/SKILL.md) | 独立任务分治 | 按需，共享文件或有依赖的任务不盲目并行 |
| [superpowers-systematic-debugging](skills/superpowers-systematic-debugging/SKILL.md) | 根因调试与性能回归诊断 | 已吸收 diagnosing-bugs 的复现、假设排序和测量方法 |
| [superpowers-using-git-worktrees](skills/superpowers-using-git-worktrees/SKILL.md) | 隔离开发环境 | 按需；安装依赖、提交和清理仍须对应授权 |
| [superpowers-verification-before-completion](skills/superpowers-verification-before-completion/SKILL.md) | 完成声明前检查证据 | 不用静态检查替代真实功能测试 |
| [superpowers-requesting-code-review](skills/superpowers-requesting-code-review/SKILL.md) | 组织审查输入和时机 | 不代表自动发布 PR 或评论 |
| [superpowers-receiving-code-review](skills/superpowers-receiving-code-review/SKILL.md) | 验证并处理评审意见 | 不盲从未经核实的建议 |
| [codebase-design](skills/codebase-design/SKILL.md) | 深模块、接口与测试接缝 | 设计讨论，不强制引入抽象 |
| [domain-modeling](skills/domain-modeling/SKILL.md) | 领域术语与架构决策 | 按需求维护领域模型 |

## 代码审查（2 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [code-review](skills/code-review/SKILL.md) | 标准与需求双轴审查 | 区分已提交差异、工作区和未跟踪文件；检查两轴实际覆盖相同范围 |
| [diegosouzapw-deep-review](skills/diegosouzapw-deep-review/SKILL.md) | 多维专项审查 | 按需，需要适配子代理和脚本，不作为每次小改动的默认流程 |

## 需求管理（5 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [gen-prd](skills/gen-prd/SKILL.md) | 访谈并生成需求文档 | 不依赖未提供的领域知识库；用户提供知识库后才能声称知识库驱动 |
| [decompose-prd](skills/decompose-prd/SKILL.md) | Epic → Feature → Task 依赖拆解 | 使用正文规则，不引用不存在的附件 |
| [prd-reviewer](skills/prd-reviewer/SKILL.md) | PRD 量化评审 | 先确认专用组织量表适用性，不把 TAPD 等字段强套所有需求 |
| [to-prd](skills/to-prd/SKILL.md) | 把已有讨论整理为 PRD | 发布到外部 tracker 另需授权与有效工具 |
| [to-issues](skills/to-issues/SKILL.md) | 拆分为纵向工单 | 创建或修改远程工单另需授权 |

## 联网与扩展（13 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [web-access](skills/web-access/SKILL.md) | 本机登录态、CDP、书签/历史、站点经验 | Node.js 22+；历史另需 sqlite3 CLI；不依赖 Chrome DevTools MCP |
| [firecrawl](skills/firecrawl/SKILL.md) | CLI 分流及结构化数据提供方发现 | 先检查版本和命令能力；MCP 是不同接口，不代替 CLI 验证 |
| [firecrawl-scrape](skills/firecrawl-scrape/SKILL.md) | 已知页面提取或已确认的数据提供方执行 | 选择 Firecrawl 时使用；提供方须接口支持、契约匹配与授权 |
| [firecrawl-crawl](skills/firecrawl-crawl/SKILL.md) | 多页或站点批量提取 | 控制范围与额度 |
| [firecrawl-map](skills/firecrawl-map/SKILL.md) | URL 发现与枚举 | 不等于读取每一页正文 |
| [firecrawl-agent](skills/firecrawl-agent/SKILL.md) | 异步结构化研究与已有任务查询 | 有界等待，检查终态、实际数据与额度，不重复提交未决任务 |
| [firecrawl-interact](skills/firecrawl-interact/SKILL.md) | 云端浏览器交互 | 支持登录及 profile，但不自动继承本机登录态 |
| [firecrawl-download](skills/firecrawl-download/SKILL.md) | 网站保存为本地文件 | 按需，实验性命令以实际 CLI 版本为准 |
| [firecrawl-parse](skills/firecrawl-parse/SKILL.md) | Firecrawl 文档解析 | 按需，托管模式上传前明确确认；敏感本地文档优先本地处理 |
| [firecrawl-build-interact](skills/firecrawl-build-interact/SKILL.md) | 将 interact 集成到产品代码 | 按需，不等同于直接操作网页 |
| [firecrawl-build-onboarding](skills/firecrawl-build-onboarding/SKILL.md) | 项目 SDK / 凭据接入与端点选择 | 检查 SDK 契约支持，不自动升级、全局安装或提交密钥 |
| [find-skills](skills/find-skills/SKILL.md) | 按关键词或支持的作者筛选发现技能 | 下载执行须授权；安装量不是安全审核，不全量覆盖定制 |
| [yida-login](skills/yida-login/SKILL.md) | 宜搭登录态管理 | 按需，OpenYida CLI；先检查已有登录态 |

Firecrawl 共 10 个独立入口；搜索说明在 `firecrawl` 主技能，不存在单独的 `firecrawl-search` 目录。

## 写作与交接（4 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [anthropic-doc-coauthoring](skills/anthropic-doc-coauthoring/SKILL.md) | 共创文档与读者测试 | 不等于文件格式转换 |
| [anthropic-internal-comms](skills/anthropic-internal-comms/SKILL.md) | 组织沟通模板 | 按需，保留独有模板，不强制公司口吻 |
| [content-research-writer](skills/content-research-writer/SKILL.md) | 研究、引用和写作迭代 | 按需，事实须有来源 |
| [session-handoff](skills/session-handoff/SKILL.md) | 可接续的交接状态文件 | 创建交接体系、改 AGENTS/.gitignore 与全局 hooks 安装须分别授权 |

## API 与记忆（5 个）

| Skill | 用途 | 依赖 / 限制 |
|-------|------|-------------|
| [anthropic-claude-api](skills/anthropic-claude-api/SKILL.md) | Claude API / Anthropic SDK 参考 | 仅明确的供应商 API 任务触发，不接管普通总结或其他供应商代码 |
| [anthropic-mcp-builder](skills/anthropic-mcp-builder/SKILL.md) | MCP 服务端设计和评测 | 按语言选择运行时 / SDK |
| [claude-mem-mem-search](skills/claude-mem-mem-search/SKILL.md) | 三层过滤检索，必要时取原始工具证据 | 第四层须实际暴露 get_tool_uses；无工具或 ID 时不伪造证据 |
| [claude-mem-smart-explore](skills/claude-mem-smart-explore/SKILL.md) | 当前源码 AST 探索 | 需相应 MCP 工具；显式全文模式必须限制范围和预算 |
| [claude-mem-knowledge-agent](skills/claude-mem-knowledge-agent/SKILL.md) | 专题语料库与持续问答 | 按需，需相应语料库工具，不假定所有版本均提供 |

## 视觉设计（6 个）

| Skill | 用途 | 使用边界 |
|-------|------|----------|
| [anthropic-algorithmic-art](skills/anthropic-algorithmic-art/SKILL.md) | 种子驱动的算法艺术 | 按需，p5.js 环境 |
| [anthropic-brand-guidelines](skills/anthropic-brand-guidelines/SKILL.md) | Anthropic 品牌规则 | 按需，仅用户需要该品牌时应用 |
| [anthropic-canvas-design](skills/anthropic-canvas-design/SKILL.md) | 静态画布构图 | 按需，交付格式由用户决定 |
| [anthropic-frontend-design](skills/anthropic-frontend-design/SKILL.md) | 前端视觉设计 | 实现后需要浏览器实测，不仅检查构建 |
| [anthropic-theme-factory](skills/anthropic-theme-factory/SKILL.md) | 主题资产与排版配色 | 按需，不覆盖用户明确的品牌要求 |
| [anthropic-web-artifacts-builder](skills/anthropic-web-artifacts-builder/SKILL.md) | 多组件 HTML artifact 构建 | 按需，Node / shell；依赖安装另需授权 |

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
