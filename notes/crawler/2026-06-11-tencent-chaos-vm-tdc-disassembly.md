---
id: "KB-CR-20260611-tencent-chaos-vm-tdc-disassembly"
module: crawler
module_id: MOD-CR
title: "腾讯 Chaos VM 字节码反汇编与 TDC 设备指纹算法还原全流程"
source:
  type: internal
  url: "internal"
  accessed: "2026-06-11"
tags: [js-reverse, jsvmp, vmp, anti-crawler, chaos-vm, tdc, bytecode, disassembler, deobfuscation, symbolic-execution, device-fingerprint, tencent, real-case]
difficulty: advanced
status: active
related: [KB-CR-20260611-qqmusic-jsvmp-reverse-engineering, KB-CR-20260611-jsvmp-overview-protection-landscape, KB-CR-20260611-jsvmp-virtualization-pipeline, KB-CR-20260611-jsvmp-interpreter-design, KB-CR-20260611-rs-vmp-dynamic-code-generation, KB-CR-20260611-sdenv-node-addon-document-all]
ingest_id: "ING-20260611-005"
updated: "2026-06-11"
---

# 腾讯 Chaos VM 字节码反汇编与 TDC 设备指纹算法还原全流程

## TL;DR

- 腾讯 Chaos VM（`__TENCENT_CHAOS_VM`）是**生产级 JSVMP 保护框架**，与某Q音乐的 while+switch 解释器同源但更复杂：~60 条虚拟指令、try-catch 异常处理、308 个子VM闭包嵌套
- 字节码采用 **Base64 + 偏移表混合编码**：解码后得到 **45,700 条**混合了操作码/操作数/常数值的线性数组，需按 opcode arity 精确分离
- 写了三件套工具链：**extract_bytecode.js**（patch 原 VM 提取 g[]）→ **disasm2.js**（CFG + 逐条反汇编）→ **reconstruct.js**（符号执行栈模拟 → JS 伪代码），输出 900+ 行还原结果
- 从还原结果识别出**腾讯 TDC 设备指纹 SDK** 的完整算法：token 生成（时间戳+随机数）、document.cookie 写入、数据存取 API（mSet/mClear/mGetData）、指纹 JSON 导出（getInfo）
- 还原出的 144 个字符串直接揭示了功能模块：`getGuid`, `tokenid`, `setCookie`, `getCookie`, `TDC_itoken`, `mSet`, `mClear`, `encodeURIComponent`, `Math.random` 等

## 适用场景

**何时用：**

- 需要还原商业 JSVMP 保护的前端 SDK 的核心算法
- 学习从零构建 JSVMP 反汇编 + 符号执行工具链的方法论
- 分析腾讯系产品的设备指纹/反爬 SDK 的实现原理
- 作为 JSVMP 逆向的进阶案例：跨度从字节码解码到算法还原全链路

**何时不用：**

- 仅了解 JSVMP 概念（参考理论三篇）
- 目标不是腾讯系 VM（指令集不同，需自适配 opcode 表）
- 快速绕过（用补环境方案可直接调用 VM 而不需还原）

## 知识要点

### 1. Chaos VM 与某Q音乐 VM 的对比

| 维度 | QQ音乐 (52pojie) | 腾讯 Chaos VM (TDC) |
|------|-----------------|-------------------|
| 命名 | `for(;;) switch(n[++g])` | `__TENCENT_CHAOS_VM` |
| 操作码数量 | 15 个 case | ~60 个有效 opcode |
| 指令总条数 | 约数千 | **45,700 条** |
| 字节码编码 | 直接数组 `n[]` | **Base64 + 偏移表混合** |
| 栈结构 | `d[]` 数组 | `U[]` 数组 + 双索引 |
| 闭包支持 | 无 | **OP_45 CREATE_CLOSURE**（308 个） |
| 异常处理 | 无 | try-catch + 异常栈 `E[]` |
| 变量捕捉 | 无 | 子VM 闭包捕获父VM变量 |
| 二进制指令 | 无 | 位移/按位运算/typeof/delete/in |
| 字符串存储 | String.fromCharCode 逐个拼接 | 同样方式，但字符串被分拆到多个基本块 |

