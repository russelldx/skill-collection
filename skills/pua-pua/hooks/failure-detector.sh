#!/bin/bash
# PUA PostToolUse hook: failure pattern analysis + de-escalation breakthrough detection
# Layer 1 of 3-layer detection: collect structured signals, inject pattern data for LLM analysis
#
# v2: Upgraded from simple counter to pattern-aware state machine
#   - Tracks error signatures (hash of last N errors) for pattern classification
#   - Detects SUCCESS after L2+ struggle → triggers de-escalation with flavor-aware recognition
#   - Injects error history into prompt so LLM can do semantic pattern analysis
#   - Flavor-specific breakthrough recognition messages

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/flavor-helper.sh"
PUA_PY="$(pua_python_cmd 2>/dev/null || true)"

# Respect /pua:off — skip injection when always_on is false
PUA_CONFIG="$(pua_config_file)"
if [ -f "$PUA_CONFIG" ]; then
  ALWAYS_ON=$(pua_json_get "$PUA_CONFIG" always_on True)
  if [ "$ALWAYS_ON" = "False" ]; then
    exit 0
  fi
fi

get_flavor

PUA_DIR="${HOME:-~}/.pua"
COUNTER_FILE="${PUA_DIR}/.failure_count"
SESSION_FILE="${PUA_DIR}/.failure_session"
# v2: error history for pattern analysis
ERROR_HISTORY_FILE="${PUA_DIR}/.error_history.jsonl"
PEAK_LEVEL_FILE="${PUA_DIR}/.peak_pressure_level"
mkdir -p "${PUA_DIR}"

# Read hook input
HOOK_INPUT=$(cat)

