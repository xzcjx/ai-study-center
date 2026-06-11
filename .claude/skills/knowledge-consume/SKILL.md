---
name: knowledge-consume
description: >-
  从 AI 学习中心跨项目查询、推荐并安装工具（C01–C05）。
  检索 tools-registry + 笔记，罗列相似结果供用户选择，确认后安装到当前项目。
  Use when user says /kb-workflow, /kb-query, /kb-recommend, /kb-install, 推荐工具,
  安装技能, 好看的前端, 从学习中心找工具, 方法论, 最佳实践流程.
---

# Knowledge Consume · 跨项目消费

## 仓库路径

本仓库路径（`KB`）：`/Users/admin/Desktop/spider_project/ai-study-center`

**查询与安装脚本在学习中心**；`--target` 指向**用户当前业务项目**。

## 责任链 checklist

```
消费 {query}
- [ ] C00 Workflow   → scripts/kb-workflow.sh（首选：完整方法论+Prompt）
- [ ] C01 Query      → scripts/query-tools.sh
- [ ] C02 Recommend  → templates/recommend-report.md
- [ ] C03 Select     → 等待用户选择（禁止跳过）
- [ ] C04 Install    → scripts/install-tool.sh（先预览，--yes 执行）
- [ ] C05 Prompt     → 输出 usage_prompt + 用户场景
```

## C00 Workflow（首选）

用户说「开发前端」「怎么做」「最佳实践」「完整流程」→ **先跑工作流**，不只推荐单个工具。

```bash
{KB}/scripts/kb-workflow.sh "{场景}" --target "{用户项目根}" [--stack] [--brief] [--prompt-only]
```

1. 用 `templates/workflow-report.md` 呈现
2. 维护阶段 W01–W05 勾选进度
3. 按 playbook 中的 `install_commands` 引导 C04 安装
4. 将 `agent_prompt_bundle` 作为 C05 交付（用户无需手写 Prompt）

## C01 Query

```bash
{KB}/scripts/query-tools.sh "{关键词}" [--json]
```

**汇总模式**（查询含 `汇总`/`导航`/`有哪些`/`大全`）：
- 同时检索 `notes/` 目录表（如 Awesome 清单 37 项）
- 区分 **可安装**（`/kb-install`）与 **参考资源**（手动访问）

## C02 Recommend

1. 运行 query，获取全部命中（相似工具全部罗列）
2. 读命中笔记 TL;DR（query 输出已含）
3. 用 `templates/recommend-report.md` 格式化
4. 有 `pairs_with` 时提示组合方案

## C03 Select

用户未明确选择前 **不得** 执行安装。

## C04 Install

```bash
# 预览
{KB}/scripts/install-tool.sh {tool-id} --target "{用户项目根}" [--agent cursor] [--method ID]

# 用户确认后
{KB}/scripts/install-tool.sh {tool-id} --yes --target "{用户项目根}" --prompt "{用户场景}"
```

- `impeccable`：提醒设置 `IMPECCABLE_DIST`
- `manual` 方法：只展示步骤

## C05 Prompt

安装成功后，输出 registry 中的 `usage_prompt`，并入用户描述。

## 只读查询

`/kb-query` → 仅 C01，不推荐、不安装。

## SSOT

- `docs/CONSUME.md`
- `knowledge/tools-registry.yaml`
