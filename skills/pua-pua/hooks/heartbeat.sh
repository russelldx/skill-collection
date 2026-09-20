#!/bin/bash
# PUA silent heartbeat hook.
# Contract: best-effort, no stdout/stderr, no additionalContext, no user-visible prompt text.

exec >/dev/null 2>&1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/flavor-helper.sh" || exit 0

is_true() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    true|1|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

is_false() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    false|0|no|off) return 0 ;;
    *) return 1 ;;
  esac
}

CONFIG="$(pua_config_file)"
OFFLINE="False"
TELEMETRY="True"
FEEDBACK_FREQUENCY=""
FLAVOR="alibaba"

if [ -f "$CONFIG" ]; then
  OFFLINE="$(pua_json_get "$CONFIG" offline False)"
  TELEMETRY="$(pua_json_get "$CONFIG" telemetry True)"
  FEEDBACK_FREQUENCY="$(pua_json_get "$CONFIG" feedback_frequency "")"
  FLAVOR="$(pua_json_get "$CONFIG" flavor alibaba)"
fi

# Normalize Chinese/alias flavor names through the shared flavor map. This keeps
# Cloudflare stats segmented by canonical flavor ids (for example 微软 → microsoft).
get_flavor >/dev/null 2>&1 || true
FLAVOR="${PUA_FLAVOR:-$FLAVOR}"

# Privacy gates: offline/off/feedback_frequency=0 means no telemetry identity is created.
is_true "$OFFLINE" && exit 0
is_false "$TELEMETRY" && exit 0
case "$FEEDBACK_FREQUENCY" in
  0|never|off|false|False) exit 0 ;;
esac

command -v curl >/dev/null 2>&1 || exit 0

STATE_DIR="${PUA_STATE_DIR:-${HOME:-.}/.pua}"
INSTALL_ID_FILE="${PUA_HEARTBEAT_ID_FILE:-${STATE_DIR}/install_id}"
LAST_FILE="${PUA_HEARTBEAT_LAST_FILE:-${STATE_DIR}/.heartbeat_last}"
mkdir -p "$STATE_DIR" || exit 0

now="$(date +%s 2>/dev/null || printf '0')"
interval="${PUA_HEARTBEAT_INTERVAL_SECONDS:-21600}"
case "$interval" in
  ''|*[!0-9]*) interval=21600 ;;
esac
if [ -f "$LAST_FILE" ] && [ "$interval" -gt 0 ]; then
  last="$(cat "$LAST_FILE" 2>/dev/null || printf '0')"
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  if [ $((now - last)) -lt "$interval" ]; then
    exit 0
  fi
fi

new_install_id() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
  elif [ -r /proc/sys/kernel/random/uuid ]; then
    cat /proc/sys/kernel/random/uuid
  else
    printf 'pua-%s-%s-%s\n' "${now}" "$$" "$(od -An -N8 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n')"
  fi
}

if [ ! -s "$INSTALL_ID_FILE" ]; then
  umask 077
  new_install_id > "${INSTALL_ID_FILE}.tmp.$$" 2>/dev/null || exit 0
  mv "${INSTALL_ID_FILE}.tmp.$$" "$INSTALL_ID_FILE" 2>/dev/null || rm -f "${INSTALL_ID_FILE}.tmp.$$"
fi

INSTALL_ID="$(cat "$INSTALL_ID_FILE" 2>/dev/null | head -n 1 | tr -cd '[:alnum:]_.:-' | cut -c1-128)"
[ -n "$INSTALL_ID" ] || exit 0

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
PLUGIN_JSON="${PLUGIN_ROOT}/plugin.json"
VERSION="unknown"
PY="$(pua_python_cmd 2>/dev/null || true)"
if [ -n "$PY" ] && [ -f "$PLUGIN_JSON" ]; then
  VERSION="$($PY -c 'import json,sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("version", "unknown"))
except Exception:
    print("unknown")' "$(pua_to_python_path "$PLUGIN_JSON")" 2>/dev/null || printf 'unknown')"
fi

PLATFORM="${PUA_HEARTBEAT_PLATFORM:-claude-code}"
EVENT_NAME="session_start"
ENDPOINT="${PUA_HEARTBEAT_ENDPOINT:-https://pua-skill.pages.dev/api/heartbeat}"

if [ -n "$PY" ]; then
  PAYLOAD="$($PY -c 'import json,sys
install_id,version,platform,event_name,flavor=sys.argv[1:6]
print(json.dumps({
  "install_id": install_id,
  "plugin_version": version,
  "platform": platform,
  "event_name": event_name,
  "flavor": flavor,
}, ensure_ascii=False, separators=(",", ":")))' "$INSTALL_ID" "$VERSION" "$PLATFORM" "$EVENT_NAME" "$FLAVOR" 2>/dev/null || true)"
else
  PAYLOAD="{\"install_id\":\"${INSTALL_ID}\",\"plugin_version\":\"${VERSION}\",\"platform\":\"${PLATFORM}\",\"event_name\":\"${EVENT_NAME}\",\"flavor\":\"alibaba\"}"
fi
[ -n "$PAYLOAD" ] || exit 0

printf '%s\n' "$now" > "$LAST_FILE" 2>/dev/null || true

(
  curl -fsS --max-time 2 \
    -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "User-Agent: pua-skill-heartbeat/${VERSION}" \
    --data-binary "$PAYLOAD" \
    >/dev/null 2>&1
) &

exit 0
