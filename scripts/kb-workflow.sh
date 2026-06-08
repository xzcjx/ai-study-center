#!/usr/bin/env bash
# 生成完整方法论工作流（工具 + 流程 + 可复用 Prompt）
# 用法: scripts/kb-workflow.sh "开发前端界面" [--target DIR] [--stack "Vue3"] [--prompt-only] [--json]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

if [[ $# -lt 1 ]]; then
  echo "用法: kb-workflow.sh <场景描述> [--target DIR] [--stack STACK] [--brand TONE] [--brief TEXT]" >&2
  echo "      [--target-files PATHS] [--colors CSS] [--aesthetic DIR] [--prompt-only] [--json]" >&2
  echo "示例: kb-workflow.sh \"优化丑组件\" --target . --stack \"Vue 3\"" >&2
  echo "列表: kb-workflow.sh --list  或  python3 kb_tools.py list-workflows" >&2
  exit 1
fi

if [[ "$1" == "--list" || "$1" == "-l" ]]; then
  python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" list-workflows "${@:2}"
  exit 0
fi

python3 "$SCRIPT_DIR/kb_tools.py" --kb-root "$KB_ROOT" workflow "$@"