### 2. 字节码编码方式

Chaos VM 使用双层编码：

```
第一层: Base64
  "JQMvAhoaJQYvAi8DLwQvBRrv..."  (59,356 字符)
  ↓ c(B) Base64 解码
  解码后字符串 "..."

第二层: 偏移表混合
  偏移表: [5, 1518, 303, 445, 329, 334, ...]
  含义: 每 N 个字节码后插入一个常数值 V
  解码算法:
    for (i in 解码字符串.charCodeAt):
      如果当前字节数 D == 偏移表[w]:
        g.push(偏移表[G])    // 插入常数值
        D++; w=下一个; G=下一个
      g.push(charCodeAt(i))
      D++
```

**为什么用混合编码？** 偏移表嵌入的常数值（如跳转地址、立即数）大幅增加了静态分析的难度——直接 dump g[] 会看到大量 >82 的"操作码"（实际是数据值），使得简单统计 opcode 范围失效。

### 3. 完整操作码表（58 条已识别）

**栈/数据流（12 条）**：

| op | 名称 | 语义 |
|----|------|------|
| 0 | GET_PROP_PREP | 弹出 obj, prop → push [obj, prop] |
| 1 | PUSH_CTX | push [H, pop()] |
| 2 | GET_PROP | pair → obj[prop] |
| 3 | SET_PROP | obj[prop] = val |
| 7 | PUSH_EMPTY_STR | push "" (pending_str) |
| 4 | STR_BUILD_CHAR | 栈顶字符串追加 charCode |
| 15 | SWAP_PACK | 交换后重新打包 |
| 67 | POP | 丢弃栈顶 |
| 69 | DUP | 复制栈顶 |
| 37 | SET_STACK_LEN | 截断栈 |
| 47 | ENSURE_ARRAY | var[n] = var[n] \|\| [] |
| 51 | GET_PROP_PREP_REV | 逆序打包 |

**加载/存储（5 条）**：

| op | 名称 | 语义 |
|----|------|------|
| 5 | LOAD_EXT_VAR | push var[g[idx]] |
| 13 | LOAD_GLOBAL | push H[U[top]] |
| 21 | PUSH_IMM | push g[D++] |
| 32 | SET_IMM | U[top] = g[D++] |
| 66 | PUSH_WRAPPED_IMM | push [n] |

**控制流（4 条）**：

| op | 名称 | 语义 |
|----|------|------|
| 12 | JMP_IF_TRUE | if (U[top]) D = target |
| 26 | JMP | D = target |
| 9 | RETURN_SIGNAL | return !!Q |
| 43 | PUSH_TRUE_SIG | return true |

**调用（4 条）**：

| op | 名称 | 语义 |
|----|------|------|
| 17 | CALL_METHOD | obj[prop].apply(obj, args) |
| 23 | NEW_CONSTRUCT | new Func(args) |
| 41 | CALL_FUNC | fn() |
| 57 | CALL_WITH_THIS | fn.apply(H, args) |

**异常（3 条）**：

| op | 名称 | 语义 |
|----|------|------|
| 16 | EXCEPTION_POP | 异常栈弹出 |
| 19 | THROW | throw U[top] |
| 68 | REGISTER_HANDLER | push [handlerAddr, stackLvl, catchVar] |

**闭包（1 条，最关键）**：

| op | 名称 | 语义 |
|----|------|------|
| **45** | **CREATE_CLOSURE** | 从当前 VM 栈捕获变量，生成子 VM 函数 |

**二进制/数学（14 条）**：
6(SHR), 8(GTE), 14(!), 25(+), 28(==), 30(\|), 33(^), 34(*), 35(/), 39(&), 44(>), 46(<<), 48(===), 54(>>>), 60(%), 64(-)

