---
id: "KB-CR-20260611-jsvmp-virtualization-pipeline"
module: crawler
module_id: MOD-CR
title: "JSVMP 虚拟化流水线：从 AST 拆分到字节码编码"
source:
  type: url
  url: "https://blog.jsvmp.com/jsvmpfenxi/"
  accessed: "2026-06-11"
tags: [js-reverse, jsvmp, vmp, anti-crawler, ast, bytecode, instruction-encoding, intermediate-code, obfuscation, jsvmp-theory]
difficulty: advanced
status: active
related: ["KB-CR-20260611-jsvmp-overview-protection-landscape", "KB-CR-20260611-jsvmp-interpreter-design", "KB-CR-20260611-rs-vmp-dynamic-code-generation", "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering", "KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis"]
ingest_id: "ING-20260611-003"
updated: "2026-06-11"
---

# JSVMP 虚拟化流水线：从 AST 拆分到字节码编码

## TL;DR

- JS 代码虚拟化的核心挑战是**JS 天然不具备本地操作指令的原子特性**，必须先通过 AST 拆分破坏语法属性，提取原子操作
- 虚拟化流水线五阶段：**结构拆分 → 指令拆分 → 字符转移 → 虚拟指令映射 → 字节码编码**，环环相扣不可跳步
- 采用**基于栈的虚拟机架构**而非寄存器架构，简化指令寻址方式和虚拟化过程
- 编码阶段引入**随机化映射策略**，同一逻辑在不同保护批次中产生完全不同的字节码
- 字符串数组（VMarray）与字节码耦合存储，使得静态分析无法直接读取语义信息

## 适用场景

**何时用：**

- 理解 JSVMP 虚拟化保护的内部实现机制
- 设计或评估 JS 代码虚拟化保护方案
- 逆向分析商业化 JSVMP 产品时需要对照参考
- 编写自研 JS 代码保护工具的理论依据

**何时不用：**

- 只需了解 JSVMP 的概念层级（参考概述篇即可）
- 直接部署现成的商业保护方案而不关心原理
- 端到端快速使用场景（直接看解释器设计篇）

## 知识要点

### 1. 结构拆分：循环与分支的平铺

结构拆分是虚拟化管线的**第一步**，目标是将高级控制流结构（循环、条件分支）平铺为线性基本块。

**条件分支处理**：

一个 IF 子树被拆分为多个表达式子树，每个子树只含一个语句块：

```
源代码:                     拆分后:
if (a > b) {                ├─ cmp a, b      (比较表达式)
  x = 1;                    ├─ ifjmp ELSE    (标记：条件跳转)
} else {                    ├─ x = 1         (then 语句块)
  x = 2;                    ├─ elsepart      (标记：else 起始)
}                           ├─ x = 2         (else 语句块)
                            └─ END           (标记：结束)
```

中间插入的 `ifjmp` 和 `elsepart` 标记用于后续虚拟映射阶段插入跳转指令和目的地址。

**循环结构处理**：

除拆分条件判断块和循环体之外，还需在循环体末尾**增加一个强制向回跳转指令**，确保循环逻辑在虚拟执行时正确还原。

### 2. 指令拆分：生成原子中间代码

指令拆分的核心工具是**抽象语法树（AST）后序遍历**。文章采用 Mozilla Rhino 引擎的 Parser 类提取 AST（也可用 acorn、esprima 等现代解析器）。

**拆分策略分为两个维度**：

**维度一：计算语句拆分**

当 AST 节点类型为**中缀表达式（InfixExpression）** 时，将操作数和运算符分离，拆成栈式架构中间指令：

```
源代码:  r2 = r1 + 3

拆分后（栈式中间代码）:
├─ push  r1          // 将 r1 压栈
├─ push  #3          // 将立即数 3 压栈
├─ add               // 栈顶两个值相加，结果压栈
└─ store r2          // 将栈顶结果保存到 r2
```

每一条中间指令都具有原子操作特性，但不具有执行能力 — 它们是后续映射为虚拟指令的原料。

**维度二：对象属性操作拆分**

对 `document.write(str)` 这类调用，采用分步拆分：

```
源代码:  document.write(str)

拆分后:
├─ get_element document, "write"    // 从 document 获取 write 属性
└─ call (arg: str)                  // 以 str 为参数调用该方法
```

