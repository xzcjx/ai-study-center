---
id: KB-AI-20260608-ai-first-gate-review-experiment
module: ai-tools
module_id: MOD-AI
topic: code-review
title: "AI 第一道 Code Review 两个月实验：数据、副作用与规则调整"
source:
  type: paste
  url: "internal"
  accessed: "2026-06-08"
tags: [code-review, team-process, ai-coding, claude, human-review, review-atrophy, pr-workflow]
difficulty: intermediate
status: active
related: [KB-AI-20260608-ai-coding-era-review-upgrade, KB-AI-20260608-ai-code-review-workflow-methodology, KB-AI-20260608-ai-code-review-prompt-guide, KB-ARCH-20260608-ai-business-code-review]
ingest_id: ING-20260608-013
updated: 2026-06-08
---

# AI 第一道 Code Review 两个月实验：数据、副作用与规则调整

## TL;DR

- 5 人团队实验：**PR 必须先过 AI Review**，原文贴进 PR 描述，人工 reviewer 标注 AI 意见对错——不是替代人工，而是**第一道筛选**。
- 两个月 **209 个 PR**，AI 标注 **344 条**问题；人工确认 **214 条有效（62%）**，其中约 **60 条（28%）** 若无 AI 大概率被人工漏掉（含 2 条安全、1 条并发幂等）。
- 三大副作用：**AI「通过」成免责牌**、提交者「AI 建议这么写」而不自检、团队对 AI 信任两极（全拒 vs 全收）。
- 意外发现：资深成员感到 **Review 能力退化**——从「主动发现问题」变成「评判 AI 清单」，心智模型构建变弱。
- 调整后规则：每周 ≥2 个 PR **先独立人工 Review 再对比 AI**；AI 意见分严重/中/低三级处理，低级忽略须在 PR 说明原因。
- 固定 Prompt 聚焦 bug / 安全 / 性能 / 业务逻辑；与 [方法论](2026-06-08-ai-code-review-workflow-methodology.md)、[企业流水线](2026-06-08-ai-business-code-review.md) 互补。

## 适用场景

**何时用：**

- 小团队（约 5 人）每周 30–40 PR，人工 Review 时间碎片化、质量参差，想用 AI 做**系统性初筛**。
- 愿意用 **2 个月实验 + 数据统计** 验证 AI 第一道关是否值得继续，而非一次性上企业流水线。
- 需要可复制流程：统一 Prompt、AI 结论原文进 PR、人工标注对错作为反馈数据。

**何时不用：**

- 已有 GitLab Webhook + RAG 全自动审计——见 [业务级流水线](2026-06-08-ai-business-code-review.md)。
- 团队无法接受「人工责任不随 AI 通过而减轻」——本实验明确禁止把 AI OK 当免责。
- 无专人复盘副作用（能力退化、信任分裂）——实验可能放大组织风险。

## 知识要点

### 1. 背景与动机

| 现状 | 痛点 |
|------|------|
| 5 人，周 30–40 PR | 认真 Review 单 PR 约 15–30 分钟 |
| 指定 reviewer → approve | 周 Review 负荷 10–15 小时，主业并行 |
| 质量参差不齐 | 多数时候「扫一眼，能跑就行」 |

假设：AI **秒级 + 系统性覆盖** 作第一道，人工聚焦 AI 难以判断的**需求与业务**。

### 2. 实验规则（三条）

**规则 1 — 提 PR 前强制 AI Review**（统一 Claude + 固定 Prompt）：

```text
请对以下代码变更做 Code Review，重点关注：
1. 潜在 bug（空指针、并发、边界条件）
2. 安全风险
3. 性能问题（N+1、大循环）
4. 业务逻辑是否合理

对每个问题说明严重程度（严重/中/低）和修改建议。
如果没有问题，直接说「未发现明显问题」。

[粘贴 diff]
```

**规则 2 — AI 意见原文贴进 PR 描述**  
不允许提交者自行过滤，人工 reviewer 可见完整 AI 输出。

**规则 3 — 人工标注 AI 意见对错**  
记录哪些有效、哪些误判——成为后续最有价值的原始数据。

### 3. 两个月数据

| 指标 | 数值 |
|------|------|
| PR 总数 | 209 |
| AI 标注问题 | 344 条 |
| 人工确认有效 | 214 条（62%） |
| 误判或不适用 | 130 条（38%） |
| 有效中人工大概率会漏 | ~60 条（占有效 28%，约每 3–4 PR 1 条） |
| 高影响漏网 | 2 条安全 + 1 条并发幂等（潜在资损级） |

**结论**：有真实兜底价值，但须正视 38% 噪声与组织副作用。

### 4. 坑 1：AI 通过 = 免责牌

