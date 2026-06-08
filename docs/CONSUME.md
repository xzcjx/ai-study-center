# 知识消费工作流（跨项目）

> **执行 SSOT**：其他项目通过本流程**查询、推荐、安装**学习中心收录的工具。  
> **工具目录**：[`knowledge/tools-registry.yaml`](../knowledge/tools-registry.yaml)  
> **Skill**：`.cursor/skills/knowledge-consume/SKILL.md`  
> **环境变量**：`AI_LEARNING_CENTER`（默认本仓库根目录）

## 总览

```mermaid
flowchart LR
  U[用户在其他项目] --> C00
  C00[Workflow 方法论] --> C01
  C01[Query 检索] --> C02[Recommend 推荐]
  C02 --> C03[用户选择]
  C03 --> C04[Install 安装]
  C04 --> C05[Prompt 使用提示]
```

## 责任链

| ID | 名称 | 输入 | 输出 | 说明 |
|----|------|------|------|------|
| **C00** | Workflow 方法论 | 场景描述 | 完整 playbook + 工具链 + Prompt | `scripts/kb-workflow.sh`（**推荐首选**） |
| **C01** | Query 检索 | 关键词/意图 | 命中工具列表 + 分数 | `scripts/query-tools.sh` |
| **C02** | Recommend 推荐 | 检索结果 | 对比表 + 简介 + TL;DR | Agent 格式化呈现 |
| **C03** | Select 选择 | 用户回复 | `tool_id` + 可选 `method` | 必须等用户明确选择 |
| **C04** | Install 安装 | 选择 + 目标目录 | 安装报告 | 先 `--dry-run`，用户确认后 `--yes` |
| **C05** | Prompt 提示 | 用户场景描述 | `usage_prompt` 填好的任务模板 | 安装后交付 |

## 快捷命令

```
/kb-workflow [场景]          # 生成完整方法论（工具+流程+Prompt）★ 首选
/kb-query [关键词]           # 只检索笔记与工具
/kb-recommend [意图]         # 检索 + 推荐对比
/kb-install [tool-id]        # 预览安装（dry-run）
/kb-install [tool-id] --yes  # 用户确认后执行
```

## C00 · Workflow 方法论（首选）

一条命令交付**可复用 playbook**：场景路由 → 分阶段 checklist → 工具安装命令 → 一键 Agent Prompt。

```bash
# 通用前端（自动路由到子工作流或完整管线）
scripts/kb-workflow.sh "开发前端界面" --target /path/to/project

# 明确场景
scripts/kb-workflow.sh "优化丑组件" --target . --stack "Vue 3" --target-files "src/components/Foo.vue"

# 仅复制 Prompt（不用反复写提示词）
scripts/kb-workflow.sh "做落地页" --prompt-only --brief "B2B SaaS 技术向首页"

# JSON 供 Agent 解析
scripts/kb-workflow.sh "参考 aura 改版" --json

# 列出全部工作流
scripts/kb-workflow.sh --list
```

**SSOT**：
- 手工编排：[`knowledge/workflows-registry.yaml`](../knowledge/workflows-registry.yaml)
- 入库自动层：[`knowledge/workflow-ingest-sync.yaml`](../knowledge/workflow-ingest-sync.yaml)（**H13 产出**）
- 映射规则：[`knowledge/workflow-sync-rules.yaml`](../knowledge/workflow-sync-rules.yaml)

**入库即进方法论**：每次 `/ingest` 完成 H13 后，新笔记自动写入 sync 层，`/kb-workflow` 下一命令即可命中。  
**与工具联动**：`tool_refs` 实时读取 `tools-registry.yaml`；新工具入库时按 intents 自动挂到对应 workflow 阶段。

### 工具总表 SSOT（推荐）

[`knowledge/tools-catalog.yaml`](../knowledge/tools-catalog.yaml) — **所有工具/网站**一张表维护：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `name` | 显示名 |
| `category` | skills / apps / mcp / reference-site / workflow / … |
| `positioning` | 一句话定位 |
| `summary` | 干什么、何时用 |
| `tags` | 检索标签 |
| `homepage` | 链接 |
| `installable` + `registry_id` | 可安装项联动 `tools-registry.yaml` |
| `kb_notes` | 深度阅读笔记路径 |