**其他（9 条）**：
10(in), 11(栈旋转), 38(null), 42(typeof), 49(delete), 53(true), 55(.shift()), 56(arr[idx]), 58(arr[idx]=), 59(undefined), 62(Object.keys), 63(false)

### 4. 工具链架构

```
tdc.js (54KB 混淆源码)
    │
    ▼ extract_bytecode.js
    │  Patch 原 VM 代码，在 return g() 处插入 globalThis.__BC__ = R
    │  输出: 45,700 字节码 → bytecode.json
    │
    ▼ disasm2.js
    │  按 opcode arity 精确分离操作码+操作数
    │  构建 CFG (1,101 个基本块)
    │  输出: 6,858 行反汇编 + 144 个字符串字典
    │
    ▼ reconstruct.js (v4)
    │  逐基本块符号执行 (栈模拟)
    │  pending_str 延迟 resolve
    │  pair [obj, method] → obj.method() 格式
    │  输出: 900+ 行 JS 伪代码
```

**关键设计决策**：

1. **提取用 patch + eval**：不写文件，在 Node.js 中提供 `window` 全局后直接 eval 修改过的源码，捕获 VM 计算结果
2. **反汇编按 arity 跳转**：不能线性扫描——`STR_BUILD_CHAR` 吃掉 1 个操作数，`CREATE_CLOSURE` 吃掉 3 + varCount\*2 + paramCount 个操作数
3. **符号执行逐块独立**：每个基本块有自己独立的符号栈，避免 goto 后的栈污染
4. **pending_str 延迟 resolve**：字符串拼接只在被用作属性名/参数时才转为字面量，过程中保持可变引用

### 5. 从伪代码识别出 TDC 算法

还原结果中的关键代码段及其对应算法：

```javascript
// B5: 配置加载
H.Object().info = U[H["window"][0]].JUgPWZCbmXaVOkAJRKUQfmFfHcekkSGP;
→ 从 window 取加密配置字符串，解码后挂到 info 字段

// B25: 获取设备 GUID
U[?][0] = v4.apply(H, [1]).getGuid();
[5].tokenid = v3;
→ 调用原生方法获取 GUID → 存为 tokenid

// B26: Token 读取与验证
U[?][0] = [4].getCookie("TDC_itoken");
if ([5].test(v3)) goto 2668;   // 正则验证
→ 读 cookie，用 /^\d+:\d+$/ 验证格式

// B42: Token 生成 (无 Date 能力)
(Math.random() * 1000000000 | 0) + (Math.random() * 1000000000 | 0)
→ 纯随机数拼接

// B54: Token 生成 (有 Date)
(Date.now() / 1000 | 0) + ":" + (Math.random() * 1000000000 | 0)

// B69: Token 时间戳修正
var parts = token.split(":");
if (parts[0].length > 11) parts[0] = (parseInt(parts[0]) / 1000) | 0;
→ 微秒级时间戳 → 秒级

// B56: Cookie 写入
H.encodeURIComponent(key) + "=" + H.encodeURIComponent(val);
U[H["document"][0]].cookie = cookieValue;
→ 标准 document.cookie 写入

// B16: API 挂载
[7].setData = [8].mSet;
[7].clearTc = [8].mClear;
[7].getData = [8].mGetData;
→ 暴露给外部的 API 映射

// B86-B99: 指纹 JSON 序列化
遍历 TDC.sd[] → 类型判断(undefined/null/number/string) → 拼接 JSON → cd 字段
```

### 6. 还原出的 53 个字符串与 37 个采集模块

**53 个字符串（覆盖功能全集）**：

