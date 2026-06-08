# 知识消费工作流（跨项目）

> **执行 SSOT**：其他项目通过本流程**查询、推荐、安装**学习中心收录的工具。  
> **工具目录**：[`knowledge/tools-registry.yaml`](../knowledge/tools-registry.yaml)  
> **Skill**：`.cursor/skills/knowledge-consume/SKILL.md`  
> **环境变量**：`AI_LEARNING_CENTER`（默认本仓库根目录）

## 总览

```mermaid
flowchart LR
  U[用户在其他项目] --> C01
  C01[Query 检索] --> C02[Recommend 推荐]
  C02 --> C03[用户选择]
  C03 --> C04[Install 安装]
  C04 --> C05[Prompt 使用提示]
```

## 责任链

| ID | 名称 | 输入 | 输出 | 说明 |
|----|------|------|------|------|
| **C01** | Query 检索 | 关键词/意图 | 命中工具列表 + 分数 | `scripts/query-tools.sh` |
| **C02** | Recommend 推荐 | 检索结果 | 对比表 + 简介 + TL;DR | Agent 格式化呈现 |
| **C03** | Select 选择 | 用户回复 | `tool_id` + 可选 `method` | 必须等用户明确选择 |
| **C04** | Install 安装 | 选择 + 目标目录 | 安装报告 | 先 `--dry-run`，用户确认后 `--yes` |
| **C05** | Prompt 提示 | 用户场景描述 | `usage_prompt` 填好的任务模板 | 安装后交付 |

## 快捷命令

```
/kb-query [关键词]           # 只检索笔记与工具
/kb-recommend [意图]         # 检索 + 推荐对比（默认入口）
/kb-install [tool-id]        # 预览安装（dry-run）
/kb-install [tool-id] --yes  # 用户确认后执行
```

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
3. 更新 `docs/INDEX.md`
4. 运行 `scripts/query-tools.sh <关键词>` 验证可检索

## 与入库流程的关系

| 流程 | 方向 | 触发 |
|------|------|------|
| Ingest H01–H12 | 写入学习中心 | `/ingest`、收录 |
| Consume C01–C05 | 从学习中心读出并安装到业务项目 | `/kb-recommend`、`/kb-install` |
