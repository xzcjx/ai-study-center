#!/usr/bin/env bash
# H13b SyncCatalog：将入库笔记中的工具同步到 tools-catalog.yaml 总表
# 用法: scripts/sync-catalog.sh <ingest_id> <note1.md> [note2.md...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

if [[ $# -lt 2 ]]; then
  echo "用法: sync-catalog.sh <ingest_id> <notes/*.md> [more...]" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" sync-catalog "$@"
