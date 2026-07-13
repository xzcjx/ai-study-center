---
id: "KB-CR-20260713-jsvmp-decompile-restore-full-workflow"
module: crawler
module_id: MOD-CR
title: "JSVMP 反编译还原全流程：从字节码解析到 AST 生成的方法论与实战"
source:
  type: url
  url: "https://www.52pojie.cn/thread-2040789-1-1.html"
  accessed: "2026-07-13"
  author: "lichuntian00（52pojie）"
tags: [js-reverse, jsvmp, vmp, anti-crawler, decompile, bytecode, ast, handler, dispatcher, register-vm, stream-cipher, instruction-decode, opcode-mapping, deobfuscation, real-case, core-methodology]
difficulty: advanced
status: active
related:
  - "KB-CR-20260611-jsvmp-overview-protection-landscape"
  - "KB-CR-20260611-jsvmp-virtualization-pipeline"
  - "KB-CR-20260611-jsvmp-interpreter-design"
  - "KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature"
  - "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
  - "KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha"
  - "KB-CR-20260713-jsdun-protect-analysis"
ingest_id: "ING-20260713-004"
updated: "2026-07-13"
---

# JSVMP 反编译还原全流程：从字节码解析到 AST 生成的方法论与实战

> **用户意图**：通过这篇笔记理解 JSVMP 反编译的核心原理——如何将一个被 VM 保护的 JS 代码恢复为可读的 AST 和最终 JS 源码。

## TL;DR

- **反编译目标**：将 JSVMP 保护的代码还原为可读的 JS 源码，核心路径是「字节码 → 指令解码 → handler 语义映射 → AST 节点 → 代码生成」
- **注册器式 VM 架构**：512 个虚拟寄存器，其中 r36 是 PC（程序计数器）、r336 是内部参数 PC、r184 是密钥相关寄存器——理解寄存器角色是定位解释器入口的第一步
- **指令分发器 C 函数**用 5 路 bit-pattern 分支对 opcode 做分类：寄存器写入、条件赋值、变长指令、空白偏移赋值、变长读取+密钥轮换——每种分支决定了后续如何读取操作数
- **B8 取指函数**实现了流密码逐字节解密：按区块切分指令流，进入新区块时通过 hJ 函数做密钥轮换，每字节 XOR 解密后推进 PC——这意味着同一段源码在不同区块位置会产生不同的密文
- **handler 语义到 AST 节点的映射**是反编译的核心步骤：handler 24→4字节赋值、handler 302→函数调用、handler 495→对象属性访问、handler 122→eval 调用——每个 handler 的行为模式对应一种 AST 节点类型
- **还原工具链**：初始化 Node 环境 → 构建 AST 框架 → 模拟 VM 执行环境 → 解析 base64 字节码 → 循环取指→路由 handler→生成对应 AST 节点 → 移除反调试检测

## 适用场景

**何时用：**

- 需要将 JSVMP 保护的代码完整还原为可读 JS 源码（而非绕过/补环境）
- 面对的 VM 是基于寄存器的架构（有明确的寄存器数组和 PC 寄存器）
- 需要还原的代码量适中，字节码可完整解析（1000–5000 条指令级别）
- 目标代码中的 handler 语义可逐一逆向分析

**何时不用：**

- VM 代码量极大（几万条指令）、恢复成本过高时（走补环境：`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`）
- 不需要完整还原算法，只需要产出签名/参数（走 trace 插桩：`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`）
- VM 使用了高度随机化的动态 opcode 映射（每次加载都不同），静态还原不具备通用性

## 知识要点

### 1. 先导知识：JSVMP 反编译在整个逆向体系中的位置

JSVMP 逆向存在三条主要路径，本笔记聚焦 **路径三——静态反编译还原**：

