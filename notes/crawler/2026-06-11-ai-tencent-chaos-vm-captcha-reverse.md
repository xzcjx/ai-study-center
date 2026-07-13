---
id: "KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha"
module: crawler
module_id: MOD-CR
title: "AI 辅助白盒还原腾讯 CHAOS VM：点选验证码纯 Python 端到端方案"
source:
  type: url
  url: "https://bbs.kanxue.com/thread-290124.htm"
  accessed: "2026-06-11"
  author: "执着的猫"
tags: [js-reverse, jsvmp, vmp, anti-crawler, ai-assisted, xtea, bytecode, deobfuscation, captcha, tdc, chaos-vm, real-case, ocr, fingerprint, cdap, mcp]
difficulty: advanced
status: active
related:
  - "KB-CR-20260611-jsvmp-overview-protection-landscape"
  - "KB-CR-20260611-jsvmp-virtualization-pipeline"
  - "KB-CR-20260611-jsvmp-interpreter-design"
  - "KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature"
  - "KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis"
  - "KB-CR-20260611-qqmusic-jsvmp-reverse-engineering"
  - "KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated"
ingest_id: "ING-20260611-007"
updated: "2026-06-11"
---

# AI 辅助白盒还原腾讯 CHAOS VM：点选验证码纯 Python 端到端方案

## TL;DR

- 本文是一篇**腾讯防水墙（TCaptcha）点选验证码的白盒逆向全记录**：从 CHAOS VM 字节码反汇编，到 XTEA 加密自动提取、37 个采集器模块指纹识别，最终在纯 Python 中端到端构造 `collect` 字段
- 核心方法论「**变化中找不变**」：tdc.js 每次加载都会变（XTEA key、opcode 索引、模块 ID 全部随机化），但**代码语义结构不变**——作者通过字符串指纹、scope chain 追踪、指令模式匹配等方式构建了跨版本稳定的自动化提取管线
- CHAOS VM 逆向经典四步：opcode 自动识别（58 个 handler 代码特征匹配）→ 反汇编（214 个函数、24000+ 条指令）→ AI 辅助伪代码还原 → 人工断点验证
- **37 个模块指纹识别**是本文最大亮点：从 3 次失败的"静态追踪返回值"方案到最终基于"字符串集合 + 结构特征"的指纹方案，验证 3 个版本全部正确
- 介绍了作者自研的 **JS Reverse MCP** 工具：将 Chrome DevTools Protocol 的完整调试能力暴露为 MCP 标准工具，支持跨域 iframe 切换、断点处求值、Hook 拦截等逆向专用操作

## 适用场景

**何时用：**

- 需要**白盒还原** JSVMP/字节码 VM 保护的加密逻辑，而非补环境黑盒执行
- 目标 VM 的代码会动态变化（每次请求重新生成），需要构建自动化提取管线而非硬编码
- 需要控制指纹值（随机化浏览器指纹、构造逼真行为轨迹）来降低检测风险
- 了解 AI + 专用 MCP 工具（如 JS Reverse MCP）在逆向分析中的协同工作流

**何时不用：**

- 仅需快速拿到加密结果 → 补环境方案（Node.js/jsdome 执行 tdc.js）更直接
- 目标 VM 代码完全静态不变 → AST 静态还原可能更简单（参考 `KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`）
- 无逆向工具链基础 → 本文方法论需要 ADB/CDP 等协议知识储备

## 知识要点

### 1. 腾讯 CHAOS VM 架构概览

tdc.js 格式化为仅约 226 行，核心是一个名为 `__TENCENT_CHAOS_VM` 的函数，定义了完整的栈式字节码虚拟机：

```javascript
for (var E = !1; !E;) E = U[k[N++]]();
// N: 程序计数器(PC)
// k: 指令流数组 (操作码+操作数)
// U: handler 函数表 (约 70 slot, 58 有效)
```

字节码编码方式：一个大数组 `["NgMBAjQ0NgYB...", 偏移1, 值1, 偏移2, 值2, ...]`，Base64 解码后 charCode 作为操作码/操作数，字符串表按偏移插入指令流。最终产出约 **45000 个元素**的指令数组。

### 2. tdc.js 每次加载的 6 项变化

