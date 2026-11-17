# <项目/任务> · <主题> 实施与交接文档

> AGENTS.md 管静态约定；当前态管本任务，事件提供原始依据。先检查角色与隔离，再运行 context 限额接续。
> 仅在用户授权目录创建/更新。STATE.json 与 §0 由 refresh 派生；事件只追加，已闭环任务原样归档。

## 当前态

```handoff-state
{
  "schemaVersion": 2,
  "session": "<chatId-or-name>",
  "title": "<主题>",
  "phase": "<当前批次>",
  "status": "in-progress",
  "updatedAt": "<ISO时间>",
  "goal": "<目标及需求来源>",
  "constraints": [],
  "acceptance": [],
  "openBlockers": [],
  "nextActions": [],
  "fileOwnership": {},
  "artifacts": [],
  "keyDecisions": [],
  "tags": [],
  "tasks": [
    {
      "id": "T1",
      "title": "<第一批>",
      "status": "in-progress",
      "verified": false,
      "archiveReady": false,
      "openItems": ["待核验"],
      "evidence": [],
      "summary": "<本批目标>"
    }
  ]
}
```

## 0、滚动摘要

由 `python scripts/handoff.py refresh "<目录>"` 自动派生，勿另写一份状态。

## 环境与工具

- 必须准确恢复的命令、路径、版本与环境条件放当前态 constraints/artifacts；这里补来源与说明，不维护第二份当前态。
- 编程：编译/启动完整命令、profile、端口；非编程：软件/网站/计算器/文献库及核验方式。
- 凭据只记安全存放位置，不复制密钥、Cookie或密码。

## 1、YYYY-MM-DD 会话：<主题>

**task**: T1

- 完成内容与关键结论：
- 用户裁决：原文或准确摘引 + 来源 + 理由 + 影响面；有效部分同步当前态。
- 验证证据：实际命令/核对方式 + 结果 + 产物位置；未验证写“待验证”。
- 新坑：现象 → 根因 → 处理 → 已修复/遗留。
- 环境变更：
- 遗留/待办：当前项同步 nextActions/openBlockers；不要仅留在历史叙述里。

## 临时文件规范

- 统一目录 + 生命周期；当前会话临时文件在授权范围内清理，长期保留注明期限。
- 近期聊天原文另获留存授权后才放 RECENT.jsonl；默认不创建、不读取宿主私人日志。

## 领域附加节（按需保留）

- 中文成稿（通用）：遵循 `session-handoff` 核心的「中文表达」约定，默认按 `shuorenhua` 顺句子，保留独立信息；只在改写已有文字时于回复附改动摘要。此行仅作提示，不替代核心规则加载。
- 编程项目：规范章节模板 `assets/code-standard-template.md`；已有 AGENTS 规则只引用，不复制维护。
- 专家团：按 TEAM.md/BRIEF.md/OUTBOX.md/QUESTIONS.md 协议协作；主角色核验后补录，隔离角色不读共享恢复包。
