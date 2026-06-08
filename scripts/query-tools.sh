#!/usr/bin/env bash
# 检索可安装工具 + 笔记摘要
# 用法: scripts/query-tools.sh "好看的前端" [--json] [--limit N]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

if [[ $# -lt 1 ]]; then
  echo "用法: query-tools.sh <关键词> [--json] [--limit N]" >&2
  exit 1
fi

QUERY="$1"
shift

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" query "$QUERY" "$@"
