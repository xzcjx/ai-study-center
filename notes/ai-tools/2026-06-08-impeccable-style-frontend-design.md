---
id: KB-AI-20260608-impeccable-style-frontend-design
module: ai-tools
module_id: MOD-AI
title: "impeccable.style：用设计词典与斜杠命令对抗 AI 前端 Slop"
source:
  type: url
  url: "https://github.com/pbakaus/impeccable"
  accessed: "2026-06-08"
tags: [impeccable, frontend-design, anti-slop, cursor, agent-skill, slash-commands, paul-bakaus]
difficulty: beginner
status: active
related: [KB-AI-20260608-taste-skill-agent-frontend, KB-AI-20260608-awesome-ai-tools-for-ui]
ingest_id: ING-20260608-003
updated: 2026-06-08
---

# impeccable.style：用设计词典与斜杠命令对抗 AI 前端 Slop

## TL;DR

- **impeccable.style** 是开源 AI 前端设计增强工具包，核心理念：AI slop 不是模型能力问题，而是**词汇问题**——开发者说不清「好看」，模型只能回退到 Inter + gray-50 + 卡片套一切。
- 技术构成：1 个 Foundation Skill（`frontend-design`）+ **20 个可调用斜杠命令**（`/audit`、`/polish`、`/colorize` 等）+ 反模式清单（Anti-Patterns）。
- 支持 **Claude Code、Cursor、Codex CLI、Gemini CLI**；从官网下载 ZIP，复制 `dist/{tool}/` 到项目或全局配置目录即可使用。
- 推荐工作流：先 `/audit` 诊断 slop 特征，再 `/distill` 简化 → `/typeset` 或 `/colorize` 优化 → `/polish` 收尾 → `/optimize` 生产级加固。
- 与 [Taste Skill](2026-06-08-taste-skill-agent-frontend.md) 互补：impeccable 偏**命令式迭代抛光**，Taste Skill 偏**生成前设计纪律与三拨盘参数**。

## 适用场景

**何时用：**

- AI 生成的页面「能跑但廉价」：Inter 字体、灰底、渐变文字、玻璃拟态、Hero 假指标、卡片嵌套卡片。
- 你说不清设计需求，但需要可执行的「设计词汇」让 agent 理解排版、配色、垂直节奏、流体字体等概念。
- 已有初版 Landing Page，想用斜杠命令逐轮审计、简化、配色、抛光，而非从零重写。

**何时不用：**

- 需要从零生成时的一套生成前协议 → 可配合 [Taste Skill](2026-06-08-taste-skill-agent-frontend.md) 或项目自有设计系统。
- 复杂 dashboard、设计系统深度定制、品牌 VI 全流程——仍需设计师或成熟组件库。
- 未安装对应工具包时，斜杠命令不可用。

## 知识要点

### 1. 问题根源：词汇而非模型

创始人 **Paul Bakaus**（jQuery UI 联合创始人、前 Google Chrome DevTools 团队成员）的核心观点：

> AI slop 美学不是模型问题，是词汇问题。

开发者常说「让它好看点」，但说不清色调统一的中性色、垂直节奏、流体字体等专业概念。模型收到模糊指令后，默认组合为：**Inter + gray-50 背景 + card 包一切**，导致全网 AI 页面高度同质。

### 2. 产品构成

| 组件 | 说明 |
|------|------|
| Foundation Skill | `frontend-design`——设计原则、美学指南、反模式清单，其他命令的底层 |
| 20 个斜杠命令 | 针对具体问题可单独调用（诊断、抛光、配色、动效等） |
| Anti-Patterns | 明确告诉 AI **什么不该做** |

### 3. 核心斜杠命令（按用途）

**诊断与评审（只看不改）**

| 命令 | 作用 |
|------|------|
| `/audit` | 无障碍、性能、响应式；识别 slop 色盘、渐变文字、玻璃拟态、Hero 指标等 |
| `/critique` | UX 评审：层级、清晰度、情感共鸣 |

**结构与视觉优化**

