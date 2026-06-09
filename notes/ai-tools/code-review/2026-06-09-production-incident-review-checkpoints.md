---
id: KB-AI-20260609-production-incident-review-checkpoints
module: ai-tools
module_id: MOD-AI
topic: code-review
title: "生产质量报告沉淀：AI Code Review 责任链 R01–R08 + DR 检测规则"
source:
  type: paste
  url: "internal: chenjunxi04_quality_report + chenlu_quality_report (2026-01~2026-05, master)"
  accessed: "2026-06-09"
tags: [code-review, review-checklist, quality-audit, detection-rule, responsibility-chain, incident-driven, agent-prompt, p0-gate]
difficulty: advanced
status: active
related:
  - KB-AI-20260608-ai-code-review-workflow-methodology
  - KB-AI-20260608-ai-coding-era-review-upgrade
  - KB-AI-20260608-ai-code-review-prompt-guide
  - KB-AI-20260608-ai-review-quality-16-schemes
ingest_id: ING-20260609-001
updated: "2026-06-09"
---

# 生产质量报告沉淀：AI Code Review 责任链 R01–R08 + DR 检测规则

## TL;DR

- 从 **123 commits / 47 bugs** 两份质量报告抽象为 **Review 责任链 R01→R08** + **24 条 DR（Detection Rule）**；DR 只描述**不变量与违反信号**，技术栈与业务名词 relegated 到附录实例映射。
- **输出 SSOT**：[`templates/review-report.md`](../../../templates/review-report.md)——Findings 表必须带 `DR 编号 + 严重度 + 违反不变量`，禁止写成「维度 1 问题列表」。
- **审判问句 = DR 的不变量问法**，一条 DR 一问；禁止在问句里出现具体中间件 API、业务字段或 OMSEC 编号。
- **P0 门禁**：命中任意 `默认严重度=P0` 的 DR → R08 Gate=**阻断合入**。
- 与 [分层 Review 方法论](2026-06-08-ai-code-review-workflow-methodology.md) 分工：方法论管**人机流程**，本篇管**判定标准（DR）与报告格式**。

## 适用场景

**何时用：**

- AI Agent 或人工 Review 任意后端/分布式 PR，需要**可审计、可复跑**的判定标准。
- 质量审计报告 triage 后沉淀为 DR，而非一次性「问题清单」。
- 团队要把 Review 产出统一为 **R 链进度 + DR Findings 表**。

**何时不用：**

- 纯样式/lint——静态分析即可。
- 期望 DR 替代业务验收——DR 覆盖工程不变量，不覆盖产品规则细节。

## 知识要点

### 0. 三层模型（避免混写）

| 层 | 名称 | 放什么 | 禁止放什么 |
|----|------|--------|------------|
| **L1** | 不变量（Invariant） | 「进行中工作崩溃后可恢复」 | Redis、Dubbo、审核工单 |
| **L2** | DR 检测规则 | 不变量 + 抽象违反信号 + 默认严重度 | 具体类名、行号 |
| **L3** | 证据（Evidence） | 文件:行、sha、OMSEC | 写入 DR 正文或审判问句 |

**你指出的问题**：初稿把 L3 甚至业务逻辑写进了「审判问句」——现已纠正为 **L1 问句 + L2 信号**，L3 仅出现在 R05/R07 报告。

---

### 1. Review 责任链 R01→R08

> 类比入库 H01→H12；**不可跳步**；R07 必须套用 [`review-report.md`](../../../templates/review-report.md)。

| ID | 名称 | 输入 | 输出 | 说明 |
|----|------|------|------|------|
| **R01** | Intake | diff / PR / 模块路径 | `review_id`、变更规模 | 锁定审查对象与时间窗 |
| **R02** | Scope | 变更文件类型与路径 | **激活的 DR 簇** | 见 §2 路由表；未激活簇标 N/A |
| **R03** | Invariant Scan | 激活簇 | 不变量候选清单 | 只列 L1，不判对错 |
| **R04** | Detect | 候选 + diff | `findings_raw[]` | 逐 DR 问一句，答「是/否/不确定」 |
| **R05** | Evidence | `findings_raw` | 每条绑定 location + 片段 | L3 证据；「不确定」须写缺什么上下文 |
| **R06** | Triage | 证据化 findings | 去重 + P0/P1/P2 | 同一根因合并；升级/降级须注明理由 |
| **R07** | Report | triage 结果 | `review-report.md` 实例 | Findings 表 **DR 列必填** |
| **R08** | Gate | P0 计数 | BLOCK / APPROVE / APPROVE_WITH_P2 | **任一 P0 DR → BLOCK** |

