---
id: "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
module: crawler
module_id: MOD-CR
title: "某Q音乐前端 JSVMP 逆向还原实战：解释器定位→插桩→指令还原"
source:
  type: url
  url: "https://www.52pojie.cn/thread-2023103-1-1.html"
  accessed: "2026-06-11"
tags: [js-reverse, jsvmp, vmp, anti-crawler, hook, instrumentation, bytecode, deobfuscation, real-case, qqmusic]
difficulty: advanced
status: active
related: [KB-CR-20260611-jsvmp-overview-protection-landscape, KB-CR-20260611-jsvmp-virtualization-pipeline, KB-CR-20260611-jsvmp-interpreter-design, KB-CR-20260611-rs-vmp-dynamic-code-generation, KB-CR-20260611-sdenv-node-addon-document-all, KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis, KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature, KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha]
ingest_id: "ING-20260611-004"
updated: "2026-06-11"
---

# 某Q音乐前端 JSVMP 逆向还原实战：解释器定位→插桩→指令还原

## TL;DR

- 某Q音乐（QQ音乐）前端签名逻辑使用 JSVMP 保护，核心是一个 **while + switch 调度循环** 的自定义字节码解释器
- 还原方法链：**识别解释器循环结构 → 提取字节码数组 n[] → 逐个 case 插桩确认功能 → 按指令执行顺序翻译回伪代码**
- 插桩（Hook）是效率关键 — 在 switch-case 分支中插入 `console.log` 记录指令地址、操作数和中间结果，精确锁定签名计算链路
- 分支跳转指令（case 13/39/47/75/82 修改 g 指针）导致字节码序列断裂，需通过前后估值推算出中断处的正确指令
- 配合 **Proxy 环境监控** 和 **Webpack 模块定位**，锁定加签逻辑所在模块并隔离分析

## 适用场景

**何时用：**

- 实战分析商业产品中 JSVMP 保护的前端签名/加密逻辑
- 需要从混淆的 VMP 解释器中还原出可读的 JS 运算逻辑
- 插件化 Hook 方法论可直接复用（case 打印、Proxy 环境对象监听）
- 学习 VMP 逆向的实操路径：理论基础对照真实案例

**何时不用：**

- 仅需概念了解 JSVMP（参考概述篇笔记）
- 面对无需还原完整逻辑的场景（直接用补环境方案绕过）
- 目标 VMP 解释器结构与本文差异过大时需自行适配 Hook 策略

## 知识要点

### 1. VMP 执行流程 vs 正常 JS 执行流程

```
正常流程:
JS 源码 → Parser 词法/语法分析 → AST → IR/字节码 → 解释执行/JIT 编译

VMP 流程:
原始 JS 源码 → Parser → AST → VMP 编译器(AST→自定义指令集) → VMP 解释器(在 JS 引擎中运行指令集) → JS 引擎继续优化/JIT
```

关键差异：VMP 编译器在 AST 之后插入了一层**自定义指令编码**，将原始语义封装为只有专用解释器能识别的指令集。

### 2. 某Q音乐 VMP 解释器结构

作者提取出某Q音乐 VMP 解释器的核心骨架：

```javascript
o = function(e, t, a, s, c) {
    return function l() {
        for (var f, p, d = [a, s, t, this, arguments, l, n, 0],
                 h = void 0,
                 g = e,     // 指令指针（程序计数器 VPC）
                 v = [],
                 aaaa; ; )
            for (; ; aaaa = n[++g])    // 逐条读取字节码
                switch (aaaa) {
                    case 0:  ...
                    case 82: ...
                }
    }
}
```

关键变量映射：

| 变量 | 角色 | 对应 JSVMP 理论 |
|------|------|----------------|
| `n` | 字节码数组（VMdata） | 自定义指令集编码后的字节码序列 |
| `g` | 指令指针（VPC） | 虚拟程序计数器，控制下一条要执行的指令 |
| `d` | 局部变量/栈数组（VMContext） | 虚拟寄存器 + 操作数栈 |
| `d[7]` | 栈顶指针 | 指向当前操作数栈顶位置 |
| `switch(aaaa)` | 调度器 Dispatcher | 按操作码分派 Handler |

**解释器识别特征**：
- `for(;;)` 无限循环嵌套 `switch` 选择结构
- 一个大数组 `n[]` 作为 switch 判断依据
- 一个计数器变量（`g`）随 case 执行递增

### 3. 字节码指令集

某Q音乐的 VMP 使用 `[OPCODE, 操作数1, 操作数2, ...]` 格式：