| 命令 | 作用 |
|------|------|
| `/distill` | 去冗余，只保留值得存在的元素 |
| `/normalize` | 对齐项目已有设计系统 |
| `/colorize` | 战略性配色，有逻辑有层次 |
| `/typeset` | 排版与阅读舒适度 |
| `/bolder` | 强化文字层次 |
| `/clarify` | 简化文案与内容结构 |
| `/quieter` | 视觉降噪，更专注 |

**收尾与生产**

| 命令 | 作用 |
|------|------|
| `/polish` | 上线前对齐、间距、细节全面检查 |
| `/overdrive` | 比 polish 更激进的视觉与交互提升 |
| `/optimize` | 性能、可访问性、代码质量一次性优化 |
| `/harden` | 弱网、大屏、小屏等极端场景加固 |

**动效与体验**

| 命令 | 作用 |
|------|------|
| `/animate` | 有意义动效（非装饰性抖动） |
| `/delight` | 情感化微交互 |

**工程与协作**

| 命令 | 作用 |
|------|------|
| `/extract` | 从页面提取可复用组件 |
| `/onboard` | 优化新用户引导流程 |
| `/teach-impeccable` | 让 AI 学习并记忆你的设计偏好 |
| `/frontend-design` | 基础设计词典（Foundation） |

完整列表见 [命令速查表](https://impeccable.style/cheatsheet)。

### 4. AI 界面常见通病（Anti-Patterns）

**配色：** 过度饱和 AI 特征色盘、渐变文字（可读性差）、滥用玻璃拟态。

**布局：** Hero 首屏堆假指标、万物卡片网格、卡片嵌套卡片。

**交互：** bounce easing 头晕、冗余文案、灰底+彩色文字辨识度差。

`/audit` 会点名上述问题；后续命令针对性修复。

### 5. 与 Taste Skill 的定位差异

| 维度 | impeccable.style | Taste Skill |
|------|------------------|-------------|
| 交互形态 | 20 个斜杠命令，迭代抛光已有页面 | SKILL.md + 三拨盘，生成前设计判断 |
| 创始人场景 | 说不清设计词汇的开发者 | 对抗 agent 默认模板与 AI tell |
| 典型流程 | `/audit` → `/distill` → `/colorize` → `/polish` | brief inference → 设计系统映射 → pre-flight |
| 安装 | ZIP 复制到 `.claude` 等目录 | `npx skills add` |

两者可组合：生成阶段用 Taste Skill，初版产出后用 impeccable 命令审计与抛光。

## 代码 / 命令

**安装（以 Claude Code 为例，项目级推荐）：**

```bash
# 从 https://impeccable.style 下载 ZIP，解压后：
cp -r dist/claude-code/.claude your-project/
```

**全局安装（所有项目生效）：**

```bash
cp -r dist/claude-code/.claude/* ~/
```

Cursor / Codex CLI / Gemini CLI 选用 ZIP 内对应 `dist/{tool}/` 目录。

**推荐优化序列：**

```
/audit      # 先诊断，不自动修复
/distill    # 简化结构
/typeset    # 排版
/colorize   # 配色
/polish     # 收尾质感
/optimize   # 生产级全面优化
```

## 注意事项

- 文章称「21 个命令」= 1 个 Foundation（`/frontend-design`）+ 20 个用户命令，计数口径需区分。
- 实测案例引自第三方分享，效果因模型、brief 与初版质量而异。
- 开源仓库：[pbakaus/impeccable](https://github.com/pbakaus/impeccable)；Star 数随时间变化，以 GitHub 为准。

## 相关链接

- [impeccable.style 官网](https://impeccable.style)
- [GitHub 仓库](https://github.com/pbakaus/impeccable)
- [命令速查表](https://impeccable.style/cheatsheet)
- 项目内：[Taste Skill 前端设计纪律](2026-06-08-taste-skill-agent-frontend.md)（`KB-AI-20260608-taste-skill-agent-frontend`）
- 项目内：[Awesome AI Tools for UI 工具导航](2026-06-08-awesome-ai-tools-for-ui.md)（`KB-AI-20260608-awesome-ai-tools-for-ui`，清单 ⭐️ 收录）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 交叉引用 Awesome AI Tools for UI 导航笔记（ING-20260608-004） |
| 2026-06-08 | 初稿（ING-20260608-003），整合用户提供的公众号导读与 GitHub 信息 |
