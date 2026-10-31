#!/bin/bash
# session-handoff hook 1/3：Edit/Write 命中交接文档时打标记
# stdin: hook JSON；标记文件：~/.qoder/tmp/handoff_updated_<session_id>
INPUT=$(cat)
# 廉价前置过滤：命中任一命名线索才继续解析。含 skill 默认产出的 HANDOFF.md，
# 以及 ~/.qoder/handoffs 的路径形态（旧版只认中文名，导致 HANDOFF.md 永远打不上标记）。
printf '%s' "$INPUT" | grep -qE '交接|实施计划|TEAM\.md|HANDOFF\.md|handoff\.md|\.handoff/|handoffs' || exit 0

PARSED=$(printf '%s' "$INPUT" | node -e 'process.stdin.setEncoding("utf8");let d="";process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>{try{const j=JSON.parse(d);console.log((j.session_id||"")+"|"+((j.tool_input&&j.tool_input.file_path)||""))}catch(e){}})')
SID=${PARSED%%|*}
FILE=${PARSED#*|}
[ -z "$SID" ] && exit 0

# hook JSON 可能给 Windows 反斜杠路径：归一化后再做匹配与尺寸测量
FILE=${FILE//$'\x5c'/'/'}

# Stop 检查已触发过则不再重新武装（防循环）
[ -f "$HOME/.qoder/tmp/handoff_gate_$SID" ] && exit 0

BASE=$(basename "$FILE")
case "$BASE" in
  *交接*|*实施计划*|TEAM.md|HANDOFF.md|handoff.md)
    # archive/ 与 .backup/ 下是只读历史，允许无限增长，不参与尺寸统计
    case "$FILE" in
      */archive/*|*/.backup/*) exit 0 ;;
    esac
    mkdir -p "$HOME/.qoder/tmp" 2>/dev/null
    MARK="$HOME/.qoder/tmp/handoff_updated_$SID"
    touch "$MARK"
    [ -n "$FILE" ] && [ "$FILE" != "$PARSED" ] && \
      { grep -qxF "$FILE" "$MARK" 2>/dev/null || printf '%s\n' "$FILE" >>"$MARK"; }
    ;;
esac
exit 0
