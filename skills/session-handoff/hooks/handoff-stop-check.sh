#!/bin/bash
# session-handoff hook 2/3：Stop 时一次性拦截检查
#   检查①：本会话改过交接文档 → 是否已追加本次会话小节
#   检查②：本会话改过的活跃交接文档字节数是否超归档阈值（防文档无限膨胀）
#   检查③：追加小节后旁侧 STATE.json 是否更新；内容/来源校验交 validate/context
# 标记文件内容 = 本会话命中的文档绝对路径（正斜杠，一行一个），由 handoff-stamp.sh 写入
# 一次性：触发后消费标记并落 gate，不再重复拦截
LIMIT=${HANDOFF_SIZE_LIMIT:-20480}
INPUT=$(cat)
ls "$HOME/.qoder/tmp/handoff_updated_"* >/dev/null 2>&1 || exit 0

SID=$(printf '%s' "$INPUT" | node -e 'let d="";process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>{try{console.log(JSON.parse(d).session_id||"")}catch(e){}})')
[ -z "$SID" ] && exit 0
MARK="$HOME/.qoder/tmp/handoff_updated_$SID"
[ -f "$MARK" ] || exit 0

# 定位 handoff.py：hook 从 ~/.qoder/hooks 加载，脚本可能落在 .qoder 技能树或相对 $0 的技能树
HANDOFF_PY=""
for _c in \
  "$HOME/.qoder/skills/session-handoff/scripts/handoff.py" \
  "$(cd "$(dirname "$0")/.." && pwd)/skills/session-handoff/scripts/handoff.py"; do
  [ -f "$_c" ] && { HANDOFF_PY="$_c"; break; }
done
if [ -n "$HANDOFF_PY" ]; then HPY="python \"$HANDOFF_PY\""; else HPY="python scripts/handoff.py"; fi

# 必须在消费标记之前测量
OVER=""
STATE_BAD=""
OVER_DIRS=""
STATE_BAD_DIRS=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in */archive/*) continue ;; esac
  [ -f "$f" ] || continue
  SZ=$(wc -c <"$f" 2>/dev/null)
  [ -n "$SZ" ] || continue
  if [ "$SZ" -gt "$LIMIT" ]; then
    OVER="$OVER
  - ${f}  →  $((SZ / 1024)) KB（阈值 $((LIMIT / 1024)) KB）"
    OVER_DIRS="$OVER_DIRS$(dirname "$f")
"
  fi
  # STATE.json 读模型：与文档同目录；缺失或比文档旧（文档改了没同步刷新）都要提醒
  DIR=$(dirname "$f")
  SJ="$DIR/STATE.json"
  if [ ! -f "$SJ" ]; then
    STATE_BAD="$STATE_BAD
  - ${f}  →  缺 STATE.json（同目录无读模型）"
    STATE_BAD_DIRS="$STATE_BAD_DIRS$DIR
"
  elif [ "$SJ" -ot "$f" ]; then
    STATE_BAD="$STATE_BAD
  - ${f}  →  STATE.json 早于文档改动（未同步刷新）"
    STATE_BAD_DIRS="$STATE_BAD_DIRS$DIR
"
  fi
done <"$MARK"

rm -f "$MARK"
touch "$HOME/.qoder/tmp/handoff_gate_$SID"

{
  echo "[会话交接检查] 本会话修改过交接文档（或 TEAM.md），结束前请完成以下适用项："
  echo
  echo "① 小节：交接文档是否已追加本次会话小节（完成内容/验证证据/新坑/环境变更/遗留待办）？"
  echo "   刚改过文档但没写小节 → 现在补上。"
  if [ -n "$OVER" ]; then
    echo
    echo "② 折叠/归档（强制，非建议）：以下活跃交接文档已超阈值 —— $OVER"
    echo "   先检查授权与角色隔离，再跑 index；20KB 是主文档整文件字节，不是 token 数。"
    echo "   新版文档核验任务 done/verified/archiveReady/evidence/openItems 后，用 archive <目录> <任务ID> 只读预览。"
    echo "   已获移动授权才加 --apply：备份、校验、原样搬 archive/<任务ID>.md，保留节号与指针，再 validate/index。"
    echo "   只加摘要却保留正文不会降低体积；没有可归档任务或用户正在编辑时，报告并停止，不删未决或限制。"
    echo "   旧文档按人工归档协议处理；不自动迁移、不改 AGENTS.md/.gitignore，不因本提示扩大授权。"
    echo "   逐目录命令："
    printf '%s' "$OVER_DIRS" | sort -u | while IFS= read -r d; do
      [ -z "$d" ] && continue
      echo "     $HPY index \"$d\""
    done
  fi
  if [ -n "$STATE_BAD" ]; then
    echo
    echo "③ 读模型 STATE.json（强制同步）：以下文档的旁侧 STATE.json 缺失或早于文档改动 —— $STATE_BAD"
    echo "   处理：新版先核对当前态与事件，再在授权范围运行 refresh 派生 STATE.json/§0；不得手写第二份账。"
    echo "   validate/context 校验来源hash和内容；此hook只作时间/体积提醒。旧版与角色隔离细则见 references/state-schema.md。"
    echo "   逐目录校验："
    printf '%s' "$STATE_BAD_DIRS" | sort -u | while IFS= read -r d; do
      [ -z "$d" ] && continue
      echo "     $HPY validate \"$d\""
    done
    echo "   找回旧结论：$HPY search \"<交接目录>\" \"<关键词>\"（离线 BM25，覆盖活跃区+archive）。"
    echo "   跨所有交接会话总览：$HPY status"
  fi
  echo
  echo "   与用户确认本次无需交接/无需归档，可直接跳过。本检查为一次性，不会再触发。"
} >&2
exit 2
