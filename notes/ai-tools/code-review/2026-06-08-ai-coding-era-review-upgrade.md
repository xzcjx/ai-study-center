---
id: KB-AI-20260608-ai-coding-era-review-upgrade
module: ai-tools
module_id: MOD-AI
topic: code-review
title: "AI 编程时代 Code Review 升级：表面合格、熟悉度盲区与五维审查"
source:
  type: paste
  url: "internal"
  accessed: "2026-06-08"
tags: [code-review, ai-coding, frontend, vue, java, self-review, legacy-code, over-engineering, review-checklist]
difficulty: intermediate
status: active
related: [KB-AI-20260608-ai-code-review-workflow-methodology, KB-AI-20260608-ai-code-review-prompt-guide, KB-ARCH-20260608-ai-business-code-review, KB-AI-20260608-ai-first-gate-review-experiment, KB-AI-20260608-ai-code-review-next-wave-trend, KB-AI-20260608-ai-review-quality-16-schemes]
ingest_id: ING-20260608-012
updated: 2026-06-08
---

# AI 编程时代 Code Review 升级：表面合格、熟悉度盲区与五维审查

## TL;DR

- 团队引入 AI 编程后，PR **体量与频率上升**，Review **不能变轻而应更重要**——AI 擅长产出「表面完整」代码，风险从语法转向**工程与长期维护**。
- 「表面完整」陷阱：类型齐全但约束不准、组件拆了但职责未清、有 try/catch 但不符合规范、有单测但只覆盖成功路径。
- Review 问题应从「有没有 bug」升级为「合入后项目是否**更难维护**」；人工应聚焦业务边界、架构、复用与历史逻辑，格式交给 lint/AI 初筛。
- **五维分维度 Prompt**（bug / 安全 / 性能 / 可维护性 / 代码质量）比泛问「帮我 review」有效得多；须按类/文件拆分投喂，并**过滤 10–20% 误建议**（缺业务上下文）。
- **熟悉度三盲区**：熟悉度遮蔽、沉没成本（舍不得删过度设计）、无外部压力（能跑就不动）——老代码季度 AI Review 价值高于新代码。
- 实战案例：4 年支付服务 AI Review 后删 **31%** 代码（修复 NPE + SQL 注入，砍掉未使用的三层设计模式抽象）；前端删除用户需补确认、防重复、分页回退等 AI 常漏项。

## 适用场景

**何时用：**

- 团队已用 Cursor/Copilot 等，PR 从几百行膨胀到上千行，Review 流于 LGTM。
- 前端 Vue3 + TS 或后端 Java 服务，需要**团队级 Review 清单**与分维度 AI 自查 Prompt。
- 维护多年的「能跑但没人敢动」模块，需要外部视角发现 NPE、注入、过度抽象。
- 与 [方法论笔记](2026-06-08-ai-code-review-workflow-methodology.md)、[Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md) 组合成完整 code-review 专题阅读路径。

**何时不用：**

- 仅需企业自动化流水线——见 [Webhook + RAG 专文](2026-06-08-ai-business-code-review.md)。
- 期望 AI Review 100% 替代人工——业务决策与实时性约束必须人过滤。

## 知识要点

### 1. AI 让 Review 更关键，不是更可有可无

| 变化 | 后果 |
|------|------|
| 产出加速 | 单次 PR 行数、文件数上升 |
| 表面完整 | loading、类型、try/catch、空状态齐全，像「成熟代码」 |
| 隐蔽风险 | 结构不符团队规范、职责混杂、类型仅为编译通过、边界/权限未处理 |

**判断升级**：从「能跑吗」→「长期可维护吗」。

### 2. 「表面完整」对照表

| 看起来 | 实际可能 |
|--------|----------|
| 类型完整 | 与真实接口不一致；`string` 代替联合类型 |
| 组件很多 | 形式拆分，职责仍堆在页面 |
| 有错误处理 | 方式不符合团队约定 |
| 有工具函数 | 项目内已有重复实现 |
| 有单测 | 仅 happy path |
| 能运行 | 权限、异常、边界、竞态未覆盖 |