关键技巧：将**点号访问**（`.`）转换为**方括号访问**（`[]`）方式，使对象名和属性名都作为字符串常量参数存在，便于后续字符转移。

**不处理的节点类型**：拆分时显式跳过 `ElementGet` 和 `FunctionCall` 节点类型（交由 Handler 解释执行），聚焦于将计算表达式和分支展开为原子操作。

### 3. 字符转移：剥离语义信息

字符转移是连接「指令拆分」与「虚拟指令映射」的关键中间环节。

**动机**：指令拆分后，所有变量名、属性名、字符串常量仍以**可读字符串字面量**形式存在于指令中。这些字符串"难以转化成字节码形式"，无法直接参与后续编码。

**转换方案**：受传统二进制程序启发 — 指令中的参数（非立即数）存储在特定存储单元中，通过寻址方式获取。将代码中所有字符串常量提取到独立的 **VMA[]（字符串数组/VMarray）** 中，原指令位置替换为数组索引 `VMA[i]`。

```
字符转移前：                    字符转移后：
指令流                           指令流
get_element document, "write"    get_element VMA[0], VMA[1]
call(arg: str)                   call(arg: VMA[2])
                                 
                                 字符串数组 VMA：
                                 VMA[0] = "document"
                                 VMA[1] = "write"
                                 VMA[2] = "str"
```

**安全收益**：
- 指令序列中只留下无意义的数字索引
- 字符串数组与字节码**耦合存储**于 WASM 模块 data 段
- 静态分析者无法从指令流中直接读取属性语义
- 字符串数组"蕴含了属性的语义和操作信息"，恢复了数组即可理解被隐藏的代码意图

### 4. 虚拟指令集设计

将中间代码分类归纳为**四类虚拟指令**，形成自定义指令集：

| 类别 | 代表指令 | 特征 |
|------|----------|------|
| **数据转移** | `lod`（加载）、`stor`（保存） | 唯一携带显式参数的指令类型 |
| **属性操作** | `get`、`set`、`call`、`fcall` | 从栈顶获取操作对象，拼接还原属性/方法调用 |
| **控制转移** | `jmp`（直接跳转）、`je`（条件跳转） | 通过修改虚拟程序计数器 VPC 实现 |
| **算术逻辑** | `add`、`sub`、`mul`、`div` 等 | 无显式操作数，栈顶取数运算后结果压栈 |

**寻址方式**（仅数据转移指令涉及，共 4 种）：

| 寻址方式 | 操作对象 | 示例 |
|----------|----------|------|
| 立即数寻址 | 常量值 | `lod #3` |
| 字符串数组寻址 | VMA[byte] | `lod VMA[0]` |
| 寄存器寻址 | 临时寄存器 | `lod R1` |
| 外部变量寻址 | VarList[byte] | `lod V[0]`（涵盖函数参数、全局变量） |

`stor` 保存指令仅支持后两种寻址（只能写入存储空间，不能写回立即数或字符串数组）。

**特殊设计考量**：
- `call` 指令因参数个数不定，Handler 需要额外参数指明参数数量
- `fcall` 模拟 `a(b)` 形式调用，同样携带实参个数参数
- 条件跳转 `je` 的判断条件**在指令执行前已计算完成并将结果压栈**，Handler 仅从栈顶读布尔值

### 5. 指令编码与字节码生成

虚拟指令被拆分为**操作码（Opcode）** 和**操作数（Operand）**，分别编码为字节码序列：

**编码结构**：

```
┌──────────┬──────────────┐
│ Opcode   │ Operand      │
│ 操作码    │ 操作数        │
│ =Handler  │ =寄存器编号   │
│  索引ID   │ /立即数值     │
│          │ /数组索引    │
└──────────┴──────────────┘
```

以 `r2 = r1 + 3` 的完整编码为例：

```
中间代码          虚拟指令        字节码编码
push r1      →   lod R1      →   [OP_LOD, R1_ID]
push #3      →   lod #3      →   [OP_LOD, 3]
add          →   add         →   [OP_ADD]
store r2     →   stor R2     →   [OP_STOR, R2_ID]
```

**随机化编码策略（核心安全机制）**：