| 类别 | 字符串 | 含义 |
|------|--------|------|
| 模块系统 | `exports`, `Object`, `defineProperty`, `__esModule` | CJS/ESM 互操作 |
| 类型检查 | `Symbol`, `toStringTag`, `object`, `string`, `undefined` | typeof 判断 |
| **核心功能** | `getGuid`, `getInfo`, `tokenid`, `getData`, `setData` | TDC API |
| 数据管理 | `mSet`, `mClear`, `mGetData`, `mInit` | 批量操作 |
| Cookie 操作 | `getCookie`, `setCookie`, `TDC_itoken`, `encodeURIComponent` | 持久化 |
| **配置密钥** | `JUgPWZCbmXaVOkAJRKUQfmFfHcekkSGP` | 嵌入加密配置 |
| 时间/日期 | `_QYXcXVgmADSEKdWeOEJhiibOeUOERJMT`, `getTime` | Date 封装 |
| 工具 | `RegExp`, `Math`, `random`, `floor`, `split`, `test`, `indexOf`, `decodeURIComponent`, `substring`, `replace` | 运行时依赖 |
| 存储 | `window`, `document`, `localStorage`, `sessionStorage`, `getItem` | DOM/Storage API |
| HTML 处理 | `outerHTML`, `innerHTML`, `toLowerCase`, `aa` | 环境检测 |
| Cookie 属性 | `; expires=Tue, 31 Dec 2030 00:00:00 UTC` | 固定过期 |
| XTEA 常量 | `0x9E3779B9`（delta）、`1315845`/`1908015`（轮常量） | 内嵌在偏移表中 |

**37 个采集模块 ID（从 cd[] 构建循环还原）**：

```javascript
// 字节码地址 1636-1672 — 逐行 .get() 推入 cd[]
cd.push(module_8.get());   cd.push(module_9.get());
cd.push(module_12.get());  cd.push(module_13.get());
cd.push(module_14.get());  cd.push(module_16.get());
cd.push(module_18.get());  cd.push(module_22.get());
cd.push(module_23.get());  cd.push(module_24.get());
cd.push(module_25.get());  cd.push(module_26.get());
cd.push(module_27.get());  cd.push(module_1.get());    // ★ 模块1穿插
cd.push(module_28.get());  cd.push(module_29.get());
cd.push(module_30.get());  cd.push(module_31.get());
cd.push(module_32.get());  cd.push(module_33.get());
cd.push(module_36.get());  cd.push(module_43.get());
cd.push(module_44.get());  cd.push(module_45.get());
cd.push(module_42.get());  cd.push(module_46.get());    // ★ 42在45之后
cd.push(module_47.get());  cd.push(module_48.get());
cd.push(module_49.get());  cd.push(module_50.get());
cd.push(module_51.get());  cd.push(module_52.get());
cd.push(module_53.get());  cd.push(module_54.get());
cd.push(module_55.get());  cd.push(module_56.get());
cd.push(module_58.get());
// 共计 37 个模块
```

模块 ID 列表：`[8,9,12,13,14,16,18,22,23,24,25,26,27,1,28,29,30,31,32,33,36,43,44,45,42,46,47,48,49,50,51,52,53,54,55,56,58]`

### 7. collect 字段的四段式 XTEA 加密结构

从字节码 + XTEA delta `0x9E3779B9` + `length % 24` 对齐逻辑还原：

```
collect = base64(xtea(chunk1))
        + base64(xtea(trajectory_chunk))
        + base64(xtea(chunk2))
        + base64(xtea(sd_raw, nopad=true))
```

**构造流程**：

1. **序列化 cd[]**：遍历 37 个模块的 `.get()` 返回值 → `JSON.stringify({cd: [...]})` → 字符串
2. **24 字节分片**：`padded = raw + " ".repeat((24 - raw.length % 24) % 24)`（空格填充到 24 对齐）
3. **XTEA ECB 加密**：每 8 字节一组（`v0 += (((v1<<4)^(v1>>>5))+v1)^(sum+key[sum&3]); sum+=0x9E3779B9; v1 += ...`），共 32 轮
4. **Base64 编码**：每 24 字节编码为 4 个 Base64 字符
5. **拼接**：所有 chunk 的 Base64 编码串接为最终 `collect` 值

**XTEA Key** 由多个子函数（14 个）分别计算后拼装到 `[4][0..3]` buffer 中 — 字节码中的 `"TBKg"`、`"u|~{"`、`"][]]"` 等字符串参与 key 计算。具体 key 值每次 tdc.js 加载时变化。

