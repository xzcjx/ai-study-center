---
id: "KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis"
module: crawler
module_id: MOD-CR
title: "某数字 4.3.2：绕过 OB 直捣 JSVMP 的 mns0301 参数逆向全流程"
source:
  type: url
  url: "https://www.52pojie.cn/thread-2098573-1-1.html"
  accessed: "2026-06-11"
  author: "LiXieZengHui"
tags: [js-reverse, jsvmp, vmp, anti-crawler, obfuscation, hook, instrumentation, log-analysis, rc4, base64, chacha20, ai-assisted, real-case]
difficulty: advanced
status: active
related:
  - "KB-CR-20260611-jsvmp-overview-protection-landscape"
  - "KB-CR-20260611-jsvmp-virtualization-pipeline"
  - "KB-CR-20260611-jsvmp-interpreter-design"
  - "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
  - "KB-CR-20260611-rs-vmp-dynamic-code-generation"
ingest_id: "ING-20260611-005"
updated: "2026-06-11"
---

# 某数字 4.3.2：绕过 OB 直捣 JSVMP 的 mns0301 参数逆向全流程

## TL;DR

- 本文针对某数字公司 v4.3.2 版本，**不依赖 AST 先还原 ob 混淆**，直接在 ob + JSVMP 双层保护上动态插桩分析 mns0301 参数
- 核心方法论：定位 JSVMP 解释器中的 `apply` 调用（opcode=`0x1f`），在此层注入日志，记录每次 VM 操作的输入/输出，从日志反推原始算法
- mns0301（即 `arr_144`）由 **时间戳 + MD5 + 环境信息 + 魔数头** 拼接，经**魔改 RC4** 加密后再过**魔改 Base64** 编码
- 全程利用 AI 辅助：将 VM 执行日志交 AI 识别出 chacha20 变体和魔改 RC4 结构，大幅降低人工还原成本
- 给出了不同复杂度 VMP 的插桩策略：简单 VMP → apply 层；中等 VMP → apply + 条件判断；复杂 VMP → 全层栈 + 数学推理

## 适用场景

**何时用：**

- 逆向分析带 ob 混淆 + JSVMP 双层保护的前端签名/加密逻辑
- 了解如何**不借助 AST 还原**直接对混淆代码进行动态插桩
- 学习通过 VM 执行日志识别加密算法（RC4、chacha20 等）的方法论
- 需要理解真实商业产品中 JSVMP 保护的参数构造流程

**何时不用：**

- ob 混淆已有成熟 AST 还原工具链且 VM 层较薄 → 先还原 ob 再分析更高效
- 仅需概念级理解 JSVMP（参考概述篇 `KB-CR-20260611-jsvmp-overview-protection-landscape`）
- 目标是通过补环境方案绕过检测（参考补环境相关笔记）

## 知识要点

### 1. 为什么在 apply 层插桩

JSVMP 的核心是将原始函数调用关系平坦化。原始代码如：

```javascript
function encrypt(a, b) { return a * b + 1; }
```

被 VMP 转化为类似：

```javascript
h[r[++p]] = h[r[++p]].apply(h[r[++p]], l)
```

所有调用关系被隐藏，**只能观察 4 类运行时信息**：
1. opcode 变化
2. PC 指针跳转
3. 栈指针移动
4. 栈元素修改

这些信息无法静态分析，只能通过动态插桩记录日志后反推。选择 **apply 层**是为了捕获每一层 VM 操作/逻辑的**输入和结果**——因为 apply 是 VM 中实际执行函数的关卡。

### 2. 定位 ob 混淆中的 JSVMP 入口与 apply 调用

**定位 VMP 入口：**

- ob 混淆将所有赋值展开为 `stack[stack_top_pointer] = stack[stack_top_pointer] operator value` 形式
- 通过全局搜索匹配 `stack[stack_top_pointer]` 模式定位栈变量
- VMP 在开始前会初始化栈，找到栈初始化位置即可定位 VMP 起点

**定位 apply 调用（opcode=0x1f）：**

- 动态还原 apply 函数在数组中的索引 → 对应 **0x32**（十进制 50）
- 利用 ob 特征：`_0x????[0x32]` 的调用模式，其中 `_0x????` 是当前函数域的解密函数变量
- 本例中全局解密函数名为 `_0x1769`
- 当 `opcode == 0x1f` 时即为 apply 调用点

插桩代码模式：
```javascript
// 在 _0x1769[0x32] 调用处注入日志
if (opcode === 0x1f) {
    console.log('[VMP-APPLY]', {
        opcode: opcode,
        fn: target_function,
        args: arguments_list,
        result: return_value
    });
}
```

完成后将 JS 压缩为一行替换原位置，刷新页面即见日志输出。

### 3. arr_144（mns0301）参数构造链

