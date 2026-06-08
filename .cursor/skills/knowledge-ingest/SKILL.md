---
name: knowledge-ingest
description: >-
  将用户提供的文章、链接、技巧按责任链（H01–H12）结构化入库到 AI 学习中心知识库。
  自动分类到 frontend/backend/testing/ai-tools/devops/database/architecture/misc 模块，
  更新 INDEX、去重、交叉引用并校验。Use when user says 整合/收录/入库/学习笔记/文章/帮我整理,
  sends /ingest, or asks to add knowledge to AI Learning Center.
---

# Knowledge Ingest · 知识入库 Skill

## 执行前

1. 读 [pipeline.md](pipeline.md)（Handler 细则）
2. 读 [docs/WORKFLOW.md](../../docs/WORKFLOW.md)
3. 读 [knowledge/registry.yaml](../../knowledge/registry.yaml)

## 责任链（严格顺序）

复制此 checklist 并在回复中勾选：

```
入库 ING-{date}-{seq}
- [ ] H01 Intake      → IngestRequest
- [ ] H02 Dedup       → DedupReport（grep INDEX + notes/）
- [ ] H03 Research    → EnrichedContext（WebFetch/WebSearch）
- [ ] H04 Classify    → ModuleAssignment（registry.yaml 打分）
- [ ] H05 Decompose   → KnowledgeAtom[]（3–10 条）
- [ ] H06 Structure   → DraftNote（templates/article.md + Schema）
- [ ] H07 Persist     → 写入 notes/{module}/
- [ ] H08 Index       → 更新 docs/INDEX.md
- [ ] H09 CrossLink   → related 双向链接
- [ ] H10 Validate    → scripts/validate-note.sh
- [ ] H13 SyncWorkflow → scripts/sync-workflow.sh（自动进方法论，H12 内执行）
- [ ] H13b SyncCatalog → scripts/sync-catalog.sh（自动进 tools-catalog 总表，H12 内执行）
- [ ] H12 Publish     → scripts/publish-ingest.sh（自动 commit + push）
- [ ] H11 Report      → templates/ingest-report.md
```

**H10 失败 → 回 H06 修复，禁止跳过。**  
**H12 默认执行**；用户显式 `--no-push` / `不要推送` 时可跳过。

## H01 Intake

- 生成 `ingest_id`: `ING-{YYYYMMDD}-{001起递增}`
- 解析 `source.type`: url | paste | file | screenshot-desc
- 无实质内容 → **终止**，向用户索要

## H02 Dedup

```bash
# 在仓库根目录执行
grep -ri "{关键词}" notes/ docs/INDEX.md
```

| 相似度 | 动作 |
|--------|------|
| ≥80% | merge 到已有笔记 |
| 40–80% | create + related 链接 |
| <40% | create |

## H04 Classify

读 registry.yaml，对 keywords 命中计分；`user_hint.module` 优先。  
跨模块 → split，每个模块独立笔记 + 互相 related。

## H06 Structure

frontmatter 必填字段见 [docs/KNOWLEDGE_SCHEMA.md](../../docs/KNOWLEDGE_SCHEMA.md)：

```yaml
---
id: KB-{PREFIX}-{date}-{slug}
module: frontend
module_id: MOD-FE
title: "..."
source: { type: url, url: "...", accessed: "YYYY-MM-DD" }
tags: []
difficulty: beginner | intermediate | advanced
status: active
related: []
ingest_id: ING-...
updated: YYYY-MM-DD
---
```

## H07 文件命名

`notes/{module}/{YYYY-MM-DD}-{kebab-slug}.md`

## H10 Validate

```bash
scripts/validate-note.sh notes/{module}/{file}.md
```

## H13 SyncWorkflow

H10 通过后、H12 之前，将本次入库笔记同步到方法论（`publish-ingest.sh` 内自动调用）：

```bash
scripts/sync-workflow.sh {ingest_id} notes/{module}/{file}.md
```

- 读取 `workflow-sync-rules.yaml`，写入 `workflow-ingest-sync.yaml`
- 与 `workflows-registry.yaml` 合并后 `/kb-workflow` 实时可用
- 若登记了 `tools-registry`，按 intents 追加 `tool_refs`

## H13b SyncCatalog

`publish-ingest.sh` 内自动调用，维护 [`knowledge/tools-catalog.yaml`](../../knowledge/tools-catalog.yaml)：

- **可安装工具**：完善 `positioning` / `tags` / `homepage`，设 `registry_id`
- **文章里新工具**：从笔记表格追加草稿行（`positioning: 待补充`），人工或下次 ingest 补全
- **验证**：`scripts/query-tools.sh "前端工具汇总"`

## H12 Publish

H10 + H13 通过后，仅 stage 本次入库文件并推送：

```bash
scripts/publish-ingest.sh ING-20260608-001 "笔记标题" \
  notes/ai-tools/2026-06-08-example.md \
  docs/INDEX.md
```

- 包含 H07 笔记、H08 INDEX、H09 关联笔记、H13 `workflow-ingest-sync.yaml`、H13b `tools-catalog.yaml`
- 禁止 `git add -A`
- 推送目标：`origin` 当前分支

## H11 用户回复

用 [templates/ingest-report.md](../../templates/ingest-report.md) 格式，须含 H12 推送结果。

## 只读查询模式

用户说「查询/有没有/搜索笔记」→ **仅 H02**，不写入文件。

## 参考

- Handler 细则：[pipeline.md](pipeline.md)
- 模块决策：[docs/MODULES.md](../../docs/MODULES.md)
