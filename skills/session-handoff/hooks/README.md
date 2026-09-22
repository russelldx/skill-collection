# hooks/ — 会话交接的运行时钩子（本目录是源，`~/.qoder/hooks/` 是部署目标）

## 为什么要放这里

skill 的 hook 属于"语义上的一部分、运行时在别处"。以前只存在于 `~/.qoder/hooks/`，脱离 skill 版本管理——卸装 skill 不会带 hook、双副本 skill 只同步内容不同步 hook。现在把源放进 skill，运行时通过 `handoff.py install-hooks` 一键部署，形成清晰的 **source-of-truth ↔ installed** 关系（类比 npm `bin/` 与 `node_modules/.bin/`）。

## 目录内容

- `handoff-stamp.sh` — PostToolUse hook。Edit/Write 命中 `*交接*` / `*实施计划*` / `TEAM.md` 时，把文档绝对路径写入 `~/.qoder/tmp/handoff_updated_<session_id>` 作为"本会话改过"标记。已触发过一次 Stop 检查后不再重新武装（防循环）。
- `handoff-stop-check.sh` — Stop hook。会话结束一次性拦截：
  - **①** 小节：改过文档但没写本节 → 补上
  - **②** 折叠/归档（活跃区字节超阈才触发）：先跑 `handoff.py index` 看 INDEX.md 的 ⚠ 待折叠清单，据此折 §0；仍超阈才物理搬 archive/
  - **③** 读模型（STATE.json 缺失或早于文档改动才触发）：同轮刷新 STATE.json 使 status/openBlockers/nextActions/updatedAt 反映真相
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

`~/.qoder/hooks/` 是默认运行时位置。若其他宿主或环境也有等价 hook 加载目录，用 `install-hooks --target <新路径>` 部署即可，源不动。（历史：QoderWork 时代的 `~/.qoderwork/` 双副本已于 2026-09-15 随迁移删除，现 `.qoder` 为唯一权威。）
