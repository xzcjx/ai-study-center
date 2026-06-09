#!/usr/bin/env bash
# 笔记 → 平台可发布内容 brief
# 用法:
#   scripts/kb-publish.sh -redbook notes/ai-tools/geo/xxx.md
#   scripts/kb-publish.sh --list
#   scripts/kb-publish.sh brief redbook @notes/xxx.md [--json 默认]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/kb_paths.sh
source "$SCRIPT_DIR/lib/kb_paths.sh"

usage() {
  echo "用法: kb-publish.sh -{platform} <笔记路径> [--save]" >&2
  echo "      kb-publish.sh --list" >&2
  echo "" >&2
  echo "平台: -redbook | -wechat | -taobao | -xianyu" >&2
  echo "示例: kb-publish.sh -redbook notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md" >&2
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

if [[ "$1" == "--list" || "$1" == "-l" ]]; then
  python3 "$SCRIPT_DIR/kb_publish.py" --kb-root "$KB_ROOT" list
  exit 0
fi

PLATFORM=""
NOTE=""
SAVE=false

for arg in "$@"; do
  case "$arg" in
    -redbook|-wechat|-taobao|-xianyu|-xiaohongshu)
      PLATFORM="${arg#-}"
      ;;
    --save)
      SAVE=true
      ;;
    @*)
      NOTE="${arg#@}"
      ;;
    *)
      if [[ -z "$NOTE" && ( -f "$arg" || "$arg" == notes/* ) ]]; then
        NOTE="$arg"
      fi
      ;;
  esac
done

if [[ -z "$PLATFORM" ]]; then
  echo "错误: 请指定平台，如 -redbook" >&2
  usage
fi

if [[ -z "$NOTE" ]]; then
  echo "错误: 请指定笔记路径" >&2
  usage
fi

python3 "$SCRIPT_DIR/kb_publish.py" --kb-root "$KB_ROOT" brief "$PLATFORM" "$NOTE"

if [[ "$SAVE" == true ]]; then
  echo "" >&2
  echo "提示: --save 由 Agent 在生成正文后写入 publish/{platform}/ 目录（见 docs/PUBLISH.md P05）" >&2
fi