**Agent 回复开头**必须含进度块（与 ingest 对齐）：

```
Review {review_id} · {gate}
- [x] R01 … R08 勾选
```

---

### 2. R02 · DR 簇路由（Scope）

| 变更信号（抽象） | 激活 DR 簇 |
|------------------|------------|
| 鉴权、查询、导出、多租户数据 | SEC + ISO |
| 异步、队列、回调、重试 | DUR + OBS + LIFE |
| 事务、缓存、双写、限流计数 | ATOM + OBS |
| 批量组装、模板、多路列映射 | ID + CTR |
| 线程池、锁、共享入参 | ISO + LIFE |
| 分页、导出、外部 IO、循环调用 | CAP + LIFE |
| 第三方返回值、webhook、枚举映射 | CTR + SEC |
| 大 diff、新模块复制、工具链文件 | CHG |
| 失败分支、异常捕获 | OBS + CTR |

未命中路由时：**10 簇全激活**（全量 Review，成本最高）。

---

### 3. DR 检测规则目录（SSOT）

每条 DR 结构：

```yaml
id: DR-XXX-NN
cluster: 簇代码
invariant: 系统应始终为真的命题（L1）
question: 审判问句（只问不变量，一问一 DR）
violation_signals: 抽象违反信号（L2，可多条）
default_severity: P0 | P1 | P2
gate: 命中是否阻断合入（P0=true）
```

#### SEC · 机密与访问

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-SEC-01** | 凭据与密钥不应进入不可撤销的持久公开面 | 是否存在本应在运行时注入的机密，被写进了版本库或等价永久存储？ | 配置文件/源码含可轮换机密；密钥与代码同生命周期 | P0 |
| **DR-SEC-02** | 敏感数据不应进入高复制、低控制的观测面 | 日志/指标/链路是否可能记录凭据、身份标识或用户内容原文？ | 完整请求体/提示词/身份字段 INFO 级输出 | P1 |
| **DR-SEC-03** | 只读或幂等读通道不应承载高敏感参数 | 是否通过易被缓存、转发、记录的读通道传递机密？ | 敏感参数出现在 URL/query/Referer 可达路径 | P1 |
| **DR-SEC-04** | 每个数据出口须证明调用者在目标 scope 内 | 是否存在未绑定 scope 的数据读取或导出路径？ | 查询/导出缺 ownership 校验；scope 条件可被 NULL/通配放大 | P0 |

#### DUR · 持久与恢复

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-DUR-01** | 进行中工作崩溃后须可恢复或可追查 | 进程异常终止时，已认领未完成的工作是否会无声消失？ | 用易失介质替代持久「处理中」状态；认领与执行非一体 | P0 |
| **DR-DUR-02** | 异步协作须覆盖最晚完成窗口 | 异步流程是否在「对方仍可能响应」之前就销毁了关联状态？ | 回调/迟到事件到达时上下文已被删除 | P0 |
| **DR-DUR-03** | 重试须可终止 | 是否存在失败路径会无限占用执行槽位？ | 无上限重试环；阻塞 worker 且无超时/放弃策略 | P0 |

#### ATOM · 原子与一致边界

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-ATOM-01** | 多副本/多介质状态变更须有一致的成败边界 | 若一半写入成功、一半失败，系统是否定义并可执行一致化策略？ | 双写无补偿；失败吞掉导致永久不一致 | P1 |
| **DR-ATOM-02** | 声明的原子边界须真实生效 | 代码声称的原子/事务边界，在运行时是否实际包住所有关键副作用？ | 装饰性事务；边界内混入不参与回滚的副作用 | P1 |
| **DR-ATOM-03** | 并发更新同一逻辑实体须互斥或幂等 | 两个并发执行路径能否以「后写覆盖」造成 Lost Update？ | 读-改-写无 CAS/锁/版本号；状态机 GET-CHECK-SET | P1 |

