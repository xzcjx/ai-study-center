#!/usr/bin/env bash
# 安装工具（默认预览，--yes 执行）
# 用法: scripts/install-tool.sh taste-skill [--method npx-default] [--agent cursor] [--target .] [--prompt "做 SaaS 落地页"] [--yes]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

if [[ $# -lt 1 ]]; then
  echo "用法: install-tool.sh <tool-id> [--method ID] [--agent cursor] [--target DIR] [--prompt TEXT] [--yes]" >&2
  echo "先运行 query-tools.sh 查看可用工具与 method id。" >&2
  exit 1
fi

TOOL_ID="$1"
shift

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" install "$TOOL_ID" "$@"
