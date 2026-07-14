---
id: "KB-CR-20260713-jsvmp-reverse-master-guide"
module: crawler
module_id: MOD-CR
title: "JSVMP 逆向方法论总纲：四条路径、决策树与完整工具链"
source:
  type: internal
  url: "基于知识库 13 篇 JSVMP 相关笔记综合总结"
  accessed: "2026-07-13"
tags: [js-reverse, jsvmp, vmp, anti-crawler, core-methodology, decision-tree, path-selection, env-spoofing, hook, instrumentation, bytecode, ast, handler, deobfuscation, ai-assisted, master-guide]
difficulty: intermediate
status: active
related:
  - "KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated"
  - "KB-CR-20260713-jsvmp-decompile-restore-full-workflow"
  - "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
  - "KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature"
  - "KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis"
  - "KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha"
  - "KB-CR-20260611-jsvmp-overview-protection-landscape"
  - "KB-CR-20260611-jsvmp-virtualization-pipeline"
  - "KB-CR-20260611-jsvmp-interpreter-design"
  - "KB-CR-20260611-sdenv-node-addon-document-all"
  - "KB-CR-20260713-jsdun-protect-analysis"
  - "KB-CR-20260713-amap-alibaba-security-reverse"
ingest_id: "ING-20260713-005"
updated: "2026-07-13"
---

# JSVMP 逆向方法论总纲：四条路径、决策树与完整工具链

> **写这篇的目的**：遇到一个 JSVMP 保护的目标，从"我该怎么办"到"用哪条路、怎么做、产出什么"，这一篇就够了。
>
> 本文基于知识库中 13 篇 JSVMP 相关笔记的系统性总结。

## TL;DR

- **有四条路径可选，不是只有一条**：① 补环境绕过（最快出结果）→ ② 动态插桩追踪（中间路线）→ ③ AST 静态反编译（最彻底）→ ④ AI 辅助混合（最智能）。选错路径是最大的时间损失
- **决策树帮你选**：目标只要签名参数 → 走①；需要理解算法但不要求源码 → 走②；需要可读可复用的源码 → 走③；VM 极其复杂 + 有 AI 工具 → 走④
- **补环境是对抗 JSVMP 的首选路径**：只要 SDK 可以离线执行且不深度依赖 DOM，构建假浏览器环境直接跑原始 SDK 是 80% 场景下性价比最高的方案
- **如果想深入理解"反编译是怎么做到的"**：核心链条是「识别解释器循环 → 定位 PC 寄存器和分发器 → 解码字节码 → 建立 handler→操作 映射表 → 生成 AST → 后处理结构化」
- **AI 在逆向中的正确用法**：不是替代你写代码，而是加速「提出假设→验证→修正」的探索循环。给 AI 足够上下文再让它分析，发现它"偷懒"走捷径时及时纠正

## 适用场景

**何时用这篇：**

- 第一次遇到 JSVMP 保护的目标，不知道从哪下手
- 已经在某个路径上卡了很久，想确认是否选错了路
- 需要向团队解释 JSVMP 逆向的全貌和可选方案

**何时不用：**

- 已经确定了路径并需要深入细节 → 跳转到对应的专题笔记
- 目标只是普通 ob 混淆而非 JSVMP → 不需要这篇

***

## 知识要点

> 本文为方法论总纲，知识要点散布于六章中。以下是各章定位导航：

| 章节 | 回答什么问题 |
|------|-------------|
| 第一章 | 四条路径分别是什么？各自产出什么？ |
| 第二章 | 遇到 JSVMP 我该选哪条路？（决策树） |
| 第三章 | 选好了路，每一步具体怎么做？ |
| 第四章 | 不管选哪条路，都要做的通用前置步骤是什么？ |
| 第五章 | 知识库里有哪些相关笔记可以深入阅读？ |
| 第六章 | 常见疑问速查（Q&A） |

## 第一章：四路径全景图

JSVMP 逆向存在四条主要路径，它们的**输入相同**（被 JSVMP 保护的 JS 代码）、**产出不同**：