```
JSVMP 保护的目标代码
    │
    ├── 路径一：补环境绕过（不还原，直接执行 SDK）
    │   参考：KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated
    │
    ├── 路径二：动态插桩追踪（运行时日志反推算法）
    │   参考：KB-CR-20260611-qqmusic-jsvmp-reverse-engineering
    │        KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis
    │
    └── 路径三：静态反编译还原（本笔记）★
        字节码 → 指令解码 → handler 语义分析 → AST 生成 → 可读 JS
        参考：KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature
```

**路径三的适用条件**：VM 架构相对稳定（非每次加载随机化 handler 映射）、代码量可控、需要得到可复用的源码级产出。

### 2. 第一步：定位和解码指令集

**获取指令集**：目标站点通过 302 重定向跳转到 JS-challenge 页面，其中的中间变量包含 base64 编码的指令集数据。使用 `atob` 解码后，每个字节与 `& 255`（即 `0xFF`）做 AND 运算，提取 8 位纯字节值。

```javascript
// 典型的指令集解码方式
const rawBase64 = "/* 从中间变量提取的 base64 字符串 */";
const decoded = atob(rawBase64);
const bytecode = [];
for (let i = 0; i < decoded.length; i++) {
    bytecode.push(decoded.charCodeAt(i) & 0xFF);
}
// bytecode 是纯字节数组，每条指令可能占 1–N 字节（由 opcode 决定）
```

**第一个关键发现——识别寄存器的含义**需要观察字节码的读取模式。如果字节码中的操作数总是作为索引去访问同一个大数组，这个数组就是**虚拟寄存器组**。

### 3. 第二步：识别寄存器式 VM 架构

本案例的 VM 使用 **512 个虚拟寄存器**（远超基于栈的 VM 复杂度），关键寄存器的角色识别：

| 寄存器 | 角色 | 识别方法 |
|--------|------|----------|
| **寄存器 36** | PC（程序计数器） | 每次取指时读取、执行后递增 |
| **寄存器 336** | 内部参数-PC | 与 r36 同步更新，用于参数传递 |
| **寄存器 184** | 密钥/解密相关 | 在 hJ 密钥轮换函数中被操作 |
| **280, 115, 509** 等 | 加密操作专用 | 被 handler 149/220/446 操作，特征为特定数学运算模式 |

**如何识别 PC 寄存器**：在所有寄存器中，有一个值在每次循环迭代后规律性递增，且被用于索引字节码数组——这就是 PC。

```javascript
// 识别 PC 的典型模式
function identifyPC() {
    // 搜索在循环中被规律性递增、且用于索引数组的变量
    // 特征：每轮取指时 r[36] 被读取，执行后 r[36] += N（N=指令长度）
    return 36; // 本案例结果
}
```

**寄存器式 vs 栈式 VM 的区别**：栈式 VM 用 push/pop 传递操作数（简单但指令多），寄存器式 VM 用寄存器编号引用操作数（指令少但寄存器管理复杂）。本案例的 handler 大量使用 `N(regId, value)` 写寄存器和 `y(regId)` 读寄存器，是典型的寄存器式架构。

### 4. 核心函数识别：N / y / C / B8 / hJ

从混淆后的 JS 代码中，需要先识别以下核心函数（不依赖变量名，通过行为模式定位）：

| 函数 | 作用 | 行为特征（如何定位） |
|------|------|---------------------|
| **N** | 写寄存器 `N(regId, value)` | 参数 2 个、内部做 `arr[idx] = val` |
| **y** | 读寄存器 `y(regId)` | 参数 1 个、内部做 `return arr[idx]` |
| **C** | 指令分发器 | 用复杂的位运算条件路由到不同处理函数，内部含 5 路分支 |
| **B8** | 取指令（含解密） | 读取 PC → 索引字节码 → XOR 解密 → 处理变长操作数 |
| **hJ** | 密钥轮换 | 8 字节解密表初始化、在区块边界被 B8 调用，内部有循环移位/XOR |

**定位 C（分发器）的技巧**：在解释器主循环中，紧接在 PC 递增/读取之后的那个包含大量 `if/switch` 或复杂位运算条件分发的函数，就是指令分发器。

