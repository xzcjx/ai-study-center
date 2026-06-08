#!/usr/bin/env bash
# 入库完成后提交并推送到远程（H12 Publish）
# 用法: scripts/publish-ingest.sh <ingest_id> <简短标题> <file1> [file2...]
# 示例: scripts/publish-ingest.sh ING-20260608-001 "Taste Skill" \
#         notes/ai-tools/frontend-design/2026-06-08-taste-skill-agent-frontend.md docs/INDEX.md
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
NOTE_FILES=()
for f in "$@"; do
  if [[ ! -f "$f" ]]; then
    echo "❌ 文件不存在: $f"
    exit 1
  fi
  STAGED+=("$f")
  if [[ "$f" == notes/* ]]; then
    NOTE_FILES+=("$f")
  fi
done

# H13 SyncWorkflow：入库笔记自动同步方法论
if [[ ${#NOTE_FILES[@]} -gt 0 ]] && [[ -x "$REPO_ROOT/scripts/sync-workflow.sh" ]]; then
  "$REPO_ROOT/scripts/sync-workflow.sh" "$INGEST_ID" "${NOTE_FILES[@]}" || {
    echo "❌ H13 SyncWorkflow 失败" >&2
    exit 1
  }
  SYNC_FILE="$REPO_ROOT/knowledge/workflow-ingest-sync.yaml"
  if [[ -f "$SYNC_FILE" ]]; then
    STAGED+=("$SYNC_FILE")
  fi
  if [[ -x "$REPO_ROOT/scripts/sync-catalog.sh" ]]; then
    CATALOG_FILE="$REPO_ROOT/knowledge/tools-catalog.yaml"
    CATALOG_BASELINE=""
    if [[ -f "$CATALOG_FILE" ]]; then
      CATALOG_BASELINE="$(mktemp)"
      cp "$CATALOG_FILE" "$CATALOG_BASELINE"
    fi
    "$REPO_ROOT/scripts/sync-catalog.sh" "$INGEST_ID" "${NOTE_FILES[@]}" || {
      echo "❌ H13b SyncCatalog 失败" >&2
      [[ -n "$CATALOG_BASELINE" ]] && rm -f "$CATALOG_BASELINE"
      exit 1
    }
    if [[ -f "$CATALOG_FILE" ]]; then
      STAGED+=("$CATALOG_FILE")
    fi
    if [[ -x "$REPO_ROOT/scripts/validate-catalog.sh" ]]; then
      VALIDATE_ARGS=()
      if [[ -n "$CATALOG_BASELINE" ]]; then
        VALIDATE_ARGS=(--baseline "$CATALOG_BASELINE")
      fi
      "$REPO_ROOT/scripts/validate-catalog.sh" "${VALIDATE_ARGS[@]}" || {
        echo "❌ H13b ValidateCatalog 失败（阻断 H12）" >&2
        echo "   请检查 git diff knowledge/tools-catalog.yaml，修 catalog 或笔记工具表后重跑 publish-ingest.sh" >&2
        [[ -n "$CATALOG_BASELINE" ]] && rm -f "$CATALOG_BASELINE"
        exit 1
      }
    fi
    [[ -n "$CATALOG_BASELINE" ]] && rm -f "$CATALOG_BASELINE"
  fi
fi

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

入库单 ${INGEST_ID}：更新笔记、索引与方法论同步层。
EOF
)"

BRANCH="$(git branch --show-current)"
git push origin "${BRANCH}"

COMMIT="$(git rev-parse --short HEAD)"
echo "✅ 已推送 ${BRANCH}@${COMMIT} → origin"
