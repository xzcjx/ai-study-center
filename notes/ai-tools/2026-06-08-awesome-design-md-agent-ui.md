---
id: KB-AI-20260608-awesome-design-md-agent-ui
module: ai-tools
module_id: MOD-AI
title: "awesome-design-md：复制 DESIGN.md 让 AI 按顶级设计系统出 UI"
source:
  type: paste
  url: "https://github.com/VoltAgent/awesome-design-md"
  accessed: "2026-06-08"
tags: [awesome-design-md, design-md, frontend-design, anti-slop, design-system, cursor, agent-skill, ui-generation]
difficulty: beginner
status: active
related: [KB-AI-20260608-vibe-coding-ui-three-strategies, KB-AI-20260608-taste-skill-agent-frontend, KB-AI-20260608-impeccable-style-frontend-design, KB-AI-20260608-anthropic-frontend-design-skill, KB-AI-20260608-awesome-ai-tools-for-ui]
ingest_id: ING-20260608-008
updated: 2026-06-08
---

# awesome-design-md：复制 DESIGN.md 让 AI 按顶级设计系统出 UI

## TL;DR

- **DESIGN.md** 是 Google Stitch 提出的项目根目录设计规范文件，与 **AGENTS.md** 平行：前者管 UI 长什么样，后者管代码怎么写；纯 Markdown，零代码依赖。
- **[awesome-design-md](https://github.com/VoltAgent/awesome-design-md)**（VoltAgent 维护，MIT，GitHub 约 88K Star）收录 **73 个**顶级产品（Stripe、Linear、Apple、Vercel 等）的 `DESIGN.md`，覆盖色板、字体、组件、布局等 **9 大维度**。
- 用法极简：`cp design-md/{brand}/DESIGN.md ./your-project/`，在 Cursor / Claude Code / Google Stitch 中说「按 DESIGN.md 构建页面」即可。
- 每个设计系统附带 `preview.html` / `preview-dark.html`，浏览器可直接预览色板与组件效果。
- 与 Agent Skill（Taste / Anthropic）、设计 Prompt 库、impeccable 抛光**互补**：DESIGN.md 解决**跨 session 风格一致**与**精确设计变量**，Skill 解决生成纪律，impeccable 解决已有页抛光。
- 长期价值在**自建品牌 DESIGN.md**；73 个开源规范是起点，定制服务见 [getdesign.md/request](https://getdesign.md/request)。

## 适用场景

**何时用：**

- AI 生成前端时配色随机、间距混乱、同一项目多页风格不统一——需要**持久化、可复用**的设计约束。
- 独立开发者 / 小团队没有 Figma 设计系统，但希望落地页接近 Stripe / Linear / Apple 级别观感。
- 已选定参考品牌风格，想一键复制完整设计变量 而非手写 500 行 design prompt。
- 与 [Vibe Coding UI 三策略](2026-06-08-vibe-coding-ui-three-strategies.md) 中「设计 Prompt」路线升级：从一次性 prompt 升级为项目级 `DESIGN.md`。

**何时不用：**

- 已有完整 Figma 设计变量 与组件库——应直接导出变量或写自家 `DESIGN.md`，不必套 Stripe/Linear 模板。
- 仅需**抛光已有页面**而非从零生成——优先 [impeccable.style](2026-06-08-impeccable-style-frontend-design.md) 的 `/audit` → `/polish`。
- 需要 agent 内置 brief inference、动效拨盘等**生成过程纪律**——配合 [Taste Skill](2026-06-08-taste-skill-agent-frontend.md) 或 [Anthropic Frontend Design Skill](2026-06-08-anthropic-frontend-design-skill.md)，而非单靠 DESIGN.md。

## 知识要点

### 1. DESIGN.md：一个文件定义 UI 规范

概念由 **Google Stitch** 推广，与根目录 **AGENTS.md** 对称：

| 文件 | 职责 |
|------|------|
| `AGENTS.md` | 告诉 coding agent 如何构建项目（架构、命令、约定） |
| `DESIGN.md` | 告诉 agent UI 应长什么样（色板、字体、组件、布局） |

不需要 Figma 导出、JSON schema 或专有格式——普通 Markdown 写清 hex、字号层级、按钮状态、间距规则，任意支持读项目文件的 AI agent 即可遵循。

**为何用 Markdown 而非 JSON/YAML**：LLM 对 Markdown 的理解与遵循显著优于结构化配置；比喂 Figma 截图或裸 JSON schema 更高效（选对数据格式有时比算法更重要）。

### 2. DESIGN.md 标准九维结构

| 维度 | 内容 | 示例 |
|------|------|------|
| 视觉主题 | 整体哲学与氛围 | cinematic dark UI / warm minimalism |
| 色板 | 语义命名 + hex | `background: #0A0A0A` / `foreground: #FAFAFA` |
| 字体 | 家族 + 完整字号层级 | Inter / SF Pro / JetBrains Mono |
| 组件 | 按钮/卡片/输入/导航及 hover、focus、disabled | 含状态说明 |
| 布局 | 间距比例、网格、留白 | 4px 基数 / max-width 1200px |
| 阴影层级 | 卡片与浮层 | sm / lg 参数 |
| Do's & Don'ts | 设计护栏与反模式 | 禁止暗底纯白字等 |
| 响应式 | 断点、触控目标 | md: 768px / lg: 1024px |
| Agent 提示 | 颜色快捷表 + 上下文模板 | 供 agent 快速引用 |

### 3. awesome-design-md 仓库概览

| 项 | 说明 |
|----|------|
| 维护方 | VoltAgent |
| GitHub | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) |
| 协议 | MIT |
| Star | 约 88K+（2026-06 核实） |
| 官网 | [getdesign.md](https://getdesign.md) |
| 规范来源 | Google Stitch DESIGN.md 规范 |

收录 **73 个**全球顶级产品设计规范，按领域分类，每个品牌一个目录，核心文件为 `DESIGN.md`，并含可视化预览 HTML。

### 4. 领域与代表风格（节选）

| 领域 | 代表产品 | 典型风格 |
|------|----------|----------|
| AI & LLM | Claude、Mistral、Replicate、Runway | 暗色电影感 / 极简白 |
| 开发者工具 | Cursor、Vercel、Raycast、Warp | 黑白极简 / 高密度信息 |
| 生产力 | Linear、Notion、Mintlify | 暖白极简 / 大留白 |
| 金融科技 | Stripe、Coinbase、Revolut | 专业可信 / 品牌紫 |
| 媒体科技 | Apple、Spotify、Tesla | 极简奢华 / 深色沉浸 |
| 设计工具 | Figma、Framer、Webflow | 创意前卫 / 画布中心 |

选型时先定**气质**（B2B 可信 vs 消费级温暖 vs 开发者极简），再复制对应 `DESIGN.md`，避免「看着好看但跟产品定位不符」。

### 5. 三步上手（零安装）

```bash
# 1. 克隆或浏览仓库，选定品牌
git clone https://github.com/VoltAgent/awesome-design-md.git

# 2. 复制到项目根目录（示例：Stripe / Linear）
cp awesome-design-md/design-md/stripe/DESIGN.md ./your-project/
# cp awesome-design-md/design-md/linear/DESIGN.md ./your-project/

# 3. 在 agent 对话中引用
# 「请使用 DESIGN.md 中的设计系统，为我创建支付页面」
```

**兼容工具**：Cursor、Claude Code、Google Stitch（原生支持）、Windsurf，及任何能读取项目文件的 AI coding agent。

预览：打开各品牌目录下 `preview.html` 或 `preview-dark.html` 查看色板、字号、按钮、卡片实效果。

### 6. 与反 Slop 工具栈的定位

| 方案 | 强项 | 弱项 |
|------|------|------|
| **DESIGN.md / awesome-design-md** | 精确设计变量、跨 session 一致、复制即用 | 不教 agent「生成前思考」与动效纪律 |
| **设计 Prompt 库**（designprompts） | 单页快速定方向 | 非项目级持久化，风格由 prompt 作者锁定 |
| **Agent Skill**（Taste / Anthropic） | brief、anti-slop、动效/密度拨盘 | 不自带 Stripe/Linear 级现成设计变量 |
| **impeccable** | 审计与抛光已有页 | 偏迭代而非从零定品牌系统 |
| **截图参考** | 布局骨架快 | 色值易漂移（见三策略文） |

**推荐组合**：

1. `DESIGN.md`（定设计变量）+ Taste / Anthropic Skill（定生成纪律）
2. 有参考图 → UI Prompt Builder 逆向 → 写入自家 `DESIGN.md` → 再生成
3. 首版生成后 → impeccable `/audit` → `/polish`

[Taste Skill](2026-06-08-taste-skill-agent-frontend.md) 的 `stitch-design-taste` 变体与 Google Stitch 兼容，可**导出** `DESIGN.md`，与 awesome-design-md **消费侧**形成闭环。

### 7. 谁最需要 & 长期护城河

| 人群 | 痛点 | DESIGN.md 效果 |
|------|------|----------------|
| 独立开发者 | 非设计师但要专业 UI | 复制顶级规范，AI 按设计变量出稿 |
| 前端开发者 | 多页风格漂移 | 一次对齐，后续页面一致 |
| 创业者 / PM | 快速原型无设计预算 | 十分钟接近 Stripe 级落地页 |
| 设计学习者 | 拆解真实设计系统 | 73 个案例作教科书 |

73 个开源系统是**通用起点**；真正护城河是**自家品牌 DESIGN.md**——把色板、字体、组件编码成 agent 可读文本。VoltAgent 提供 [定制服务](https://getdesign.md/request) 验证了这一需求。

### 8. AI 原生设计交付趋势（观察）

`AGENTS.md` + `DESIGN.md` 正成为 AI 时代的轻量「产品需求文档」：设计交付从 Figma → JSON → 代码的线性链，转向 **文件 → AI Agent → 直接产出**。Signal 明确：编程 agent 时代的设计规范载体正在从专有工具转向**仓库内可读文本**。

## 代码 / 命令

### 复制 Stripe 风格 DESIGN.md

```bash
cp path/to/awesome-design-md/design-md/stripe/DESIGN.md ./your-project/DESIGN.md
```

### Cursor / Claude Code 引用模板

```text
请严格遵循项目根目录 DESIGN.md 中的设计系统实现以下页面：
- 使用文档中的色板语义名与 hex，禁止自行发明配色
- 字体、间距、圆角、阴影按文档层级
- 遵守 Do's & Don'ts 章节

需求：{支付页 / 登录页 / 仪表盘等}
```

### 从预览页选型

```bash
# 本地打开预览（示例路径以仓库实际结构为准）
open awesome-design-md/design-md/linear/preview.html
open awesome-design-md/design-md/stripe/preview-dark.html
```

## 工具 / 资源

| 资源 | 链接 | 说明 |
|------|------|------|
| awesome-design-md | [GitHub](https://github.com/VoltAgent/awesome-design-md) | 73 个 DESIGN.md 合集，MIT |
| getdesign.md | [官网](https://getdesign.md) | 浏览与定制入口 |
| Google Stitch DESIGN.md 规范 | Stitch 文档 | DESIGN.md 格式 SSOT |
| 定制 DESIGN.md | [getdesign.md/request](https://getdesign.md/request) | 任意网站转 DESIGN.md |

## 注意事项

- 文章标题「87K Star」与 2026-06 GitHub 核实约 **88K**，以仓库实时 Star 为准。
- 复制他人品牌 `DESIGN.md` 适合原型与学习；**对外产品**应改写为自有品牌设计变量，避免视觉侵权与定位错位。
- `DESIGN.md` 不替代无障碍审计、国际化、复杂交互规范——生产环境仍需设计/工程复核。
- 与一次性 design prompt 相比，修改 `DESIGN.md` 即可全局影响后续生成，但**首次选型**仍需判断品牌气质是否匹配产品。

## 相关链接

- [awesome-design-md 仓库](https://github.com/VoltAgent/awesome-design-md)
- [getdesign.md](https://getdesign.md)
- [VoltAgent Discord](https://s.voltagent.dev/discord)
- 项目内：[Vibe Coding UI 三策略](2026-06-08-vibe-coding-ui-three-strategies.md)（`KB-AI-20260608-vibe-coding-ui-three-strategies`）— 系列前篇，预告 DESIGN.md 持久化
- 项目内：[Taste Skill](2026-06-08-taste-skill-agent-frontend.md)（`KB-AI-20260608-taste-skill-agent-frontend`）
- 项目内：[impeccable.style](2026-06-08-impeccable-style-frontend-design.md)（`KB-AI-20260608-impeccable-style-frontend-design`）
- 项目内：[Anthropic Frontend Design Skill](2026-06-08-anthropic-frontend-design-skill.md)（`KB-AI-20260608-anthropic-frontend-design-skill`）
- 项目内：[Awesome AI Tools for UI](2026-06-08-awesome-ai-tools-for-ui.md)（`KB-AI-20260608-awesome-ai-tools-for-ui`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 初稿（ING-20260608-008），整合 awesome-design-md / DESIGN.md 与 73 设计系统用法 |
