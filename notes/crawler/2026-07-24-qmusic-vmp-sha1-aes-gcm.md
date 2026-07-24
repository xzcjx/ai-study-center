---
id: "KB-CR-20260724-qmusic-vmp-sha1-aes-gcm"
module: crawler
module_id: MOD-CR
title: "QQ 音乐 VMP 初始化分析：SHA-1 特征识别与 AES-GCM 请求体解密"
source:
  type: url
  url: "https://www.52pojie.cn/thread-2116112-1-1.html"
  accessed: "2026-07-24"
  reliability: browser-fetched
tags: [js-reverse, jsvmp, vmp, anti-crawler, qqmusic, sign, opcode-mapping, base64, varint, zigzag, stack-vm, instrumentation, sha1, aes-gcm, response-decode, real-case]
difficulty: advanced
status: active
related: [KB-CR-20260713-jsvmp-reverse-master-guide, KB-CR-20260611-qqmusic-jsvmp-reverse-engineering, KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature, KB-CR-20260713-jsvmp-decompile-restore-full-workflow]
ingest_id: "ING-20260724-001"
updated: "2026-07-24"
---

# QQ 音乐 VMP 初始化分析：SHA-1 特征识别与 AES-GCM 请求体解密

## TL;DR

- 文章通过 QQ 音乐 Sign 生成链路定位 VMP：关键特征是 IIFE/柯里化封装、Base64 密文、变长整数解码、指令映射表和 `switch-case` 解释器。
- 初始化链路可概括为：Base64 解码 → VL-Base128/Varint 解码 → ZigZag 解码 → 指令映射 → 栈式 VM 执行。
- 该 VMP 使用约 83 个 case，并通过映射表隐藏字节流中的真实 opcode；分析时不能把解码后的 byte opcode 直接当作真实指令号。
- Sign 的 40 位十六进制输出、512 bit 分块、80 轮压缩和 5 个状态寄存器更新，构成识别 SHA-1 的组合特征。
- 请求体加密符合 AES-GCM 的长度特征：密文主体后增加 16 字节认证标签和 12 字节 IV；响应体还需关注后续的循环异或步骤。

## 适用场景

**何时用：**

- 分析 Web 端 JSVMP/VMP 保护的签名、请求体加密或响应体解码。
- 需要先判断 VM 类型，再决定插桩、跟栈还是静态还原策略。
- 需要从日志和输出长度快速识别 SHA-1、AES-GCM 等标准算法。

**何时不用：**

- 只需要调用自有系统接口，且已具备合法 SDK 或服务端接口时，不必逆向前端保护逻辑。
- 目标逻辑属于 WASM 主导、没有明显 JS `switch` 解释器时，本文的 case 级插桩方法需要调整。

## 知识要点

### 1. 从 Sign 生成位置识别 VMP

定位搜索请求中的 `sign` 生成点后，若输出具有稳定前缀但源码中找不到对应明文，继续观察调用链。出现以下组合信号时，可以优先怀疑 VMP：

- `for (;;)` 或嵌套无限循环包裹 `switch`。
- 大数组作为指令流，程序计数器不断递增或跳转。
- 大量 `case` 分支与 `[++[]]` 等混淆表达式。
- IIFE 返回函数，外部以连续括号调用，形成柯里化/闭包式初始化。

### 2. IIFE 与柯里化负责隐藏 VM 上下文

形如 `(function(){})()()()` 的结构通常不是多余调用，而是把工具函数、指令表、解码函数和解释器放入私有作用域，再逐层传入参数。分析时可先把它改写成显式变量：

```javascript
const privateScope = (function () {
  const decodeBase64 = ...;
  const decodeVarint = ...;
  const opcodeMap = ...;
  const interpreter = ...;
  return function run(encoded, mode) {
    return interpreter(decodeVarint(decodeBase64(encoded)), mode);
  };
})();
```

### 3. 指令流的四层解码链

```text
Base64 字符串 → 自定义 Base64 表解码 → 有符号字节数组
→ VL-Base128 / Varint 解码 → ZigZag 解码
→ 指令映射表查询 → 真实 opcode → switch-case Handler
```

Base64 阶段通过自定义表把字符转换为 6 bit 值，再每 4 个字符还原 3 个字节。随后每个字节只取低 7 位，最高位用于表示后续是否还有字节；多字节数据按小端序拼接。最后使用 ZigZag 解码把无符号值还原为有符号整数：

```javascript
function zigzagDecode(value) {
  return (value >> 1) ^ -(value & 1);
}
```

### 4. 映射表隐藏真实 opcode

指令流中的值不一定就是 `switch` 里的 case 编号，典型关系是：

```text
real_opcode = opcodeMap[byte_opcode]
```