| case | 操作码 | 功能描述 |
|------|--------|----------|
| 0 | PUSH | 压入常量值 |
| 8 | LOAD_VAR | 从变量区加载值 |
| 13 | JMP_IF_FALSE | 条件跳转（修改 g 指针） |
| 28 | GET_PROP | 对象属性访问 `d[key1] = d[key2][key3]` |
| 30 | SET_PROP | 对象属性赋值 |
| 39 | JUMP | 无条件跳转 |
| 47 | LABEL | 跳转目标标记 |
| 50 | CALL | 函数调用 |
| 67 | STORE_VAR | 保存到变量区 |
| 69 | ADD | 加法运算 |
| 72 | BUILTIN_CALL | 内置函数调用（如 String.fromCharCode） |
| 75 | RET | 返回 |
| 76 | ARRAY_INIT | 数组初始化 |
| 78 | STRING_CONCAT | 字符串拼接 |
| 82 | COND_JUMP | 条件跳转变体 |

**分支跳转指令**（case 13 / 39 / 47 / 75 / 82）是还原的核心难点——它们会跳转至其他指令地址，导致字节码序列出现「不连续」的断裂。

### 4. 插桩（Hook）方法论

作者采用的方法：在解释器 switch-case 每个关键分支中插入 `console.log`，输出中间值、指令地址和执行结果。

**核心 Hook 点（按重要性排序）**：

```javascript
// case 28 — 对象属性读取（最核心）
console.log('[Hook] case 28 start, g=', g);
const key1 = n[++g];   // 目标变量
const key2 = n[++g];   // 对象引用
const key3 = n[++g];   // 属性名
d[key1] = d[key2][key3];
console.log(`[Hook] d[${key1}] = d[${key2}][${key3}] =>`, d[key1]);

// case 69 — 加法运算
console.log('[Hook] case 69 start');
d[n[++g]] = d[n[++g]] + d[n[++g]];
console.log(`[Hook] 加法结果 =>`, d[n[g-2]]);

// case 78 — 字符串拼接
console.log('[Hook] case 78 start, g=', g);
// 关键：String.fromCharCode 常在此处分步拼接
const target = n[++g];
const src = n[++g];
d[target] += String.fromCharCode(d[src]);
console.log(`[Hook] d[${target}] += chr(${d[src]}) => '${d[target]}'`);

// case 8 — 变量加载
console.log('[Hook] case 8 start');
d[n[++g]] = d[n[++g]];
console.log(`[Hook] d[${n[g-1]}] = d[${n[g]}] =>`, d[n[g-1]]);

// case 30 — 属性赋值
console.log('[Hook] case 30 start');
const t1 = n[++g], t2 = n[++g], t3 = n[++g];
d[t1][t2] = d[t3];
console.log(`[Hook] 属性赋值: d[${t1}][${t2}] =`, d[t1][t2]);

// case 50 — 函数调用
console.log('[Hook] case 50 start, g=', g);
// 记录调用前的参数状态

// case 67 — 变量保存
console.log('[Hook] case 67 start');
d[n[++g]] = d[n[++g]];
console.log(`[Hook] 保存: d[${n[g-1]}] = d[${n[g]}] =>`, d[n[g-1]]);

// case 72 — 内置函数调用（如 String.fromCharCode）
console.log('[Hook] case 72 start, g=', g);

// case 76 — 数组初始化
console.log('[Hook] case 76 start');
d[n[++g]] = Array(d[n[++g]]);
```

**插桩原则**：
1. 每个 case 开头打印当前的 `g`（指令指针位置）
2. 每个操作后打印涉及变量的值和变化
3. 重点 Hook **属性访问**、**函数调用**、**字符串操作** — 这些是签名计算的核心链路

### 5. 分支跳转处理

分支跳转导致字节码序列断裂，无法顺序读取。处理方法：

1. **标记跳转目标**：识别每个跳转指令的目标地址（case 13/39/47/75/82 修改 `g` 的位置）
2. **记录跳转关系**：建立 `跳转源→跳转目标` 映射表
3. **前后估值**：对于断裂处，通过前后已知变量值推断被跳过的中间指令的正确归属
4. **执行路径追踪**：在插桩输出中按实际执行顺序记录每一条经过的指令

### 6. 辅助定位手段

**Proxy 环境对象监控**：

```javascript
window = globalThis
window.navigator = {}
window.location = { constructor: '', host: 'y.qq.com' }

// 监控的关键对象
proxyObjs = ['window', 'document', 'location', 'navigator', 'history', 'screen', 'host']

// 对每个对象设置 Proxy 拦截，记录所有属性读写
function getEnvs(objs) {
    objs.forEach(name => {
        // 拦截 get/set 操作，输出访问日志
    })
}
```

**Webpack 模块定位**：

修改 webpack 加载器代码，在模块加载函数中添加日志：

```javascript
// 原始 webpack 加载器
function(t, e, n) {
    // 修改为:
    console.log('加载模块---> ', t);  // 输出模块 ID
    // ... 原始加载逻辑
}
```

通过模块 ID 反向定位签名逻辑所在的 webpack chunk。

### 7. 还原伪代码出参

将指令序列按执行顺序翻译后得到的部分还原结果：

