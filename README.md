# AI 学习中心

> **结构化个人知识库** — 责任链工作流驱动的学习笔记仓库。

## 快速开始

**在 Cursor 中打开本文件夹**，然后：

```
/ingest https://example.com/article     # 收录文章（全链路 H01→H12，含自动推送）
/ingest --module frontend [粘贴正文]      # 指定模块入库
/query playwright                         # 只查已有笔记（本仓库内）
/kb-publish -redbook @notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md  # 笔记→小红书
/kb-publish -wechat @notes/.../xxx.md   # 笔记→公众号
/kb-publish -taobao @notes/.../xxx.md   # 笔记→淘宝商品
/kb-publish -xianyu @notes/.../xxx.md   # 笔记→闲鱼 listing
```

**在任意其他项目中**（需全局 Skill `ai-learning-center-consume`）：

```
/kb-workflow 开发前端界面       # ★ 完整方法论+工具链+可复用 Prompt
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
业务项目 /kb-workflow → kb-workflow.sh → 分阶段 playbook + install + Prompt
业务项目 /kb-recommend → query-tools.sh → 用户选择 → install-tool.sh → usage_prompt
```

## 目录

| 路径 | 作用 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | Agent 入口指令 |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | **责任链 SSOT**（H01–H12） |
| [`docs/MODULES.md`](docs/MODULES.md) | 9 大知识模块 |
| [`docs/KNOWLEDGE_SCHEMA.md`](docs/KNOWLEDGE_SCHEMA.md) | 笔记 Schema |
| [`knowledge/registry.yaml`](knowledge/registry.yaml) | 模块机器可读注册表 |
| [`knowledge/tools-registry.yaml`](knowledge/tools-registry.yaml) | 可安装工具目录 |
| [`knowledge/workflows-registry.yaml`](knowledge/workflows-registry.yaml) | 方法论工作流 SSOT（手工编排） |
| [`knowledge/workflow-ingest-sync.yaml`](knowledge/workflow-ingest-sync.yaml) | 入库自动同步层（H13） |
| [`knowledge/workflow-sync-rules.yaml`](knowledge/workflow-sync-rules.yaml) | 入库→方法论映射规则 |
| [`knowledge/tools-catalog.yaml`](knowledge/tools-catalog.yaml) | **工具总表 SSOT**（汇总查询） |
| [`docs/CONSUME.md`](docs/CONSUME.md) | 跨项目消费 SSOT（C01–C05） |
| [`docs/PUBLISH.md`](docs/PUBLISH.md) | 笔记 → 平台发布 SSOT（P01–P06） |
| [`.cursor/skills/knowledge-ingest/`](.cursor/skills/knowledge-ingest/) | 入库 Skill |
| [`.cursor/skills/knowledge-consume/`](.cursor/skills/knowledge-consume/) | 消费 Skill |
| [`.cursor/skills/knowledge-publish/`](.cursor/skills/knowledge-publish/) | 发布 Skill |
| [`.cursor/rules/`](.cursor/rules/) | 全局 + 流水线规则 |
| [`notes/`](notes/) | 知识正文（9 模块） |
| [`scripts/validate-note.sh`](scripts/validate-note.sh) | 笔记校验工具 |
| [`scripts/publish-ingest.sh`](scripts/publish-ingest.sh) | 入库后自动 commit + push |
| [`scripts/query-tools.sh`](scripts/query-tools.sh) | 检索可安装工具 |
| [`scripts/install-tool.sh`](scripts/install-tool.sh) | 预览/安装工具到业务项目 |
| [`scripts/kb-publish.sh`](scripts/kb-publish.sh) | 笔记 → 平台发布 brief |
| [`scripts/publish-content.sh`](scripts/publish-content.sh) | 发布成稿后自动 commit + push |
| [`knowledge/platforms-registry.yaml`](knowledge/platforms-registry.yaml) | 小红书/公众号/淘宝/闲鱼规范 |
| [`publish/`](publish/) | 发布成稿输出目录 |

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
| 爬虫 | `notes/crawler` |
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

## 跨项目消费（完整指引）