### 5. 指令分发器 C 的 5 路 bit-pattern 分支（核心详解）

这是反编译中最关键、最复杂的部分。C 函数通过 opcode 的**位模式匹配**（而非枚举 switch）来决定指令类型：

```
C(opcode) 接收一个字节的 opcode
  │
  ├── 分支 1：w | 48 == w
  │   含义：opcode 高 2 位为 00（与 48=0b110000 做 OR 不变）
  │   动作：寄存器写入——从字节码读取常量值，N(目标寄存器, 常量)
  │   示例：opcode=0x01 → 将立即数写入指定寄存器
  │
  ├── 分支 2：w - 5 | 5 >= w && w + 4 & 43 < w
  │   含义：opcode 落在 [5, ~9] 范围
  │   动作：条件/值设置操作——根据位标志设置寄存器值
  │   示例：opcode=0x06 → 条件赋值
  │
  ├── 分支 3：w >> 1 & 12 < 12 && w + 6 >> 4 >= 3
  │   含义：opcode 高 4 位在 [3, 11] 范围
  │   动作：变长指令——读取 1 字节，检查最高位
  │        - 最高位=1 → 扩展为长指令（读更多字节）
  │        - 最高位=0 → 短指令
  │   示例：opcode=0x35 → 变长读取，可能是函数调用或对象操作
  │
  ├── 分支 4：w + 5 >> 3 == 1
  │   含义：opcode 在 [3, ~10] 范围内（+5 后右移 3 位等于 1）
  │   动作：寄存器值作为空白偏移量赋值
  │   示例：opcode=0x04 → 间接寻址写入
  │
  └── 分支 5：w + 7 ^ 27 < w && w - 6 ^ 9 >= w
      含义：opcode 在较高范围
      动作：变长读取 + 密钥轮换
           - 8bit 读取 + 密钥轮换
           - 或 7bit + 2bit 分段读取
           - 或 9bit 读取
      示例：opcode=0x3A → 密钥轮换后的变长指令
```

**为什么用位模式匹配而非 switch**：位模式匹配使得 opcode 编码高度紧凑——相邻 opcode 值可能对应完全不同的指令类型，增加静态分析的难度。反编译时必须逐条验证分支条件在 opcode 全集上的行为。

### 6. B8 取指函数：流密码逐字节解密

B8 是连接"密文字节码"和"明文指令"的关键：

```
B8() 执行流程：
  │
  ├── 1. 从 PC（寄存器 36）读取当前指令位置
  │
  ├── 2. 检查位置是否超出字节码边界
  │     超出 → 返回结束标记
  │
  ├── 3. 判断当前位置属于哪个解密区块
  │     每个区块有独立的密钥状态
  │
  ├── 4. 如果进入新区块 → 调用 hJ() 做密钥轮换
  │     hJ() 更新 8 字节解密表（可能是 S-box 或 LFSR）
  │
  ├── 5. XOR 解密：plaintext_byte = ciphertext_byte XOR key_stream[position % 8]
  │     注意：密钥流是逐字节的，不是按块 CBC 模式
  │
  ├── 6. PC 递增（PC += 指令长度）
  │
  └── 7. 如果是变长指令 → 解码扩展操作数
        例：读取下一字节的高位标志 → 决定操作数是 1/2/4 字节
```

**含义**：同一段 JS 源码在不同位置编译出的密文完全不同（因为密钥流随位置变化）。这也是为什么**不能直接对比两个版本的文件来 diff**——即使源码相同，只要字节码位置不同，密文就完全不同。

**hJ 密钥轮换识别**：hJ 通常在 B8 中被条件调用（if 进入新区块），操作一个 8 字节数组，内部有循环移位和 XOR 操作。这个 8 字节数组就是解密表。

### 7. Handler 到 AST 节点的语义映射

反编译的核心步骤：**每个 handler 操作 → 对应的 AST 节点类型**。