#### ID · 标识与关联

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-ID-01** | 并列集合同步变换须保持元素对应 | 多路并行集合经筛选/映射后，是否仍保证同一索引指向同一逻辑实体？ | 一路 filter 其他路未 filter；隐式「等长同序」假设 | P0 |
| **DR-ID-02** | 标识生成与解析须同一规则且冲突可检测 | 同一实体的标识在不同阶段用不同规则生成或解析吗？ | 双 fallback 不一致；随机 ID 无冲突检测 | P0 |
| **DR-ID-03** | 关联键须不可歧义解码 | 是否依赖可嵌入分隔符的字符串编解码来建立对象关联？ | 拼接后再 split 反查；分隔符可出现在合法 payload 中 | P1 |

#### OBS · 失败语义（禁止静默成功）

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-OBS-01** | 失败不得以空/假/默认成功冒充成功 | 调用方能否在失败时被误导为「正常完成」？ | catch 后 return null/false/empty；缺错误态 | P1 |
| **DR-OBS-02** | 已消耗的可计量资源在失败路径须对称 | 失败时是否仍占用配额/令牌/次数而无退还或记录？ | 先扣后用；异常路径无补偿 | P1 |
| **DR-OBS-03** | 异步流程须产生可查询终态 | 长轮询/等待方能否在合理时间内区分成功、失败、超时？ | 异步失败仅打日志；无终态写入 | P1 |

#### ISO · 隔离

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-ISO-01** | 共享入参在调用链中应视为不可变 | 被多处复用的入参对象是否在 callee 内被隐式修改？ | 修改共享 DTO/配置对象字段 | P0 |
| **DR-ISO-02** | 执行上下文绑定的互斥须在同上下文释放 | 绑定特定执行上下文的互斥，是否在上下文切换后仍被持有？ | 锁/TL 跨线程/async 边界 | P0 |
| **DR-ISO-03** | 多租户 scope 须全路径一致 | 是否存在读写路径对 tenant scope 应用不一致？ | 写时带 tenant、读时不带；查重跨 tenant | P0 |

#### LIFE · 资源生命周期

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-LIFE-01** | 并发资源创建与释放须成对 | 是否存在创建了池/客户端/执行器却无对称 shutdown 的路径？ | 双初始化单销毁；每请求 new 池 | P0 |
| **DR-LIFE-02** | 阻塞型工作与计算型共享池应隔离 | IO/阻塞任务是否运行在共享计算池上且无隔离？ | 默认公共池跑阻塞调用 | P1 |

#### CAP · 容量与边界

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-CAP-01** | 单次请求资源消耗须有上界 | 是否存在单次操作可能随数据量线性耗尽内存/连接？ | 全量加载后处理；无 export 上限 | P0 |
| **DR-CAP-02** | 外部依赖等待须 bounded | 对外部依赖的调用是否可能无限等待？ | 缺 timeout；join 无上限 | P1 |
| **DR-CAP-03** | 热路径元操作应 bounded | 热路径是否重复执行与请求量线性相关的元数据操作？ | 循环内反射/解析/远程配置读且无缓存 | P2 |

#### CTR · 外部契约

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-CTR-01** | 外部未知值须映射为显式语义 | 外部系统返回值不在已知集合时，是否仍原样透传下游？ | 未知枚举/suggestion 直接 pass-through | P0 |
| **DR-CTR-02** | 读写可见性假设须匹配 | 写入后立即读的路径，是否与存储可见性延迟假设一致？ | 异步可见 + 同步轮询无兜底 | P1 |
| **DR-CTR-03** | 关键约束顺序须与业务语义一致 | 消耗性操作是否在约束校验之前执行？ | 先产生计费/不可逆副作用，后校验配额 | P0 |

#### CHG · 变更可审性

| DR | 不变量 | 审判问句 | 违反信号（抽象） | 默认 |
|----|--------|----------|------------------|------|
| **DR-CHG-01** | 变更体量须可被人工或 Agent 完整审阅 | 单次变更是否过大或夹带无关产物，导致审查失效？ | 单 MR 数千行；文档/脚手架 >50% | P1 |
| **DR-CHG-02** | 同一概念不应重复实现而无边界 | 是否引入与现有模块并行的第二实现？ | 同名/同责类多份；复制粘贴常量 | P2 |

---

### 4. R04 执行协议（Detect）

