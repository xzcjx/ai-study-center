---
id: KB-AI-20260608-taste-skill-agent-frontend
module: ai-tools
module_id: MOD-AI
title: "Taste Skill：为 AI Agent 前端生成注入设计纪律"
source:
  type: url
  url: "https://github.com/Leonxlnx/taste-skill"
  accessed: "2026-06-08"
tags: [taste-skill, agent-skill, frontend-design, anti-slop, cursor, design-system, motion]
difficulty: intermediate
status: active
related: []
ingest_id: ING-20260608-001
updated: 2026-06-08
---

# Taste Skill：为 AI Agent 前端生成注入设计纪律

## TL;DR

- Taste Skill 是一组可安装的 **Agent Skills**（`SKILL.md`），不是 npm UI 组件库；定位为「The Anti-Slop Frontend Framework for AI Agents」，在写代码前先做设计判断、选型与交付自检。
- 默认技能 `design-taste-frontend` 已切到 **v2 experimental**，通过三个拨盘（`DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`）控制布局实验度、动效强度与信息密度。
- v2 强化 brief inference、官方设计系统映射（Fluent / Material / Carbon / Primer 等）、anti-AI-tell 规则、动效工程纪律与 pre-flight 交付检查。
- 技能分 **实现类**（直接产出代码）与 **图像生成类**（先出参考图再实现）；一行 `npx skills add` 即可安装到 Cursor、Codex、Claude Code 等环境。
- 更适合 landing page、portfolio、改版场景；不适合复杂 dashboard、数据表、多步表单等系统型产品界面。

## 适用场景

**何时用：**

- 用 Cursor、Codex、Claude Code、ChatGPT 等 AI agent 生成前端，但输出总带「模板腔」（居中紫蓝渐变、三张功能卡、玻璃拟态、假仪表盘）。
- 独立开发者或小团队需要早期产品页、作品集、活动页的第一版更接近可评审状态。
- 构建 agent 工作流，希望把「设计前判断 → 过程约束 → 交付检查」写成可复用协议。

**何时不用：**

- 复杂 dashboard、数据表、多步产品表单、代码编辑器、实时协作 UI 或原生移动应用——应优先成熟产品设计系统与专用组件。
- 生产环境需要稳定可重复行为时，v2 仍在 pre-release，可暂时固定 `design-taste-frontend-v1`。
- 品牌本身需要强烈装饰风格时，brief 必须显式覆盖默认 anti-slop 规则。

## 知识要点

### 1. 本质定位：设计导演手册，而非 UI 框架

Taste Skill 通过 `SKILL.md` 的 frontmatter 与正文规则，指导 agent 在生成前端时判断页面类型、选择设计系统、控制动效复杂度、规避常见 AI 味道，并在交付前自检。它不替代设计师，也不提供现成组件，而是给模型一套可执行的「设计纪律」。

仓库明确声明：**无官方 coin 或 crypto 项目**，任何借名发行的资产均非官方背书。

### 2. 三个核心拨盘（1–10）

| 拨盘 | 含义 | 低值 | 高值 |
|------|------|------|------|
| `DESIGN_VARIANCE` | 布局实验程度 | 居中、干净 | 不对称、现代感 |
| `MOTION_INTENSITY` | 动效丰富度 | 悬停反馈 | 滚动视差、磁性效果 |
| `VISUAL_DENSITY` | 信息密度 | 宽松留白 | 密集后台风格 |

三个参数可按 brief 灵活调整，避免锁死在单一审美。

### 3. v2 experimental 关键协议

**Brief inference（Design Read）**：写代码前先读 brief——页面类型（SaaS landing、作品集、重设计、编辑页等）、vibe words、参考站点、受众、品牌资产与隐含约束，并输出一句设计判断。

**设计系统映射**：若项目明显属于 Microsoft、Google、IBM、Shopify、Atlassian、GitHub、GOV.UK、USWDS 等风格，优先使用官方包（如 Fluent UI、Material 3、Carbon、Primer），而非手搓仿制 CSS。glassmorphism、brutalism、editorial 等方向则用 Web 标准或已有组件库诚实实现。

**Anti-AI-tell 规则**：禁止随处 em dash、装饰性 section 编号、无意义版本标签、照片署名式文案、底部装饰 text strip、滚动提示、默认装饰状态点、过度分割线、styled div 假产品 UI 等重复「模板腔」。

