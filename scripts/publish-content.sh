#!/usr/bin/env bash
# 内容发布成稿完成后提交并推送到远程（P07 Publish）
# 用法: scripts/publish-content.sh <publish_id> <platform> <简短标题> <file1> [file2...]
# 示例: scripts/publish-content.sh PUB-20260609-001 taobao "微信AI带货淘宝文案" \
#         publish/taobao/2026-06-09-微信\ AI\ 带货....md
# 跳过推送: scripts/publish-content.sh --no-push PUB-... taobao "标题" publish/...
set -euo pipefail

NO_PUSH=false
if [[ "${1:-}" == "--no-push" ]]; then
  NO_PUSH=true
  shift
fi

PUBLISH_ID="${1:?用法: publish-content.sh [--no-push] <publish_id> <platform> <title> <file...>}"
PLATFORM="${2:?缺少 platform（redbook/wechat/taobao/xianyu）}"
TITLE="${3:?缺少标题}"
shift 3

if [[ $# -eq 0 ]]; then
  echo "❌ 未指定待提交文件"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

STAGED=()
for f in "$@"; do
  if [[ ! -f "$f" ]]; then
    echo "❌ 文件不存在: $f"
    exit 1
  fi
  if [[ "$f" != publish/* ]]; then
    echo "❌ 发布推送仅允许 publish/ 下文件: $f"
    exit 1
  fi
  STAGED+=("$f")
done

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "❌ 当前目录不是 git 仓库"
  exit 1
fi

git add "${STAGED[@]}"

if git diff --cached --quiet; then
  echo "⚠️  无变更可提交（可能已提交过）"
  exit 0
fi

git commit -m "$(cat <<EOF
publish(${PLATFORM}): ${TITLE}

发布单 ${PUBLISH_ID}：${PLATFORM} 平台成稿。
EOF
)"

if [[ "$NO_PUSH" == true ]]; then
  COMMIT="$(git rev-parse --short HEAD)"
  echo "✅ 已本地提交 ${COMMIT}（--no-push，未推送）"
  exit 0
fi

if ! git remote get-url origin &>/dev/null; then
  echo "⚠️  未配置 origin 远程，已提交但未推送"
  exit 0
fi

BRANCH="$(git branch --show-current)"
git push origin "${BRANCH}"

COMMIT="$(git rev-parse --short HEAD)"
echo "✅ 已推送 ${BRANCH}@${COMMIT} → origin"