## 代码 / 命令

### 工具链使用

```bash
# 1. 提取字节码
node extract_bytecode.js 2>/dev/null > $TMPDIR/bc.json

# 2. 反汇编（前 200 条指令）
node disasm2.js --start=0 --limit=200

# 3. 符号执行还原（200 个基本块）
node reconstruct.js --start=0 --limit=200

# 4. 全量反汇编
node disasm2.js --full --limit=30000 > chaos_full_disasm.txt
```

### 还原出的 TDC 完整算法

```javascript
// ====== 从 45,700 条 Chaos VM 字节码还原 ======

// 1. XTEA 加密核心（从 delta=2654435769 定位）
function xteaEncrypt(v0, v1, key) {
  var sum = 0;
  // 字节码: U[[6][0]] + 2654435769 → 32 轮迭代
  for (var i = 0; i < 32; i++) {
    // (v1 << 4) ^ (v1 >>> 5) + v1 ^ (sum + key[sum & 3])
    v0 += (((v1 << 4) ^ (v1 >>> 5)) + v1) ^ (sum + key[sum & 3]);
    sum += 0x9E3779B9;  // delta
    // (v0 << 4) ^ (v0 >>> 5) + v0 ^ (sum + key[(sum>>11) & 3])
    v1 += (((v0 << 4) ^ (v0 >>> 5)) + v0) ^ (sum + key[(sum >>> 11) & 3]);
  }
  return [v0, v1];
}

// 2. 24 字节对齐填充 + 分块
function pad24(str) {
  var rem = str.length % 24;
  if (rem > 0) str += " ".repeat(24 - rem);  // 空格填充
  return str;
}

// 3. 37 个模块采集 → cd[]
// 模块 ID 列表: [8,9,12,13,14,16,18,22,23,24,25,26,27,
//               1,28,29,30,31,32,33,36,43,44,45,42,
//               46,47,48,49,50,51,52,53,54,55,56,58]
function buildCd(modules) {
  var cd = [];
  var order = [8,9,12,13,14,16,18,22,23,24,25,26,27,
               1,28,29,30,31,32,33,36,43,44,45,42,
               46,47,48,49,50,51,52,53,54,55,56,58];
  for (var i = 0; i < order.length; i++) {
    cd.push(modules[order[i]].get());
  }
  return cd;
}

// 4. 四段式 collect 构造
function buildCollect(key, cd, trajectory, sdStr) {
  var allData = {
    cd: cd,
    sd: { od: "C", ft: sdStr }
  };
  var raw = JSON.stringify(allData);

  // 24 字节对齐
  var padded = pad24(raw);

  // 按 24 字节分片 → 每片内按 8 字节 XTEA 加密
  var result = "";
  for (var i = 0; i < padded.length; i += 24) {
    var chunk = padded.substring(i, i + 24);
    for (var j = 0; j < 24; j += 8) {
      // 将 8 字节转为 2 个 uint32
      var v0 = (chunk.charCodeAt(j) << 24) | (chunk.charCodeAt(j+1) << 16) |
               (chunk.charCodeAt(j+2) << 8) | chunk.charCodeAt(j+3);
      var v1 = (chunk.charCodeAt(j+4) << 24) | (chunk.charCodeAt(j+5) << 16) |
               (chunk.charCodeAt(j+6) << 8) | chunk.charCodeAt(j+7);
      var enc = xteaEncrypt(v0, v1, key);
      // Base64 编码每个 uint32 → 4 字节
      result += uint32ToBase64(enc[0]) + uint32ToBase64(enc[1]);
    }
  }
  return result;  // 这就是 collect 字段
}

// 5. Token 生成
function getOrCreateToken() {
  var token = getCookie("TDC_itoken");
  var pattern = /^\d+:\d+$/;

  if (!token || !pattern.test(token)) {
    var rand = Math.floor(Math.random() * 1e9);
    if (typeof Date !== "undefined" && Date.now) {
      token = (Date.now() / 1000 | 0) + ":" + Math.floor(Math.random() * 1e9);
    } else {
      token = rand + "" + Math.floor(Math.random() * 1e9);
    }
  } else {
    var parts = token.split(":");
    if (parts[0].length > 11) {
      parts[0] = (parseInt(parts[0]) / 1000) | 0;
      token = parts[0] + ":" + parts[1];
    }
  }

  document.cookie = "TDC_itoken=" + encodeURIComponent(token) +
    "; expires=Tue, 31 Dec 2030 00:00:00 UTC; path=/";
  return token;
}
```

