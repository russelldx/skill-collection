# hooks/ — 会话交接的运行时钩子（本目录是源，`~/.qoder/hooks/` 是部署目标）

## 为什么要放这里

skill 与 hook 的关系是"语义上的一部分、运行时在别处"。以前 hook 只放在 `~/.qoder/hooks/`，不在 skill 的版本管理中：卸装 skill 不会带上 hook，双副本 skill 也只同步内容，不同步 hook。现在把源码放进 skill，再通过 `handoff.py install-hooks` 一键部署到运行时位置。这样就明确了 **source-of-truth ↔ installed** 的关系（类比 npm `bin/` 与 `node_modules/.bin/`）。

## 目录内容

- `handoff-stamp.sh` — PostToolUse hook。Edit/Write 命中 `*交接*` / `*实施计划*` / `TEAM.md` / `HANDOFF.md`（含 `~/.qoder/handoffs/`、`.handoff/` 下的路径）时，把文档绝对路径写入 `~/.qoder/tmp/handoff_updated_<session_id>`，作为"本会话改过"的标记；`archive/`、`.backup/` 下的写入不计数。触发过一次 Stop 检查后，就不再重新启用检查，以防循环。
  - 2026-10-31 修正：旧版只认中文文件名，而 skill 默认产出的是 `HANDOFF.md`。两套命名对不上，导致标记一直打不上，Stop 检查也会静默放行。现已补上 `HANDOFF.md` / `handoff.md` 与 handoffs 路径线索。
- `handoff-stop-check.sh` — Stop hook，在主agent回复结束时提醒一次，不等于会话退出，也不等于自动验收：
  - **①** 小节：提醒核对本轮记录，hook本身不验证记录内容。
  - **②** 归档（活跃预算 = 当前态块 + §0 超过阈值）：先检查角色/授权与任务是否形成闭环。archive默认只预览，获准后才用 --apply 原样搬移；摘要不能代替实际移走主文档中的内容。
  - **③** 读模型（STATE.json 缺失或早于文档改动）：新版用 refresh 从当前态派生读模型，再用 validate/context 校验来源hash与内容；旧版仍按人工流程处理，不擅自迁移。
  - 阈值 `HANDOFF_LIVE_LIMIT`（默认 20480，兼容旧名 `HANDOFF_SIZE_LIMIT`）判活跃预算；`HANDOFF_WHOLE_LIMIT`（默认 49152）只对整文件 WARN，不改退出码。hook 调 `handoff.py size` 取数；脚本不可用或目录受角色隔离时回退 `wc -c` 按整文件判，旧文档无当前态块时同样按整文件判。退出码 2 = 阻断，标"确认无需"可跳过（一次性）

## 部署与升级

**独立授权门槛**：以下命令会写入全局运行时目录，可能影响后续所有会话。执行前，要先说明目标路径、会如何覆盖/备份，以及会做哪些检查；只有用户明确批准全局 hooks 安装/升级，才可执行。用户允许创建交接文件、编辑 AGENTS.md/.gitignore 或修改本目录源码，都不等于批准安装。反过来，获得安装授权，也不能自动创建项目交接文件或修改 AGENTS.md/.gitignore；这些操作必须分别检查是否已获授权。权限/配置变更仍按系统/开发者要求处理，不得绕过限制。

```
# 仅在用户明确授权全局部署后：复制到 ~/.qoder/hooks/（旧版备份、sha256 校验）
python scripts/handoff.py install-hooks

# 部署到别处（如自定义路径）
python scripts/handoff.py install-hooks --target "$HOME/other/hooks"
```

修改流程：在用户授权范围内修改本目录源码；只有另行获准全局升级，才运行 install-hooks。未获准时，只保留源码改动，并报告“未部署”。`~/.qoder/hooks/` 里实际加载的副本不会随本目录自动更新，部署前先备份，避免两份文案再次漂移。不要直接编辑 `~/.qoder/hooks/` 中的文件，也不要因为 hook 的提示，就自动扩大对持久文件/配置的编辑权限。

## 其他宿主 / 部署目标

`~/.qoder/hooks/` 是默认运行时位置。其他宿主必须先验证事件/输入/输出协议；`install-hooks --target` 只复制文件，不负责注册，也不保证兼容。本目录仍只有原有的打标与Stop提醒源码，没有部署压缩恢复或聊天采集hook；Qoder可选接入的范围与限制见 `references/state-schema.md`。