# Only process Bash tool results
TOOL_NAME=$(echo "$HOOK_INPUT" | "${PUA_PY:-python3}" -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
if [ "$TOOL_NAME" != "Bash" ]; then
  exit 0
fi

# Extract tool result and exit code
TOOL_RESULT=$(echo "$HOOK_INPUT" | "${PUA_PY:-python3}" -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('tool_result', '')
if isinstance(result, dict):
    result = result.get('content', result.get('text', str(result)))
print(str(result)[:2000])
" 2>/dev/null || echo "")

EXIT_CODE=$(echo "$HOOK_INPUT" | "${PUA_PY:-python3}" -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('tool_result', {})
if isinstance(result, dict):
    print(result.get('exit_code', result.get('exitCode', 0)))
else:
    print(0)
" 2>/dev/null || echo "0")

IS_ERROR="false"

# Exit code is the PRIMARY signal — it's deterministic and reliable.
# Text grep is SECONDARY and only applies when exit_code is non-zero.
# This prevents false positives like "0 failed" or "no error" being flagged.
if [ "$EXIT_CODE" != "0" ] && [ "$EXIT_CODE" != "" ]; then
  IS_ERROR="true"
elif echo "$TOOL_RESULT" | grep -qiE '^error:|^fatal:|^panic:|Traceback \(most recent|Exception:|command not found|No such file or directory|Permission denied'; then
  # Only check text patterns when exit_code is 0 but output contains unambiguous error markers
  # These patterns are anchored (^) or specific enough to avoid false positives
  IS_ERROR="true"
fi

# Track session: reset counter if new session
CURRENT_SESSION=$(echo "$HOOK_INPUT" | "${PUA_PY:-python3}" -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")
STORED_SESSION=""
[ -f "$SESSION_FILE" ] && STORED_SESSION=$(cat "$SESSION_FILE" 2>/dev/null || echo "")

if [ "$CURRENT_SESSION" != "$STORED_SESSION" ]; then
  echo "0" > "$COUNTER_FILE"
  echo "0" > "$PEAK_LEVEL_FILE"
  : > "$ERROR_HISTORY_FILE"
  echo "$CURRENT_SESSION" > "$SESSION_FILE"
fi

# Read current count
COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")
[ -z "$COUNT" ] && COUNT=0

# Read peak pressure level reached this session
PEAK_LEVEL=0
[ -f "$PEAK_LEVEL_FILE" ] && PEAK_LEVEL=$(cat "$PEAK_LEVEL_FILE" 2>/dev/null || echo "0")
[ -z "$PEAK_LEVEL" ] && PEAK_LEVEL=0

# ═══════════════════════════════════════════════════════
# v2: DE-ESCALATION — Success after L2+ struggle
# ═══════════════════════════════════════════════════════
if [ "$IS_ERROR" = "false" ]; then
  if [ "$COUNT" -ge 3 ] && [ "$PEAK_LEVEL" -ge 2 ]; then
    # ★ BREAKTHROUGH detected: success after sustained struggle
    # Record the breakthrough event
    echo "{\"ts\":$(date +%s),\"event\":\"breakthrough\",\"from_level\":$PEAK_LEVEL,\"after_failures\":$COUNT}" >> "$ERROR_HISTORY_FILE" 2>/dev/null || true

    # Reset pressure state
    echo "0" > "$COUNTER_FILE"
    echo "0" > "$PEAK_LEVEL_FILE"

    # Flavor-aware de-escalation recognition
    case "$PUA_FLAVOR" in
      alibaba)
        DE_ESCALATION_MSG="这才是 Owner 该有的样子。3.75 打底。现在复盘一下：刚才卡了 ${COUNT} 次，根因是什么？把正确路径写下来，下次直达。这叫**沉淀方法论**。"
        ;;
      bytedance)
        DE_ESCALATION_MSG="结果到位了。ROI 翻正。现在做一件事：把刚才有效的方法提炼成 SOP，写到 memory 里。数据驱动不是说说——你刚经历的 ${COUNT} 次失败就是数据，别浪费。"
        ;;
      huawei)
        DE_ESCALATION_MSG="军令状完成。烧不死的鸟是凤凰——你刚证明了自己烧不死。现在按自我批判流程复盘：哪个假设一开始就是错的？哪个应该更早排除？写入经验库。胜则举杯相庆。"
        ;;
      tencent)
        DE_ESCALATION_MSG="赛马跑出来了。你赢了这条赛道。现在做灰度验证——确认结果可复现、边界清楚。然后把这套打法沉淀下来，下次小步快跑直接跑通。"
        ;;
      baidu)
        DE_ESCALATION_MSG="搜索 + 深挖有效果了。基本盘守住了。现在把搜索路径和关键发现记录下来——简单可依赖的前提是路径可复用。"
        ;;
      pinduoduo)
        DE_ESCALATION_MSG="本分做到了。结果出来了就是硬核。现在回头看：${COUNT} 次失败里有多少步是可以砍掉的？极致效率 = 下次零弯路。"
        ;;
      meituan)
        DE_ESCALATION_MSG="做难而正确的事，你做到了。猛将发于卒伍——这次卡住就是你的卒伍。现在苦练基本功：把解题路径标准化，下次遇到同类直接套。"
        ;;
      jd)
        DE_ESCALATION_MSG="结果拿到了。这才是兄弟该有的执行力。正道成功——过程虽然硬，但路子是对的。现在沉淀下来，让下一个兄弟不用再走这些弯路。"
        ;;
      xiaomi)
        DE_ESCALATION_MSG="极致！这次交付够极致。和用户交朋友的前提是你真的在意质量。现在把这个方案的性价比拉满——记录最短路径，下次专注直达。"
        ;;
      netflix)
        DE_ESCALATION_MSG="Keeper Test: passed. You fought through ${COUNT} failures — that's what stunning colleagues do. Now document what worked and WHY the earlier approaches failed. That's the learning loop that separates adequate from exceptional."
        ;;
      musk)
        DE_ESCALATION_MSG="Good. Shipped. Now apply The Algorithm retrospectively: which of those ${COUNT} failed attempts should never have existed? What requirement should you have questioned from the start? Delete the waste from your mental model."
        ;;
      jobs)
        DE_ESCALATION_MSG="That's A-player work. Real artists ship — and you just shipped through ${COUNT} failures. Now apply subtraction: what's the MINIMUM path to this solution? Strip away everything you tried that was unnecessary. Elegance = the shortest path."
        ;;
      amazon)
        DE_ESCALATION_MSG="Delivered Results. That's LP #1 in action. Now Working Backwards from this success: write a mini post-mortem. Which LP did you violate early on? Dive Deep into why. Earn Trust by documenting the path for others."
        ;;
      microsoft)
        DE_ESCALATION_MSG="Impact Descriptor update: trajectory moved from SLITE back to Successful Impact. ${COUNT} failures → changed action → verified result — that's a complete learning loop. Document this in your Connects: individual impact + leveraged existing work evidence."
        ;;
      *)
        DE_ESCALATION_MSG="突破了。${COUNT} 次失败后找到正确方案——这才是真正的 problem solving。现在复盘：为什么之前卡住？正确路径是什么？写入 memory，下次直达。"
        ;;
    esac

    cat << EOF
[PUA 突破 ✨ — De-escalation from L${PEAK_LEVEL}]

> ${DE_ESCALATION_MSG}

