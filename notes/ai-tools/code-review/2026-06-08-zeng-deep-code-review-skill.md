---
id: KB-AI-20260608-zeng-deep-code-review-skill
module: ai-tools
module_id: MOD-AI
topic: code-review
title: "zeng-code-review-deep：多智能体深度代码审查 Skill 设计"
source:
  type: paste
  url: "https://github.com/zengle22/zeng-skills"
  author: "可治理的智能体"
  accessed: "2026-06-08"
tags: [code-review, multi-agent, agent-skill, deep-review, fix-pass, audit, ai-coding, governance]
difficulty: advanced
status: active
related: [KB-AI-20260608-ai-review-quality-16-schemes, KB-AI-20260608-ai-code-review-next-wave-trend, KB-AI-20260608-ai-coding-era-review-upgrade, KB-ARCH-20260608-ai-business-code-review, KB-AI-20260608-ai-first-gate-review-experiment]
ingest_id: ING-20260608-016
updated: 2026-06-08
---

# zeng-code-review-deep：多智能体深度代码审查 Skill 设计

## TL;DR

- AI 写码提速后，稀缺能力变为**判断代码是否可信**；AI 代码常「表面完整」却存在未接入主路径、重复实现、mock 残留、吞错误、绕过类型等隐蔽风险。
- **zeng-code-review-deep**（[zeng-skills](https://github.com/zengle22/zeng-skills)）用**多 Agent 专项并行**替代单 Agent 泛审：智能选角 → 多维审查 → 去重仲裁 → 修复任务 → 独立审计 → 报告合成。
- **4 个必选维度**常驻（一致性、规范、功能逻辑、数据结构）；10+ 专项维度与语言专家（Python/TS/Go）按需激活，由 Selector 根据变更内容选角。
- 审查产物**全部落盘**（`reviews/*.json`、`fix-tasks.json`、`audit-report.json` 等），形成可追踪、可复盘治理链；**不默认自动改码**，输出结构化修复任务 + 可选补丁，人类确认后应用。
- 适合核心模块、安全敏感、大型 AI 生成 PR；日常小改仍用轻量 Review，发现高风险信号再升级 Deep Review。

## 适用场景

**何时用 Deep Review：**

- AI 生成的大型 PR 合并前；核心业务模块重构后。
- 权限、安全、支付、数据迁移相关变更。
- 前后端契约 / DTO 字段调整后；测试覆盖率高但对**测试可信度**存疑。
- 需要对照 FRZ/FEAT/AC 需求包做实现一致性验收。
- 团队希望审查从「聊天建议」升级为**可审计工程流程**。

**何时不用（改用轻量 Review）：**

- 文档小修、格式调整、配置微调等低风险变更。
- 每次保存都跑 Deep Review——调用成本与噪音不可持续。
- 仅需单文件 Prompt 扫描——见 [Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md)。

**与专题其他笔记：**

| 笔记 | 关系 |
|------|------|
| [16 方案](2026-06-08-ai-review-quality-16-schemes.md) | 本篇是方案 4（多模型）、5（结构化）、6（调用链）的**落地实例** |
| [下一波机会](2026-06-08-ai-code-review-next-wave-trend.md) | 战略：PR 入口治理；本篇：深度质量门实现 |
| [Review 升级](2026-06-08-ai-coding-era-review-upgrade.md) | AI 代码「表面合格」风险；本篇独立 **AI 代码风险** 维度 |
| [企业流水线](2026-06-08-ai-business-code-review.md) | Webhook+RAG 规模化；本篇偏 Agent Skill 本地/仓库内深度审查 |

## 知识要点

### 1. 传统 Review 的两类局限

| 方式 | 强项 | 弱项 |
|------|------|------|
| 人工 PR Review | 经验、业务判断 | 覆盖不稳定；Reviewer 关注点差异大 |
| 单 Agent 审查 | 快速扫明显问题 | 难同时保持十几维度专家敏感度 |

**审查-修复断点**：发现问题 → 聊天/评论建议 → 开发者自行理解修复 → **缺少系统性二次验证** → 结果难追踪、任务不明确、修复可能引入新问题。

### 2. AI 生成代码的特有风险形态

不是「质量差」，而是**看起来完整**：

| 风险模式 | 示例 |
|----------|------|
| 未接入 | 新函数无真实调用路径 |
| 重复实现 | 无视已有工具函数，签名不同行为分叉 |
| mock 残留 | 假配置、硬编码测试凭据进生产代码 |
| 假完成 | TODO 占位关键逻辑；只实现 happy path |
| 类型绕过 | `any`、断言、`unsafe` 逃避检查 |
| 资源泄漏 | 未关闭连接、句柄、监听器 |
| 调试残留 | `console.log` / `print` / `debugger` |
| 过度抽象 | 简单场景引入不必要复杂度 |

在 zeng-code-review-deep 中，**AI 代码风险**为独立审查维度，不与普通规范混谈。

### 3. 总体流水线

```text
智能选角 (Selector)
  ↓
多 Agent 并行专项审查
  ↓
去重合并 (Moderator)
  ↓
冲突仲裁 (Conflict-Arbiter)
  ↓
修复任务生成 (Fix Pass)
  ↓
独立审计 (Audit-Agent)
  ↓
最终报告合成 (final-report.md)
```

**输入模式**：

| 模式 | 用途 |
|------|------|
| `commit` | 单次提交审查 |
| `pr` | 分支对比审查 |
| `module` | 模块健康检查 |
| `frz` | 对照 FRZ/FEAT/AC 需求一致性 |

### 4. 多 Agent 专项审查（视角隔离）

**4 个必选维度**（任何变更必覆盖）：

1. **代码一致性** — 命名、架构分层、API 风格、重复代码、跨文件约定
2. **代码规范** — 类型注解、注释、imports、复杂度、文档字符串
3. **功能逻辑** — 业务正确性、边界、异常路径、状态转换
4. **数据结构** — 模型设计、类型安全、序列化、DTO/Entity/Schema 对齐

**按需激活的专家维度**：

并发安全 · 安全性 · UX · 性能 · 可维护性 · 可观测性 · 契约一致性 · **AI 代码风险** · 需求一致性 · 测试质量

**语言专家 Agent**（示例关注点）：

| 语言 | 典型审查点 |
|------|------------|
| Python | 可变默认参数、循环导入、异步上下文、None 处理 |
| TypeScript | `any` 逃逸、`as` 滥用、Promise 未 await、JSX key |
| Go | goroutine 泄露、channel 阻塞、nil interface、循环中 defer、error wrapping |

### 5. 智能选角（Selector）

避免每次全量跑所有维度——平衡调用成本、延迟与噪音。

| 变更信号 | 激活维度 |
|----------|----------|
| async/锁/channel/goroutine | 并发安全 |
| 认证/授权/用户输入/上传 | 安全 |
| `.tsx`/CSS/交互组件 | UX + TypeScript 专家 |
| API/DTO/OpenAPI/Protobuf | 契约一致性 |
| TODO/mock/重复实现/过度抽象 | AI 代码风险 |

原则：**基础四维常驻，专项维度按风险动态激活**。

### 6. 结构化落盘产物

| 文件 | 职责 |
|------|------|
| `role-panel.json` | 本次激活 Agent 与维度 |
| `reviews/*.json` | 各专项 Agent 独立输出 |
| `consolidated-review.json` | Moderator 合并去重 |
| `review-conflicts.json` | 严重级别或「是否为问题」分歧 |
| `review-consensus.json` | **权威问题清单** |
| `fix-tasks.json` | 结构化修复任务 |
| `audit-report.json` | 流程可信度审计 |
| `final-report.md` | 人类可读终稿 |

每个 issue 可追踪：来源维度、发现 Agent、代码位置、严重级别、是否进入修复、是否审计确认。

### 7. Fix Pass：审查连接修复

每个修复任务含：问题 ID、严重级别、文件行号、描述、**修复策略**、是否可自动补丁、影响测试、验证命令、预估工作量。

**修复策略类型**：最小改动（guard/分支）· 重构 · 增测 · 更新契约 · 删除死代码/重复/调试代码。

**重要取舍**：生成任务 + **可选补丁**，**不默认应用**——业务逻辑、安全、契约类问题须人类确认。

### 8. 独立审计（Audit-Agent）

**不共享**前序 Agent 对话上下文，只读磁盘产物，审计**治理链**而非重新审代码：

- 产物是否完整；issue ID 是否连续
- P0/P1 是否都有修复任务；冲突是否有处理记录
- 人工决策是否正确应用；终稿是否覆盖共识清单

关注：「这次 Code Review 的流程是否可信」——从 AI 辅助审查走向 **AI 审查治理**。

### 9. 分层审查分工

```text
日常小变更 / 文档 / 配置微调     → 轻量 Code Review
核心模块 / 安全 / AI 大 PR       → zeng-code-review-deep
轻量审查发现高风险信号           → 升级到 Deep Review
```

### 10. 工具 / 资源清单

| 工具 | 类型 | 说明 |
|------|------|------|
| [zeng-skills](https://github.com/zengle22/zeng-skills) | Agent Skill 仓库 | 含 `zeng-code-review-deep` 等多智能体 Skill |
| [zeng-code-review-deep](https://github.com/zengle22/zeng-skills) | Agent Skill | 多 Agent 深度审查 + 修复任务 + 独立审计 |

## 代码 / 命令

### 典型触发方式

```bash
# 审查最近一次提交
zeng-code-review-deep --mode commit --ref HEAD~1

# 审查 PR 分支
zeng-code-review-deep --mode pr --base main --head feature/x

# 审查核心模块
zeng-code-review-deep --mode module --path src/services/order/

# 对照需求包做实现一致性审查
zeng-code-review-deep --mode frz --frz-ref FRZ-20260521-001 --path src/services/order/
```

### 引入 Skill（Cursor / 支持 Skill 的 Agent 环境）

```bash
# 将仓库作为 Skill 来源（路径按本地克隆调整）
git clone https://github.com/zengle22/zeng-skills.git ~/.cursor/skills/zeng-skills
# 在 Agent 中引用 zeng-code-review-deep skill 后对目标仓库触发审查
```

### fix-tasks.json 字段示例（概念结构）

```json
{
  "tasks": [
    {
      "issue_id": "CR-001",
      "severity": "P0",
      "file": "src/services/order.ts",
      "line": 42,
      "strategy": "minimal_fix",
      "description": "订单状态绕过状态机直接赋值",
      "patch_optional": true,
      "verify_cmd": "npm test -- order.state",
      "effort": "S"
    }
  ]
}
```

## 注意事项

- Deep Review **成本高**，应作为高风险质量门，非默认全量流程。
- 多 Agent 并行依赖 Skill 运行时支持子 Agent 调度；落地前确认环境能力。
- 自动补丁仅作参考，合入前须人工 diff 审核，尤其业务与安全类。
- GitHub 仓库较新（公开信息有限），具体 Agent 提示词与目录结构以仓库 `SKILL.md` 为准。
- 与 [企业 Webhook 流水线](2026-06-08-ai-business-code-review.md) 可互补：流水线做 MR 触发与通知，Deep Skill 做仓库内深度多维审查。

## 相关链接

- 原文：可治理的智能体《一个 skill 全方位审核 AI 写的代码：多智能体 Deep Code Review Skill 的设计》（用户粘贴，2026-06-08）
- 仓库：[zeng-skills](https://github.com/zengle22/zeng-skills)
- 项目内：[16 个提升评审质量方案](2026-06-08-ai-review-quality-16-schemes.md)（`KB-AI-20260608-ai-review-quality-16-schemes`）
- 项目内：[AI Code Review 下一波机会](2026-06-08-ai-code-review-next-wave-trend.md)（`KB-AI-20260608-ai-code-review-next-wave-trend`）
- 项目内：[AI 编程时代 Review 升级](2026-06-08-ai-coding-era-review-upgrade.md)（`KB-AI-20260608-ai-coding-era-review-upgrade`）
- 项目内：[业务级 AI Code Review 流水线](2026-06-08-ai-business-code-review.md)（`KB-ARCH-20260608-ai-business-code-review`）
- 项目内：[AI 第一道 Review 实验](2026-06-08-ai-first-gate-review-experiment.md)（`KB-AI-20260608-ai-first-gate-review-experiment`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 初稿（ING-20260608-016），整合 zeng-code-review-deep 多智能体深度审查 Skill 设计 |
