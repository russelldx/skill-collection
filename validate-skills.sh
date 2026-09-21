#!/usr/bin/env bash
set -eu
exec "${PYTHON:-python}" "$(dirname "$0")/validate-skills.py" "$@"