### Base64 编码（自定义实现，从 charAt 序列还原）

```javascript
// 字节码证据: "charAt", "charCodeAt" 序列 @ 地址 9520-9536
// VM 内部实现了自定义 Base64（不依赖 window.btoa），
// 但优先检测 window.btoa（@ 地址 1557）
function customBase64(bytes) {
  var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  var result = "";
  for (var i = 0; i < bytes.length; i += 3) {
    var a = bytes[i], b = bytes[i + 1] || 0, c = bytes[i + 2] || 0;
    result += chars[a >> 2];
    result += chars[((a & 3) << 4) | (b >> 4)];
    result += i + 1 < bytes.length ? chars[((b & 15) << 2) | (c >> 6)] : "=";
    result += i + 2 < bytes.length ? chars[c & 63] : "=";
  }
  return result;
}
```
      token = (Date.now() / 1000 | 0) + ":" + Math.floor(Math.random() * 1e9);
    } else {
      // 无 Date 环境 (Node/补环境)
      token = rand + "" + Math.floor(Math.random() * 1e9);
    }
  } else {
    var parts = token.split(":");
    if (parts[0].length > 11) {
      // 微秒时间戳 → 秒
      parts[0] = (parseInt(parts[0]) / 1000) | 0;
      token = parts[0] + ":" + parts[1];
    }
  }

  document.cookie = encodeURIComponent("TDC_itoken") + "=" +
    encodeURIComponent(token) +
    "; expires=Tue, 31 Dec 2030 00:00:00 UTC; path=/";
  return token;
}
```

## 注意事项

- **VM 识别特征**：`__TENCENT_CHAOS_VM` 函数 + `function c(B)` Base64 解码器 + `["JQMvAhoaJQYv...", [5, 1518, ...]]` 数据块 — 这三个特征同时出现即可判定为 Chaos VM
- **偏移表陷阱**：偏移表包含大量超过 82 的值（如 `1518`, `1e9`, `0.75`），这些不是操作码而是嵌入数据值 — 反汇编时必须先解码，不能直接把 g[] 当作纯指令流
- **CLOSURE 递归**：308 个 CREATE_CLOSURE 指令创建了嵌套子 VM，每个子 VM 有自己的入口地址 — 完整还原需递归展开（当前工具链仅标记了入口，未展开子VM内部）
- **pending_str 解析时机**：字符串是运行时逐字符拼接的 — 直接 dump 字节码会看到单个 charCode，必须在符号执行中追踪拼接序列
- **Cookie 过期时间固定**：写死 `2030-12-31`，这是判断 TDC 版本的指纹特征
- **`JUgPWZCbmXaVOkAJRKUQfmFfHcekkSGP`** 是 Base64 编码的初始化配置 — 解码后含站点信息和加密密钥，需单独分析

## 相关链接

- 项目内：
  - [某Q音乐前端 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`) — 同类 VM 的动态插桩方法论
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST→字节码编码
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — WASM 解释器架构
  - [瑞数 VMP 动态代码生成逆向分析](../crawler/2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`) — 另一商业 VMP 实战
  - [补环境框架：document.all C++ Addon](../crawler/2026-06-11-sdenv-node-addon-document-all.md) (`KB-CR-20260611-sdenv-node-addon-document-all`) — 补环境路径

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-005）：腾讯 TDC Chaos VM 全链路分析 — 字节码解码→反汇编→符号执行→算法还原 |
