#!/usr/bin/env bash
# Source this file, then compile/run retained inspection or template tools.
# Dependencies must already exist. Nothing is downloaded or installed.
POI_SCRIPTS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) POI_CP_SEPARATOR=';' ;;
  *) POI_CP_SEPARATOR=':' ;;
esac

poi_allowed() {
  case "$1" in
    DeleteColumn*|VerifyShift*)
      printf '%s\n' 'PAUSED: delete-column and its incomplete verifier are reference-only.' >&2
      return 2 ;;
    DumpStructure|DumpAll|RowInfo|CheckRich|MergeTemplate) return 0 ;;
    *) printf 'Unsupported POI entrypoint: %s\n' "$1" >&2; return 2 ;;
  esac
}

poi_dependencies() {
  if [ -z "${POI_CLASSPATH:-}" ]; then
    printf '%s\n' 'Set POI_CLASSPATH to existing POI 4.1.2 and dependency jars (or an absolute lib/* directory). Use ; on Windows, : on POSIX. No dependencies are installed automatically.' >&2
    return 2
  fi
}

poi_compile() {
  local source name
  local sources=()
  [ "$#" -gt 0 ] || { printf '%s\n' 'Supply retained Java source names, e.g. DumpStructure.java.' >&2; return 2; }
  for source in "$@"; do
    name="${source##*/}"
    name="${name%.java}"
    poi_allowed "$name" || return $?
    sources+=("$POI_SCRIPTS_DIR/$name.java")
  done
  poi_dependencies || return $?
  # Compile into the caller's scratch directory, never the skill or dependency tree.
  javac -encoding UTF-8 -cp "$POI_CLASSPATH" -d . "${sources[@]}"
}

poi_run() {
  local main="${1:-}"
  poi_allowed "$main" || return $?
  shift
  poi_dependencies || return $?
  java -Dfile.encoding=UTF-8 -cp ".${POI_CP_SEPARATOR}${POI_CLASSPATH}" "$main" "$@"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  poi_run "$@"
fi
