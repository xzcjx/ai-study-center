#!/usr/bin/env bash
# 入库完成后提交并推送到远程（H12 Publish）
# 用法: scripts/publish-ingest.sh <ingest_id> <简短标题> <file1> [file2...]
# 示例: scripts/publish-ingest.sh ING-20260608-001 "Taste Skill" \
#         notes/ai-tools/2026-06-08-taste-skill-agent-frontend.md docs/INDEX.md
set -euo pipefail

INGEST_ID="${1:?用法: publish-ingest.sh <ingest_id> <title> <file...>}"
TITLE="${2:?缺少标题}"
shift 2

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
  STAGED+=("$f")
done

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "❌ 当前目录不是 git 仓库"
  exit 1
fi

if ! git remote get-url origin &>/dev/null; then
  echo "❌ 未配置 origin 远程，跳过推送"
  exit 1
fi

git add "${STAGED[@]}"

if git diff --cached --quiet; then
  echo "⚠️  无变更可提交（可能已提交过）"
  exit 0
fi

git commit -m "$(cat <<EOF
docs(ingest): ${TITLE}

入库单 ${INGEST_ID}：更新笔记与索引。
EOF
)"

BRANCH="$(git branch --show-current)"
git push origin "${BRANCH}"

COMMIT="$(git rev-parse --short HEAD)"
echo "✅ 已推送 ${BRANCH}@${COMMIT} → origin"