```
                        ┌──────────────────────────────┐
                        │  被 JSVMP 保护的 JS 代码      │
                        │  （字节码 + 解释器 + 检测）    │
                        └──────────────┬───────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
    ┌───────▼───────┐          ┌───────▼───────┐          ┌───────▼───────┐
    │  路径一        │          │  路径二        │          │  路径三        │
    │  补环境绕过    │          │  动态插桩追踪  │          │  静态反编译    │
    │               │          │               │          │               │
    │ 产出: 签名/参数│          │ 产出: 伪代码   │          │ 产出: 可读源码 │
    │ 周期: 小时级   │          │ 周期: 天级     │          │ 周期: 周级     │
    │ 可复用性: 低   │          │ 可复用性: 中   │          │ 可复用性: 高   │
    └───────┬───────┘          └───────┬───────┘          └───────┬───────┘
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       │
                               ┌───────▼───────┐
                               │  路径四        │
                               │  AI 辅助混合   │
                               │               │
                               │ 产出: 视目标定 │
                               │ 周期: 加速50%+ │
                               │ 多路径融合     │
                               └───────────────┘
```

### 路径一：补环境绕过（推荐首选）

**一句话**：不还原算法，构建假浏览器环境直接执行原始 SDK 离线产出签名。

**代表笔记**：`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`、`KB-CR-20260713-amap-alibaba-security-reverse`

**核心流程**：
```
抓取 SDK 文件（线上实时抓，不用镜像）
  → 追踪环境（trace_env.js 自愈 Proxy 自动发现缺失属性）
  → 构建 fake_env.js（navigator/DOM/存储/平台类/WebGL）
  → 构建假 XHR（捕获签名钩子）
  → SDK 初始化配置（paths/aid 从浏览器 DevTools 复制）
  → 锁定随机性（调试用，Math.random=()=>0.5）
  → TLS 指纹绕过（curl_cffi / cycletls）
  → 线上验证（唯一充分证据）
```

**优点**：最快出结果（小时级），不需要理解 VM 内部逻辑，面对 >100KB 字节码时是唯一可行方案

**缺点**：SDK 版本更新后可能失效，强依赖 DOM 渲染的场景无法使用

**适用条件**：
- SDK 可以离线加载执行（不依赖实时 Canvas 指纹等 DOM 渲染结果）
- 追求稳定高频产出（配合持久化签名服务器 `sign.js --server`）
- 目标 SDK 文件数量少（通常 1-3 个）

### 路径二：动态插桩追踪

**一句话**：在解释器关键位置注入日志，运行时记录每个 VM 操作的输入输出，从日志反推原始算法。

**代表笔记**：`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`、`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`

**核心流程**：
```
定位 JSVMP 解释器（while + switch 循环结构）
  → 识别核心变量（PC/opcode/栈/寄存器）
  → 在解释器循环内插桩（注入日志代码）
  → 运行 → 收集操作日志（opcode 序列 + 操作数值）
  → 从日志反推原始算法逻辑
  → 输出伪代码或直接实现算法
```

**优点**：不需要理解每个 handler 的语义（只需要追踪数据流），对 ob + JSVMP 双层保护有效

**缺点**：日志量可能极大（几千条指令），需要运行环境支持

**适用条件**：
- 目标代码可成功执行（补环境或浏览器中）
- 需要理解签名算法的逻辑但不要求完整源码
- 解释器结构清晰可定位（while-switch 模式）

### 路径三：AST 静态反编译（最彻底，成本最高）

**一句话**：将 JSVMP 字节码完整还原为可读的 JS 源码，通过 handler 语义映射生成 AST。

**代表笔记**：`KB-CR-20260713-jsvmp-decompile-restore-full-workflow`、`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`

**核心流程**：
```
解码字节码（atob → &0xFF → 字节数组）
  → 识别 VM 架构（寄存器式 vs 栈式，PC 寄存器定位）
  → 核心函数识别（N=写寄存器, y=读寄存器, C=分发器, B8=取指解密）
  → 分析分发器 C 的分支逻辑（bit-pattern → 指令类型分类）
  → 逐个 handler 做语义分析 → 建立 handler→AST节点 映射表
  → 模拟执行（不真跑，模拟 PC 递增和寄存器状态）
    ├── B8 取指+流密码解密
    ├── C 分发 → 确定操作数格式
    ├── 路由到 handler 映射 → 生成对应 AST 节点
    └── 追加到 AST 树
  → 后处理：平坦化→结构化（合并 if-else、识别 while、展开函数递归）
  → 代码生成（escodegen/babel-generator）
```

**优点**：产出完整可读源码，可跨版本迁移（改映射表即可），适合研究型工作

**缺点**：周期以周计，面对超大 VM（几万条指令）成本不可控，OP 随机化的 VM 需要大量适配

**适用条件**：
- VM 架构相对稳定（非每次加载随机化 handler 映射）
- 代码量可控（1000-5000 条指令级别）
- 需要得到可复用的源码级产出

