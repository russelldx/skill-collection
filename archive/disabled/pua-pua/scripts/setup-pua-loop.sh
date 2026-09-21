#!/bin/bash

# PUA Loop Setup Script
# Creates state file for in-session PUA Loop
# Gate protocol inspired by Karpathy's autoresearch
#
# Adapted from Ralph Wiggum by Anthropic (MIT License)
# https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

set -euo pipefail

# Parse arguments
PROMPT_PARTS=()
MAX_ITERATIONS=10
COMPLETION_PROMISE="null"
VERIFY_COMMAND="null"

# Parse options and positional arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      cat << 'HELP_EOF'
PUA Loop - Autonomous iterative development loop with gate protocol

USAGE:
  /pua-loop [PROMPT...] [OPTIONS]

ARGUMENTS:
  PROMPT...    Initial prompt to start the loop (can be multiple words without quotes)

OPTIONS:
  --verify '<command>'             Verification command — hook runs it as Oracle gate
                                   after <promise>. If it fails, promise is REJECTED.
                                   (Inspired by autoresearch's Oracle Isolation)
  --max-iterations <n>             Maximum iterations (default: 10; range: 1–100)
  --completion-promise '<text>'    Promise phrase (USE QUOTES for multi-word)
  -h, --help                       Show this help message

GATE PROTOCOL (inspired by autoresearch):
  Phase 1 (in-prompt): Claude runs tests, decides to output <promise>
  Phase 2 (in-hook):   Hook independently runs --verify command
  If Phase 2 fails → promise REJECTED → loop continues within the iteration cap
  The verifier is stored in editable state, not an immutable security boundary.
  Never change approved verification criteria to manufacture a passing result.

  To signal completion: <promise>YOUR_PHRASE</promise>
  To terminate:         <loop-abort>reason</loop-abort>
  To pause:             <loop-pause>what is needed</loop-pause>

EXAMPLES:
  /pua-loop Fix all tests --verify 'npm test' --completion-promise 'ALL TESTS PASS'
  /pua-loop Build a REST API --verify 'curl -sf http://localhost:3000/health'
  /pua-loop Optimize bundle --verify 'node -e "s=require(\"fs\").statSync(\"dist/main.js\").size; process.exit(s>500000?1:0)"'
  /pua-loop Refactor cache layer --verify 'npm test' --max-iterations 10

STOPPING:
  Default: stop at 10 iterations; --max-iterations accepts 1–100, never unlimited.
  A verified promise, <loop-abort>, <loop-pause>, or Ctrl+C can stop earlier.
  Missing verification never counts as completion; the hook rejects and pauses.
  This archived script is reference-only; do not register hooks or start a real loop.

MONITORING:
  ls ~/.claude/pua/loop-*.md                 # State (per-project)
  cat .claude/pua-loop-history.jsonl         # Iteration history
HELP_EOF
      exit 0
      ;;
    --max-iterations)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --max-iterations requires a number argument" >&2
        exit 1
      fi
      if ! [[ "$2" =~ ^[1-9][0-9]{0,2}$ ]] || (( 10#$2 > 100 )); then
        echo "Error: --max-iterations must be an integer from 1 to 100, got: $2" >&2
        exit 1
      fi
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --completion-promise)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --completion-promise requires a text argument" >&2
        echo "   Note: Multi-word promises must be quoted!" >&2
        exit 1
      fi
      COMPLETION_PROMISE="$2"
      shift 2
      ;;
    --verify)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --verify requires a command argument" >&2
        echo "" >&2
        echo "   Examples:" >&2
        echo "     --verify 'npm test'" >&2
        echo "     --verify 'cargo build && cargo test'" >&2
        echo "     --verify 'curl -sf http://localhost:3000/health'" >&2
        exit 1
      fi
      VERIFY_COMMAND="$2"
      shift 2
      ;;
    *)
      PROMPT_PARTS+=("$1")
      shift
      ;;
  esac
done

PROMPT="${PROMPT_PARTS[*]}"