| 变化项 | 说明 | 影响 |
|--------|------|------|
| XTEA 加密密钥 | 4 个 int32 的 key 每次完全不同 | 无法硬编码 key |
| key 的运行时偏移 | 加密时给特定 key 索引加的偏移值 | 必须动态提取 |
| 操作码索引 | VM 的 58 个操作码在 handler 数组中的位置打乱 | 无法硬编码 opcode 映射 |
| 37 个模块的 ID | 每个采集器模块的注册 ID 随机重新分配 | 无法按 ID 判断模块类型 |
| 模块的调用顺序 | cd 数组中模块的排列顺序随机打乱 | 无法硬编码字段位置 |
| key 构建函数的 scope | 真实/诱饵 key buffer 的索引每次不同 | 无法硬编码判别规则 |

### 3. 操作码自动识别

操作码索引每次变化，但 **handler 函数的代码特征不变**。通过代码模式匹配自动识别 58 个操作码：

```python
patterns = {
    'ADD':  lambda code: 'b+a' in code or 'a+b' in code,
    'SUB':  lambda code: 'b-a' in code,
    'MUL':  lambda code: 'b*a' in code,
    'SHL':  lambda code: '<<' in code and '>>>' not in code,
    'USHR': lambda code: '>>>' in code,
    'PUSH_IMM': lambda code: 'k[N++]' in code and len(code) < ...,
    ...
}
```

### 4. 反汇编器 214 函数 24000+ 指令

反汇编采用递归下降策略：
1. **字节码解码**：提取 Base64 字节码和字符串表，合并为指令数组
2. **函数边界识别**：`FUNC_DEF` 指令标记函数起始 PC 和参数个数
3. **跳转目标标注**：`GOTO`/`JMP_IF`/`JMP_UNLESS` 目标地址标注为 label
4. **按函数输出**：每个函数输出为独立的 `.asm` 文件

```asm
; func_15662.asm — module 13 的 .get 函数
15662  PUSH_STR "Array"
15664  LOAD_GLOBAL            ; window.Array
15665  CALL_NEW 0             ; new Array()
15667  STORE_VAR 5            ; M[5] = arr
15671  PUSH_IMM 0
15673  VAR_PROP               ; arr[0]
15674  PUSH_IMM 537691106
15676  SET_PROP               ; arr[0] = 537691106
15677  PUSH_ARRAY 5
15679  RETURN
```

### 5. XTEA 加密定位与 Key 提取

**算法定位**：在 45000 个指令元素中搜索 `0x9E3779B9`（TEA 系列 delta 常量），直接定位到 XTEA 核心函数（约 255 条指令）。

调用链：`func_9181 (XTEA核心)` ← `func_7313 (主加密)` ← `func_10005 (导出包装)` ← `func_6186 (mGetData)` = `TDC.getData` 的实际实现。

**Key 真假混淆**：主加密函数有 14 个子函数参与 key 构建，其中只有 4 个写入真实 key buffer（buf_A），其余 10 个写入诱饵 buffer（buf_B）。真实和诱饵使用完全相同的字符串。

**不改的判别规则**：XTEA 函数**必须引用真实的 key buffer 才能加密**。从 XTEA 函数的 scope 声明出发，逆向追踪它引用的是哪个 buffer，再映射到父函数中找到写入该 buffer 的子函数——这条 scope chain 追踪逻辑跨版本稳定。

### 6. 37 个模块指纹识别（4 次迭代的突破）

这是全文最核心的方法论突破：

- **v1–v3 失败**：试图通过"追踪 `.get` 函数的返回值来源"来识别模块类型。字节码中能找到正确的 JS API 字符串，但**位置映射全部错误**——类型识别对了但分配给了错误的模块
- **根因**：VM 的动态语义（变量自增、共享引用、运行时 scope 修改）无法通过纯静态分析推断

**突破性洞察**：tdc.js 的"动态化"是**重新排列，不是重新生成**。模块 ID 和位置变了，但每个模块的代码逻辑完全不变。

**指纹方案**：
```python
fingerprint_rules = {
    'user_agent':          {'userAgent'},
    'canvas_fingerprint':  {'getContext', '2d'},
    'webgl_renderer':      {'UNMASKED_RENDERER_WEBGL'},
    'timezone':            {'getTimezoneOffset'},
    'webdriver_detect':    {'$cdc_asdjflasutopfhvcZLmcfl_'},
    'webrtc_ip':           {'RTCPeerConnection'},
    ...
}
```