### 路径四：AI 辅助混合

**一句话**：将 AI 作为"加速引擎"，在以上任一路径中加速最关键又最耗时的工作。

**代表笔记**：`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`、`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`

**AI 在四个环节的加速效果**：

| 环节 | AI 作用 | 加速倍数 | 适合哪条路径 |
|------|---------|----------|-------------|
| 环境桩类型修正 | 读取追踪日志 → 识别类型不匹配 → 批量修正 | ~10× | 路径一 |
| Base64 字母表/密钥识别 | 快速编写和运行匹配脚本 | ~5× | 所有路径 |
| 系统性实验 | 提出假设→AI 生成实验脚本→批量运行→分析结果 | ~20× | 所有路径 |
| 模板批量定制 | 一次性完成所有 TODO 占位符替换 | ~5-10× | 路径一/三 |
| Handler 语义分析 | 分析 VM 中大量循环和 case 分支 | ~50% 时间减少 | 路径二/三 |
| opcode 自动识别 | 代码特征匹配 + 反汇编 | 数天→数小时 | 路径三 |

**AI 使用原则（来自实战总结）**：
- ✅ 给 AI**足够上下文**再让它分析（结合浏览器正常运行环境）
- ✅ 遇到不符合预期的输出时**及时阻止并引导**
- ❌ 不要什么都不看就一味让 AI 执行
- ❌ AI 会偷懒走 Playwright 无头浏览器方案——这不是你要的路径一
- ❌ AI 面对大量 case 分支时会走猜测路径——猜测往往得出荒唐结论

***

## 第二章：决策树——遇到 JSVMP 先问自己三个问题

```
目标被 JSVMP 保护
    │
    ├─ Q1：你需要什么产出？
    │   ├── 只要签名/参数，能调通接口就行
    │   │   └── 走路径一：补环境绕过 ★首选
    │   │
    │   ├── 需要理解算法逻辑，但不要求完整源码
    │   │   └── 走路径二：动态插桩追踪
    │   │
    │   └── 需要完整可读的源码，长期复用
    │       └── 走路径三：静态反编译
    │
    ├─ Q2：SDK 代码量多大？
    │   ├── < 500 KB，指令数 < 5000
    │   │   └── 路径二/三可行
    │   │
    │   └── > 1 MB，指令数 > 10000
    │       └── 放弃路径三，走路径一或路径二
    │           （参考：JS盾格式化后 24000 行，作者劝退）
    │
    └─ Q3：SDK 是否深度依赖 DOM/渲染？
        ├── 不依赖（纯计算型签名）
        │   └── 路径一可行（最简单的场景）
        │
        ├── 轻度依赖（WebGL 指纹 / Canvas 指纹）
        │   └── 路径一可行，需要完整 WebGL/Canvas mock
        │
        └── 重度依赖（实时渲染 / 用户交互轨迹验证）
            └── 路径一不可行，走路径二/三
```

### 快速自测清单

遇到新目标时，按顺序做了这些事，你就在正确的路上：

```
□ 1. 打开浏览器 DevTools → Sources → 搜索 .init( 定位 SDK 入口
□ 2. 查看加载的 JS 文件大小（>100KB → 严肃对待）
□ 3. 判断 SDK 是否可离线执行（补环境可行性）
□ 4. 确定产出目标（参数 vs 算法 vs 源码）
□ 5. 选择路径
□ 6. 不管哪条路，先做 SDK 抓取（capture_sdk.js / 手动保存）
□ 7. 确认是否每次加载 SDK 代码结构变化
□ 8. 开始执行
```

***

## 第三章：四条路径的详细工作流

### 路径一完整工作流（补环境绕过）

