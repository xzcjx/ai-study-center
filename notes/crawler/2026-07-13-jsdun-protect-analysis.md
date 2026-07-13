---
id: "KB-CR-20260713-jsdun-protect-analysis"
module: crawler
module_id: MOD-CR
title: "JS 盾（JS DUN PROTECT）加固逆向分析：虚拟方法表、双层 VM 与壳机制"
source:
  type: url
  url: "https://bbs.kanxue.com/thread-291766.htm"
  accessed: "2026-07-13"
  author: "人生导师/一只鸭子（看雪论坛）"
tags: [js-reverse, jsvmp, vmp, anti-crawler, code-protection, js-shield, jsdun, virtual-method-table, dispatcher, opcode, eval-iife, obfuscation, shell, real-case]
difficulty: advanced
status: active
related: ["KB-CR-20260611-jsvmp-overview-protection-landscape", "KB-CR-20260611-jsvmp-virtualization-pipeline", "KB-CR-20260611-jsvmp-interpreter-design", "KB-CR-20260611-rs-vmp-dynamic-code-generation", "KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated", "KB-CR-20260713-amap-alibaba-security-reverse"]
ingest_id: "ING-20260713-002"
updated: "2026-07-13"
---

# JS 盾（JS DUN PROTECT）加固逆向分析：虚拟方法表、双层 VM 与壳机制

## TL;DR

- **JS盾设计思路强但"浪费生命"**：双层动态代码执行 + VM 指令集完整覆盖 + 独一档的虚拟方法表（`X.$`），但强度核心在于**膨胀**而非精巧——单段 `console.log` 加固后格式化达 24000 行 JSVMP
- **`&& 0 || expr` 短路表达式链**是整个加固最有价值的部分：将顺序语句伪装成表达式链，把 `eval` 内 IIFE 的整个执行流程串成一条 `return && ... || ... && 0 || ...` 的超长链，未见别家用过
- **虚拟方法表 `X.$` 三层设计**：① 操作原语表（vtable，用字符串 key 隐藏真实函数引用）→ ② 调度器 `X.$[8]`（两层 `.call` 间接调用，静态分析完全无法推断调用目标）→ ③ opcode 化（JS 原生方法被编号成指令，与 VM 字节码处于同一抽象层级）
- **壳机制类比 Android 加固**：用 `Function` 构造器加载加密运行时 → 自解密产出检测代码 + 主 VM 代码 + 补环境检测
- **作者警告**：除非有明确业务需求，不要对抗这个东西——VSCode 直接因括号嵌套崩溃，格式化会触发壳检测拒绝执行

## 适用场景

**何时用：**

- 遇到 JS盾加固的目标页面，需理解其 VM 架构和检测机制
- 设计自研 JSVMP 保护方案，参考其虚拟方法表 + 调度器统一入口的设计模式
- 研究商业 JS 代码保护产品的架构边界

**何时不用：**

- 目标是快速产出签名/参数（**走补环境路径**：`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`）
- 没有明确业务需求纯粹出于好奇——作者原话："非常非常浪费生命"
- 仅是常规 ob 混淆而非 JSVMP（参考 `KB-CR-20260611-jsvmp-overview-protection-landscape` 区分）

## 知识要点

### 1. 加固产物规模与分析方法

**测试用例**：仅一段 `console.log`。

**加固产物**：字节码满天飞，调用链极度混乱。VSCode 直接崩溃——括号嵌套完全打乱，格式化产出不可信。最终使用 **Vim 手动分析**。

**核心分析方法**：先看括号闭合状态，看结构而非变量名。因为所有函数调用被间接化为数组索引 + `.call`，变量名是噪音。

### 2. eval IIFE + `&& 0 || expr` 短路表达式链

整个文件骨架结构：

```
eval(function(r, Z) {
  return expr1 && 0 || expr2 && 0 || expr3 && 0 || ... ;
}(bytecode, undefined))
```

- `r`：接收字节码
- `Z`：始终为 `undefined`，用于短路判断
- 函数体是**一条 `return` 语句**，用 `&&` 和 `||` 短路运算串起来的超长表达式链

**按顺序完成三件事**：
1. 第一轮 VM 执行
2. 取出第二轮 VM 的字节码与执行环境
3. 第二轮 VM 执行

**`&& 0 || expr` 模式**本质是"先执行副作用（`expr1`），再跳到下一个表达式"——将顺序语句伪装成表达式链。作者评价：**这是整个加固里最有价值的部分，没见别家用过。**

```javascript
// 伪代码等价还原
// X && 0 || Y   ≈   X; Y
// 即：先执行 X 获取副作用，短路到 0，|| 触发下一个表达式 Y 的执行

// 最终效果：一条 return 语句完成全部初始化流程
return (
  vm_round1_execute() && 0 ||
  extract_round2_bytecode() && 0 ||
  vm_round2_execute() && 0 ||
  final_result
)
```

### 3. 虚拟方法表（X.$）三层设计

作者认为这是 JS盾 最核心也最具启发性的设计。

#### 第一层：操作原语表（vtable）

```javascript
// 三行代码构造 VM 的操作原语表
// 每项对应一个底层操作（push, call, get, set, ...）
// 构造过程有前置副作用：用字符串 key 将真实函数引用藏起来
// Object.keys 遍历根本看不到——因为 JS 函数本质是对象，可挂任意属性
```

