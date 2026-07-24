---
id: "KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature"
module: crawler
module_id: MOD-CR
title: "记一次 AST 还原 JSVMP：某音 X-Bogus / _signature 静态还原全流程"
source:
  type: url
  url: "https://www.52pojie.cn/thread-1752755-1-1.html"
  accessed: "2026-06-11"
  author: "sergiojune"
tags: [js-reverse, jsvmp, vmp, anti-crawler, ast, deobfuscation, esprima, escodegen, estraverse, x-bogus, signature, real-case]
difficulty: advanced
status: active
related:
  - "KB-CR-20260713-jsvmp-reverse-master-guide"
  - "KB-CR-20260611-jsvmp-overview-protection-landscape"
  - "KB-CR-20260611-jsvmp-virtualization-pipeline"
  - "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
  - "KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis"
  - "KB-CR-20260611-rs-vmp-dynamic-code-generation"
  - "KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha"
  - "KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated"
  - "KB-CR-20260713-jsvmp-decompile-restore-full-workflow"
  - "KB-CR-20260724-qmusic-vmp-sha1-aes-gcm"
ingest_id: "ING-20260611-006"
updated: "2026-06-11"
---

# 记一次 AST 还原 JSVMP：某音 X-Bogus / _signature 静态还原全流程

## TL;DR

- 本文展示了一套完整的 **AST 静态还原 JSVMP** 方法论：读取 VMP 字节码 → 解析每个 case 对应操作 → 用 AST 节点替换 VMP 代码 → 生成可读 JS
- 目标为某音（巨量引擎）的 `X-Bogus` 和 `_signature` 参数，经 AST 还原后得到约 200 行可读的签名逻辑
- 核心技巧：**if-else 分支合并**（if/else 分开执行到汇合点重连）、**if→while 循环识别**（检测指针跳回即改写为循环）、**函数递归还原**（VMP 内部函数调用通过递归展开）
- 调试策略：在每个未处理的 case 前插入 `throw Error("未处理")`，运行时抛出异常即可精确定位待补充的 case，逐个击破
- 与动态插桩法互补：本文是 **AST 静态还原路径**（折腾一次输出可读代码），前一篇笔记是 **动态插桩路径**（不还原 OB 直接运行时追踪）

## 适用场景

**何时用：**

- 需要对 JSVMP 保护的代码进行**可读性还原**，而非仅提取运行时结果
- 目标 VM 的字节码/opcode 语义可通过调试逐一映射
- 静态分析优先，希望一次还原永久使用（算法可抠出在 Python/Node.js 中调用）
- 掌握 esprima/escodegen/estraverse 等 AST 工具链

**何时不用：**

- VM 极度复杂、opcode 数量庞大且语义难以穷举 → 优先考虑动态插桩法
- 仅需提取最终的签名/加密结果 → 补环境或 RPC 方案更高效
- OB 混淆层尚未去除 → 需先 AST 还原 OB 混淆（参考技巧：转 if-else 为 switch 定位）

## 知识要点

### 1. JSVMP 还原三步法

作者将 JSVMP 还原归纳为三个递进步骤：

1. **读取 VMP 代码**：分析循环中每个操作（case）对应的语义。识别关键变量——字节码数组（`_0x307ee4`）、代码起始位置（`_0x5b7220`）、局部变量/外部变量栈（`_0x4372f0`）、栈对象（`_0x9ac2c2`）等
2. **修改源代码**：将 VMP 相关代码替换为对应的 AST 节点。例如栈顶变量 `_$0` → AST Identifier，属性访问 `_$0["dfp"]` → AST MemberExpression
3. **运行代码**：生成最终还原结果

### 2. if-else 分支处理策略

JSVMP 中的条件分支是最棘手的问题之一。作者给出的策略：

```
1. 先执行 if 分支，保存当前栈状态和指针位置
2. 将 else 分支的指针设为 if 分支的结果值，继续执行
3. 当 if 分支指针 == else 分支指针时，两个分支汇合
4. 在汇合点重建完整的 if-else AST 节点
```

这种"分别执行、汇合重连"的策略优雅地解决了 VMP 平坦化带来的分支还原难题。

### 3. if→while 循环识别

当检测到分支结束时指针跳回 if 起始位置，说明这是一个循环结构：

- 原始 VMP 中通过 `if (condition) { body; jump_back; }` 实现循环
- 还原时识别此模式，将 `if` 改写为 `while` 节点
- 关键检测点：分支结束后的目标指针是否等于当前 if 的起始位置

### 4. 函数递归还原

VMP 内部定义函数时，函数体本身也是 VMP 代码：

- 定位 VMP 内部的函数定义（通常是某个 opcode 触发）
- 对该函数体递归调用相同的 AST 还原流程
- 记录已还原函数（`funs = {}`），防止重复还原导致死循环

### 5. AST 工具链与代码结构