```
Phase 1: SDK 抓取
  capture_sdk.js (Playwright) → 按 >20KB + URL 正则匹配过滤
  → bundles/ 目录 + manifest.json (SHA-256)
  
Phase 2: 自动化环境追踪 ★核心创新
  trace_env.js:
    guessDefault() → ~80 个启发式猜值规则
    makeHealer()  → 递归 2 层 Proxy 自动补全
    自动重跑      → 最多 8 轮自愈
  输出: fake_env.js

Phase 3: 构建假浏览器环境
  navigator 层 (~40 属性): UA, platform, hardwareConcurrency=8, deviceMemory=8
  DOM 层: document.createElement, canvas 2D/webgl
  存储层: localStorage/sessionStorage (Storage 原型类)
  平台类: Headers/Request/Response/FormData/Blob (typeof===function)
  Observer: IntersectionObserver/MutationObserver/ResizeObserver (空类)
  反检测: process/Deno/require/global/module 全部 undefined

Phase 4: 假 XHR + 签名提取
  SDK hook XMLHttpRequest.prototype.send
  fake XHR responseText 需返回合法 JSON（data.d 等字段）
  window.bdms.init() 触发签名
  URL 中提取签名字段

Phase 5: init() 配置 + paths 发现 ★最高频静默故障点
  浏览器 DevTools → 全文搜索 .init(
  paths 是正则前缀数组，不是字面量路径

Phase 5.5: 轨迹数据注入 + debug_trajectory.js 诊断

Phase 6: 锁定随机性（调试用，生产不用）
  Math.random = () => 0.5; Date.now = () => 1700000000000;

Phase 7: TLS 指纹 + 线上验证
  curl_cffi / cycletls 模拟 TLS 指纹
  真实 HTTP 往返验证是唯一充分证据
```

**关键踩坑点**（五个静默故障点）：

| 踩坑点 | 症状 | 解决 |
|--------|------|------|
| 凭记忆写 stub | SDK 在各种奇怪属性上崩溃 | 永远先 trace 再补全 |
| TLS 指纹未模拟 | 签名正确但返回 200 空 body | 使用 curl_cffi impersonate |
| URL 参数顺序打乱 | 签名校验失败 | 保持原始参数顺序（不用 URLSearchParams.toString()） |
| 假 XHR 响应 JSON 不完整 | SDK 静默跳过初始化 | 确保 responseText 含 data.d 等字段 |
| SDK 定时器未清理 | Node 进程不退出 | 显式 process.exit(0) |

**生产级部署**：
```
sign.js --server (持久化 Node 进程)
  + persistent_signer.py (Python 客户端管理生命周期)
  → 首次 ~1500ms，后续零开销
```

### 路径二完整工作流（动态插桩追踪）

```
Step 1: 定位解释器
  搜索特征: while(true) 或 for(;;) + switch 结构
  确认变量: PC、opcode 数组、操作数栈/寄存器

Step 2: 提取字节码
  定位字节码数组（通常是一个大数组，包含操作码）
  console.log(n[0], n[1], n[2]) 确认完整性

Step 3: 识别解释器核心变量（参考 JSVMP 理论三篇）
  栈式 VM: stack[], push/pop
  寄存器式 VM: registers[512], N()/y()
  PC: 循环中规律递增的变量（从 n[PC] 取指令）

Step 4: 插桩
  在每个 opcode 执行前注入日志:
  console.log(`[${pc}] opcode=${op} stack=${JSON.stringify(stack)}`)
  
  关键插桩位置（参考 ob-bypass 笔记）:
  定位 JSVMP 解释器中的 apply 调用（opcode=0x1f）
  在此层注入日志，记录每次 VM 操作的输入/输出

Step 5: 运行 → 收集日志
  日志内容: opcode 序列 + 操作数值 + 函数调用参数/返回值
  注意: 日志量可能几千行

Step 6: 日志分析 → 反推算法
  从操作符序列识别算法模式:
  - XOR+XOR+XOR = 可能是加密轮
  - 大量位运算 = 可能是哈希
  - 字符拼接 = 可能是参数构造
```

### 路径三完整工作流（AST 静态反编译）

```
Step 1: 解码指令集
  atob → &0xFF → 纯字节数组

Step 2: 识别 VM 架构 + 核心函数
  关键函数定位（通过行为模式而非变量名）:
  N(regId, val) → 写寄存器（内部 arr[idx]=val）
  y(regId)     → 读寄存器（内部 return arr[idx]）
  C(opcode)    → 指令分发器（含多路位运算条件分支）
  B8()         → 取指令+流密码解密
  hJ()         → 密钥轮换（8 字节解密表）

Step 3: 分析 C 分发器的分支逻辑
  核心是 bit-pattern 匹配（不是 switch）:
  - w|48==w          → 寄存器写入
  - w-5|5>=w && ...  → 条件/值设置
  - w>>1&12<12 && ...→ 变长指令
  - w+5>>3==1        → 寄存器值偏移
  - w+7^27<w && ...  → 变长读取+密钥轮换

Step 4: 建立 handler→AST 映射表
  逐个分析 handler 的操作语义:
  - handler 24  → 4 字节赋值 → Literal + AssignmentExpression
  - handler 302 → 函数调用   → CallExpression
  - handler 495 → 对象属性   → MemberExpression
  - handler 122 → eval 调用  → CallExpression(callee=eval)
  - handler 149/220/446 → AES 加密轮

Step 5: 模拟执行 → AST 生成
  while (pc < bytecode.length) {
    opcode = B8(pc);                 // 取指+解密
    instrType = C(opcode);           // 分发
    operands = readOperands(instrType);  // 读取操作数
    astNode = handlerToAST(handlerId, operands);  // 映射
    blockStatement.body.push(astNode);             // 追加
    detectAndSkipAntiDebug();         // 跳过反调试
  }

Step 6: 后处理（结构化）
  - if-else 合并: PC 分支→汇合的节点合并
  - while 循环识别: PC 回跳 → 改写循环结构
  - 函数递归展开: PC 远跳→返回 → 提取函数声明
  - 反调试剥离: 死循环跳转→删除对应 AST 节点

Step 7: 代码生成
  escodegen.generate(ast) → 可读 JS 源码
```

