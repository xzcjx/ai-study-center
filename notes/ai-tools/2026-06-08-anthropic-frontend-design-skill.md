---
id: KB-AI-20260608-anthropic-frontend-design-skill
module: ai-tools
module_id: MOD-AI
title: "Anthropic Frontend Design Skill：三步告别 AI 前端 Slop"
source:
  type: paste
  url: "https://github.com/anthropics/skills/tree/main/skills/frontend-design"
  accessed: "2026-06-08"
tags: [anthropic, frontend-design, agent-skill, claude-code, anti-slop, aesthetic-direction, coolors]
difficulty: beginner
status: active
related: [KB-AI-20260608-taste-skill-agent-frontend, KB-AI-20260608-awesome-ai-tools-for-ui, KB-AI-20260608-three-ways-remove-ai-slop]
ingest_id: ING-20260608-005
updated: 2026-06-08
---

# Anthropic Frontend Design Skill：三步告别 AI 前端 Slop

## TL;DR

- 裸跑 Claude Code 生成前端，常见产出是**蓝紫渐变 + 平淡布局**的 AI slop；功能完整但缺乏设计感。
- **三步升级**：① 安装 Anthropic 官方 `frontend-design` Skill → ② 用 [coolors.co](https://coolors.co/) 等专业配色附到 prompt → ③ 显式指定 `aesthetic direction`（如 Minimalism、Dark Mode）。
- Skill 核心是生成前的 **Design Thinking**：先定 Purpose / Tone / Differentiation，再写代码；会主动规避 Inter、紫渐变等 generic 审美。
- Claude Code 安装路径：`/plugin` → Add Marketplace → `anthropics/claude-code` → 安装 `frontend-design` 插件；prompt 末尾加 `use frontend-design skill`。
- 与 [Taste Skill](2026-06-08-taste-skill-agent-frontend.md) 同属生成前约束类 Skill；Taste Skill 偏三拨盘参数与 anti-slop 纪律，Anthropic 版偏**美学方向选择与排版/动效指南**，可按 agent 环境二选一或组合。

## 适用场景

**何时用：**

- 使用 **Claude Code** 生成单页 HTML、React 组件、landing page，输出总带「AI 味」。
- 需要可复现的 A/B 对比实验：同一功能 prompt + Skill + 配色 + 风格方向，快速验证 UI 提升幅度。
- 希望不写 CSS 也能让 agent 产出有明确美学立场（极简、暗黑、有机精致等）的界面。
- 已在 [Awesome AI Tools for UI](2026-06-08-awesome-ai-tools-for-ui.md) 清单里看到本 Skill，需要实操安装与 prompt 配方。

**何时不用：**

- 复杂 B2B dashboard、设计系统已锁定的生产项目——应遵循现有 Figma / 组件库，而非让 Skill 自由发挥「大胆美学」。
- 使用 Cursor 且未配置该 Skill——需改用 `npx skills add` 或粘贴 `SKILL.md`，Claude Code 插件路径不适用。
- 仅需**抛光已有页面**而非从零生成——优先 [impeccable.style](2026-06-08-impeccable-style-frontend-design.md) 的 `/audit` → `/polish` 工作流。

## 知识要点

### 1. 问题：为什么默认 AI UI 很丑

社区实验（Todo List SPA，纯 HTML/CSS/JS + LocalStorage）显示：不加任何设计约束时，Claude Code 能完整实现 CRUD、筛选、排序等功能，但视觉呈现典型 slop 特征——蓝紫色配色、卡片布局平庸、层次扁平。根因与 [Awesome AI Tools for UI](2026-06-08-awesome-ai-tools-for-ui.md) 笔记一致：**模型缺设计直觉，回退统计默认审美**。

### 2. 三步升级法（社区验证配方）

| 步骤 | 动作 | 效果 |
|------|------|------|
| ① 装 Skill | Claude Code 安装 `frontend-design` 插件，prompt 加 `use frontend-design skill` | 告别默认蓝紫，布局与层次明显提升；agent 会自推 `Aesthetic Direction`（如 Organic & Refined） |
| ② 喂配色 | 从 coolors.co 选色板，以 CSS 变量 HEX/HSL 写入 prompt，并强调「颜色严格符合」 | AI 严格执行专业配色，避免自主选丑色 |
| ③ 定风格 | prompt 加 `use aesthetic direction: Minimalism` 或 `Dark Mode` 等 | 同一功能呈现截然不同气质（极简清爽 vs 赛博暗黑） |

**结论**：Skill 是最大杠杆；配色与风格方向是叠加增益，三步齐备可达「专业级」观感。

### 3. Skill 机制：Design Thinking 先于写码

官方 `SKILL.md`（[anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design)）要求编码前明确：

- **Purpose**：界面解决什么问题、服务谁
- **Tone**：选定极端美学立场（brutally minimal、retro-futuristic、organic/natural、luxury/refined 等），拒绝模糊中间态
- **Differentiation**：一个令人记住的视觉锚点

实现时强调：独特字体（禁 Inter/Arial 泛用）、CSS 变量统一色板、高冲击力动效（staggered reveal）、非常规空间构图（不对称、重叠、破格网格）、氛围背景（噪点、渐变网格、纹理）。

**硬性反模式**：紫渐变白底、Space Grotesk 等社区过度使用字体、可预测的三卡布局、缺乏语境的 cookie-cutter 设计。

### 4. Claude Code 插件安装

文章实验环境：Claude Code 2.0.55 + Minimax-M2。安装步骤：

1. 终端启动 Claude Code
2. 输入 `/plugin`
3. 选择 **Add Marketplace**
4. 输入仓库名：`anthropics/claude-code`
5. 选择 **Browse and install plugins**
6. 安装 **frontend-design** 插件

插件底层即 `anthropics/skills` 仓库中的 `frontend-design` Skill。

### 5. 对比实验设计（可复现）

**固定任务**：单文件 Todo List SPA（HTML5 + CSS3 + ES6+，LocalStorage 持久化，响应式，WCAG 2.1 AA）。

**三组对照**：

| 实验 | 条件 | 配色 | 风格 | 观感 |
|------|------|------|------|------|
| 1 基础 | 裸 Claude Code | 默认蓝紫 | 无 | 功能 ✅，AI 味重 |
| 2 +Skill | frontend-design + coolors 色板 | dark-teal / sea-green / celadon / tea-green | agent 自推 | 明显专业感 |
| 3 +风格 | 实验 2 + aesthetic direction | 同上 | Minimalism 或 Dark Mode | 风格鲜明、可预期 |

实验 2 示例色板（coolors）：

```css
--dark-teal: #114b5f;
--sea-green: #1a936f;
--celadon: #88d498;
--tea-green: #c6dabf;
```

### 6. 与其他 anti-slop 工具的定位

| 工具 | 平台侧重 | 机制 | 互补关系 |
|------|----------|------|----------|
| Anthropic frontend-design | Claude Code 原生插件 | 生成前美学方向 + 反 generic 规则 | 官方维护，Claude 生态首选 |
| Taste Skill | Cursor / Codex / ChatGPT | 三拨盘 + brief inference + pre-flight | 参数化更强，适合 landing/dashboard 切换 |
| impeccable.style | Cursor / Claude / Codex | 生成后斜杠命令抛光 | 与任一生成前 Skill 组合 |

## 代码 / 命令

### Claude Code 插件安装（交互式）

```
/plugin
→ Add Marketplace
→ anthropics/claude-code
→ Browse and install plugins
→ frontend-design
```

### 实验 2 提示词骨架

```text
{Todo List 完整需求 prompt}

color palette is below:
--dark-teal: #114b5f;
--sea-green: #1a936f;
--celadon: #88d498;
--tea-green: #c6dabf;

颜色要严格符合上面的 css 要求

save local file todo.html
use frontend-design skill
```

### 实验 3 风格控制

```text
{需求 + 配色同上}

save local file todo-minimal.html
use aesthetic direction: Minimalism
use frontend-design skill
```

```text
save local file todo-dark.html
use aesthetic direction: Dark Mode
use frontend-design skill
```

### 非 Claude Code 环境（npx / 粘贴）

```bash
npx skills add https://github.com/anthropics/skills --skill frontend-design
```

或从仓库复制 `skills/frontend-design/SKILL.md` 粘贴到对话，并写明 `Follow frontend-design skill`。

## 注意事项

- 文章实验基于 **Claude Code + Minimax-M2**，其他模型/编辑器效果可能有差异，需自行 A/B。
- `aesthetic direction` 为社区实验用语，与 Skill 内 **Tone** 概念对应；可用 Minimalism、Dark Mode 或 Skill 列举的 retro-futuristic、organic/natural 等。
- Skill 鼓励「大胆美学」，生产环境若需克制企业风，须在 prompt 中显式覆盖（如 `luxury/refined` + 品牌色板）。
- impeccable 也有名为 `frontend-design` 的 Foundation Skill，**与 Anthropic 官方 Skill 不同产品**，勿混淆安装源。

## 相关链接

- [Anthropic frontend-design Skill 仓库](https://github.com/anthropics/skills/tree/main/skills/frontend-design)
- [Claude Code 插件市场 anthropics/claude-code](https://github.com/anthropics/claude-code)
- [coolors.co 配色工具](https://coolors.co/)
- 项目内：[Awesome AI Tools for UI 导航](2026-06-08-awesome-ai-tools-for-ui.md)（`KB-AI-20260608-awesome-ai-tools-for-ui`）
- 项目内：[Taste Skill 前端设计纪律](2026-06-08-taste-skill-agent-frontend.md)（`KB-AI-20260608-taste-skill-agent-frontend`）
- 项目内：[impeccable.style 设计词典](2026-06-08-impeccable-style-frontend-design.md)（`KB-AI-20260608-impeccable-style-frontend-design`）
- 项目内：[三种方法去除 AI 编程 Slop](2026-06-08-three-ways-remove-ai-slop.md)（`KB-AI-20260608-three-ways-remove-ai-slop`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 交叉引用三种去 Slop 方法论笔记（ING-20260608-006） |
| 2026-06-08 | 初稿（ING-20260608-005），整合社区三步实验导读与 anthropics/skills SKILL.md |