对每个**已激活** DR，严格三步：

1. **只问** `question` 一句（L1）。
2. 若「是/很可能」→ 在 diff 中找 **violation_signals** 对应证据（L2→L3）。
3. 写入 finding：`{dr_id, severity, location, invariant, impact, suggestion}`。

**禁止**：跳过 DR 直接写「Top 5 问题」；禁止用技术细节替代 question。

---

### 5. 附录 · 报告实例 → DR 映射（L3 溯源）

> 以下**不得**写入 DR 或审判问句；仅用于证明 DR 来自真实审计。

| DR | 两报告中的实例（摘要） |
|----|------------------------|
| DR-SEC-01 | 生产 API 密钥进 git |
| DR-SEC-04 | 停车统计无租户校验；SQL `OR client_id IS NULL` |
| DR-DUR-01 | 持久队列改进程内集合 |
| DR-DUR-02 | 异步 HTTP 失败 finally 删 task |
| DR-DUR-03 | 限流 while 无限重试 |
| DR-ISO-01 | 修改共享 Chat 请求对象 |
| DR-ISO-02 | 分布式锁跨 async pipeline |
| DR-ID-01 | LLM 并行数组索引错位 |
| DR-ID-02 | uuid 双 fallback 不一致 |
| DR-CTR-01 | 未知 suggestion 原样回传 CMS |
| DR-CTR-03 | LLM 调用后才 TPM 校验 |
| DR-ATOM-03 | GET-CHECK-SET 状态迁移 |
| DR-OBS-01 | catch 返 null 调用方当成功 |
| DR-LIFE-01 | 双 PostConstruct 双 executor |
| DR-CAP-01 | 内存扫全表导出 Excel |
| DR-CHG-01 | 单需求 1.2 万行；plan.backup 进 git |

**统计结论（仍有效）**：膨胀变更与 bug 数正相关——由 **DR-CHG-01** 覆盖，不单独设业务 DR。

---

## 代码 / 命令

### Agent Prompt（责任链 + DR 版）

```text
你是 Code Review Agent。严格按 R01→R08 执行；输出必须套用 templates/review-report.md。

R04：对「已激活 DR 簇」内每条 DR，只问 question 一句，再判 violation_signals。
Findings 表 DR 列必填；禁止输出未绑定 DR 的 findings。
P0 DR 命中 → R08 Gate=BLOCK。

【禁止】在审判问句或 DR 描述中使用：具体中间件类名、业务实体名、OMSEC 编号。
【允许】在 R05 Evidence 的 location 列写 文件:行。

已激活簇：【R02 输出】
PR 背景：【…】
Diff：【…】
```

### Cursor 一句话

```text
按 notes/ai-tools/code-review/2026-06-09-production-incident-review-checkpoints.md
执行 R01→R08，输出 templates/review-report.md 格式。
```

### 报告模板路径

[`templates/review-report.md`](../../../templates/review-report.md)

## 注意事项

- **DR 稳定、实例会变**：新事故应新增 appendix 映射，而非改写 question。
- **「不确定」不是通过**：R05 须列出缺失的 scope/上下文，R08 默认 **需人类确认**。
- DR 不覆盖产品规则正确性——例如「审核策略是否该 ignore」属产品，但「失败伪装成功」由 **DR-OBS-01 / DR-CTR-03** 覆盖。
- 与 [五维 Review](2026-06-08-ai-coding-era-review-upgrade.md) 互补：五维偏认知框架，本篇偏**可执行判定表**。

## 相关链接

- 报告模板：[`templates/review-report.md`](../../../templates/review-report.md)
- 溯源：`chenjunxi04_quality_report.md`、`chenlu_quality_report.md`
- 项目内：[AI Code Review 方法论](2026-06-08-ai-code-review-workflow-methodology.md) · `KB-AI-20260608-ai-code-review-workflow-methodology`
- 项目内：[AI 编程时代 Review 升级](2026-06-08-ai-coding-era-review-upgrade.md) · `KB-AI-20260608-ai-coding-era-review-upgrade`

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-09 | v2：改为 R01–R08 责任链 + 24 条 DR；审判问句抽象为不变量；新增 review-report 模板；技术/业务细节下沉附录 |
| 2026-06-09 | v1（ING-20260609-001）：初稿 10 维清单（已废弃结构） |