#### 7.1 值赋值类 Handler

| Handler | 操作 | AST 节点 |
|---------|------|----------|
| **24** | 4 字节赋值：`N(reg, 32bit_const)` | `AssignmentExpression` / `Literal` |
| **66** | 1 字节赋值：`N(reg, 8bit_const)` | `AssignmentExpression` / `Literal` |
| **105** | 双字节赋值：`N(reg, 16bit_const)` | `AssignmentExpression` / `Literal` |

这些 handler 通过枚举映射决定字节宽度，然后将常量值存入指定寄存器。

#### 7.2 函数调用类 Handler

| Handler | 操作 | AST 节点 |
|---------|------|----------|
| **302** | 函数调用：`func.call(thisArg, ...args)` | `CallExpression` |
| **122** | eval 调用：`eval(code)` | `CallExpression` (callee=eval) |

**Handler 302 的还原关键**：它通常涉及从寄存器取函数引用、取 this、取参数列表，然后执行调用。生成 AST 时，函数引用映射为 `callee`，this 映射为 `MemberExpression.object` 或直接传给 `.call()`。

#### 7.3 对象/属性操作类 Handler

| Handler | 操作 | AST 节点 |
|---------|------|----------|
| **495** | 对象属性访问/创建新上下文 | `MemberExpression` |
| **265** | 属性赋值 | `AssignmentExpression` (左值为 MemberExpression) |
| **477** | 创建新对象 | `NewExpression` / `ObjectExpression` |
| **319** | 数组操作 | `ArrayExpression` / `MemberExpression[computed=true]` |

#### 7.4 加密操作类 Handler

| Handler | 操作 | 涉及的寄存器 |
|---------|------|-------------|
| **149** | 加密轮操作-类型A | r280 |
| **220** | 加密轮操作-类型B | r280 |
| **446** | 加密结果提取 | r280 |

这些 handler 通常对应 AES 加密的不同阶段（SubBytes/ShiftRows/MixColumns/AddRoundKey），因为原文提到代码中有 AES 加密块，且 handler 间有明确的轮次循环调用模式。

### 8. 完整还原工具链设计

以下是还原工具的核心流程（基于作者实现）：

```
还原工具主循环：
  │
  ├── 1. 初始化 Node 环境（vm.createContext 或 isolated-vm）
  │     - 提供最小化的假浏览器环境（不触发反调试）
  │     - 注入 N/y/C/B8/hJ 等核心函数的桩实现
  │
  ├── 2. 构建 AST 树根节点
  │     - Program → FunctionDeclaration → BlockStatement
  │     - 所有还原出的表达式挂到 BlockStatement.body
  │
  ├── 3. 解析 base64 指令集 → 字节数组
  │     - atob 解码 → .charCodeAt(i) & 0xFF
  │
  ├── 4. 模拟 VM 执行环境（不真正执行，只模拟状态）
  │     - 虚拟寄存器数组 new Array(512)
  │     - PC = 0（初始指令位置）
  │     - 解密表 = 初始状态
  │
  ├── 5. 指令处理循环（核心）：
  │     │
  │     ├── a. B8() 取指 + 解密 → 得到明文 opcode
  │     ├── b. C(opcode) 分发 → 确定指令类型和操作数格式
  │     ├── c. 根据类型读取操作数 → 从字节码中读取 N 字节
  │     ├── d. 路由到对应 handler 的语义映射函数
  │     │      ├── 值赋值 handler → 生成 Literal + AssignmentExpression 节点
  │     │      ├── 函数调用 handler → 生成 CallExpression 节点
  │     │      ├── 属性操作 handler → 生成 MemberExpression 节点
  │     │      └── 加密操作 handler → 生成对应的 Crypto API AST 节点
  │     │
  │     └── e. 将生成的 AST 节点追加到 BlockStatement.body
  │
  ├── 6. 后处理：
  │     ├── if-else 分支合并（还原后的 if/else 可能是分开执行的）
  │     ├── if→while 循环识别（检测 PC 回跳 → 改写为循环结构）
  │     ├── 函数递归还原（VM 内部函数调用通过递归展开）
  │     └── 移除反调试/检测代码（handler 执行后的检测调用）
  │
  └── 7. AST → 代码生成（escodegen/esprima 或 babel/generator）
        → 输出可读 JS 源码
```