对于没有区分性字符串的通用模块，用 `.get` 函数的指令数 + entry 函数的指令数 + 是否包含特定指令来区分。

**结果**：3 个 tdc.js 版本、37 个模块、**全部正确识别**，无一 unknown。

### 7. collect 的四段式结构

```
collect = base64(xtea(chunk1_padded))
        + base64(xtea(trajectory_padded))
        + base64(xtea(chunk2_padded))
        + base64(xtea(sd_str))
```

- chunk1: `{"cd":[...` + 轨迹前的指纹值
- trajectory: 鼠标轨迹数据 `[[x,y,t],[dx,dy,dt],...]`
- chunk2: 轨迹后指纹值 + `"sd":{"od":"C","ft":"xxx"}}`
- chunk1/trajectory/chunk2 用空格 pad 到 24 字节对齐，sd 不 pad。XTEA 为 ECB 模式（每 8 字节独立加密）

### 8. 完整端到端流程

```python
def main():
    # 1. 生成随机指纹 (6 款 Mac 设备画像 + 随机 Chrome 版本)
    profile = random_profile()
    # 2. prehandle 获取会话
    sess, pow_cfg, captcha_info = prehandle(profile)
    # 3. 下载并解析 tdc.js（静态提取 key、offsets、模块类型、调用顺序）
    tdc_js = download_tdc(sess)
    key, offsets, eks, module_types, require_seq, traj_index = parse_tdc(tdc_js)
    # 4. 下载验证码图片 + OCR (HSV 分割 + PaddleOCR)
    image = download_image(captcha_info)
    chars = locate_chars(image)
    click_points = match_click_points(chars, captcha_info['instruction'])
    # 5. 生成轨迹 (贝塞尔曲线)
    trajectory = generate_trajectory(click_points)
    # 6. 构造 collect
    collect = build_collect(key, offsets, module_types, require_seq, traj_index, trajectory, profile, eks)
    # 7. 求解 PoW + 生成 ans
    pow_answer = solve_pow(pow_cfg)
    ans = generate_ans(click_points)
    # 8. 提交验证
    result = verify(sess, collect, eks, ans, pow_answer)
    print(f"验证通过！ticket: {result['ticket']}")
```

纯 Python 实现，不依赖浏览器环境，单次执行约 **2–3 秒**（主要耗时在网络请求和 OCR）。

### 9. JS Reverse MCP 工具介绍

作者自研的 MCP 服务器，将 Chrome DevTools Protocol（CDP）的完整调试能力暴露为标准化 MCP 工具，解决 AI 编码助手"无法直接操控浏览器调试器"的短板。

**30+ 工具覆盖全链路**：

| 能力领域 | 工具 | 逆向场景 |
|----------|------|----------|
| 脚本分析 | list_scripts, search_in_sources, get_script_source | 搜索 tdc.js 中 `2654435769` 定位 XTEA delta 常量 |
| 断点调试 | set_breakpoint, set_breakpoint_on_text, XHR/Fetch 断点 | 在压缩代码中搜索文本自动设断点 |
| 执行控制 | pause/resume/step_over/step_into/step_out | 在 XTEA 入口 step into 确认算法细节 |
| 函数追踪 | hook_function, trace_function | hook `encodeURIComponent` 抓取 collect 原始数据 |
| 网络分析 | list_network_requests, get_request_initiator | 从 XHR 请求倒推到加密函数调用栈 |
| 运行时检查 | evaluate_on_callframe, inspect_object | 在断点处提取闭包中的 XTEA key |

**三大不可替代能力**：

1. **跨域 iframe 切换**：通过 CDP `Runtime.executionContextCreated` 事件追踪所有 frame 执行上下文，支持 `select_frame(1)` 切换到 `turing.captcha.gtimg.com` 直接访问 `TDC` 对象
2. **断点处求值**：`evaluate_on_callframe` 可在暂停的调用帧上下文中求值闭包变量（如 XTEA key buffer），Playwright/Puppeteer 只能执行全局 console 脚本，无法访问局部闭包变量
3. **过检测**：连接到用户已运行的正常 Chrome 实例（`--remote-debugging-port=9222`），`navigator.webdriver === false`，`window.chrome` 正常，零自动化标记