if [[ -z "$PROMPT" ]]; then
  echo "❌ Error: No prompt provided" >&2
  echo "   Examples:" >&2
  echo "     /pua-loop Fix all tests --verify 'npm test'" >&2
  echo "     /pua-loop Build a REST API --verify 'npm test' --completion-promise 'DONE'" >&2
  exit 1
fi

# This archived script is for inspection and isolated tests only, not activation.
# Refuse unverified new state; the hook separately rejects legacy missing-verifier promises.
if [[ -z "${VERIFY_COMMAND//[[:space:]]/}" ]] || [[ "$VERIFY_COMMAND" == "null" ]]; then
  echo "Error: --verify is required; missing verification cannot establish completion." >&2
  exit 1
fi

# Create state file
# v3.2: 用 cwd 哈希命名状态文件，解决多目录 loop 实例互相覆盖的 bug
# 每个项目目录有独立的 loop-<hash>.md，不再共享单一 loop-active.md
PUA_HOME_DIR="${HOME}/.claude/pua"
mkdir -p "$PUA_HOME_DIR"
mkdir -p .claude

CWD_HASH=$(printf '%s' "$(pwd)" | md5sum 2>/dev/null | cut -c1-8 || printf '%s' "$(pwd)" | md5 2>/dev/null | cut -c1-8 || echo "default")
ABS_STATE="${PUA_HOME_DIR}/loop-${CWD_HASH}.md"
LEGACY_STATE=".claude/pua-loop.local.md"

# YAML quoting
if [[ -n "$COMPLETION_PROMISE" ]] && [[ "$COMPLETION_PROMISE" != "null" ]]; then
  COMPLETION_PROMISE_YAML="\"$COMPLETION_PROMISE\""
else
  COMPLETION_PROMISE_YAML="null"
fi

if [[ -n "$VERIFY_COMMAND" ]] && [[ "$VERIFY_COMMAND" != "null" ]]; then
  VERIFY_COMMAND_YAML="\"$VERIFY_COMMAND\""
else
  VERIFY_COMMAND_YAML="null"
fi

# Build completion instruction
if [[ -n "$COMPLETION_PROMISE" ]] && [[ "$COMPLETION_PROMISE" != "null" ]]; then
  PROTOCOL_COMPLETION="6. 只有当任务完全完成且验证通过时，输出 <promise>${COMPLETION_PROMISE//\"/}</promise>"
else
  PROTOCOL_COMPLETION="6. 此 loop 无完成信号，最多运行 $MAX_ITERATIONS 轮；用 <loop-abort> 终止、<loop-pause> 暂停或 Ctrl+C 停止，不将达到轮数上限视为完成"
fi

# Build verify gate instruction
if [[ -n "$VERIFY_COMMAND" ]] && [[ "$VERIFY_COMMAND" != "null" ]]; then
  VERIFY_PROTOCOL="== 验证门控（Oracle Isolation，借鉴 autoresearch）==