### 9. 反调试检测的剥离

每次 handler 执行后，VM 会运行一次检测/反篡改检查。反编译时需要识别并移除这些检测点：

**检测函数的特征**：
- 在 handler 执行后立即调用（主循环末尾）
- 读取出厂值做校验和比对
- 检测到异常 → 陷入死循环或抛假错误
- 函数体通常很短（几行代码），操作固定的几个寄存器

**剥离方法**：在主循环处理中，如果当前指令的操作模式符合"读固定寄存器 → 校验和 → 条件跳转"且跳转目标是当前指令自身（死循环），则跳过该指令不生成 AST。

### 10. 后处理：从平坦化控制流到结构化控制流

反编译出的 AST 是**平坦化**的（所有指令线性排列，通过 PC 跳转实现分支），需要后处理恢复结构化控制流：

| 场景 | 识别方法 | 还原方法 |
|------|----------|----------|
| **if-else** | PC 在条件后跳转到两个不同位置，其中一个位置执行完后跳到汇合点 | 合并为 `IfStatement` |
| **while 循环** | PC 在某处往回跳（跳转目标 < 当前位置）且跳转条件涉及循环变量 | 改写为 `WhileStatement` |
| **内部函数调用** | PC 跳到一个远处位置，执行一段后跳回 | 提取为独立的 `FunctionDeclaration` |

**技巧**：参考 `KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature` 中的"if-else 分支合并"和"if→while 循环识别"方法——这两个方法是通用的，适用于大多数 JSVMP 反编译场景。

## 代码 / 命令

```javascript
// ==========================================
// 1. 指令集解码
// ==========================================
function decodeInstructionSet(base64Str) {
    const decoded = atob(base64Str);
    const bytecode = [];
    for (let i = 0; i < decoded.length; i++) {
        bytecode.push(decoded.charCodeAt(i) & 0xFF);
    }
    return bytecode;
}

// ==========================================
// 2. B8 取指函数（流密码解密）的语义还原
// ==========================================
// 原始 B8 的伪代码：
function B8_semantic(pc, bytecode, keyTable, blockSize) {
    // 判断当前区块
    const currentBlock = Math.floor(pc / blockSize);
    if (currentBlock !== lastBlock) {
        hJ_rotateKey(keyTable);  // 密钥轮换
        lastBlock = currentBlock;
    }
    // XOR 解密当前字节
    const plainOpcode = bytecode[pc] ^ keyTable[pc % 8];
    pc += 1; // 基础指令 1 字节
    // 如果是变长指令，读取额外操作数
    // ...
    return { opcode: plainOpcode, newPc: pc };
}

// ==========================================
// 3. C 分发器伪代码（5 路 bit-pattern）
// ==========================================
function C_dispatcher(w) {
    // 分支 1：寄存器写入
    if ((w | 48) === w) {
        return { type: 'REG_WRITE_CONST', handler: resolveHandler(w) };
    }
    // 分支 2：条件赋值
    if ((w - 5 | 5) >= w && (w + 4 & 43) < w) {
        return { type: 'CONDITIONAL_SET', handler: resolveHandler(w) };
    }
    // 分支 3：变长指令
    if ((w >> 1 & 12) < 12 && (w + 6 >> 4) >= 3) {
        return { type: 'VARIABLE_LENGTH', handler: resolveHandler(w) };
    }
    // 分支 4：寄存器值空白偏移
    if ((w + 5 >> 3) === 1) {
        return { type: 'REG_OFFSET', handler: resolveHandler(w) };
    }
    // 分支 5：变长读取 + 密钥轮换
    if ((w + 7 ^ 27) < w && (w - 6 ^ 9) >= w) {
        return { type: 'VARIABLE_LENGTH_WITH_KEY_ROTATION', handler: resolveHandler(w) };
    }
}

// ==========================================
// 4. Handler→AST 映射示例
// ==========================================
function handlerToAST(handlerId, operands, registers) {
    switch (handlerId) {
        case 24: // 4字节常量写入寄存器
            return {
                type: 'AssignmentExpression',
                left: { type: 'Identifier', name: `reg_${operands[0]}` },
                right: { type: 'Literal', value: operands[1] }
            };
        case 302: // 函数调用
            return {
                type: 'CallExpression',
                callee: { type: 'Identifier', name: `reg_${operands[0]}` },
                arguments: operands.slice(1).map(a =>
                    ({ type: 'Identifier', name: `reg_${a}` }))
            };
        case 495: // 对象属性访问
            return {
                type: 'MemberExpression',
                object: { type: 'Identifier', name: `reg_${operands[0]}` },
                property: { type: 'Identifier', name: `reg_${operands[1]}` },
                computed: false
            };
        case 122: // eval 调用
            return {
                type: 'CallExpression',
                callee: { type: 'Identifier', name: 'eval' },
                arguments: [{ type: 'Identifier', name: `reg_${operands[0]}` }]
            };
        // ... 更多 handler 映射
    }
}

// ==========================================
// 5. 反调试检测的识别和剥离
// ==========================================
function isAntiDebugCheck(instruction, registers) {
    // 特征：读取固定寄存器 → 校验和比对 → 死循环跳转（跳转到自身）
    if (instruction.type === 'CONDITIONAL_SET' &&
        instruction.jumpTarget === instruction.currentPc) {
        return true; // 死循环 = 反调试
    }
    return false;
}
```

