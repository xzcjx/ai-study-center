# Handler 细则（knowledge-ingest 子文档）

> 主 Skill：[SKILL.md](SKILL.md) · 工作流：[docs/WORKFLOW.md](../../docs/WORKFLOW.md)

---

## H01 · Intake

| 项 | 说明 |
|----|------|
| 输入 | 用户原始消息 |
| 输出 | `IngestRequest`（见 KNOWLEDGE_SCHEMA §1） |
| 停止条件 | 无 URL、无正文、无截图描述 |

**ingest_id 生成**：查 `docs/INDEX.md`「最近更新」表当日已有条数 +1。

---

## H02 · Dedup

| 项 | 说明 |
|----|------|
| 输入 | `IngestRequest` |
| 输出 | `DedupReport { similar_found, candidates[], recommended_action }` |

**搜索策略**（按优先级）：
1. INDEX 标题精确/模糊匹配
2. `grep -ri` notes/ 正文
3. tags 交集

**merge 条件**：同主题 + 已有笔记 status=active + 用户未要求独立成篇。

---

## H03 · Research

| 项 | 说明 |
|----|------|
| 输入 | `IngestRequest` |
| 输出 | `EnrichedContext { raw, fetched, official_refs[] }` |

- URL → WebFetch
- 版本敏感技术 → WebSearch 核实最新 API
- 失败不阻断，标注 `source.reliability: user-only`

---

## H04 · Classify

| 项 | 说明 |
|----|------|
| 输入 | `EnrichedContext` |
| 输出 | `ModuleAssignment[] { module, module_id, score, action }` |

**打分**：registry.yaml keywords 每命中 +1；标题命中 +2；用户 hint +5。

**split 示例**：
- 「Docker 跑 Playwright CI」→ testing(0.6) + devops(0.5) → split 两篇

---

## H05 · Decompose

| 项 | 说明 |
|----|------|
| 输入 | `EnrichedContext` + `ModuleAssignment` |
| 输出 | `KnowledgeAtom[]` |

**Atom 质量门禁**：
- title ≤ 80 字符
- summary 一句话可独立理解
- 必须可归类到单一 module

---

## H06 · Structure

| 项 | 说明 |
|----|------|
| 输入 | `KnowledgeAtom[]` |
| 输出 | `DraftNote`（含 frontmatter + 正文） |

模板：[templates/article.md](../../templates/article.md)

**merge 模式**：保留原 frontmatter.id，更新 `updated`，变更记录追加。

---

## H07 · Persist

| 项 | 说明 |
|----|------|
| 输入 | `DraftNote[]` |
| 输出 | `paths[]` |

- create → 新文件
- merge → 覆盖/追加已有文件（保留变更记录）
- 文件名冲突 → `{slug}-2.md`

---

## H08 · Index

更新 [docs/INDEX.md](../../docs/INDEX.md) 四处：
1. 统计表篇数 +N
2. 分类表新行（日期|标题|标签|链接|KB-id）
3. 标签云追加新 tag
4. 最近更新表

---

## H09 · CrossLink

- 读 DedupReport.candidates → 写入 `related: [KB-...]`
- 打开关联笔记，追加 reciprocal link
- 正文「相关链接」章节同步

---

## H10 · Validate

```bash
scripts/validate-note.sh <file.md>
```

exit 0 → 过；非 0 → 带错误回 H06。

---

## H13 · SyncWorkflow

| 项 | 说明 |
|----|------|
| 输入 | H07 笔记路径 + `ingest_id` |
| 输出 | 更新 `knowledge/workflow-ingest-sync.yaml` |
| 规则 SSOT | `knowledge/workflow-sync-rules.yaml` |

```bash
scripts/sync-workflow.sh {ingest_id} notes/{module}/{file}.md
```

**自动映射**：
1. 笔记 `tags` → `playbook_notes` + `keywords`（按 `tag_to_workflows`）
2. 笔记 `module` 兜底 → 默认 workflow
3. `tools-registry` 中同 `kb_id` 工具 → `tool_refs`（按 `intent_to_tool_refs`）
4. 标题关键词 → `router_triggers`

**消费侧**：`kb-workflow.sh` 加载时合并 base + sync 层，无需手改 `workflows-registry.yaml`。

失败 → 阻断 H12（`publish-ingest.sh` exit 1）。

---

## H13b · SyncCatalog

| 项 | 说明 |
|----|------|
| 输入 | H07 笔记路径 + `ingest_id` |
| 输出 | `knowledge/tools-catalog.yaml` 增量 |
| 解析 SSOT | `scripts/kb_tools.py` `_extract_catalog_entries` |

```bash
scripts/sync-catalog.sh {ingest_id} notes/{module}/{file}.md
```

- 仅工具清单表 / 含 http 链接的行 → 新草稿或 `kb_notes` 关联
- 对比矩阵、变更记录表 → **跳过**

失败 → 阻断 H12。

---

## H13c · ValidateCatalog

| 项 | 说明 |
|----|------|
| 输入 | sync 后的 `tools-catalog.yaml` + sync 前 baseline |
| 输出 | exit 0 / 1 |
| 脚本 | `scripts/validate-catalog.sh` |

```bash
scripts/validate-catalog.sh --baseline /tmp/catalog-before.yaml
```

**Agent 复核**（失败或草稿 > 3 时 mandatory）：

```bash
git diff knowledge/tools-catalog.yaml
```

修 catalog 或笔记 → 重跑 `publish-ingest.sh`。**禁止**带 junk catalog push。

---

## H12 · Publish

| 项 | 说明 |
|----|------|
| 输入 | H07 `paths[]` + H08/H09 额外改动 |
| 输出 | `PublishReport { status, commit, branch, remote, error? }` |

```bash
scripts/publish-ingest.sh {ingest_id} "{title}" {paths...}
```

- 仅提交本次入库相关文件
- 用户显式 `--no-push` / `不要推送` → `status: skipped`
- 推送失败不阻断 H11，在报告中说明

---

## H11 · Report

模板：[templates/ingest-report.md](../../templates/ingest-report.md)

用户可见 TL;DR ≤ 3 条；须汇报 H12 推送结果；技术细节在笔记正文。
