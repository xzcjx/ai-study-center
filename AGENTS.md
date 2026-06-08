# AI 学习中心 · Agent 指令

> 本仓库是**结构化知识库**，不是应用项目。  
> 你的首要职责：**按责任链将用户提供的知识入库**。

## 启动条件

在以下情况**必须**读取并执行 [`docs/WORKFLOW.md`](docs/WORKFLOW.md) 全链路（H01→H11）：

- 用户要求整合/收录/入库文章或技巧
- 用户发送 `/ingest`
- 用户粘贴教程、链接、截图描述并要求整理

在以下情况**只读查询**（H02 Dedup 子流程）：

- 用户问「有没有 X 相关笔记」

## 必读文件（按顺序）

1. [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — 责任链 SSOT
2. [`knowledge/registry.yaml`](knowledge/registry.yaml) — 模块注册表
3. [`docs/KNOWLEDGE_SCHEMA.md`](docs/KNOWLEDGE_SCHEMA.md) — 笔记 Schema
4. [`.cursor/skills/knowledge-ingest/SKILL.md`](.cursor/skills/knowledge-ingest/SKILL.md) — 执行 Skill

## 硬性约束

- **不可跳过 Handler**；H10 失败不得交付
- **不可**整篇复制原文；提炼为 KnowledgeAtom
- **不可**提交密钥；`.env` 类内容不入库
- **不可**修改 PuSou 等无关仓库
- 所有笔记 **中文撰写**，技术术语保留英文

## 产出物

| 产物 | 路径 |
|------|------|
| 笔记正文 | `notes/{module}/*.md` |
| 总索引 | `docs/INDEX.md` |
| 入库报告 | 回复用户（模板 `templates/ingest-report.md`） |

## 快捷命令

```
/ingest [URL 或正文]              # 全链路入库
/ingest --module frontend [内容]  # 指定模块
/query [关键词]                   # 只查不重写
```

## 进度追踪

执行入库时在回复中维护进度（可复制 checklist）：

```
入库进度 ING-YYYYMMDD-NNN
- [x] H01 Intake
- [x] H02 Dedup
- [x] H03 Research
- [ ] H04 Classify
...
```