Pressure reset: L${PEAK_LEVEL} → L0. You MUST now:
1. Briefly identify WHY previous ${COUNT} attempts failed (root cause, not symptoms)
2. Record the CORRECT approach in memory/evolution.md for future reuse
3. Verify the solution is complete (don't celebrate prematurely)

[PUA生效 🔥] Breakthrough after ${COUNT} consecutive failures. Method that worked should be internalized.
EOF
    exit 0
  fi

  # Normal success: just reset counter, no fanfare
  if [ "$COUNT" -gt 0 ]; then
    echo "0" > "$COUNTER_FILE"
    # Don't reset peak_level — it tracks the session's highest struggle point
  fi
  exit 0
fi

# ═══════════════════════════════════════════════════════
# FAILURE PATH: increment counter + record error signature
# ═══════════════════════════════════════════════════════
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# v2: Record error signature for pattern analysis
# Extract a short error signature (first error line, max 200 chars)
# Extract error signature: first line containing error-like pattern, or first non-empty line, or exit code
ERROR_SIG=$(echo "$TOOL_RESULT" | grep -iE 'error|fatal|Traceback|Exception|FAILED|panic|refused|denied|not found|cannot|unable|timeout' | head -1 | cut -c1-200)
[ -z "$ERROR_SIG" ] && ERROR_SIG=$(echo "$TOOL_RESULT" | head -1 | cut -c1-200)
[ -z "$ERROR_SIG" ] && ERROR_SIG="exit_code_${EXIT_CODE}"

# Append to error history (keep last 10 entries)
echo "{\"ts\":$(date +%s),\"count\":$COUNT,\"sig\":\"$(echo "$ERROR_SIG" | sed 's/"/\\"/g' | tr '\n' ' ')\"}" >> "$ERROR_HISTORY_FILE" 2>/dev/null || true
tail -10 "$ERROR_HISTORY_FILE" > "${ERROR_HISTORY_FILE}.tmp" 2>/dev/null && mv "${ERROR_HISTORY_FILE}.tmp" "$ERROR_HISTORY_FILE" 2>/dev/null || true

# v2: Analyze error pattern (structural, not semantic)
# Compare last 3 error signatures to detect repetition
PATTERN_ANALYSIS=""
if [ "$COUNT" -ge 3 ]; then
  PATTERN_ANALYSIS=$(${PUA_PY:-python3} -c "
import json, hashlib, sys

history_file = sys.argv[1]
try:
    with open(history_file) as f:
        entries = [json.loads(line.strip()) for line in f if line.strip()]
except:
    entries = []

if len(entries) < 3:
    print('insufficient_data')
    sys.exit(0)

recent = entries[-3:]
sigs = [e.get('sig', '') for e in recent]
hashes = [hashlib.md5(s.encode()).hexdigest()[:8] for s in sigs]

# Pattern A: all same hash → spinning (same error repeated)
if len(set(hashes)) == 1:
    print('SPINNING|' + sigs[-1][:100])
# Pattern B: all different → exploring (different errors each time)
elif len(set(hashes)) == len(hashes):
    print('EXPLORING|' + '|'.join(s[:60] for s in sigs))
# Pattern C: mixed (some same, some different)
else:
    print('MIXED|' + '|'.join(s[:60] for s in sigs))
" "$ERROR_HISTORY_FILE" 2>/dev/null || echo "")
fi

# Track peak pressure level
CURRENT_LEVEL=0
if [ "$COUNT" -ge 5 ]; then
  CURRENT_LEVEL=4
elif [ "$COUNT" -eq 4 ]; then
  CURRENT_LEVEL=3
elif [ "$COUNT" -eq 3 ]; then
  CURRENT_LEVEL=2
elif [ "$COUNT" -eq 2 ]; then
  CURRENT_LEVEL=1
fi

if [ "$CURRENT_LEVEL" -gt "$PEAK_LEVEL" ]; then
  echo "$CURRENT_LEVEL" > "$PEAK_LEVEL_FILE"
fi

# ═══════════════════════════════════════════════════════
# PRESSURE ESCALATION (enhanced with pattern context)
# ═══════════════════════════════════════════════════════
if [ "$COUNT" -lt 2 ]; then
  # First failure: no intervention yet
  exit 0
fi

# Extract pattern type for injection
PATTERN_TYPE=$(echo "$PATTERN_ANALYSIS" | cut -d'|' -f1)
PATTERN_DETAIL=$(echo "$PATTERN_ANALYSIS" | cut -d'|' -f2-)

# Build pattern-aware injection block
PATTERN_BLOCK=""
if [ -n "$PATTERN_TYPE" ] && [ "$PATTERN_TYPE" != "insufficient_data" ]; then
  case "$PATTERN_TYPE" in
    SPINNING)
      PATTERN_BLOCK="
[🔄 Pattern: SPINNING — same error repeating]
> The last 3 errors have the SAME signature: \`${PATTERN_DETAIL}\`
> You are NOT making progress. STOP retrying the same approach.
> MANDATORY: List 3 fundamentally different strategies before your next Bash call.
> If you've been trying variations of the same fix, that counts as ONE strategy — you need 2 more that are COMPLETELY different."
      ;;
    EXPLORING)
      PATTERN_BLOCK="
[📊 Pattern: EXPLORING — different errors each time]
> Each of your last 3 attempts produced a DIFFERENT error. This means you ARE making progress — you're narrowing the problem space.
> Recent error signatures:
$(echo "$PATTERN_DETAIL" | tr '|' '\n' | sed 's/^/> · /')
> Continue exploring, but add structure: what does each new error tell you about the root cause?"
      ;;
    MIXED)
      PATTERN_BLOCK="
[📊 Pattern: MIXED — partially repeating errors]
> Some errors are repeating, others are new. Check: are you oscillating between two broken approaches?
> Recent signatures:
$(echo "$PATTERN_DETAIL" | tr '|' '\n' | sed 's/^/> · /')
> Pick the approach that showed the MOST DIFFERENT error (closest to working) and commit to it."
      ;;
  esac
fi

if [ "$COUNT" -eq 2 ]; then
  cat << EOF
[PUA L1 ${PUA_ICON} — Consecutive Failure Detected]

> ${PUA_L1}
${PATTERN_BLOCK}

You MUST switch to a FUNDAMENTALLY different approach. Not parameter tweaking — a different strategy.
If you haven't loaded the full PUA methodology, invoke Skill tool with 'pua'.
Current flavor: ${PUA_FLAVOR} ${PUA_ICON}. ${PUA_FLAVOR_INSTRUCTION}
Active methodology: ${PUA_METHODOLOGY}
EOF
elif [ "$COUNT" -eq 3 ]; then
  cat << EOF
[PUA L2 ${PUA_ICON} — Soul Interrogation]

> ${PUA_L2}
${PATTERN_BLOCK}

Mandatory steps:
1. Read the error message word by word
2. Search (WebSearch / Grep) for the core problem
3. Read the original context around the failure (50 lines up/down)
4. List 3 fundamentally different hypotheses
5. Reverse your main assumption

[方法论切换建议 🔄] Current methodology (${PUA_FLAVOR}) has failed to resolve this. Consider switching:
- If spinning in loops → switch to ⬛ Musk (The Algorithm: question the requirement itself, then delete)
- If giving up → switch to 🟤 Netflix (Keeper Test: this approach isn't worth keeping, replace it entirely)
- If not searching → switch to ⚫ Baidu (search everything first, then judge)
- If quality is poor → switch to ⬜ Jobs (subtraction + pixel-perfect)
Announce the switch: > [方法论切换 🔄] 从 ${PUA_ICON} ${PUA_FLAVOR} 切换到 [new flavor]: [reason]
Current flavor: ${PUA_FLAVOR} ${PUA_ICON}. ${PUA_FLAVOR_INSTRUCTION}
EOF
elif [ "$COUNT" -eq 4 ]; then
  cat << EOF
[PUA L3 ${PUA_ICON} — Performance Review]

> ${PUA_L3}
${PATTERN_BLOCK}

Complete the 7-point checklist:
- [ ] Read the failure signal word by word?
- [ ] Searched the core problem with tools?
- [ ] Read the original context around failure?
- [ ] All assumptions verified with tools?
- [ ] Tried the opposite assumption?
- [ ] Reproduced in minimal scope?
- [ ] Switched tools/methods/angles/stack?
Current flavor: ${PUA_FLAVOR} ${PUA_ICON}. ${PUA_FLAVOR_INSTRUCTION}
EOF
else
  cat << EOF
[PUA L4 ${PUA_ICON} — Graduation Warning + MANDATORY Methodology Switch]

> ${PUA_L4}
${PATTERN_BLOCK}

Current methodology (${PUA_FLAVOR}) has FAILED. You MUST switch to a different methodology NOW.
Switch priority based on failure pattern:
1. ⬛ Musk — Question: does this requirement even need to exist? Delete everything unnecessary first.
2. 🔴 Huawei — Blue Army: attack your own solution from the opposite direction. What if your core assumption is wrong?
3. 🔶 Amazon — Dive Deep: go to the lowest level of detail. Read source code line by line. Working Backwards from the desired output.
4. 🟣 Pinduoduo — Cut all middle layers: what's the shortest path from problem to solution?

If ALL methodologies exhausted → output structured failure report:
1. Verified facts
2. Excluded possibilities (with evidence for each exclusion)
3. Narrowed problem scope
4. Recommended next steps
5. Which methodologies were tried and why they failed
EOF
fi

exit 0
