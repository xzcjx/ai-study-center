---
name: knowledge-ingest
description: >-
  将用户提供的文章、链接、技巧按责任链（H01–H12）结构化入库到 AI 学习中心知识库。
  自动分类到 frontend/backend/testing/ai-tools/devops/database/architecture/misc 模块，
  更新 INDEX、去重、交叉引用并校验。
  Use when user says 整合/收录/入库/学习笔记/文章/帮我整理,
  sends /ingest, or asks to add knowledge to AI Learning Center.
---

# Knowledge Ingest · 知识入库 Skill

## 回购路径

本仓库路径（`KB`）：`/Users/admin/Desktop/spider_project/ai-study-center`

所有脚本在仓库根目录执行。

## 执行前

1. 读 `AGENTS.md`
2. 读 `docs/WORKFLOW.md`（责任链 SSOT）
3. 读 `knowledge/registry.yaml`（模块注册表）

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
- [ ] H13 SyncWorkflow → scripts/sync-workflow.sh（H12 内，方法论）
- [ ] H13b SyncCatalog → scripts/sync-catalog.sh（H12 内，tools-catalog 增量）
- [ ] H13c ValidateCatalog → scripts/validate-catalog.sh（H12 内，**阻断 push**）
- [ ] H12 Publish     → scripts/publish-ingest.sh（H13c 通过后 commit + push）
- [ ] H11 Report      → templates/ingest-report.md
```

**H10 失败 → 回 H06 修复，禁止跳过。**  
**H13c 失败 → 修 catalog 或笔记工具表，禁止 push。**  
**H12 默认执行**；用户显式 `--no-push` / `不要推送` 时可跳过。

## H01 Intake

- 生成 `ingest_id`: `ING-{YYYYMMDD}-{001起递增}`
- 解析 `source.type`: url | paste | file | screenshot-desc
- 无实质内容 → **终止**，向用户索要

**ingest_id 生成**：查 `docs/INDEX.md`「最近更新」表当日已有条数 +1。

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

**搜索策略**（按优先级）：
1. INDEX 标题精确/模糊匹配
2. `grep -ri` notes/ 正文
3. tags 交集

**merge 条件**：同主题 + 已有笔记 status=active + 用户未要求独立成篇。

## H03 Research

| 项 | 说明 |
|----|------|
| 输入 | `IngestRequest` |
| 输出 | `EnrichedContext { raw, fetched, official_refs[] }` |

- URL → WebFetch
- 版本敏感技术 → WebSearch 核实最新 API
- 失败不阻断，标注 `source.reliability: user-only`

## H04 Classify

读 registry.yaml，对 keywords 命中计分；`user_hint.module` 优先。

**打分**：registry.yaml keywords 每命中 +1；标题命中 +2；用户 hint +5。

跨模块 → split，每个模块独立笔记 + 互相 related。

## H05 Decompose

| 项 | 说明 |
|----|------|
| 输入 | `EnrichedContext` + `ModuleAssignment` |
| 输出 | `KnowledgeAtom[]`（3–10 条） |

**Atom 质量门禁**：
- title ≤ 80 字符
- summary 一句话可独立理解
- 必须可归类到单一 module

## H06 Structure

frontmatter 必填字段见 `docs/KNOWLEDGE_SCHEMA.md`：

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

模板：`templates/article.md`

**merge 模式**：保留原 frontmatter.id，更新 `updated`，变更记录追加。

## H07 文件命名与路径

1. H04 选定 `module` 后，读 `registry.yaml` → `topics`，按 keywords 选 `topic`（若有）
2. 有 topic：`notes/{module}/{topic}/{YYYY-MM-DD}-{kebab-slug}.md`
3. 无 topic：`notes/{module}/{YYYY-MM-DD}-{kebab-slug}.md`
4. frontmatter 必填 `topic: {id}`（当写入 topic 子目录时）
5. create → 新文件；merge → 覆盖/追加已有文件（保留变更记录）
6. 文件名冲突 → `{slug}-2.md`

## H08 Index

更新 `docs/INDEX.md` 四处：
1. 统计表篇数 +N
2. 分类表新行（日期|标题|标签|链接|KB-id）
3. 标签云追加新 tag
4. 最近更新表

## H09 CrossLink

- 读 DedupReport.candidates → 写入 `related: [KB-...]`
- 打开关联笔记，追加 reciprocal link
- 正文「相关链接」章节同步

## H10 Validate

```bash
scripts/validate-note.sh notes/{module}/{file}.md
```

exit 0 → 过；非 0 → 带错误回 H06。

## H13 SyncWorkflow

```bash
scripts/sync-workflow.sh {ingest_id} notes/{module}/{file}.md
```

**自动映射**：
1. 笔记 `tags` → `playbook_notes` + `keywords`（按 `tag_to_workflows`）
2. 笔记 `module` 兜底 → 默认 workflow
3. `tools-registry` 中同 `kb_id` 工具 → `tool_refs`（按 `intent_to_tool_refs`）
4. 标题关键词 → `router_triggers`

失败 → 阻断 H12。

## H13b SyncCatalog

```bash
scripts/sync-catalog.sh {ingest_id} notes/{module}/{file}.md
```

- 仅工具清单表 / 含 http 链接的行 → 新草稿或 `kb_notes` 关联
- 对比矩阵、变更记录表 → **跳过**

失败 → 阻断 H12。

## H13c ValidateCatalog

```bash
scripts/validate-catalog.sh --baseline /tmp/catalog-before.yaml
```

**Agent 复核**（失败或草稿 > 3 时 mandatory）：

```bash
git diff knowledge/tools-catalog.yaml
```

修 catalog 或笔记 → 重跑 `publish-ingest.sh`。**禁止**带 junk catalog push。

**阻断条件**：YAML 结构损坏、重复 id、单次草稿 > 8、泛化 id（`tool-2` 等）、表格维度词误入。

## H12 Publish

H10 + H13 + **H13c** 通过后，仅 stage 本次入库文件并推送：

```bash
scripts/publish-ingest.sh ING-20260608-001 "笔记标题" \
  notes/ai-tools/frontend-design/2026-06-08-example.md \
  docs/INDEX.md
```

- 包含 H07 笔记、H08 INDEX、H09 关联笔记、H13 `workflow-ingest-sync.yaml`、H13b `tools-catalog.yaml`
- 禁止 `git add -A`
- 推送目标：`origin` 当前分支
- 用户显式 `--no-push` / `不要推送` → `status: skipped`
- 推送失败不阻断 H11，在报告中说明

## H11 用户回复

用 `templates/ingest-report.md` 格式，须含 H12 推送结果。

## 只读查询模式

用户说「查询/有没有/搜索笔记」→ **仅 H02**，不写入文件。

## SSOT 参考

- 责任链 SSOT：`docs/WORKFLOW.md`
- 模块决策：`docs/MODULES.md`
- 笔记 Schema：`docs/KNOWLEDGE_SCHEMA.md`
- 笔记模板：`templates/article.md`
- 入库报告模板：`templates/ingest-report.md`