**关键技巧**：真实函数引用不暴露在数组值中，而是挂在函数对象的**非枚举属性**上。`Object.keys` 遍历时看不到，但运行时可通过预知的字符串 key 取出。

#### 第二层：调度器（X.$[8]）

调度器是 VM 的核心执行引擎：

```javascript
// 核心表达式
X.$[1][X.$[0]](targetFunc, thisArg, ...args)
// 本质等价于: targetFunc.call(thisArg, ...args)
// 但静态分析看到的是：属性访问 + 间接 call，无法推断调用目标
```

- 所有栈操作和函数调用全部收敛到此入口
- 通过函数 opcode 参数选择目标
- **两层 `.call` 间接调用**：一是取到 `call` 方法本身，二是用它调用目标函数

#### 第三层：设计意图

| 目的 | 实现方式 |
|------|----------|
| **破坏 AST 可读性** | 无任何直接函数调用 → 全部变成数组索引 + 间接 call → AST 分析工具基本废了 |
| **统一执行入口** | 所有底层操作走一个调度器 → 方便做 hook 检测 → 如有人 hook 了 push/call，调度器可感知异常 |
| **opcode 化** | JS 原生方法被编号成指令 → 与 VM 字节码指令集处于同一抽象层级 → 执行流完全在 VM 控制之下 |

### 4. 壳机制：类比 Android 加固

JS盾的壳与 Android APP 加固思路高度相似，但无需 mmap 开辟空间——直接用 `Function` 构造器搞定：

```
┌──────────────────────────────────────────┐
│ 1. 加载壳代码（加密后的运行时）             │
│    ↓ Function 构造器动态执行               │
│ 2. 壳自解密                               │
│    ├── 产出检测代码（环境指纹 + 反调试）    │
│    └── 产出主 VM 代码（原始约 13000 行）   │
│ 3. 补环境（document / navigator / location）│
│    ↓ 壳代码主动探测浏览器特征               │
│ 4. 解密后 JSVMP 代码（格式化后 24000 行）  │
│    → 作者称见过的最大 JSVMP                 │
└──────────────────────────────────────────┘
```

**补环境后可在 Node 上运行解密产物**。

### 5. 格式化触发检测

**关键坑**：格式化代码会触发壳的检测逻辑导致拒绝执行。

**解决办法**：
- **不格式化直接补环境跑**（推荐，但调试极困难）
- 自己写可靠的反混淆器（成本远超预期）

### 6. 作者建议的三层保护方案设计

从学习角度，作者整理了一个递进式保护方案：

| 层级 | 内容 | 目的 |
|------|------|------|
| **第一层** | AST 混淆 + 字符串加密 | 熟悉代码隐藏→恢复→执行的完整流程，不涉及 VM |
| **第二层** | 简单 VM（解释器模式） | 支持几十条基础指令，把简单 JS 编译成自己的字节码再写解释器执行 |
| **第三层** | 动态化 VM（随机化） | opcode 映射、栈结构、方法表索引均可随机化，每次产出的 VM 结构不同 |

## 代码 / 命令

```javascript
// && 0 || expr 模式的语义等价还原
// 原始形式:
//   exprA && 0 || exprB && 0 || exprC
// 等价于:
//   exprA; exprB; exprC

// 调度器核心：两层 .call 间接调用
// X.$[1] 是 Function.prototype.call
// X.$[0] 是当前 opcode 对应的目标函数引用
// 实际调用链: call.call(targetFunc, thisArg, ...args)
//            = targetFunc.call(thisArg, ...args)

// 虚拟方法表构造示意（简化版）
const vtable = [];
vtable[0] = Array.prototype.push;    // opcode 0: push
vtable[1] = Function.prototype.call; // opcode 1: call（调度器核心）
vtable[2] = Object.getOwnPropertyDescriptor; // opcode 2: ...

// 用非枚举属性隐藏真实函数引用
const REAL_PUSH = Array.prototype.push;
vtable[0].__hidden_real = REAL_PUSH; // Object.keys 不可见
```

## 注意事项

- **VSCode/IDE 会直接崩溃**：括号嵌套完全打乱，格式化输出不可信，需要用 Vim 等轻量编辑器
- **格式化触发检测**：壳代码有完整性校验，任何格式化/美化操作可能导致拒绝执行
- **不要手动对抗**：作者原话"除非有明确的业务需求，不要对抗这个东西，非常非常浪费生命"
- **补环境是可行路径**：壳解密后代码可在 Node 上运行（配合足够逼真的假浏览器环境）
- **静态分析工具基本废了**：虚拟方法表 + 间接 call 使 AST 分析产出不可读

## 相关链接

- [原文：看雪论坛 — JS盾（JS DUN PROTECT）加固小记](https://bbs.kanxue.com/thread-291766.htm)
- 项目内：
  - [JSVMP 概述与 JS 代码保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线：AST 拆分→字节码编码](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — 字节码生成流程
  - [JSVMP 虚拟解释器设计：WASM 编译与调度机制](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — 解释器架构参考
  - [瑞数 VMP 动态代码生成原理逆向分析](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`) — 另一商业 VMP 加固逆向
  - [a_bogus 补环境 + AI 加速全流程](../crawler/2026-07-13-a-bogus-env-spoofing-ai-accelerated.md) (`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`) — 补环境路径：对抗 VMP 的另一方法论

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-13 | 初稿（ING-20260713-002）：看雪论坛 JS盾加固逆向分析 |