作者通过日志追踪，完整还原了 mns0301 参数的构造过程：

```
arr_144
  ├── arr_20 = arr_4 + arr_16
  │     ├── arr_4: 从 window._dsn 获取环境值转 ASCII
  │     └── arr_16: func(arr_24)
  │           ├── [0-7]: 时间戳高低位（小端序 uint32 × 2）
  │           ├── [8-23]: MD5 字符串逐字节转 int
  │           └── 经 VM 执行（chacha20 变体处理）
  │
  └── arr_124 = arr_108 + arr_16
        ├── arr_108 = arr_97 + arr_11
        │     ├── arr_97 = arr_44 + arr_53
        │     │     ├── arr_44 (48 字节固定结构):
        │     │     │   [0-3]:   魔数头 [121, 104, 96, 41]
        │     │     │   [4-7]:   时间戳相关
        │     │     │   [8-15]:  随机数（小端序）
        │     │     │   [15-23]: 环境/设备相关
        │     │     │   [24-35]: 随机数相关（3 组 4 字节）
        │     │     │   [35-43]: MD5 前三分之一，每字节与 RAND & 0xFF 异或
        │     │     └── arr_53/arr_a1: 长度信息（拼接在开头）
        │     └── arr_11: 固定环境数据
        └── arr_16 (复用上述 arr_16)
```

VM 初始化阶段：每次从 arr_24 取 4 个元素，按小端序拼接为 uint32：
```javascript
value = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
```

### 4. 魔改 RC4 加密引擎识别

定位到 `_0x57c9e7` 函数（对应 `_0x30ce91`），其 return 调用 `_0x31ad27`。插桩后观察到：

- 初始化 256 字节 S 盒（变量 `c`）
- 每轮改变状态，每字节进行一次 push 输出密码流
- 典型的 **S 盒 swap 操作** + **密钥流生成**过程

**结论**：这是一个魔改 RC4（RC4 变体）。将 VM 执行日志交 AI 即可自动生成还原代码。

### 5. 魔改 Base64 编码分析

RC4 变换后得到字节串，经魔改 Base64 编码为最终传输格式。

- 定位到新的 JS 文件（同样含 ob + JSVMP）
- 在 apply 位置插桩 → 转换后对应 16 进制为 **0x87**
- 定位到 **5 层调用**链
- 编码表：**一半硬编码**，剩下一半需通过 VM 执行逻辑确定

校验通过后继续追踪 VM 执行即可还原完整编码表。

### 6. AI 辅助算法识别方法论

作者展示了一种高效的工作方式：

1. 将 VM 执行日志中的数值流输出给 AI
2. AI 识别出 **chacha20 变体**（取 4 个 uint32 各拆为 4 个 uint8，共 16 位）
3. 验证示例：`1210961166` → `0x482DCD0E` → `[72, 45, 205, 14]` → 小端 `[14, 205, 45, 72]` ✅
4. RC4 的 S 盒 swap + 密钥流生成同样由 AI 自动识别

这大幅降低了人工从日志反推算法的脑力成本。

### 7. 不同复杂度 VMP 的插桩策略（作者经验总结）

| 难度 | VMP 特征 | 插桩策略 |
|------|---------|---------|
| 简单 | 单一 VM 循环 | apply 层 + 日志看结构 |
| 中等 | VM + 条件分支 | apply + 条件判断 + 日志看结构 |
| 复杂 | 多层 VM、动态调度 | 一次性插全：先整体打点 → 分段分块 → 同时多个断点 → 一个过程多次调用生成多份日志 → 综合分析 |

**console 注入技巧**：hook `rand` 和 `Date.now()`，在关键函数参数中夹带时间戳标识（ts_1、ts_2...），在关键位置 hook 以区分不同调用路径。

## 注意事项

- 本文目标产品为某数字公司 v4.3.2，不同版本的保护机制可能有差异，方法可迁移但具体偏移需重新定位
- 不适用于需要**完全静态还原**的场景——本文全程依赖动态插桩
- 复杂 VMP 的分层分块插桩需要大量重复实验，耗时较长
- 作者未公开完整的自动化脚本，文中方法论需要自行实现插桩逻辑
- ob 混淆将变量名替换为 `_0x????` 模式，不同文件/版本命名不同，需重新搜索定位

## 相关链接

- [原文：某数字-4.3.2-绕过ob直捣JSVMP-mns0301-详细分析](https://www.52pojie.cn/thread-2098573-1-1.html)
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST→字节码编码
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — WASM 解释器架构
  - [某Q音乐 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`) — 另一篇 apply 层插桩实战
  - [瑞数 VMP 动态代码生成逆向](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`) — VMP 逆向通用方法论

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-005）：52pojie 某数字 4.3.2 绕过 OB 直捣 JSVMP 的 mns0301 全流程分析 |
