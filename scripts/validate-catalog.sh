#!/usr/bin/env bash
# H13b 质量门禁：校验 tools-catalog.yaml 结构与 sync 增量
# 用法:
#   scripts/validate-catalog.sh
#   scripts/validate-catalog.sh --baseline /tmp/catalog-before.yaml
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

BASELINE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --baseline)
      BASELINE="${2:?缺少 baseline 路径}"
      shift 2
      ;;
    *)
      echo "未知参数: $1" >&2
      echo "用法: validate-catalog.sh [--baseline <file>]" >&2
      exit 1
      ;;
  esac
done

ARGS=(validate-catalog)
if [[ -n "$BASELINE" ]]; then
  ARGS+=(--baseline "$BASELINE")
fi

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" "${ARGS[@]}"