## 注意事项

- **bit-pattern 条件不是简单的枚举**：C 函数的 5 路分支条件用位运算而非 switch，需逐字节验证每个 opcode 值（0x00–0xFF）落到哪个分支
- **流密码解密必须在 B8 内部完成**：不能在字节码预处理阶段"一次性解密"，因为密钥状态随区块位置变化
- **PC 寄存器识别是第一步**：在 512 个寄存器中找到 PC 才能定位取指循环，没找到 PC 之前不要尝试分析其他寄存器
- **handler 映射需要反复验证**：某些 handler 在不同上下文中行为不同（多态 handler），需要带入实际操作数测试
- **加密 handler（149/220/446）可跳过**：如果不关心加密算法本身，这组 handler 可以保留为黑盒调用（直接生成对应 Crypto API 调用而不是逐轮展开）
- **AST 后处理不是可选的**：原始 AST 是平坦化控制流，不合并 if/while 的话生成的代码和汇编相差无几——仍然"不可读"

## 相关链接

- [原文：52pojie — Web逆向之VMP还原全流程](https://www.52pojie.cn/thread-2040789-1-1.html)
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — 理论：为什么需要 VM 保护
  - [JSVMP 虚拟化流水线：AST 拆分→字节码编码](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — 正向：如何生成 VM 字节码
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — 正向：解释器架构
  - [AST 还原 JSVMP X-Bogus/_signature 全流程](../crawler/2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) (`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`) — **同路径**：另一篇 AST 静态还原实战（if-else 合并、循环识别）
  - [某Q音乐 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`) — 路径二：动态插桩追踪
  - [AI 白盒还原腾讯 CHAOS VM](../crawler/2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) (`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`) — opcode 自动识别 + 反汇编
  - [JS盾加固逆向分析](../crawler/2026-07-13-jsdun-protect-analysis.md) (`KB-CR-20260713-jsdun-protect-analysis`) — 虚拟方法表调度器设计

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-13 | 初稿（ING-20260713-004）：52pojie JSVMP 反编译还原全流程——从字节码到 AST 的完整方法论 |