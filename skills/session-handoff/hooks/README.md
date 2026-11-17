# hooks/ — 会话交接的运行时钩子（本目录是源，`~/.qoder/hooks/` 是部署目标）

## 为什么要放这里

skill 的 hook 属于"语义上的一部分、运行时在别处"。以前只存在于 `~/.qoder/hooks/`，脱离 skill 版本管理——卸装 skill 不会带 hook、双副本 skill 只同步内容不同步 hook。现在把源放进 skill，运行时通过 `handoff.py install-hooks` 一键部署，形成清晰的 **source-of-truth ↔ installed** 关系（类比 npm `bin/` 与 `node_modules/.bin/`）。

## 目录内容

- `handoff-stamp.sh` — PostToolUse hook。Edit/Write 命中 `*交接*` / `*实施计划*` / `TEAM.md` / `HANDOFF.md`（含 `~/.qoder/handoffs/`、`.handoff/` 下的路径）时，把文档绝对路径写入 `~/.qoder/tmp/handoff_updated_<session_id>` 作为"本会话改过"标记；`archive/`、`.backup/` 下的写入不计数。已触发过一次 Stop 检查后不再重新武装（防循环）。
  - 2026-10-31 修正：旧版只认中文文件名，而 skill 默认产出的是 `HANDOFF.md`，两套命名对不上 → 标记永远打不上，Stop 检查静默放行。现补上 `HANDOFF.md` / `handoff.md` 与 handoffs 路径线索。
- `handoff-stop-check.sh` — Stop hook，主agent回复结束时一次性提醒，不等于会话退出或自动验收：
  - **①** 小节：提醒核对本轮记录，hook本身不验证记录内容。
  - **②** 归档（主文档整文件字节超阈）：先检查角色/授权与任务闭环，archive默认预览，获准后 --apply 原样搬移；摘要不能代替物理减载。
  - **③** 读模型（STATE.json 缺失或早于文档改动）：新版从当前态 refresh 派生，validate/context 校验来源hash与内容；旧版按人工流程，不擅自迁移。
  - 阈值 `HANDOFF_SIZE_LIMIT`（默认 20480），退出码 2 = 阻断，标"确认无需"可跳过（一次性）

## 部署与升级

**独立授权门槛**：以下命令会写全局运行时目录并可能影响后续所有会话。先说明目标路径、覆盖/备份和检查行为，只有用户明确批准全局 hooks 安装/升级才可执行。允许创建交接文件、编辑 AGENTS.md/.gitignore 或改本目录源码，均不等于批准安装。反之，安装授权也不允许自动创建项目交接文件或修改 AGENTS.md/.gitignore；这些分别检查授权。权限/配置变更仍按系统/开发者要求处理，不绕过限制。

```
# 仅在用户明确授权全局部署后：复制到 ~/.qoder/hooks/（旧版备份、sha256 校验）
python scripts/handoff.py install-hooks

# 部署到别处（如自定义路径）
python scripts/handoff.py install-hooks --target "$HOME/other/hooks"
```

修改流程：在用户授权范围内改本目录源码；只有另行获准全局升级时才运行 install-hooks。未获准则保留为源码改动并报告“未部署”。不要在 `~/.qoder/hooks/` 就地编辑，也不要因 hook 提示自动扩大持久文件/配置编辑权限。

## 其他宿主 / 部署目标

`~/.qoder/hooks/` 是默认运行时位置。其它宿主必须先验证事件/输入/输出协议；`install-hooks --target` 只复制文件，不负责注册或保证兼容。本目录仍只有原有打标与Stop提醒源码，没有部署压缩恢复或聊天采集hook；Qoder可选接入边界见 `references/state-schema.md`。