**动效工程纪律**：推荐 Motion 的 `motion/react`；提供 GSAP sticky-stack、horizontal-pan 的 canonical skeleton；禁止用 React state 跟踪连续滚动或鼠标值；`MOTION_INTENSITY > 3` 时需处理 `prefers-reduced-motion`。

**Pre-flight 检查**：交付前自检 hero 溢出、CTA 可见性、按钮对比度、主题一致性、动效是否真实存在、列表/卡片是否偷懒重复。

### 4. 技能分层：实现类 vs 图像生成类

**实现类（产出代码）**

| Install name | 用途 |
|--------------|------|
| `design-taste-frontend` | 默认 v2，landing / portfolio / redesign |
| `design-taste-frontend-v1` | 稳定 v1，兼容旧工作流 |
| `gpt-taste` | GPT/Codex 更严格版，更强 anti-slop |
| `image-to-code` | 参考图 → 分析 → 实现 |
| `redesign-existing-projects` | 已有项目先审计再改版 |
| `high-end-visual-design` | 柔和、留白、高级感 |
| `full-output-enforcement` | 禁止半成品与 placeholder |
| `minimalist-ui` | Notion/Linear 式克制编辑风 |
| `industrial-brutalist-ui` | 瑞士排版、强对比粗野主义 |
| `stitch-design-taste` | Google Stitch 兼容，可导出 `DESIGN.md` |

**图像生成类（仅参考图）**

| Install name | 用途 |
|--------------|------|
| `imagegen-frontend-web` | 网站 hero、多区块排版参考 |
| `imagegen-frontend-mobile` | 移动端界面与流程参考 |
| `brandkit` | 品牌板、配色、字体、VI 参考 |

选型建议：新站点从 `design-taste-frontend` 起手；改版用 `redesign-existing-projects`；先探索视觉方向时用 image-generation skills，定稿后再交给 coding agent。

### 5. 与 Cursor / 其他 Agent 的协作方式

在任务中显式要求 agent **follow design-taste-frontend**，并补充页面类型、受众、品牌调性与参考网站。也可将 `SKILL.md` 复制进项目或粘贴到对话中。

Image-first 流程示例：先 `imagegen-frontend-web` 出帧，再 `image-to-code` 分析并实现，避免 agent 直接跳到默认模板。

### 6. 局限与风险

- 效果依赖模型是否认真遵守 SKILL.md；不同 agent 支持程度、上下文长度、项目已有设计系统与用户 brief 清晰度均会影响产出。
- v2 为 experimental，API 与细节会持续迭代至 v2.0.0 stable；生产流程应关注 CHANGELOG。
- 强规则可能误伤合法品牌风格，需用 brief 显式覆盖默认约束。

## 代码 / 命令

```bash
# 安装全部技能
npx skills add https://github.com/Leonxlnx/taste-skill

# 仅安装默认前端审美技能（v2 experimental）
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"

# 固定 v1 行为
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend-v1"
```

**Prompt 示例（新项目）：**

```
Follow the design-taste-frontend skill. Build a B2B SaaS landing page for technical buyers.
The brand should feel precise, restrained, and developer-friendly,
closer to GitHub Primer than generic AI gradients.
```

**Prompt 示例（image-first）：**

```
Follow image-to-code: generate visual references first, analyze the selected frame, then implement it in code.
```

## 注意事项

- 微信原文链接（`mp.weixin.qq.com`）访问需验证，入库以 GitHub README 与用户整理正文为准。
- 校验脚本会扫描敏感关键词；笔记中涉及「无官方代币」等声明时避免无意义的英文敏感词堆砌。
- 框架无关：规则针对设计意图，React / Vue / Svelte 均可配合使用。

## 相关链接

- [Taste Skill 仓库](https://github.com/Leonxlnx/taste-skill)
- [项目站点 tasteskill.dev](https://tasteskill.dev)
- [Agent Skills CLI（vercel-labs/agent-skills）](https://github.com/vercel-labs/agent-skills)
- 微信导读（链接可能需验证）：[让 AI 前端从「丑爆」到「惊艳」](https://mp.weixin.qq.com/s/T9c4UeM9iw_bN6BsqiK49Q)

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 初稿（ING-20260608-001），整合 GitHub README 与用户提供的导读正文 |
