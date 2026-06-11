# AI 学习中心 · Claude Code 指令

> 本仓库是**结构化知识库（Knowledge Base）**，不是应用代码仓库。
> 你的首要职责：**按责任链将用户提供的知识入库**。

## 第一优先级

用户消息涉及「整合 / 收录 / 入库 / 文章 / 学习笔记 / /ingest」时：
1. **立即读取** `AGENTS.md` 与 `docs/WORKFLOW.md`
2. **执行**责任链 H01→H12（详见下文 Skill 路由）
3. **不可跳过** H10 Validate；H12 默认自动 commit + push（用户显式 `--no-push` 除外）

用户消息涉及「查询 / 有没有 / 搜索笔记」时：
- 仅执行 H02 Dedup，**不写文件**

用户消息涉及「/kb-recommend / /kb-install / 从学习中心找工具 / 推荐工具并安装」时：
1. 读 `docs/CONSUME.md`
2. 执行 C01→C05；**C03 必须等用户选择后再安装**

用户消息涉及「/kb-publish / -redbook / -wechat / -taobao / -xianyu / 生成小红书 / 闲鱼商品」时：
1. 读 `docs/PUBLISH.md`
2. 执行 P01→P07→P06；默认写入 `publish/` 并 P07 推送（用户 `--no-push` / `--no-save` 除外）

## 回购路径

本仓库路径：`/Users/admin/Desktop/spider_project/ai-study-center`

所有脚本以仓库根目录为工作目录执行。

## SSOT 文件

| 用途 | 路径 |
|------|------|
| Agent 入口 | `AGENTS.md` |
| 责任链 SSOT | `docs/WORKFLOW.md` |
| 模块注册 | `knowledge/registry.yaml` + `docs/MODULES.md` |
| 笔记 Schema | `docs/KNOWLEDGE_SCHEMA.md` |
| 入库 Skill | `.claude/skills/knowledge-ingest/SKILL.md` |
| 消费 Skill | `.claude/skills/knowledge-consume/SKILL.md` |
| 发布 Skill | `.claude/skills/knowledge-publish/SKILL.md` |
| 工具目录 | `knowledge/tools-registry.yaml` |
| 消费工作流 | `docs/CONSUME.md` |
| 发布工作流 | `docs/PUBLISH.md` |
| 平台规范 | `knowledge/platforms-registry.yaml` |
| 总索引 | `docs/INDEX.md` |

## 产出约束

- 笔记 → `notes/{module}/`（8 模块，见 registry.yaml）
- 每篇必须有 YAML frontmatter + TL;DR + 适用场景
- 入库后必须更新 INDEX + 运行 `scripts/validate-note.sh` + `scripts/publish-ingest.sh`
- 中文撰写，技术术语保留英文

## 禁止

- 跳过责任链 Handler
- 整篇搬运原文
- 引入 package.json / Docker 等运行时（除非用户明确要求）
- 修改本仓库外的项目
- 入库含密钥的内容

## 快捷指令

```
/ingest [URL或正文] [--module frontend]
/query [关键词]
/kb-recommend [意图]
/kb-install [tool-id]
/kb-publish -redbook @notes/...
/kb-publish -wechat @notes/...
/kb-publish -taobao @notes/...
/kb-publish -xianyu @notes/...
```