`/kb-recommend 前端工具汇总` **优先读总表**，不再从笔记表格临时解析。

入库 **H13b**（`sync-catalog.sh`）自动：笔记表格中新工具 → 追加总表草稿；registry 工具 → 关联 `kb_notes`。

**内置工作流**：

| ID | 场景 |
|----|------|
| `fe-full-pipeline` | 前端总管线（自动分流 A/B/C/D） |
| `fe-polish-existing` | 已有组件迭代抛光 |
| `fe-from-scratch` | 从零生成页面 |
| `fe-redesign-reference` | aura.build 参考克隆 |
| `fe-demo-shell` | Gemini 壳层 + Agent 业务 |

Agent 必须用 [`templates/workflow-report.md`](../templates/workflow-report.md) 呈现，并维护阶段勾选进度。

## C01 · Query

```bash
scripts/query-tools.sh "好看的前端界面"
scripts/query-tools.sh "anti-slop" --json
```

搜索范围：
1. `knowledge/tools-registry.yaml`（intents / keywords / 别名）
2. 关联 `notes/` 笔记 TL;DR

## C02 · Recommend

Agent 必须：
- 罗列**全部相似结果**（≥2 时做对比，不只推荐一个）
- 每条含：简介、匹配分、支持 Agent、安装方式、常搭配工具
- 标注**默认安装 method**
- 提示组合方案（如 taste-skill + impeccable）

使用模板：[`templates/recommend-report.md`](../templates/recommend-report.md)

## C03 · Select

**禁止**未经用户选择直接安装。

用户可说：
- `选 1` / `装 taste-skill`
- `用 npx-v1 方法`
- `两个都装，先 taste 再 impeccable`

## C04 · Install

```bash
# 预览（默认）
scripts/install-tool.sh taste-skill --target /path/to/user/project

# 指定 Agent 类型与安装方法
scripts/install-tool.sh impeccable --agent cursor --method cursor-project --target .

# 用户确认后执行，并带入场景 prompt
scripts/install-tool.sh taste-skill --yes --target . --prompt "做 B2B SaaS 技术向落地页"
```

规则：
- `--target` 默认为**用户当前打开的项目根目录**（非学习中心）
- `impeccable` 需先设置 `IMPECCABLE_DIST` 指向 ZIP 解压后的 `dist/`
- `manual` 类型只输出步骤，不执行 shell
- 安装失败不修改学习中心笔记

## C05 · Prompt

安装成功后，从 registry 读取 `usage_prompt`，将用户场景填入模板，作为可复制的 Agent 任务。

## 跨项目配置

### 环境变量

```bash
export AI_LEARNING_CENTER=/Users/alu0901/AI-Agent/AI-Learning-Center
```

### 全局 Skill

`~/.cursor/skills/ai-learning-center-consume/SKILL.md` — 在任意工作区触发 `/kb-recommend` 等命令。

### 新增可安装工具

1. 入库笔记 `notes/{module}/`
2. 在 `knowledge/tools-registry.yaml` 添加条目（intents、keywords、install.methods）
3. 在 `knowledge/workflows-registry.yaml` 的对应阶段 `tool_refs` 中引用（如有适用场景）
4. 更新 `docs/INDEX.md`
5. 运行 `scripts/query-tools.sh <关键词>` 与 `scripts/kb-workflow.sh "<场景>"` 验证

### 新增方法论工作流

1. 入库 playbook 笔记 `notes/{module}/`
2. 在 `knowledge/workflows-registry.yaml` 添加 `workflows` 条目（phases、tool_refs、playbook_notes）
3. 可选：在 `routers` / `workflow_aliases` 增加路由
4. 运行 `scripts/kb-workflow.sh --list` 验证

## 与入库流程的关系

| 流程 | 方向 | 触发 |
|------|------|------|
| Ingest H01–H12 | 写入学习中心 | `/ingest`、收录 |
| Consume C00–C05 | 从学习中心读出方法论并安装到业务项目 | `/kb-workflow`、`/kb-recommend`、`/kb-install` |
