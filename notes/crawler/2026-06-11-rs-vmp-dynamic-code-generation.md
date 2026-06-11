---
id: KB-CR-20260611-rs-vmp-dynamic-code-generation
module: crawler
module_id: MOD-CR
title: "瑞数vmp动态代码生成原理逆向分析"
source:
  type: url
  url: "https://blog.howduudu.tech/article/95f60638eaa0647bcf327fb4f2c2887c/"
  accessed: "2026-06-11"
tags: [js-reverse, vmp, anti-crawler, security, code-generation, obfuscation]
difficulty: advanced
status: active
related: [KB-CR-20260611-sdenv-node-addon-document-all, KB-CR-20260611-jsvmp-overview-protection-landscape, KB-CR-20260611-jsvmp-virtualization-pipeline, KB-CR-20260611-jsvmp-interpreter-design, KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis, KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature, KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha]
ingest_id: ING-20260611-001
updated: "2026-06-11"
---

# 瑞数vmp动态代码生成原理逆向分析

## TL;DR

- 瑞数vmp（虚拟代码保护，JavaScript Virtual Machine Protection）通过**固定字符串 + 动态 seed**（nsd）生成每次不同但功能等价的代码，是常见反爬方案
- nsd（数字 seed）通过线性同余生成器驱动代码差异化：**数组乱序、变量名随机化、换行数随机化**
- `$_ts` 对象是关键运行时容器，存储 cp 六个元素、jf 防格式化标记、aebi 代码片段映射
- 动态代码生成核心算法 `grenIfelse` 是**深度优先递归 + if/else 嵌套**，约 200 行 JS 即可还原
- `$_ts.cp[3]`（校验和）和 `$_ts.jf`（格式化标记）是两个**主要异常触发点**，值不对会导致代码崩溃或死循环
- 逆向分析项目 `rs-reverse` 已开源在 GitHub：https://github.com/pysunday/rs-reverse

## 适用场景

**何时用：**

- 分析使用了瑞数安全产品反爬保护的网站
- 学习 JavaScript 虚拟机保护技术的逆向思路
- 构建自动化请求时需理解动态代码生成逻辑以避免触发反爬
- 研究 JSVMP（JavaScript Virtual Machine Protection）虚拟机保护的通用分析方法

**何时不用：**

- 简单的参数签名/校验（不需 VM 级别分析）
- 纯粹的前端 UI 逆向（本文涉及的是代码安全层，非界面还原）
- 常规的 API 接口自动化（本文属于深层次安全逆向，非接口对接）

## 知识要点

### 1. 三种不变的字符串：代码生成的原材料

瑞数动态代码虽然每次生成结果不同，但原材料固定。三类字符串分别作用：

