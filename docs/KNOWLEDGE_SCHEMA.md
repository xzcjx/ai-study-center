# 知识条目 Schema

> 所有入库笔记必须符合本 Schema。校验脚本：`scripts/validate-note.sh`

## 1. 入库请求（IngestRequest）

Agent 收到用户输入后，在 **H01 Intake** 阶段解析为：

```yaml
ingest_id: "ING-{YYYYMMDD}-{序号}"   # 如 ING-20260608-001
source:
  type: url | paste | file | screenshot-desc
  value: "原文链接或摘要"
  author: "可选"
user_hint:
  module: "frontend | null"          # 用户指定模块，可为空
  tags: ["react", "hooks"]
  action: create | merge | null      # 用户指定动作，可为空
raw_content: "用户提供的正文或提取结果"
```

## 2. 知识原子（KnowledgeAtom）

**H05 Decompose** 将内容拆为可独立检索的原子：

```yaml
atom_id: "ATOM-{note-slug}-{n}"
title: "简短标题"
summary: "一句话"
detail: "展开说明"
code: "可选代码块"
applicable_when: "适用场景"
module: "frontend"
tags: ["react", "performance"]
```

一篇笔记通常包含 3–10 个 Atom。

## 3. 笔记 frontmatter（必填）

每篇 `notes/**/*.md` 顶部 YAML：

```yaml
---
id: "KB-{MODULE}-{YYYYMMDD}-{slug}"   # 如 KB-FE-20260608-react-memo
module: frontend                       # 对应 registry.yaml
module_id: MOD-FE
title: "React memo 性能优化要点"
source:
  type: url
  url: "https://..."
  accessed: "2026-06-08"
tags: [react, performance, memo]
difficulty: beginner | intermediate | advanced
status: active | deprecated | draft
related: []                            # 其他笔记 id 列表
ingest_id: "ING-20260608-001"
updated: "2026-06-08"
---
```

## 4. 笔记正文结构（必填章节）

| 章节 | 必填 | 说明 |
|------|------|------|
| `# {title}` | ✅ | 与 frontmatter.title 一致 |
| `## TL;DR` | ✅ | 3–7 条 bullet |
| `## 适用场景` | ✅ | 何时用、何时不用 |
| `## 知识要点` | ✅ | 按 Atom 组织的小节 |
| `## 代码 / 命令` | 有则必填 | 完整可复制 |
| `## 注意事项` | 推荐 | 常见坑 |
| `## 相关链接` | ✅ | 原文 + 项目内交叉引用 |
| `## 变更记录` | ✅ | 日期 + 说明 |

## 5. 索引行格式（docs/INDEX.md）

```markdown
| 2026-06-08 | React memo 性能优化 | `react`, `performance` | [笔记](../notes/frontend/2026-06-08-react-memo.md) | `KB-FE-20260608-react-memo` |
```

## 6. 入库报告（IngestReport）

**H11 Report** 输出给用户：

```yaml
ingest_id: ING-20260608-001
action: create | merge | split
module: frontend
files:
  created: []
  updated: []
atoms_count: 5
dedup:
  similar_found: false
  merged_into: null
validation: passed | failed
publish:
  status: pushed | skipped | failed
  commit: "af78990"          # pushed 时填写
  branch: main
  error: null                # failed 时填写原因
tldr:
  - "要点 1"
  - "要点 2"
  - "要点 3"
```
