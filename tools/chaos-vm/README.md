# Chaos VM 反编译工具链

> 腾讯 `__TENCENT_CHAOS_VM` 字节码反汇编与 JS 伪代码还原三件套  
> 对应笔记：`KB-CR-20260611-tencent-chaos-vm-tdc-disassembly`

## 文件说明

| 文件 | 作用 | 输入 | 输出 |
|------|------|------|------|
| `extract_bytecode.js` | 从 tdc.js 中提取 45,700 条字节码 | `tdc.js` | `$TMPDIR/bc.json` |
| `disasm.js` | 按 opcode arity 精确反汇编 | `$TMPDIR/bc.json` | 反汇编文本 |
| `reconstruct.js` | 符号执行 → JS 伪代码还原 | `$TMPDIR/bc.json` | JS 伪代码文本 |
| `tdc.js` | 原始混淆源码（54KB） | — | — |

## 快速开始

```bash
cd tools/chaos-vm

# Step 1: 提取字节码
node extract_bytecode.js 2>/dev/null > $TMPDIR/bc.json

# Step 2: 反汇编（查看前 200 条指令）
node disasm.js --start=0 --limit=200

# Step 3: 符号执行还原（200 个基本块 → JS 伪代码）
node reconstruct.js --start=0 --limit=200

# Full 全量反汇编
node disasm.js --full --limit=30000

# Full 符号执行还原
node reconstruct.js --start=0 --limit=600
```

## 工具详解

### extract_bytecode.js

**原理**：修改 tdc.js 源码 — 在 VM 的 `return g(), R`（字节码加载器）前插入 `globalThis.__BC__ = R;`，然后在 Node.js 中 `eval` 执行，从全局对象取出解码后的字节码数组。

```javascript
// 核心机制
const patched = src.replace(
  /return g\(\),\s*R/,
  'globalThis.__BC__ = R; return g(), R'
);
eval(patched);  // window = globalThis
const bytecode = globalThis.__BC__;  // 45,700 条目
```

**为什么不用手动提取**：tdc.js 使用 Base64 + 偏移表**混合编码** — 偏移表中的值（`1518`, `1e9`, `0.75`, `2654435769`）是作为数据内嵌在指令流中的，手动解码需要完整复现 VM 的 `c()` 解码器和 loader 逻辑。直接 patch 运行原码省去这层解码风险。

### disasm2.js

**原理**：按 opcode arity 逐条解析。不是简单的线性扫描 — 必须按每条指令所需的操作数个数跳过操作数。

```javascript
// arity 表（部分）
const arities = { 4:1, 5:1, 11:1, 12:1, 17:1, 21:1, 23:1,
                  26:1, 32:1, 37:1, 41:1, 47:1, 57:1, 66:1, 68:3 };
// OP_45 CREATE_CLOSURE: arity = 3 + varCount*2 + paramCount
```

**输出格式**：
```
[  1126] ADD                  a + b
[  1127] PUSH_IMM             push g[D++] [value=2654435769]
[  1129] ADD                  a + b
[  1130] ARRAY_IDX_SET        arr[idx] = val
→ 识别为: U[[6][0]] += 2654435769  (XTEA delta)
```

**参数**：
- `--start=N` : 起始地址（默认 0）
- `--limit=N` : 最大指令数（默认 200，`--full` 全量）
- `--full`   : 全量反汇编

### reconstruct.js

**原理**：在基本块（CFG）级别做符号执行：
1. 构建控制流图（CFG），识别所有基本块和跳转关系
2. 预扫描提取全部字符串（`PUSH_EMPTY_STR + STR_BUILD_CHAR*` 序列）
3. 逐基本块符号执行：用符号栈模拟 VM 操作，`pair [obj, "method"]` 自动识别为 `obj.method()` 格式
4. 块间栈独立（避免 goto 后的栈污染）

**关键设计**：
- `pending_str` 延迟 resolve — 字符逐个拼接过程中不做转换，只在被用作属性名时一次性转为字符串字面量
- `prop()` 自动识别 `.method` vs `[index]` 格式
- `call()` 自动拆分 `[obj, method]` 对为 `obj.method(args)`

**参数**：
- `--start=N` : 起始地址（默认 0）
- `--limit=N` : 最大基本块数（默认 80）

## 技术细节

### Chaos VM 操作码表（58 条已识别）

| 类别 | opcode | 语义 |
|------|--------|------|
| 栈操作 | 0,1,2,3,7,4,15,51,67,69,37,47 | pair/GET/SET/push/pop/dup |
| 加载/存储 | 5,13,21,32,66 | var/global/imm |
| 控制流 | 12,26,9,43 | jmp/ret |
| 调用 | 17,23,41,57 | method/new/func/ctx |
| 异常 | 16,19,68 | pop/throw/handler |
| 闭包 | **45** | CREATE_CLOSURE（308 个） |
| 数学/位 | 6,8,14,25,28,30,33,34,35,39,44,46,48,54,60,64 | 全部算术/位/比较运算 |

### 字节码编码结构

```
第一层: Base64 解码 (c 函数)
  "JQMvAhoaJQYvAi8DLwQvBRrv..."  →  charCode 序列

第二层: 偏移表插入
  [5, 1518, 303, 445, ...]
  每 N 个 charCode → 插入一个常数值 V
  → 最终 45,700 个元素的指令流 g[]
```

## 相关笔记

- [腾讯 Chaos VM 反汇编与 TDC 算法还原](../../notes/crawler/2026-06-11-tencent-chaos-vm-tdc-disassembly.md)
- [AI 辅助白盒还原腾讯 CHAOS VM：点选验证码纯 Python 端到端方案](../../notes/crawler/2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md)
- [某Q音乐 JSVMP 逆向还原实战](../../notes/crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md)