```javascript
const escodegen = require('escodegen');   // AST → 代码
const esprima = require('esprima');       // 代码 → AST
const estraverse = require('estraverse'); // 遍历/替换 AST 节点
const Syntax = estraverse.Syntax;

var funs = {};  // 记录已还原的 VMP 函数，避免重复处理
```

还原流程：
1. 先修改外层主函数（文中以 `_$webrt_1670312749` 命名）
2. 用 `estraverse` 遍历 AST，匹配 VMP 特征节点
3. 替换为对应的普通 JS AST 节点
4. 用 `escodegen` 输出可读代码

### 6. 调试：throw Error 逐个击破

当面对 0–255 全范围 opcode 时，逐一处理非常耗时。作者的高效策略：

```javascript
// 在每个未处理 case 前插入
throw Error("未处理");
```

- 运行代码时，第一个抛异常的 case 就是需要补充处理的
- 处理完后再次运行，定位下一个未处理的 case
- 循环直到所有 case 处理完毕，无异常抛出

这个方法让作者可以**增量式**完成还原，而不是一次性写完所有 256 个 case 的处理逻辑。

### 7. 还原产物与效果

还原后得到约 200 行可读 JavaScript：

- 核心函数 `_0x5b7a61_vmp`（参数 22 个）
- 拦截 `XMLHttpRequest` 的 `open`、`setRequestHeader`、`send`、`overrideMimeType`
- 从参数中获取 `msTkn`（身份标识）、`msStatus` 等
- 调用工具函数计算 `X-Bogus` 和 `_signature`
- 处理 `onload` 回调中的响应头 `x-ms-tkn` 更新逻辑
- 包含设备信息采集、异步请求等 DOM 操作

还原完成后，算法可**抠出在 Python 中调用**，实现完全脱离浏览器环境的签名计算。

### 8. 作者经验总结

> "还原 JSVMP 就是体力活，一开始比较难，熟悉了之后就会越来越快，但需要了解一些 AST 节点的定义"

这反映了 JSVMP 逆向的本质：**门槛在方法论和工具链**，一旦掌握，不同目标的还原过程高度可复用。

## 代码 / 命令

### 核心变量映射（调试阶段识别）

```javascript
// JSVMP 核心变量
var bytecode    = _0x307ee4;  // 字节码数组
var pc          = _0x5b7220;  // 程序计数器（代码起始位置）
var local_stack = _0x4372f0;  // 局部变量 + 外部变量的栈
var stack_obj   = _0x9ac2c2;  // 栈对象

// 栈顶/次顶变量约定
var _$0 = stack[top];      // 栈顶
var _$1 = stack[top - 1];  // 栈次顶
// _$2, _$3 ... 依次类推
```

### 执行轨迹收集

```javascript
// 在每个 case 前插入
june.push(case_num);  // 收集 opcode 执行序列，用于后续分析
```

### AST 工具基础用法

```javascript
const escodegen = require('escodegen');
const esprima = require('esprima');
const estraverse = require('estraverse');
const Syntax = estraverse.Syntax;

// 代码 → AST
const ast = esprima.parseScript(code);

// 遍历 + 替换
estraverse.replace(ast, {
  enter: function (node, parent) {
    // 匹配 VMP 特征节点并替换
    if (isVMPCall(node)) {
      return buildASTNode(node);  // 返回新 AST 节点
    }
  }
});

// AST → 代码
const result = escodegen.generate(ast);
```

## 注意事项

- 本文发布于 2023-03-01，目标平台代码可能已升级，具体偏移和变量名需重新定位，但**方法论完全可迁移**
- AST 还原方案的**前期投入较大**（需逐一映射 0–255 个 opcode），但还原完成后永久可用
- 文中提到先用 AST 去掉部分混淆和扁平化处理，将大量 if-else 转为 switch 以便定位——这是预处理步骤，在本文未展开
- 还原产物的 ~200 行代码仍依赖部分宿主环境（DOM、XHR 拦截），完全脱离浏览器调用需额外适配
- 对比动态插桩法：AST 法适合**一劳永逸**的还原，动态法适合**快速出结果**的场景

## 相关链接

- [原文：记一次使用AST还原某短视频JSVMP](https://www.52pojie.cn/thread-1752755-1-1.html)
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST 拆分→字节码编码全过程
  - [某数字 4.3.2 绕过 OB 直捣 JSVMP mns0301 分析](../crawler/2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) (`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`) — **动态插桩法**：不还原 OB 直接运行时追踪
  - [某Q音乐 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`) — 解释器定位→插桩→指令还原
  - [瑞数 VMP 动态代码生成逆向分析](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`) — VMP 逆向通用方法论
  - [AI 白盒还原腾讯 CHAOS VM 验证码端到端](../crawler/2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) (`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`) — 纯 Python 从零构造 collect + JS Reverse MCP 工具

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-006）：52pojie AST 静态还原某音 JSVMP 的 X-Bogus/_signature 全流程 |
