#!/usr/bin/env bash
# 校验单篇知识库笔记是否符合 Schema
# 用法: scripts/validate-note.sh notes/frontend/2026-06-08-example.md
set -euo pipefail

FILE="${1:?用法: validate-note.sh <note.md>}"
ERR=0

red() { echo "❌ $*"; ERR=1; }
green() { echo "✅ $*"; }

[[ -f "$FILE" ]] || { red "文件不存在: $FILE"; exit 1; }

# frontmatter 存在
if ! head -1 "$FILE" | grep -q '^---$'; then
  red "缺少 YAML frontmatter（需以 --- 开头）"
else
  green "frontmatter 存在"
fi

# 必填 frontmatter 字段
REQUIRED_FIELDS=(id module module_id title ingest_id updated status difficulty)
# topic：ai-tools 下已注册主题的笔记必填
MODULE=$(sed -n '/^---$/,/^---$/p' "$FILE" | grep '^module:' | head -1 | sed 's/module: *//' | tr -d '"'"'"'"')
TOPIC=$(sed -n '/^---$/,/^---$/p' "$FILE" | grep '^topic:' | head -1 | sed 's/topic: *//' | tr -d '"'"'"'"')
if [[ "$MODULE" == "ai-tools" && -z "$TOPIC" ]]; then
  red "ai-tools 模块笔记须填写 topic（见 registry.yaml topics）"
fi
if [[ -n "$TOPIC" && "$FILE" != *"/${TOPIC}/"* ]]; then
  red "文件路径应与 topic 一致: 期望路径含 /${TOPIC}/，当前: ${FILE}"
fi
for field in "${REQUIRED_FIELDS[@]}"; do
  if ! sed -n '/^---$/,/^---$/p' "$FILE" | grep -q "^${field}:"; then
    red "frontmatter 缺少字段: ${field}"
  fi
done

# 必填正文章节
REQUIRED_SECTIONS=("TL;DR" "适用场景" "知识要点" "相关链接" "变更记录")
for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "## ${section}" "$FILE"; then
    red "正文缺少章节: ## ${section}"
  fi
done

# TL;DR 至少 3 条 bullet
TLDR_COUNT=$(sed -n '/## TL;DR/,/^## /p' "$FILE" | grep -c '^- ' || true)
if [[ "$TLDR_COUNT" -lt 3 ]]; then
  red "TL;DR 至少需要 3 条 bullet（当前: ${TLDR_COUNT}）"
else
  green "TL;DR 条数: ${TLDR_COUNT}"
fi

# 禁止敏感模式
if grep -qiE '(api[_-]?key|secret|password|token|Bearer\s+[A-Za-z0-9])' "$FILE"; then
  red "检测到可能的密钥/Token，请移除后再入库"
fi

# id 格式
NOTE_ID=$(sed -n '/^---$/,/^---$/p' "$FILE" | grep '^id:' | head -1 | sed 's/id: *//' | tr -d '"'"'"'"')
if [[ -n "$NOTE_ID" && ! "$NOTE_ID" =~ ^KB-[A-Z]+-[0-9]{8}- ]]; then
  red "id 格式应为 KB-{PREFIX}-{YYYYMMDD}-{slug}，当前: ${NOTE_ID}"
else
  green "id 格式: ${NOTE_ID:-ok}"
fi

if [[ "$ERR" -eq 1 ]]; then
  echo ""
  echo "校验失败。请修复后重新运行。"
  exit 1
fi

echo ""
echo "校验通过: $FILE"
exit 0
