---
id: KB-AI-20260608-ai-code-review-prompt-guide
module: ai-tools
module_id: MOD-AI
topic: code-review
title: "AI Code Review 实战：Prompt 模板、集成方式与人工协作"
source:
  type: paste
  url: "internal"
  accessed: "2026-06-08"
tags: [code-review, prompt, cursor, claude, copilot, security-review, flask, sonarqube, codacy]
difficulty: beginner
status: active
related: [KB-ARCH-20260608-ai-business-code-review, KB-AI-20260608-ai-code-review-workflow-methodology, KB-AI-20260608-ai-coding-era-review-upgrade, KB-AI-20260608-ai-first-gate-review-experiment, KB-AI-20260608-ai-code-review-next-wave-trend]
ingest_id: ING-20260608-010
updated: 2026-06-08
---

# AI Code Review 实战：Prompt 模板、集成方式与人工协作

## TL;DR

- 人工 Review 慢（约 100 行 15–20 分钟）且易疲劳；AI 适合作为**第一轮快速扫描**（约 100 行 10 秒级），人工负责业务逻辑与架构深度审查。
- AI **强项**：语法/类型、空值、SQL 注入/XSS、命名与重复、注释缺失；**弱项**：复杂业务 Bug、并发、需运行时数据的性能问题、团队风格偏好。
- 提供三套可复制 **Prompt 模板**：基础审查、安全专项、代码规范；输出统一为 🔴/🟡/🟢 分级 + 行号 + 修复建议。
- 集成方式：GitHub Copilot Enterprise PR 审查、**Cursor 对话审查当前文件**、独立工具（Codacy / SonarQube）做规模化扫描。
- 补足局限：在 Prompt 中注入**业务规则**；勿直接粘贴 AI 修复代码；敏感代码用本地/企业内工具。
- 企业级 Webhook + RAG 全链路见架构专文 [业务级 AI Code Review](2026-06-08-ai-business-code-review.md)。

## 适用场景

**何时用：**

- 日常 PR 需要快速第一轮扫描，释放 senior 精力给业务逻辑与架构。
- 单人或小团队没有专职 Reviewer，希望用 Claude/ChatGPT/Cursor 做安全与规范初筛。
- 新人代码需要全面检查 + 导师二次把关。
- 需要可复用的 Review Prompt 模板沉淀到团队工具库。

**何时不用：**

- 核心业务、有历史事故知识库——应上 [Webhook + RAG 流水线](2026-06-08-ai-business-code-review.md)，而非仅粘贴代码到聊天窗。
- 高度敏感源码——避免公有云 LLM，改 SonarQube 本地部署或内网模型。
- 期望 AI 100% 替代人工——关键路径与核心逻辑仍需人工确认。

## 知识要点

### 1. 人工 vs AI 辅助 Review

| 维度 | 人工 Review | AI 辅助 Review |
|------|-------------|----------------|
| 速度 | 100 行约 15 分钟 | 100 行约 10 秒级 |
| 覆盖面 | 受注意力限制 | 全量覆盖 |
| 知识面 | 个人经验边界 | 广泛最佳实践 |
| 专注度 | 易疲劳 | 质量一致 |
| 沟通成本 | 需解释讨论 | 直接给结论 |
| 发现问题 | 逻辑 Bug 强 | 安全漏洞强，复杂逻辑一般 |

**正确定位**：AI = 第一轮快速扫描；人 = 深度审查 + 业务判断。

### 2. AI 识别率预期（文章口径）

| 类型 | 识别率 |
|------|--------|
| 语法/类型、空值、SQL 注入/XSS、命名、重复、缺注释、简单逻辑 | > 85% |
| 复杂业务逻辑、多线程并发、需 profiling 的性能、团队风格偏好 | 一般 |

### 3. Prompt 模板一：基础代码审查

```text
请帮我做代码审查，从以下几个维度评估：

【需要关注的问题类型】
1. Bug 和安全漏洞
2. 代码可读性和可维护性
3. 性能问题
4. 潜在风险

【代码】
[粘贴需要审查的代码]

【语言/框架】
[例如：Python + Django 4.0]

请用以下格式输出：
## 问题列表
### 🔴 高优先级（必须修复）
- 问题描述 + 具体位置（行号）
- 原因分析
- 修复建议

### 🟡 中优先级（建议修复）
### 🟢 低优先级（可选优化）

## 总结
- 代码整体质量评分（1-10 分）
- 核心问题概述
- 需要人工关注的地方
```

### 4. Prompt 模板二：安全专项审查

```text
请帮我做安全代码审查，重点关注：
1. SQL 注入  2. XSS  3. CSRF
4. 认证/授权漏洞  5. 敏感数据泄露  6. 文件操作安全

【代码】[粘贴代码]
【语言】[语言/框架]

请输出：
## 安全问题清单
### 漏洞类型
- 位置 / 严重程度 / 原因 / 修复方案
```

### 5. Prompt 模板三：代码规范审查

```text
请审查是否符合团队规范，重点：
1. 命名规范  2. 函数长度（≤50 行）
3. 注释规范  4. 分层结构  5. 错误处理

【代码】[粘贴代码]
【规范要求】[团队规范文档，如有]

请用表格输出问题清单。
```

### 6. 实战案例：Flask 用户注册模块（要点）

待审代码典型问题（AI 应命中）：

