---
id: KB-AI-20260608-three-ways-remove-ai-slop
module: ai-tools
module_id: MOD-AI
topic: frontend-design
title: "三种方法去除 AI 编程 Slop：参考克隆、Gemini 壳层、Agent Skills"
source:
  type: paste
  url: "internal"
  accessed: "2026-06-08"
tags: [anti-slop, aura-build, google-ai-studio, gemini, agent-skill, taste-skill, claude-code, ui-reference]
difficulty: beginner
status: active
related: [KB-AI-20260608-taste-skill-agent-frontend, KB-AI-20260608-anthropic-frontend-design-skill, KB-AI-20260608-awesome-ai-tools-for-ui, KB-AI-20260608-vibe-coding-ui-three-strategies]
ingest_id: ING-20260608-006
updated: 2026-06-08
---

# 三种方法去除 AI 编程 Slop：参考克隆、Gemini 壳层、Agent Skills

## TL;DR

- AI 编程常见 **Slop 症状**：蓝紫渐变、满屏 emoji、千篇一律圆角卡片与三栏布局——功能能跑但一眼「AI 开发」。
- **方法 1 参考克隆**：从 [aura.build](https://aura.build) 挑选好看案例，复制源码喂给 Claude Code/Cursor，比照着重构自己的产品，避免模型抽卡不确定性。
- **方法 2 模型分工**：在 **Google AI Studio** 用 Gemini 3.x 免费快速搭 UI 壳层并在线预览，下载后再用 **Codex / Claude Code** 做业务逻辑——UI 审美交给 Gemini，智能体能力交给当世双雄。
- **方法 3 Agent Skills**：`npx skills add` 安装设计 Skill（文章实测为 [Taste Skill](2026-06-08-taste-skill-agent-frontend.md)），同一模型同一 prompt 前后对比效果显著；Claude Code 用户也可选 [Anthropic frontend-design](2026-06-08-anthropic-frontend-design-skill.md)。
- 三种方法均免费可上手，可按场景组合：有明确审美参考 → 方法 1；要惊喜抽卡 + 省 UI 生成用量 → 方法 2；日常 agent 工作流内嵌 → 方法 3。

## 适用场景

**何时用：**

- 用 AI 开发了十多个项目，个人站、作品集、工具站总带浓重 AI 味，需要系统性去 slop。
- 已有 Claude Code / Codex 主力开发环境，不想换工具链，只想提升 UI 产出质量。
- 找不到满意设计稿，或相反——已在 aura.build 看到心仪模板，想快速落地。
- 无法稳定使用 Gemini CLI / Antigravity，但仍想借 Gemini 的前端审美优势。

**何时不用：**

- 企业级产品已有 Figma 设计系统与组件库——应遵循设计规范，而非自由「比照样板」。
- 复杂后台、数据密集型应用——三种方法均偏 landing / 营销页 / 展示站，dashboard 需专用设计系统。
- 期待零 prompt 工程——方法 1 需挑选参考并写清「比照样式重构」，方法 3 需安装 Skill 并在任务中显式启用。

## 知识要点

### 1. AI 编程 Slop 的典型表现

社区半年多项目复盘总结的「一眼 AI」特征：

| 症状 | 表现 |
|------|------|
| 配色 | 蓝紫渐变、高饱和默认色 |
| 装饰 | 满屏 emoji、过度图标 |
| 布局 | 圆角卡片套娃、三栏功能块、居中大标题 |
| 气质 | 各项目长得像同一个模板 |

去 slop 的本质不是「写更多 CSS」，而是**给模型方向**——参考、更强审美模型、或设计约束 Skill。

### 2. 方法 1：参考好看 UI，直接喂给 AI（最简单）

**思路**：把饭喂到嘴边——找到心仪网站 UI，让 agent **比照样式**实现你的产品，避免纯抽卡。

**推荐资源：[aura.build](https://aura.build)**

- 内置大量 Web / 移动端 UI 交互 demo，含表格、图表、导航、侧边栏、对话框、登录框等基础组件。
- 每个案例以**源代码**形式提供；部分精品需 Pro，免费区案例对多数人够用。
- 站点支持 Remix 热门模板，底层使用 Gemini 3.1 Pro 等模型生成设计系统。

**工作流**：

1. 在 aura.build 浏览 Trending / Free Templates，选定心仪案例
2. 复制该案例源代码
3. 在 Claude Code（或 Cursor）中提示：**参考这份代码的风格与布局，重构我的 {页面}**
4. 对比改造前后——质感提升、AI 味显著减少

**优势**：审美方向由人选定，结果可预期。  
**劣势**：依赖找到合适参考；风格可能过于贴近模板。

### 3. 方法 2：Google AI Studio + Codex/Claude 分工

**思路**：前端审美最强的模型（社区共识：**Gemini 3 Pro** 系列）与最强编程智能体（**Claude Code、Codex**）**分开用**。

**为什么不全程 Gemini agent**：Gemini 模型前端能力强，但编程智能体生态（工具调用、长任务、代码库理解）仍弱于 Claude Code / Codex；且 CLI 直连受网络与账号限制。

**推荐分工流程**：

```
Google AI Studio（Gemini 3.x，免费在线）
    → 快速搭 UI 框架 + 在线预览
    → 下载项目
Codex / Claude Code
    → 接入业务逻辑、API、状态管理
```

**优势**：

- AI Studio 免费、免会员即可在线预览，适合早期 demo
- UI 颜值高，且把 UI 生成用量集中在 Studio，节省主 agent 的调用额度
- 保留「抽卡惊喜感」——不像方法 1 必须锁定某一模板

**劣势**：两套工具切换；下载后的代码需与现有工程栈对齐。

### 4. 方法 3：Agent Skills 提升 UI 能力

**思路**：把专业 UI/UX 实践经验封装为 `SKILL.md` 知识库，agent 在 Skill 指导下生成，同一模型同一 prompt 前后差距明显。

文章实测环境：**Claude Code + Sonnet 4.5**，论坛站案例——未启用 Skill 时典型 slop；启用后排版、层次、配色显著提升。

**文章所指开源项目**：社区高频为 [Taste Skill](https://github.com/Leonxlnx/taste-skill)（`npx skills add` 一键安装）。本库已有 [专文](2026-06-08-taste-skill-agent-frontend.md)。

**Claude Code 替代**：Anthropic 官方 [frontend-design 插件](2026-06-08-anthropic-frontend-design-skill.md)（`/plugin` → `anthropics/claude-code`）。

**优势**：一次安装，融入日常 agent 工作流；不依赖外站、不切换工具。  
**劣势**：需记得在 prompt 中启用 Skill；不同 Skill 风格纪律不同，需选型。

### 5. 三种方法选型矩阵

| 维度 | 方法 1 aura 参考 | 方法 2 Gemini 壳层 | 方法 3 Agent Skills |
|------|------------------|--------------------|---------------------|
| 上手难度 | ⭐ 最低 | ⭐⭐ 中等 | ⭐⭐ 中等 |
| 结果可预期性 | 高（人选参考） | 中（抽卡 + 可预览） | 中高（Skill 约束） |
| 工具切换 | 无 | 有（Studio → Codex） | 无 |
| 适合页面 | 改版、个人站、落地页 | 早期 demo、新项目壳层 | 日常任意前端任务 |
| 与本库工具 | — | Google AI Studio | taste-skill / anthropic-frontend-design |

**组合建议**：

- 改版个人站：方法 1 定方向 → 方法 3 抛光细节
- 全新产品 demo：方法 2 出壳 → Codex 填业务 → 方法 3 统一审美纪律
- 纯 agent 流：方法 3 为主，方法 1 作灵感库

### 6. 案例：作者去 slop 前后

文章作者（轩辕）半年 AI 编程十余项目复盘：

- **改造前**：个人网站、SVG 动画站（svganimate.ai）典型 AI 模板脸
- **改造后**：同样功能，视觉质感与品牌感明显提升

说明 slop 可通过工作流改造系统性去除，而非单次 prompt 调优。

## 代码 / 命令

### 方法 1：Claude Code 参考重构 prompt 骨架

```text
请参考以下 aura.build 案例源代码的风格、配色、排版与动效，
重构我的个人网站首页。保留我现有的内容与功能，只改视觉与布局。

[粘贴 aura.build 案例源码]

输出：更新后的首页代码，保存为 index.html
```

### 方法 2：Google AI Studio

1. 打开 https://aistudio.google.com
2. 选择 Gemini 3.x 模型，用自然语言描述 UI 需求
3. 在线预览满意后导出/下载项目
4. 在 Codex / Claude Code 中：`基于下载的 UI 壳层，实现 {业务功能}`

### 方法 3：Taste Skill 安装

```bash
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
```

```text
Follow design-taste-frontend skill. Build a forum website homepage.
```

跨项目消费：`/kb-install taste-skill --yes --target .`

## 注意事项

- aura.build 部分模板为 **PRO / 付费**，使用前确认许可证与源码可见性。
- 「Gemini 3 Pro 前端审美最强」为社区经验共识，模型版本迭代快，需自行 A/B 验证。
- 方法 3 文章截图未标明具体 Skill 仓库名，与本库 Taste Skill 安装命令与效果描述一致；Cursor 用户同理可用 `npx skills add` 或 `/kb-install taste-skill`。
- 文章含 svganimate.ai 产品推广，与去 slop 方法论无强耦合，入库仅保留案例背景。
- emoji 滥用、蓝紫渐变等亦被 Taste Skill / Anthropic Skill 列为 explicit anti-pattern，与方法 3 叠加效果更好。

## 相关链接

- [aura.build 设计案例库](https://aura.build)
- [Google AI Studio](https://aistudio.google.com)
- [Taste Skill 仓库](https://github.com/Leonxlnx/taste-skill)
- 项目内：[Taste Skill 前端设计纪律](2026-06-08-taste-skill-agent-frontend.md)（`KB-AI-20260608-taste-skill-agent-frontend`）
- 项目内：[Anthropic Frontend Design Skill](2026-06-08-anthropic-frontend-design-skill.md)（`KB-AI-20260608-anthropic-frontend-design-skill`）
- 项目内：[Awesome AI Tools for UI 导航](2026-06-08-awesome-ai-tools-for-ui.md)（`KB-AI-20260608-awesome-ai-tools-for-ui`）
- 项目内：[Vibe Coding UI 三策略对比](2026-06-08-vibe-coding-ui-three-strategies.md)（`KB-AI-20260608-vibe-coding-ui-three-strategies`，同主题不同方法：Prompt 形态 A/B）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 交叉引用 Vibe Coding 三策略笔记（ING-20260608-007） |
| 2026-06-08 | 初稿（ING-20260608-006），整合轩辕社区导读三种去 AI 味方法论 |