文章示例中的解释器约有 83 个 case。分析时应同时记录原始字节值、映射后的真实 opcode、当前 PC、跳转后的 PC，以及当前栈/上下文索引和值。

### 5. 通过栈结构区分栈式 VM

若解释器存在类似 `h[index]` 的统一数据数组，并且 case 主要通过索引读取、写回、传参，可以优先判定为栈式或“栈 + 上下文数组”VM：

| 变量角色 | 作用 |
|---|---|
| 指令数组 | 保存解码后的 opcode 与操作数 |
| PC | 指向下一条指令 |
| 数据栈 | 保存构造函数、字符串、临时值和返回值 |
| 调用栈 | 保存函数跳转后的返回地址 |
| 闭包环境 | 保存解释器共享的工具函数和外部参数 |

函数调用 case 往往会先收集参数，再以偏移量计算子函数入口，返回值写回数据栈；这比单看某一个 case 更能确认 VM 的调用模型。

### 6. 插桩应从高价值点开始

直接在所有 case 和运算符上输出日志，容易造成日志爆炸甚至拖垮浏览器。更稳妥的顺序是：

1. 先记录解释器入口、PC、opcode 映射和输入参数。
2. 优先插桩 `call/apply`、函数创建、属性访问、字符串拼接等高信息量操作。
3. 根据调用链缩小到 Sign、请求体或响应体相关分支。
4. 最后只针对 `+`、`^`、位移等高频运算补充日志。
5. 使用 `JSON.stringify` 输出数组，避免控制台折叠导致信息丢失。

### 7. 用输出特征识别 SHA-1

文章通过多项独立特征确认 Sign 链路中的哈希算法：输出长度为 40 个十六进制字符，即 160 bit；输入按 512 bit（64 字节）分块；每块执行 80 轮压缩；维护 5 个 32 位状态寄存器；Padding 包含 `0x80`，末尾写入原始消息长度。

这些特征比仅凭函数名或常量猜测更可靠。对于长度为 971 字节的示例，应先按字节计算分块余数，再验证 `0x80` 和长度字段是否出现在日志中。

### 8. 请求体与响应体的加解密边界

请求体部分呈现 AES-GCM 特征：加密结果相对明文增加 16 字节 Tag，另有 12 字节 IV，符合 GCM 常见推荐长度。Key 与 IV 需要从合法授权的自有调试环境中确认，不能从文章或日志中传播真实敏感值。

响应体的处理不能只看“转换成字节数组再 decode”。文章后续补充指出，还存在一个长度为 21 的数组参与循环异或，因此应把响应体解码拆为：字节转换 → 异或 → 最终文本解码，并用单步跟踪或窄范围插桩确认顺序。

## 代码 / 命令

### Varint 解码骨架

```javascript
function decodeVarint32(buffer, offset = 0) {
  let result = 0;
  let shift = 0;

  while (true) {
    const byte = buffer[offset++];
    result |= (byte & 0x7f) << shift;
    if ((byte & 0x80) === 0) break;
    shift += 7;
    if (shift >= 32) throw new Error("Varint 超过 32 位");
  }

  return { value: result, offset };
}
```

### 解释器日志字段建议

```javascript
console.log("[vm]", JSON.stringify({
  pc,
  byteOpcode,
  realOpcode: opcodeMap[byteOpcode],
  stackIndex,
  stackValue,
}));
```

## 注意事项

- 文章中的 Key、IV、请求样本和个人信息应视为敏感数据，不要复制进知识库。
- `byte_opcode`、映射后的 `real_opcode` 和 case 编号是三个不同概念，混淆后会导致错误的指令表。
- 解释器中的同一 slot 可能被重复使用，日志应尽量在运算前记录输入，而不是只记录最终值。
- SHA-1/AES-GCM 的识别结论需要结合长度、轮数、常量和状态更新验证，不能只凭一个输出格式判断。
- 本笔记只用于自有或已获授权目标的安全研究、互操作和调试。

## 相关链接

- [原文：Q音VMP初始化分析&SHA-1算法识别](https://www.52pojie.cn/thread-2116112-1-1.html)
- 项目内：[JSVMP 逆向方法论总纲](2026-07-13-jsvmp-reverse-master-guide.md)（`KB-CR-20260713-jsvmp-reverse-master-guide`）
- 项目内：[某Q音乐前端 JSVMP 逆向还原实战](2026-06-11-qqmusic-jsvmp-reverse-engineering.md)（`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`）
- 项目内：[AST 还原 JSVMP 签名逻辑](2026-06-11-ast-restore-jsvmp-x-bogus-signature.md)（`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`）
- 项目内：[JSVMP 反编译还原全流程](2026-07-13-jsvmp-decompile-restore-full-workflow.md)（`KB-CR-20260713-jsvmp-decompile-restore-full-workflow`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-24 | 初稿（ING-20260724-001） |