| 优先级 | 问题 | 要点 |
|--------|------|------|
| 🔴 | SQL 注入 | 字符串拼接 SQL → 参数化 `?` 占位 |
| 🔴 | 口令明文存储 | 注册/登录需哈希（生产应用 bcrypt/argon2，非仅 SHA256） |
| 🔴 | 连接泄漏 | 用 `with sqlite3.connect(...)` 或 try/finally |
| 🟡 | 缺输入校验 | 用户名长度、邮箱格式、口令强度 |
| 🟡 | 缺错误处理 | 全局 `@app.errorhandler` |
| 🟡 | 硬编码 DB 路径 | 环境变量或配置 |
| 🟢 | 命名与 docstring | `conn`→`db_connection` 等 |

**人工仍需关注**：注册后流程（邮件、初始化）、数据库唯一约束、业务规则（如「用户名不能与邮箱相同」）。

### 7. 集成到开发流程

| 方式 | 做法 | 适合 |
|------|------|------|
| GitHub Copilot Enterprise | PR 页 Copilot tab 自动分析 | 已购企业版团队 |
| Cursor 内置 | `Cmd/Ctrl+L` →「请审查当前文件，关注 Bug、安全、质量」 | 开发时边写边审 |
| 独立扫描工具 | Codacy / SonarQube 等 | 团队规模化、CI 门禁 |
| 企业流水线 | GitLab Webhook + RAG | 见 [架构专文](2026-06-08-ai-business-code-review.md) |

**团队协作建议**：

| 场景 | 推荐 |
|------|------|
| 日常 PR | AI 第一轮 + 人工第二轮 |
| 重要模块 | AI 深度 Review + 人工架构评审 |
| 安全相关 | AI 初筛 + 安全专家确认 |
| 新人代码 | AI 全面 Review + 导师带读 |

### 8. 补足 AI 局限：注入业务规则

```text
【业务规则（审查时请考虑）】
1. 用户名不能和邮箱相同
2. 每用户最多创建 100 个帖子
3. 口令须含数字和字母
4. 仅管理员可删他人内容
```

静态分析无法推断的业务约束，必须在 Prompt 显式列出。

### 9. 常见问题速查

| 问题 | 建议 |
|------|------|
| 意见太多看不过来 | 只处理 🔴，🟡🟢 排期 |
| AI 说没问题却有 Bug | 关键路径必须人工 Review |
| 修复建议能直接用吗 | **不要直接复制**；理解思路后自写，AI 代码可能不完整或风格不符 |
| 代码保密 | 敏感代码不用公有云 LLM；用 SonarQube 本地或内网模型 |

## 代码 / 命令

### Cursor 审查当前文件

```text
请帮我审查当前文件的代码，重点关注 Bug、安全漏洞和代码质量问题。
按 🔴/🟡/🟢 分级，给出行号与可执行修复建议。
```

### SQL 注入修复示意（参数化查询）

```python
# ❌ 字符串拼接
cursor.execute("SELECT * FROM users WHERE username = '" + username + "'")

# ✅ 参数化
cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
```

## 工具 / 资源

| 工具 | 链接 | 说明 |
|------|------|------|
| Claude / ChatGPT | — | 通用 Review，随时粘贴代码 |
| Cursor | [cursor.com](https://cursor.com) | 开发时审查当前文件 |
| GitHub Copilot Enterprise | GitHub PR | 企业版 PR 自动审查 |
| Codacy | [codacy.com](https://www.codacy.com/) | 多语言自动扫描，团队规模化 |
| SonarQube | [sonarqube.org](https://www.sonarqube.org/) | 本地/企业部署，安全要求高 |

## 注意事项

- 文章称 AI Review「比人工快 10 倍」为经验口径，实际取决于模型、代码复杂度与 Prompt 质量。
- DeepCode 已被 GitHub 收购，选型时以 GitHub Advanced Security 等现行产品为准。
- Flask 案例中 `hashlib.sha256` 仅作示意；生产环境应使用 **bcrypt / argon2** 等专用口令哈希。
- 本篇为**个人/团队轻量流程**；与 [业务级流水线](2026-06-08-ai-business-code-review.md) 互补，非替代关系。
- 系列预告：第 5 篇「用 AI 重构旧代码」尚未入库。

## 相关链接

- 项目内：[AI Code Review 方法论](2026-06-08-ai-code-review-workflow-methodology.md)（`KB-AI-20260608-ai-code-review-workflow-methodology`）— 提 PR 前自查、分层检查、有效意见
- 项目内：[业务级 AI Code Review 全链路](2026-06-08-ai-business-code-review.md)（`KB-ARCH-20260608-ai-business-code-review`）— Webhook、RAG、Diff 预处理
- 项目内：[AI 编程时代 Review 升级](2026-06-08-ai-coding-era-review-upgrade.md)（`KB-AI-20260608-ai-coding-era-review-upgrade`，五维分维度 Prompt、团队清单）
- 项目内：[AI 第一道 Review 两个月实验](2026-06-08-ai-first-gate-review-experiment.md)（`KB-AI-20260608-ai-first-gate-review-experiment`，固定 Prompt + PR 贴原文）
- 项目内：[AI Code Review 下一波机会](2026-06-08-ai-code-review-next-wave-trend.md)（`KB-AI-20260608-ai-code-review-next-wave-trend`，工具版图与选型）
- [SonarQube 文档](https://docs.sonarqube.org/)
- [Codacy 文档](https://docs.codacy.com/)

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 交叉引用下一波机会趋势笔记（ING-20260608-014） |
| 2026-06-08 | 交叉引用第一道 Review 实验笔记（ING-20260608-013） |
| 2026-06-08 | 交叉引用 Review 升级笔记（ING-20260608-012） |
| 2026-06-08 | 交叉引用 CR 方法论笔记（ING-20260608-011） |
| 2026-06-08 | 初稿（ING-20260608-010），整合 AI Code Review Prompt 模板、Flask 案例与集成方式 |