> 详细 SSOT：[`docs/CONSUME.md`](docs/CONSUME.md)

### 什么时候用

| 场景 | 在哪执行 | 命令 |
|------|----------|------|
| 收录文章/技巧到知识库 | 任意项目 | `/ingest`（全局 Skill `ai-learning-center-ingest`） |
| 查已有笔记 | 本仓库或任意项目 | `/query` |
| 找工具 + 对比推荐 | **业务项目** | `/kb-recommend`（全局 Skill `ai-learning-center-consume`） |
| 安装选中的工具 | **业务项目** | `/kb-install` |

### 消费责任链 C01–C05

| ID | 步骤 | 说明 |
|----|------|------|
| C01 | Query | 检索 `tools-registry.yaml` + 笔记 TL;DR |
| C02 | Recommend | 罗列相似结果 + 简介对比，**等你选择** |
| C03 | Select | 你回复序号或 tool id |
| C04 | Install | 先预览（dry-run），确认后 `--yes` 执行 |
| C05 | Prompt | 输出填好场景的 `usage_prompt` |

### 对话命令（在业务项目里）

```
/kb-recommend 好看的前端界面     # 检索 + 推荐对比
/kb-query anti-slop              # 只检索，不推荐、不安装

# 你选完之后：
/kb-install taste-skill          # 预览将执行的安装命令
/kb-install taste-skill --yes    # 你明确确认后再装
```

**推荐交互示例：**

1. 你说：`/kb-recommend 好看的前端界面`
2. Agent 列出 Taste Skill、impeccable 等候选并对比
3. 你回复：`选 1，帮我预览安装` 或 `装 taste-skill，做 B2B SaaS 落地页`
4. Agent 先展示 dry-run，你说 `确认安装` 后执行
5. Agent 给你可复制到任务里的 Prompt 模板

### 脚本命令（终端直接跑）

```bash
# 环境变量（可选，默认即本仓库路径）
export AI_LEARNING_CENTER=/Users/alu0901/AI-Agent/AI-Learning-Center

# 检索工具
scripts/query-tools.sh "好看的前端界面"
scripts/query-tools.sh "anti-slop" --json

# 预览安装（默认不执行）
scripts/install-tool.sh taste-skill --target /path/to/your-app
scripts/install-tool.sh taste-skill --method npx-v1 --target .

# 确认后安装，并带入场景描述
scripts/install-tool.sh taste-skill --yes --target . --prompt "做 B2B SaaS 技术向落地页"

# impeccable 需先下载 ZIP 并设置 dist 路径
export IMPECCABLE_DIST=/path/to/impeccable-unzip/dist
scripts/install-tool.sh impeccable --agent cursor --method cursor-project --yes --target .
```

### 全局 Skill 安装位置

| Skill | 路径 | 作用 |
|-------|------|------|
| `ai-learning-center-ingest` | `~/.cursor/skills/ai-learning-center-ingest/` | 跨项目**写入**学习中心 |
| `ai-learning-center-consume` | `~/.cursor/skills/ai-learning-center-consume/` | 跨项目**查询/推荐/安装** |

本仓库内还有本地 Skill：`.cursor/skills/knowledge-ingest/`、`.cursor/skills/knowledge-consume/`。

### 新增可安装工具

1. 笔记入库 `notes/{module}/`（`/ingest`）
2. 在 [`knowledge/tools-registry.yaml`](knowledge/tools-registry.yaml) 添加 `intents`、`keywords`、`install.methods`
3. 验证：`scripts/query-tools.sh "你的关键词"`

## 维护

- 新增模块 → 改 `registry.yaml` + `MODULES.md` + `INDEX.md`
- 每篇笔记必须通过 `scripts/validate-note.sh`
- 校验通过后运行 `scripts/publish-ingest.sh` 推送到 `origin`（Gitee：`https://gitee.com/DestOwen/ai-study-center.git`）
- 整合完成后 Agent 回复 ingest-report（含推送结果）
- 新增可安装工具 → 同步 `tools-registry.yaml`（见上文）

---

*最后更新：2026-06-08*