| 字符串 | 作用 | GitHub 链接 |
|--------|------|-------------|
| cp 值字符串 | 复制到 `window.$_ts.cp[0]` 和 `cp[2]`，供动态代码运行 | [$_ts.js](https://github.com/pysunday/rs-reverse/blob/main/src/immutext/%24_ts.js) |
| globalText1/2 | globalText1 生成第一段代码，globalText2 生成第二段代码 | [global.js](https://github.com/pysunday/rs-reverse/blob/main/src/immutext/global.js) |
| nsd 和 cd 值 | 由 `$_ts` 带入，nsd 是驱动代码差异化的核心 seed | — |

理解这三类字符串是逆向 vmp 的**第一步**：从混淆代码中提取固定部分，剩下的差异化均源于 nsd。

### 2. nsd 的三大作用：差异化引擎

nsd 是一串每次不同的数字，通过 `getScd` 函数（线性同余生成器）产生关联序列：

```javascript
function getScd(scd) {
  return function(look) {
    scd = 15679 * (scd & 65535) + 2531011;
    return scd;
  }
}
```

**核心机制**：闭包持有 `scd` 变量，每次调用返回新值。三个主要用途：

- **数组乱序**（`arraySwap`）：通过 `scd() % len` 决定交换下标，打乱变量名数组 `cp[1]`
- **生成变量名数组**（`grenKeys`）：先生成固定长度的 `_$`+字母数字组合，再用 arraySwap 打乱 → 存入 `$_ts.cp[1]`
- **控制换行数量**：`scd() % 5` 决定 globalText1 每段代码前的换行数，使代码外观每次不同

**关键推理**：如果能精确复制 getScd 和初始 seed，就可以**完全还原任意一次运行生成的动态代码**——这是逆向工作的核心突破口。

### 3. `$_ts` 部分值的初始化：防格式化检测

`grenJf` 方法返回值赋给 `$_ts.jf`，用于判断源码是否被格式化：

```javascript
function grenJf() {
  const flags = [1, 0, 0];
  const flag = --flags[1];  // 格式化检测通过执行
  return !flag;              // 反码检测通过执行
}
```

`const flag = --flags[1]` 前后有两项检测：
- **前面**：格式化检测（格式化后源码布局变化会触发异常）
- **后面**：序列化检测（检查反码是否被自动解码，如 16 进制 → 10 进制）

**如果这两个检测被绕过，代码将进入死循环或崩溃。** 这也是上一篇博文提到的「代码格式化后无法正常运行」的根本原因。

### 4. 动态代码生成核心算法：grenIfelse

核心程序不足 200 行（[Coder.js](https://github.com/pysunday/rs-reverse/blob/main/src/handler/Coder.js)），动态代码分两部分生成。

**解析 globalText1 流程**：

1. 用 `optext`/`opmate`/`opdata` 初始化游标
2. 定义全局变量（`G_$e4` 等五个）
3. 定义 `keycodes`（映射代码片段）：

```javascript
this.keycodes.push(...optext.getLine(
  optext.getCode() * 55295 + optext.getCode()
).split(String.fromCharCode(257)));
```

**核心递归 `grenIfelse`**（净化后）：

```javascript
const grenIfelse = function(start, end, codeArr) {
  const arr8 = [4, 16, 64, 256, 1024, 4096, 16384, 65536];
  const key = 'key';
  let text;
  let diff = end - start;

  if (diff == 0) return codeArr;
  else if (diff == 1) { /* 省略 */ }
  else if (diff <= 4) {
    // 短区间：展开为线性 if/else if 链
    text = "if("; end--;
    for (; start < end; start++) {
      codeArr.push(text, key, "===", start, "){");
      text = "}else if(";
    }
    codeArr.push("}else{"); codeArr.push("}");
  } else {
    // 长区间：取 2^n 步长，递归二分
    const step = arr8[arr8.findIndex(it => diff <= it) - 1] || 0;
    text = "if(";
    for (; start + step < end; start += step) {
      codeArr.push(text, key, "<", start + step, "){");
      grenIfelse(start, start + step, codeArr);  // 递归左子区间
      text = "}else if(";
    }
    codeArr.push("}else{");
    grenIfelse(start, end, codeArr);              // 递归右子区间
    codeArr.push("}");
  }
  return codeArr;
};
```

**运行 `grenIfelse(0, 10, []).join('')` 可直观看到生成的 if/else 嵌套代码**。这是动态代码中那堆看似不可读的条件判断的来源。

### 5. `$_ts` 对象全字段速查

```javascript
{
  "cd":    "原 $_ts.cd 值不变",
  "cp": [
    "源码固定文本 cp0",           // cp[0]
    "变量名数组（由 nsd 打乱）",   // cp[1]
    "源码固定文本 cp2",           // cp[2]
    "校验和（每隔 100 字符取值累加，值不对异常）", // cp[3]
    "生成代码用时的毫秒时间戳",    // cp[4]
    undefined,                     // cp[5]
    ""                             // cp[6]
  ],
  "jf":    "防格式化标记，false=未格式化，值不对异常",
  "aebi":  "多组数字数组，数组长度对应代码片段数",
  "scj":   [],
  "lcd":   undefined,
  "nsd":   undefined
}
```

**两个主要异常触发点**：
- **`cp[3]`**：类似文件 hash，对代码字符串每 100 字符取值算 ASCII 累加，值对不上直接异常
- **`jf`**：标记是否被格式化，`false` 才正常执行（格式化后该值变化）

### 6. JSVMP 逆向方法论总结

逆向瑞数 vmp 的执行路径：

```
入口文件 run_$a9_ENTER()_0_1.js
  ↓ _$f2(69) 进入解析（仅执行一次）
  ↓ 提取固定字符串（cp0/cp2/globalText1/globalText2）
  ↓ 还原 getScd 闭包 → 复现 nsd 序列
  ↓ 用 nsd 还原 arraySwap → 得到变量名数组 cp[1]
  ↓ 解析 globalText1 → 调用 grenIfelse 生成结构化代码
  ↓ 解析 globalText2 → 调用 this.special 方法
  ↓ 计算并设置 cp[3] 校验和 + jf 防格式化标记
  ↓ 验证 cp[4] 时间戳
```

**逆向关键路径**：固定字符串提取 → nsd seed 确定 → getScd 还原 → 变量名映射 → 代码逻辑还原。一旦这三个环节闭环，动态代码就可以**精确复现**。

## 代码 / 命令

```javascript
// 示例：验证 grenIfelse 输出
const test = grenIfelse(0, 10, []);
console.log(test.join(''));
// 输出为完整的 if/else 嵌套判断结构
```

GitHub 项目完整代码：https://github.com/pysunday/rs-reverse

## 注意事项

- **`$_ts.cp[3]` 校验和**：对代码字符串每 100 字符取 charCode 累加，任何代码修改都需重新计算，否则异常
- **`$_ts.jf` 防格式化**：格式化（Prettier/IDE 格式化）会改变代码布局导致 jf 标记被改写，触发死循环
- **debugger 删不掉**：不是简单删除 debugger 语句就能过，删除会破坏 cp[3] 校验
- 本文分析的是瑞数 vmp **动态代码生成**阶段，不是完整的 cookie 生成逆向，后续还需逆向 cookie 生成逻辑
- 逆向仅供学习研究，不应用于非法用途

## 相关链接

- [原文：瑞数vmp-动态代码生成原理](https://blog.howduudu.tech/article/95f60638eaa0647bcf327fb4f2c2887c/)
- [GitHub：rs-reverse 逆向分析项目](https://github.com/pysunday/rs-reverse)
- 项目内：[补环境框架：document.all 的 C++ Node Addon 方案](./2026-06-11-sdenv-node-addon-document-all.md) (`KB-CR-20260611-sdenv-node-addon-document-all`)
  - [某数字 4.3.2 绕过 OB 直捣 JSVMP mns0301 分析](./2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) (`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`) — ob+JSVMP 双层保护的动态插桩实战
  - [AST 还原 JSVMP X-Bogus/_signature 全流程](./2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) (`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`) — 静态还原路径：AST 节点替换 VMP 代码
  - [AI 白盒还原腾讯 CHAOS VM 验证码端到端](./2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) (`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`) — 纯 Python 从零构造 collect + JS Reverse MCP 工具

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-001） |