每次保护时**随机替换操作码与字节码的映射关系**。用文章原话："通过修改编码规则来改变虚拟指令和字节码的映射关系" — 同一条 `add` 指令在批次 A 中编码为 `0x05`，在批次 B 中可能为 `0x1A`。

此外，整个字节码程序**可进一步整体加密**保存，使得静态分析者无法直接读取指令流，必须先定位并解密。这构成了**双重保护**：随机化映射 + 整体加密。

### 6. 虚拟机架构选型：栈式 vs 寄存器式

JSVMP 选择**基于栈的虚拟机**架构，理由如下：

| 维度 | 栈式虚拟机 | 寄存器式虚拟机 |
|------|-----------|---------------|
| 虚拟化过程 | 较固定和简单 | 较复杂 |
| 指令寻址方式 | 更简单 | 更复杂 |
| 指令条数 | 较多（需显式压栈） | 较少 |
| 实现复杂度 | 低 | 高 |
| 适合场景 | 保护方案设计 | 高性能 VM |

栈式架构的执行流程：所有操作数 → lod 压栈 → 运算指令从栈顶取数 → 结果压回栈顶 → stor 保存。寄存器仅作为"临时存储中间值"的辅助角色。

## 代码 / 命令

### 基于 acorn 的 AST 遍历示例（简化示意）

```javascript
// 思路示意，非生产代码
const acorn = require('acorn');

function splitExpression(node) {
  if (node.type === 'AssignmentExpression') {
    const left = node.left;
    const right = node.right;
    if (right.type === 'BinaryExpression') {
      // r2 = r1 + 3 → 拆分为原子操作
      return [
        { op: 'lod', arg: right.left },   // push r1
        { op: 'lod', arg: right.right },  // push 3
        { op: right.operator },            // add
        { op: 'stor', arg: left }          // store r2
      ];
    }
  }
  return [node];
}
```

### 字符转移示意

```javascript
// 字符串提取与替换
const VMA = [];
function transferString(node) {
  if (typeof node.arg === 'string' && !isNumeric(node.arg)) {
    const idx = VMA.indexOf(node.arg);
    if (idx === -1) {
      VMA.push(node.arg);
      node.arg = `VMA[${VMA.length - 1}]`;
    } else {
      node.arg = `VMA[${idx}]`;
    }
  }
  return node;
}
```

### 编码随机化示意

```javascript
// 每次保护时随机生成操作码映射
function generateOpcodeMap(instructions) {
  const uniqueOps = [...new Set(instructions.map(i => i.op))];
  const shuffled = [...uniqueOps].sort(() => Math.random() - 0.5);
  const map = {};
  uniqueOps.forEach((op, i) => { map[op] = shuffled[i]; });
  return map;
}
```

## 注意事项

- AST 解析工具的选择影响拆分质量：Rhino 引擎是 Java 实现，现代 JS 环境下推荐 acorn/esprima，需确保对 ES6+ 语法的完整支持
- 字符转移时字符串数组的**顺序**会影响字节码结构 — 一旦确定就不可轻易变更，否则所有 Handler 的索引引用失效
- `lod` 指令的 4 种寻址方式在 Handler 中需用**不同的操作码区分**，不能仅靠操作数判断
- 控制转移指令的偏移计算均为**相对偏移**（目的地址 - 当前地址），不是绝对地址
- 编码随机化的种子若可被预测，则随机策略形同虚设 — 需使用密码学安全的随机源

## 相关链接

- 原文汇总：[JSVMP 原理分析 - 虚拟指令与编码相关文章](https://blog.jsvmp.com/jsvmpfenxi/)
  - [JS代码指令拆分](https://blog.jsvmp.com/jschaifen/) · [JS代码字符转移](https://blog.jsvmp.com/jszifuzhuanyi/)
  - [虚拟指令和Handler设计](https://blog.jsvmp.com/orderandhandler/) · [指令编码](https://blog.jsvmp.com/instructioncoding/)
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`)
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`)
  - [某Q音乐 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`)
  - [瑞数 VMP 动态代码生成逆向分析](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`)
  - [某数字 4.3.2 绕过 OB 直捣 JSVMP mns0301 分析](../crawler/2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) (`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`) — ob+JSVMP 双层保护的动态插桩实战

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-003）：综合 blog.jsvmp.com 中 AST 拆分、字符转移、虚拟指令、指令编码 4 篇文章 |