### 路径四与其他路径的结合方式

```
AI 加入的时机：

路径一 + AI:
  环境追踪日志分析（AI 读日志→识别类型错误→批量修正）
  模板定制（AI 替换所有 TODO 占位符）
  系统性实验（172 vs 192 实验，AI 生成+运行+分析）

路径二 + AI:
  Handler 语义分析（AI 擅长处理大量 VM case 分支）
  日志模式识别（从几千条日志中识别算法模式）

路径三 + AI:
  opcode 自动识别（58 个 handler 代码特征匹配）
  反汇编（214 个函数、24000+ 条指令）
  AST 后处理（合并 if-else、识别循环）
```

***

## 第四章：所有路径的通用前置步骤

不管选哪条路，以下步骤是**必须做的**：

### 前置 1：SDK 抓取

**原则：永远从目标站点线上实时抓取，不要从 GitHub 镜像或博客复制。** SDK 版本以周为单位变化，过期文件导致签名被静默拒绝。

```javascript
// capture_sdk.js 核心逻辑
// 1. Playwright 打开目标页面
// 2. 过滤 JS 响应: 文件大小 > 20KB
// 3. URL 正则匹配: vmp|protect|crawler|risk|sec|sdk|runtime|bundler|glue|loader|sign|guard|shield
// 4. 保存到 bundles/ + 生成含 SHA-256 的 manifest.json
```

### 前置 2：判断 VM 类型

| 特征 | 含义 | 相关笔记 |
|------|------|----------|
| while+switch 循环 + 大数组 | 栈式 VM | 某Q音乐、CHAOS VM |
| 512 寄存器 + N/y 读写函数 | 寄存器式 VM | 反编译全流程 |
| `X.$[]` 虚拟方法表 + 两层 .call | JS盾风格 | JS盾分析 |
| `eval(IIFE)` + `&& 0 \|\| expr` | eval 链 + 短路伪装 | JS盾分析 |
| `Function` 构造器 + 壳解密 | Android 加固风格 | JS盾分析 |
| 流密码逐字节解密指令 | 动态密钥流 | 反编译全流程 |

### 前置 3：确定 SDK 版本稳定性

每次加载时比较：
- 文件 SHA-256 是否变化？
- opcode 映射是否变化？
- 字节码数组是否变化？

如果每次加载都完全变化 → 放弃路径三 → 走路径一或二。

### 前置 4：使用 AI 的通用原则

1. **先自己看懂大局**再让 AI 分析细节（AI 不知道什么重要什么不重要）
2. **给 AI 完整上下文**（浏览器正常运行环境 + 已分析出的结构信息）
3. **AI 走捷径时及时纠正**（Playwright 方案 = 路径一的劣化版）
4. **AI 猜测时补充信息**（case 分支多时，不是让 AI 猜而是给更多实际运行数据）
5. **AI 生成好后自己验证**（交叉对比浏览器 vs 本地产出的签名/参数）

***

## 第五章：知识库导航

按阅读顺序排列，从理论到实战：

### 理论篇（先读）

| 笔记 | 回答什么问题 |
|------|-------------|
| [JSVMP 概述与保护全景](2026-06-11-jsvmp-overview-protection-landscape.md) | JSVMP 是什么、为什么需要它 |
| [JSVMP 虚拟化流水线](2026-06-11-jsvmp-virtualization-pipeline.md) | 正向：JS 代码如何变成字节码（五阶段） |
| [JSVMP 虚拟解释器设计](2026-06-11-jsvmp-interpreter-design.md) | 正向：解释器如何执行字节码（五大组件） |

### 路径一：补环境（最常用）