```javascript
// 变量初始化
d = []
d[24] = Array(0);
d[17] = 25;

// 字符串拼接还原（String.fromCharCode 逐个拼接）
d[10] = "";
d[10] += String.fromCharCode(103);  // 'g'
d[10] += String.fromCharCode(108);  // 'l'
d[10] += String.fromCharCode(111);  // 'o'
d[10] += String.fromCharCode(98);   // 'b'
d[10] += String.fromCharCode(97);   // 'a'
d[10] += String.fromCharCode(108);  // 'l'
// 最终 d[10] = 'global'

// 属性链访问还原
d[10] = d[0][d[10]];  // window['global']
```

**还原策略**：
- 字符串拼接（`String.fromCharCode` 序列）直接从字节码中写出
- 属性访问链按 Hook 日志中的嵌套关系还原
- 分支跳转处按执行路径展开（保留条件判断结构）
- 函数调用通过 `o(入口地址, ...)` 形式标注，表示跳转到其他 VMP 子函数

作者的方法论核心："不写 AST 而直接通过指令序列还原伪代码"——这是一种偏门但高效的实用主义路径。

## 代码 / 命令

### 字节码提取的 Python 脚本

```python
# 输入：从 DevTools 复制出的 vmp_code（按行分割的字节码）
vmp_code = vmp.split('\n')

with open("output.txt", "w", encoding="utf-8") as file:
    for i in range(0, len(vmp_code), 2):
        if i + 2 < len(vmp_code):
            begin = int(vmp_code[i])
            end = int(vmp_code[i + 2])
            code = vmp_code[i + 1]
            substring = g[begin:end]
            file.write(
                f'{code} -- 开始索引{begin} -- 结束索引{end} '
                f'执行差值{end-begin} -- 指令集  {substring}\n'
            )
```

### 解释器插桩通用模板

```javascript
// 在解释器函数开头或 switch 入口处插入
const ORIGINAL_HANDLERS = {};  // 保存原始 case 逻辑

// 批量插桩
function instrumentCase(caseNum, handler) {
    const original = ORIGINAL_HANDLERS[caseNum];
    return function() {
        console.log(`[VMP] case ${caseNum} @ g=${g}`);
        const result = original.apply(this, arguments);
        console.log(`[VMP] case ${caseNum} result:`, result);
        return result;
    };
}
```

### 执行路径追踪

```javascript
// 在解释器最外层 for 循环中插入
const traceLog = [];
const MAX_TRACE = 10000;  // 防止死循环

while (true) {
    const opcode = n[++g];
    traceLog.push({ addr: g, opcode, stack: d.slice(0, d[7] + 1) });
    
    if (traceLog.length > MAX_TRACE) {
        console.log('[VMP] Trace limit reached');
        break;
    }
    
    switch (opcode) {
        // ... case handlers
    }
}

// 导出跟踪日志
console.log(JSON.stringify(traceLog));
```

## 注意事项

- **插桩有性能代价**：大规模 console.log 在 VMP 的高频循环中可能导致页面卡死，建议先限制日志输出次数或用断点（debugger）替代部分打印
- **分支跳转的地址 1-based vs 0-based**：需确认某Q音乐 VMP 代码中 `g` 是 0 起始还是 1 起始，否则跳转偏移计算会偏差一格
- **d[7] 栈顶指针需同步**：每个操作码的栈操作必须精确匹配，push 使 d[7]++，pop 使 d[7]--，插桩时若遗漏会导致整个栈错乱
- **Proxy 监控有覆盖盲区**：某些 VMP 实现直接访问 `globalThis` 或使用 `Reflect.get` 绕过 Proxy，需逐对象验证
- **Webpack 模块 ID 可能被二次混淆**：部分实现在 webpack 打包后又对模块 ID 做编码，需先解密再定位
- **`String.fromCharCode` 可被替换**：某些 VMP 实现用查找表替代逐个字符拼接，此时 case 72 的 Hook 方法需调整

## 相关链接

- [原文](https://www.52pojie.cn/thread-2023103-1-1.html) — 52pojie 脱壳破解区，作者 utf8，2025-04-10
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST→字节码编码全过程
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — WASM 解释器架构
  - [瑞数 VMP 动态代码生成逆向分析](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`) — 另一商业 VMP 实战逆向
  - [补环境框架：document.all C++ Addon](../crawler/2026-06-11-sdenv-node-addon-document-all.md) (`KB-CR-20260611-sdenv-node-addon-document-all`) — 补环境对抗 VMP 的另一路径
  - [某数字 4.3.2 绕过 OB 直捣 JSVMP mns0301 分析](../crawler/2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) (`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`) — ob+JSVMP 双层保护的动态插桩实战
  - [AST 还原 JSVMP X-Bogus/_signature 全流程](../crawler/2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) (`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`) — 静态还原路径：AST 节点替换 VMP 代码
  - [AI 白盒还原腾讯 CHAOS VM 验证码端到端](../crawler/2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) (`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`) — 纯 Python 从零构造 collect + JS Reverse MCP 工具

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-004）：52pojie 某Q音乐前端 JSVMP 逆向还原实战全流程 |