### 3. AI 缺少的项目级判断

模型难知：团队封装惯例、组件历史设计原因、字段业务含义、复用规划、跨模块影响、维护成本增量。

Review 重心：**工程风险** > 语法风格。

### 4. 前端实战：删除用户（Vue3）

AI 常给出极简版：

```typescript
async function handleDelete(id: string) {
  await deleteUser(id)
  await fetchList()
}
```

Review 须追问：二次确认、防重复点击、失败/成功提示、末条删除后分页回退、权限、操作日志等。

工程版要点：`deleting` 锁、`ElMessageBox.confirm`、try/catch/finally、删除后 `shouldBackToPrevPage` 再 `fetchList`。

### 5. 类型：写了 ≠ 安全

```typescript
// ❌ 仅为编译通过
interface UserItem { status: string }

// ✅ 表达业务约束
type UserStatus = 'enabled' | 'disabled' | 'locked'
const userStatusTextMap: Record<UserStatus, string> = { ... }
```

Review 看类型是否**减少错误**，而非是否存在。

### 6. 人工 Review 四维重点（前端团队）

1. **团队结构**：api 层、types、composables、是否重复造轮子  
2. **组件职责**：页面是否同时扛查询/表格/弹窗/权限/导出  
3. **异常与边界**：失败、空数据、重复提交、并发、切页后请求返回  
4. **重复逻辑**：格式化、权限、分页、上传校验是否已有实现  

### 7. 常见坑

| 坑 | 说明 |
|----|------|
| AI 自查 ≠ 免人工 | 业务上下文（字段为何不展示、角色权限）只有人知道 |
| 不 Review Prompt | 代码离谱时要追问生成 Prompt 是否含规范/分层/禁 any |
| PR 过大 | AI 加速易上千行；应拆类型→composable→组件→页面→单测 |
| 只看功能不看半年后可维护性 | 「完整能跑」最易放过 |

### 8. 团队 AI Code Review 清单（可进 PR 模板）

1. 目录与 request 封装规范  
2. 禁 any / 过度断言  
3. loading、空态、异常  
4. 防重复提交/点击  
5. 无重复逻辑  
6. 可复用组件/工具是否已用  
7. 页面组件是否过重  
8. 单测是否必要且覆盖关键路径  
9. 权限与敏感字段  
10. （生成代码）所用 Prompt 是否含团队约束  

### 9. 五维分维度 Prompt（老代码 / 核心类适用）

```text
请对以下代码做 Code Review，按 5 个维度逐一分析：

1. 潜在 bug（空指针、并发、边界）
2. 安全风险（注入、越权、敏感信息泄露）
3. 性能问题（N+1、大对象、重复计算）
4. 可维护性（职责单一、耦合、扩展性）
5. 代码质量（命名、注释、复杂度）

对每个问题：
- 具体类名/行号
- 为什么是问题
- 修复建议
- 严重程度：严重 / 中 / 低

[粘贴单个类或文件，建议每次一个类，约千行内]
```

**勿用**泛问「帮我 review 一下」——无维度约束会得到无效夸奖。

### 10. 后端实战：4 年服务 Review 摘要

| 发现 | 严重度 | 动作 |
|------|--------|------|
| `order.getItems()` / `getPrice()` 潜在 NPE | 严重 | 入口校验或 Optional |
| 2 种支付方式却 6 类、~340 行设计模式叠床架屋 | 中 | 合并为 ~120 行 `PaymentService`，等真扩展再抽象 |
| `jdbcTemplate` 拼接 SQL 的注入风险 | 严重 | 改参数化查询 |
| 风控接口建议加 5 分钟缓存 | — | **拒绝**：业务要求实时，AI 不知会议上下文 |

结果：1240 行 → 860 行（**-31%**），单测全过，功能一致。

### 11. 熟悉度三盲区（为何自己 Review 不出）