GitHub 地址：`github.com/zhizhuodemao/js-reverse-mcp`

### 10. AI 的准确贡献边界（作者诚实评估）

**AI 做得好**：字节码精读与伪代码还原（300 条指令的函数几分钟出初稿）、模式识别（14 个 key 子函数中找真/假判别规则）、方案迭代速度提升、跨文件 scope chain 追踪。

**AI 做不好**：JS 位运算语义（`>>` 不截断但 `>>>` 截断的差异容易出错）、VM 动态行为推断（LOAD_DYN/共享引用/运行时 scope 修改无法静态分析）、**创造性突破**（"从追踪返回值到指纹识别"的思路转换是人提出的）。

## 代码 / 命令

### Key 提取公式（跨版本不变）

```python
# 每个 key 元素的生成公式
key[index] = Σ (charCodeAt(string[i]) << offset) << (shift)
# i = 0..3
# 变化的是 string、offset、index
```

### 轨迹生成（贝塞尔曲线）

```python
def generate_trajectory(click_points):
    trajectory = []
    last_x, last_y, last_t = 0, 0, 0
    for target_x, target_y in click_points:
        points = bezier_move(last_x, last_y, target_x, target_y)
        for x, y, t in points:
            if not trajectory:
                trajectory.append([x, y, t])    # 第一个点绝对值
            else:
                trajectory.append([x - last_x, y - last_y, t - last_t])  # 相对偏移
            last_x, last_y, last_t = x, y, t
    trajectory.append([1, 1, 12])  # 固定结尾
    return trajectory
```

### JS Reverse MCP 安装

```bash
git clone https://github.com/zhizhuodemao/js-reverse-mcp.git
cd js-reverse-mcp
npm install
npm run build

# 启动 Chrome（保留登录状态）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

# Claude Code 配置
claude mcp add js-reverse node /path/js-reverse-mcp/build/src/index.js -- --browser-url=http://127.0.0.1:9222
```

## 注意事项

- 本文目标为腾讯防水墙 V1（文字点选），方案可迁移到其他 CHAOS VM 保护的目标，但模块指纹规则和 opcode 匹配需针对新目标重新编写
- 如果腾讯对模块代码本身进行变换（指令替换、插入花指令、变量名混淆），基于字符串指纹的识别方案将受到挑战
- eks 是 Base64 编码的 176 字节数据（XTEA key + offsets + 元数据的加密信封），key 生命周期与 tdc.js 绑定：页面加载时生成新 key，整个验证会话内不变
- PaddleOCR 识别准确率约 85%，形近字（"边"/"芭"/"笆"）容易混淆，可换更强的 Transformer 模型优化
- JS Reverse MCP 连接到已运行的 Chrome 实例时，需确保 chrome 启动参数正确（`--remote-debugging-port=9222`）

## 相关链接

- [原文：使用AI还原腾讯点选验证码算法-动态jsvmp](https://bbs.kanxue.com/thread-290124.htm)（看雪论坛，作者：执着的猫，2026-02-28）
- [JS Reverse MCP GitHub](https://github.com/zhizhuodemao/js-reverse-mcp) — 作者自研的 JS 逆向专用 MCP 工具
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST 拆分→字节码编码
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — WASM 解释器架构（CHAOS VM 为 JS 版栈式解释器）
  - [AST 还原 JSVMP X-Bogus/_signature 全流程](../crawler/2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) (`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`) — 另一种静态还原路径
  - [某数字绕过 OB 直捣 JSVMP mns0301 分析](../crawler/2026-06-11-ob-bypass-jsvmp-mns0301-analysis.md) (`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`) — 动态插桩路径
  - [某Q音乐 JSVMP 逆向还原实战](../crawler/2026-06-11-qqmusic-jsvmp-reverse-engineering.md) (`KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`) — 解释器定位→插桩→指令还原

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-007）：看雪论坛 AI 辅助白盒还原腾讯 CHAOS VM 点选验证码全流程（含 JS Reverse MCP 工具） |