案例：AI 称「未发现明显问题」→ reviewer 备注「AI 过了」即 approve → 实际**漏需求点**（非 bug，需求文档约束 AI 不知）。

**对策**：明确规定 **AI 结论不减人工责任**；AI 说没问题，人仍须认真看。改善但未完全消失。

### 5. 坑 2：懒得自己想

提交者答「AI 建议这么写的」却无法解释合理性；代码 **AI 痕迹** 加重（结构、注释、命名趋同），**个人判断**减少。

### 6. 坑 3：信任度两极

| 类型 | 行为 | 风险 |
|------|------|------|
| 完全不信任 | 逐条反驳 AI，部分出于抵触 | 那 60 条漏网在其 PR 仍可能漏 |
| 完全信任 | 照单全收，如低频接口也加 Caffeine | 不必要复杂度 |

团队对「AI 意见几分可信」长期无共识。

### 7. 意外变化：Review 能力退化

资深成员反馈：习惯变成**先看 AI 发现了什么，再判断对错**，而非从头到尾自建心智模型找问题。

- 以前：主动发现（构建完整逻辑图景）
- 现在：被动评判（对错判断）

长期是否萎缩主动发现能力——**未知但可感知**，类似计算器与导航对心算、记路的影响。

### 8. 复盘后规则调整（继续 AI，加码约束）

**约束 A — 肌肉保持**  
每人每周至少 **2 个 PR**：必须先**独立完成人工 Review**，再看 AI 结论并对比。

**约束 B — 三级处理 AI 意见**

| 级别 | 处理 |
|------|------|
| 严重 | 人工必须确认，不可跳过 |
| 中等 | 人工判断是否适用，**须留理由** |
| 低级 | 可忽略，但 PR 中**说明原因** |

目的：保持人的判断，而非被 AI 清单牵着走。

新规则跑两周后，团队反馈「更健康一些」；成本是 Review 时间增加（先人工再对比再处理差异）。

### 9. 与专题其他笔记的关系

| 笔记 | 关系 |
|------|------|
| [Review 升级](2026-06-08-ai-coding-era-review-upgrade.md) | 五维 Prompt、表面合格、老代码 Review |
| [方法论](2026-06-08-ai-code-review-workflow-methodology.md) | 作者自查、分层检查、PR 描述——可叠在实验**之前** |
| [Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md) | 更多模板与 Codacy/Sonar 集成 |
| [企业流水线](2026-06-08-ai-business-code-review.md) | 规模化 Webhook+RAG，可替代手工贴 diff |

本实验是 **轻量组织流程**，适合验证「第一道 AI 关」是否值得投资自动化。

### 10. 作者结论（观察）

- **价值真实**：60 条漏网之鱼是兜底，尤其安全与并发类。
- **副作用真实**：不思考、能力退化感、信任分裂——**使用方式**问题，非工具本身。
- 工具越好用，越易停止锻炼被替代的能力；失去常在**无察觉**中发生。

## 代码 / 命令

### PR 描述模板（含 AI 原文）

```markdown
## AI Code Review（Claude，提 PR 前）

[粘贴 AI 完整输出，不得删改]

## 人工 Review 记录（Reviewer 填写）

| AI 条目 | 判定（有效/误判/不适用） | 说明 |
|---------|---------------------------|------|
| … | … | … |
```

### 每周「先人工后 AI」自查

对指定 PR 在对话中先完成：

```text
我先独立 Review 以下 diff，不参考 AI。请在我完成后，再给出你的 Review 供对比。
[diff]
```

## 注意事项

- 数据来自 **5 人团队 2 个月** 样本，外推需结合规模与业务。
- 「62% 有效 / 38% 误判」依赖 reviewer 标注质量，存在主观性。
- 实验用 Claude + 手工贴 diff；规模化应迁 [Webhook 流水线](2026-06-08-ai-business-code-review.md)。
- 评论指出：人工 + AI 对比 **增加时间与成本**——需与漏网损失权衡。
- 业务逻辑合理性在 Prompt 中列出，但 AI **仍不知需求文档**——人工必须覆盖需求完整性。

## 相关链接

- 项目内：[AI 编程时代 Review 升级](2026-06-08-ai-coding-era-review-upgrade.md)（`KB-AI-20260608-ai-coding-era-review-upgrade`）
- 项目内：[AI Code Review 方法论](2026-06-08-ai-code-review-workflow-methodology.md)（`KB-AI-20260608-ai-code-review-workflow-methodology`）
- 项目内：[AI Code Review Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md)（`KB-AI-20260608-ai-code-review-prompt-guide`）
- 项目内：[业务级 AI Code Review 流水线](2026-06-08-ai-business-code-review.md)（`KB-ARCH-20260608-ai-business-code-review`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 初稿（ING-20260608-013），整合 AI 第一道 Review 两个月团队实验复盘 |