| 笔记 | 核心价值 |
|------|----------|
| [a_bogus 补环境 + AI 加速](2026-07-13-a-bogus-env-spoofing-ai-accelerated.md) | **首选阅读**——完整的 7 阶段补环境工作流 + trace_env.js 自愈 Proxy + 生产级持久化签名架构 |
| [某德地图阿里系安全防护](2026-07-13-amap-alibaba-security-reverse.md) | 阿里系 fireyejs/baxia 体系 + bx-ua/x-dc 双参数 + AI 辅助方法论原则 |
| [补环境框架：document.all C++ Addon](2026-06-11-sdenv-node-addon-document-all.md) | 纯 JS 无法模拟的底层 API 的 Node Addon 方案 |

### 路径二：动态插桩

| 笔记 | 核心价值 |
|------|----------|
| [某Q音乐 JSVMP 插桩还原](2026-06-11-qqmusic-jsvmp-reverse-engineering.md) | 完整的解释器定位→插桩→指令还原流程 |
| [绕过 OB 直捣 JSVMP](2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) | ob + JSVMP 双层保护的动态插桩实战 |

### 路径三：静态反编译

| 笔记 | 核心价值 |
|------|----------|
| [JSVMP 反编译还原全流程](2026-07-13-jsvmp-decompile-restore-full-workflow.md) | **反编译方法论圣经**——寄存器式 VM → C 分发器 5 路 bit-pattern → handler→AST 映射 |
| [AST 还原 X-Bogus/_signature](2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) | 完整的 AST 静态还原 + if-else 合并 + 循环识别技巧 |

### 路径四：AI 辅助 + 保护机制研究

| 笔记 | 核心价值 |
|------|----------|
| [AI 辅助 CHAOS VM 验证码](2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) | opcode 自动识别 + 模块指纹 + MCP 工具链 |
| [瑞数 VMP 动态代码生成](2026-06-11-rs-vmp-dynamic-code-generation.md) | 动态代码生成型 VMP 的逆向分析 |
| [JS盾加固逆向分析](2026-07-13-jsdun-protect-analysis.md) | 虚拟方法表 + 双层 VM + 壳机制——了解保护方案的上限 |

***

## 第六章：常见问题速查

### Q: 我应该先学哪条路径？

**先学路径一（补环境）**。理由：
1. 80% 的实际需求是"调通接口"而非"还原源码"
2. 补环境是性价比最高的方案
3. 补环境成功后对解释器的运行行为会有直观理解，为路径二/三打下基础

### Q: 补环境和 AST 反编译的关系是什么？

它们是互补的，不是对立的。补环境成功后可以拿产出的签名做线上验证。如果后续需要源码级复用，再走 AST 反编译。

### Q: trace_env.js 找不到怎么办？

自己写。核心是 Proxy + 自愈逻辑。关键是 `guessDefault()` 的启发式规则和递归 Proxy 深度的控制。参考 `KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated` 中的代码实现。

### Q: 字节码流密码怎么破？

三步骤：① 识别 B8 取指函数中的 XOR 操作 → ② 识别密钥流来源（固定 keyTable vs 动态 hJ 轮换）→ ③ 模拟密钥流状态 → 逐字节 XOR 解密。注意密钥随区块变化，不能"一次性解密"。

### Q: 解释器找不到怎么办？

搜索以下特征：
- `while(true)` + `switch`
- 大数组（>100 元素）被索引访问的模式
- 变量的规律性递增（每次循环+N，N 不固定 = 变长指令）
- 多层嵌套的 `.call` / `.apply` 调用

### Q: 什么时候该放弃一条路径换另一条？

| 信号 | 含义 | 动作 |
|------|------|------|
| SDK 每次加载字节码完全不同 | VM 动态随机化 | 放弃路径三 → 换路径一/二 |
| 补环境跑了 20+ 轮自愈还崩溃 | SDK 深度依赖 DOM | 换路径二 |
| 字节码 > 2 万条指令 | 反编译成本超预期 | 放弃路径三 → 换路径一 |
| 插桩日志 5000+ 行还看不清逻辑 | handler 语义太复杂 | 换成路径三（反编译）或路径一 |

## 相关链接

- 知识库内：见第五章导航表（12 篇笔记全部双向链接）
- 外部参考：[blog.jsvmp.com](https://blog.jsvmp.com/jsvmpfenxi/) — JSVMP 正向理论

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-13 | 初稿（ING-20260713-005）：基于 13 篇知识库笔记综合总结 |