| 盲区 | 表现 |
|------|------|
| 熟悉度遮蔽 | 大脑自动补全「没问题」，回忆式阅读非审查 |
| 沉没成本 | 舍不得删当年「得意」的过度设计 |
| 无外部压力 | 能跑、无投诉则无人回头看 |

AI 优势：**无感情包袱**，只看代码文本（劣势：不懂业务决策，须人过滤）。

### 12. 三条实操建议

1. **分维度 Prompt**，按文件/类拆分投喂  
2. **季度**对「能跑但久未动」模块做 AI Review，不只审新 PR  
3. **过滤误建议**时反问「这段为什么这么写」——能答则写进注释；答不出则可能真该改  

### 13. 与专题其他笔记的分工

| 笔记 | 侧重 |
|------|------|
| **本篇** | 为何 AI 时代 CR 更重、表面合格、清单、五维 Prompt、老代码案例 |
| [方法论](2026-06-08-ai-code-review-workflow-methodology.md) | PR 前自查、分层检查、有效意见写法 |
| [Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md) | 基础/安全/规范三模板、工具集成 |
| [企业流水线](2026-06-08-ai-business-code-review.md) | GitLab Webhook、RAG、Diff 预处理 |

## 代码 / 命令

### 提交前 AI 自查（前端改动）

```text
请按下面维度检查这次前端代码改动：
1. 组件职责是否清晰  2. 重复逻辑  3. Vue3+TS 实践
4. 异常处理  5. any/类型准确度  6. 异步竞态  7. 测试  8. 对已有业务影响

按「问题、影响、修改建议」输出。
```

### 分页删除后回退（示意）

```typescript
function shouldBackToPrevPage(total: number, page: number, pageSize: number) {
  const isLastItemInPage = (total - 1) <= (page - 1) * pageSize
  return page > 1 && isLastItemInPage
}
```

## 注意事项

- 五维 Prompt 产出须人工过滤；实时性、合规、风控等约束只有团队知道。
- 删过度设计前跑全量单测；「YAGNI」不等于永远不抽象，而是**真需要时再抽象**。
- SQL 注入示例为真实生产隐患类型；修复用参数化，勿在笔记中保留可滥用 payload 细节。
- 两篇来源均为社区实战分享（前端团队观 + 后端 4 年服务案例），落地时替换为自有栈与规范。

## 相关链接

- 项目内：[AI Code Review 方法论](2026-06-08-ai-code-review-workflow-methodology.md)（`KB-AI-20260608-ai-code-review-workflow-methodology`）
- 项目内：[AI Code Review Prompt 实战](2026-06-08-ai-code-review-prompt-guide.md)（`KB-AI-20260608-ai-code-review-prompt-guide`）
- 项目内：[业务级 AI Code Review 流水线](2026-06-08-ai-business-code-review.md)（`KB-ARCH-20260608-ai-business-code-review`）
- 项目内：[AI 第一道 Review 两个月实验](2026-06-08-ai-first-gate-review-experiment.md)（`KB-AI-20260608-ai-first-gate-review-experiment`，团队数据与副作用）
- 项目内：[AI Code Review 下一波机会](2026-06-08-ai-code-review-next-wave-trend.md)（`KB-AI-20260608-ai-code-review-next-wave-trend`，行业趋势与 PR 入口）
- 项目内：[16 个提升评审质量方案](2026-06-08-ai-review-quality-16-schemes.md)（`KB-AI-20260608-ai-review-quality-16-schemes`，方案 8/10/11）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-08 | 交叉引用 16 方案质量提升笔记（ING-20260608-015） |
| 2026-06-08 | 交叉引用下一波机会趋势笔记（ING-20260608-014） |
| 2026-06-08 | 交叉引用第一道 Review 实验笔记（ING-20260608-013） |
| 2026-06-08 | 初稿（ING-20260608-012），整合「团队 AI 编程后 Review 更重要」与「AI Review 老代码删 31%」两篇实战 |
