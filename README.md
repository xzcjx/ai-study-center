# AI 学习中心

> **结构化个人知识库** — 责任链工作流驱动的学习笔记仓库。

## 快速开始

**在 Cursor 中打开本文件夹**，然后：

```
/ingest https://example.com/article     # 收录文章（全链路 H01→H12，含自动推送）
/ingest --module frontend [粘贴正文]      # 指定模块入库
/query playwright                         # 只查已有笔记（本仓库内）
```

**在任意其他项目中**（需全局 Skill `ai-learning-center-consume`）：

```
/kb-recommend 好看的前端界面    # 检索工具 + 对比推荐，等你选择
/kb-install taste-skill          # 预览安装到当前项目
/kb-install taste-skill --yes    # 你确认后再执行
```

## 架构

```
用户输入
   ↓
责任链 H01→H12（见 docs/WORKFLOW.md）
   ↓
notes/{module}/*.md  +  docs/INDEX.md
```

**跨项目消费**（[`docs/CONSUME.md`](docs/CONSUME.md)）：

```
业务项目 /kb-recommend → query-tools.sh → 用户选择 → install-tool.sh → usage_prompt
```

## 目录

| 路径 | 作用 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | Agent 入口指令 |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | **责任链 SSOT**（H01–H12） |
| [`docs/MODULES.md`](docs/MODULES.md) | 8 大知识模块 |
| [`docs/KNOWLEDGE_SCHEMA.md`](docs/KNOWLEDGE_SCHEMA.md) | 笔记 Schema |
| [`knowledge/registry.yaml`](knowledge/registry.yaml) | 模块机器可读注册表 |
| [`knowledge/tools-registry.yaml`](knowledge/tools-registry.yaml) | 可安装工具目录 |
| [`docs/CONSUME.md`](docs/CONSUME.md) | 跨项目消费 SSOT（C01–C05） |
| [`.cursor/skills/knowledge-ingest/`](.cursor/skills/knowledge-ingest/) | 入库 Skill |
| [`.cursor/skills/knowledge-consume/`](.cursor/skills/knowledge-consume/) | 消费 Skill |
| [`.cursor/rules/`](.cursor/rules/) | 全局 + 流水线规则 |
| [`notes/`](notes/) | 知识正文（8 模块） |
| [`scripts/validate-note.sh`](scripts/validate-note.sh) | 笔记校验工具 |
| [`scripts/publish-ingest.sh`](scripts/publish-ingest.sh) | 入库后自动 commit + push |
| [`scripts/query-tools.sh`](scripts/query-tools.sh) | 检索可安装工具 |
| [`scripts/install-tool.sh`](scripts/install-tool.sh) | 预览/安装工具到业务项目 |

## 知识模块

| 模块 | 目录 |
|------|------|
| 前端 | `notes/frontend` |
| 后端 | `notes/backend` |
| 测试 | `notes/testing` |
| AI 工具 | `notes/ai-tools` |
| DevOps | `notes/devops` |
| 数据库 | `notes/database` |
| 架构 | `notes/architecture` |
| 其他 | `notes/misc` |

## 责任链一览

| ID | 名称 | 职责 |
|----|------|------|
| H01 | Intake | 解析输入，生成 ingest_id |
| H02 | Dedup | 去重，决定 create/merge |
| H03 | Research | 联网补充/核实 |
| H04 | Classify | 分配到模块 |
| H05 | Decompose | 拆为知识原子 |
| H06 | Structure | 按 Schema 结构化 |
| H07 | Persist | 写入 notes/ |
| H08 | Index | 更新 INDEX.md |
| H09 | CrossLink | 交叉引用 |
| H10 | Validate | 运行校验脚本 |
| H12 | Publish | 提交并推送到 Gitee |
| H11 | Report | 交付入库报告 |

详见 [`docs/WORKFLOW.md`](docs/WORKFLOW.md)。

## 维护

- 新增模块 → 改 `registry.yaml` + `MODULES.md` + `INDEX.md`
- 每篇笔记必须通过 `scripts/validate-note.sh`
- 校验通过后运行 `scripts/publish-ingest.sh` 推送到 `origin`
- 整合完成后 Agent 回复 ingest-report（含推送结果）

---

*最后更新：2026-06-08*
