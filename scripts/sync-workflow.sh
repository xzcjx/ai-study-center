#!/usr/bin/env bash
# H13 SyncWorkflow：将入库笔记/工具同步到方法论（workflow-ingest-sync.yaml）
# 用法: scripts/sync-workflow.sh <ingest_id> <note1.md> [note2.md...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

if [[ $# -lt 2 ]]; then
  echo "用法: sync-workflow.sh <ingest_id> <notes/*.md> [more...]" >&2
  exit 1
fi

INGEST_ID="$1"
shift

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" sync-workflow "$INGEST_ID" "$@"