- 你输出 <promise> 后，hook 会独立运行: ${VERIFY_COMMAND//\"/}
- 如果验证命令退出码 ≠ 0 → 你的 promise 被拒绝 → 在轮数上限内继续
- 验证命令保存在可编辑状态中，不是不可绕过的安全边界；禁止修改获准标准来制造通过
- 先自己跑一遍验证命令确认通过，再输出 <promise>"
else
  VERIFY_PROTOCOL="== 验证门控 ==
- 未设置 --verify 命令，完成声明会被拒绝并暂停
- 需要用户审定验证命令；不以自我声明代替验证"
fi

cat > "$ABS_STATE" <<EOF
---
active: true
iteration: 1
session_id: ${CLAUDE_CODE_SESSION_ID:-}
max_iterations: $MAX_ITERATIONS
completion_promise: $COMPLETION_PROMISE_YAML
verify_command: $VERIFY_COMMAND_YAML
promise_rejections: 0
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
started_cwd: "$(pwd)"
---

$PROMPT

== PUA 行为协议（每次迭代必须遵守）==
1. 读取项目文件和 git log，了解上次做了什么（Git 是你的跨迭代记忆）
2. 如果存在 .claude/pua-loop-history.jsonl，先读取了解之前的迭代结果，避免重复失败的方案
3. 按三条红线执行：闭环验证、事实驱动、穷尽一切方案
4. 跑 build/test 验证改动，不要跳过
5. 发现问题就修，修完再验证（不声称完成，先验证）
$PROTOCOL_COMPLETION
$VERIFY_PROTOCOL
== 防原地打转协议（借鉴 autoresearch Stall Detection）==
- 每轮开始先检查 git log + git diff：如果发现自己在重复上轮的改动，必须切换到完全不同的方案
- 连续 3 轮改同一个文件的同一区域 → 退一步重新分析根因，不要继续修补
- 如果 build/test 持续失败，先读完整的错误输出，搜索相关源码和文档，列出 3 个不同假设再行动
- promise 被拒绝 → 读 hook 返回的验证输出，修复后再尝试
禁止：
- 不要超出用户授权范围、绕过权限或修改验证标准来获得通过
- 遇到缺失权限、关键歧义或用户停止要求，立即暂停并报告
- 不要在未验证的情况下声称完成
- 不要把自主迭代当成提交、推送、删除或注册 hooks 的授权
- 不要连续 3 轮用同一种方法——如果不行就换
EOF

# 向后兼容：同步写 legacy 相对路径（老监控工具 / 已部署的 reap-orphans 兜底）
cp "$ABS_STATE" "$LEGACY_STATE"

# Initialize history log（保留相对路径，hook 写入也用它；后续可迁移到绝对路径）
echo "{\"iteration\":0,\"status\":\"init\",\"verify_command\":$(if [[ "$VERIFY_COMMAND" != "null" ]]; then echo "\"${VERIFY_COMMAND//\"/}\""; else echo "null"; fi),\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > .claude/pua-loop-history.jsonl
echo "{\"iteration\":0,\"status\":\"init\",\"verify_command\":$(if [[ "$VERIFY_COMMAND" != "null" ]]; then echo "\"${VERIFY_COMMAND//\"/}\""; else echo "null"; fi),\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"state_path\":\"$ABS_STATE\"}" >> "${PUA_HOME_DIR}/loop-history.jsonl"

# Output setup message
cat <<EOF
🔄 PUA Loop activated (with autoresearch-style gate protocol)

Iteration: 1
Max iterations: $MAX_ITERATIONS
Completion promise: $(if [[ "$COMPLETION_PROMISE" != "null" ]]; then echo "\"${COMPLETION_PROMISE//\"/}\""; else echo "none"; fi)
Verify command: $(if [[ "$VERIFY_COMMAND" != "null" ]]; then echo "\"${VERIFY_COMMAND//\"/}\" (Oracle gate — hook runs independently)"; else echo "none (completion rejected)"; fi)

Gate protocol:
  Phase 1: Claude runs tests → decides to output <promise>
  Phase 2: Hook runs --verify command → confirms or REJECTS
  $(if [[ "$VERIFY_COMMAND" != "null" ]]; then echo "Verifier configured; its passing result is required for completion"; else echo "No verifier: completion is rejected and paused for user review"; fi)

To monitor: cat .claude/pua-loop-history.jsonl
To cancel:  /cancel-pua-loop or Ctrl+C

🔄
EOF

echo ""
echo "$PROMPT"

# Display completion promise requirements if set
if [[ "$COMPLETION_PROMISE" != "null" ]]; then
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "CRITICAL - Completion Gate"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  echo "To complete this loop, output: <promise>${COMPLETION_PROMISE//\"/}</promise>"
  echo ""
  if [[ "$VERIFY_COMMAND" != "null" ]]; then
    echo "⚡ ORACLE GATE ACTIVE:"
    echo "  After you output <promise>, the hook will run:"
    echo "    ${VERIFY_COMMAND//\"/}"
    echo "  If exit code is nonzero, the promise is rejected; continuation stays within the cap."
    echo "  Editable verifier state is not a security boundary; preserve approved criteria."
  else
    echo "  No verifier: completion is rejected and the loop pauses for user review."
    echo "  Self-reported completion cannot substitute for verification."
  fi
  echo ""
  echo "═══════════════════════════════════════════════════════════"
fi
