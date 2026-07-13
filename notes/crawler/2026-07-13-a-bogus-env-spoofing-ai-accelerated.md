---
id: "KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated"
module: crawler
module_id: MOD-CR
title: "JSVMP 类型 a_bogus 补环境复现：基于 Claude Code 与 DeepSeek V4 的 AI 加速实践"
source:
  type: url
  url: "https://bbs.kanxue.com/thread-291194.htm"
  accessed: "2026-07-13"
  author: "红皮西瓜（看雪论坛）"
tags: [js-reverse, jsvmp, vmp, anti-crawler, browser-emulation, sdenv, fake-env, trace, proxy, signature, a-bogus, ai-assisted, claude-code, deepseek, tls-fingerprint, persistent-signer, real-case]
difficulty: advanced
status: active
related: ["KB-CR-20260611-jsvmp-overview-protection-landscape", "KB-CR-20260611-jsvmp-virtualization-pipeline", "KB-CR-20260611-jsvmp-interpreter-design", "KB-CR-20260611-sdenv-node-addon-document-all", "KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature", "KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha"]
ingest_id: "ING-20260713-001"
updated: "2026-07-13"
---

# JSVMP 类型 a_bogus 补环境复现：基于 Claude Code 与 DeepSeek V4 的 AI 加速实践

## TL;DR

- **补环境替代算法提取**：面对 100KB+ opcode 表的 JSVMP 签名字段（某音系 `a_bogus`），走"构建假浏览器环境 → 直接执行原始 SDK → 离线产出签名"的路径，将传统 3–5 天手动迭代压缩到数小时
- **trace_env.js 自愈 Proxy 是核心创新**：内置 ~80 个启发式猜值规则 + 递归两层 Proxy 自动补全缺失属性 + 最多 8 轮自愈重跑，输出可直接 `require` 的 `fake_env.js` 完整环境桩
- **AI 在四个环节加速**：环境桩类型修正、自定义 Base64 字母表识别、172 vs 192 系统化实验、模板批量定制
- **五个高频踩坑点**：先追踪再补全、TLS 指纹必须先排查、URL 参数顺序不可变、假 XHR 响应 JSON 必须完整、SDK 内部定时器需显式 `process.exit(0)`
- **生产级持续签名架构**：`sign.js --server` 持久化 Node 进程 + `persistent_signer.py` 管理生命周期，首次 ~1500ms 后复用零开销

## 适用场景

**何时用：**

- 目标签名逻辑受 JSVMP 保护，算法代码量巨大（100KB+ 字节码），静态还原周期以周/月计
- 目标 SDK 可以离线加载执行（不依赖实时 DOM 渲染结果）
- 有 Claude Code / DeepSeek V4 等 AI 编程助手可用，加速探索-验证循环
- 签名字段需要稳定、高频产出（配合持久化签名服务器）

**何时不用：**

- 目标 SDK 强依赖 DOM 渲染（Canvas 指纹需要真实绘制），补环境方案复杂度超过静态还原
- 类名/变量名已被彻底混淆且无从定位 SDK 入口
- 仅需单次/低频签名 —— 直接浏览器拦截更省时
- 追求比补环境更彻底的方案（参考 AST 还原路径：`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`）

## 知识要点

### 1. 补环境 vs 算法提取：范式转换

JSVMP 保护的签名字段，传统路径是"定位解释器 → 插桩 → 日志分析 → 反推算法"（参考 `KB-CR-20260611-qqmusic-jsvmp-reverse-engineering`、`KB-CR-20260611-ob-bypass-jsvmp-mns0301-analysis`）。补环境方法论提供另一条路径：

**核心思路**：不提取算法本身，而是在 Node.js 的 `vm` 沙箱中构建足够逼真的假浏览器环境，直接执行原始 SDK 文件来离线产出签名。将问题从"理解算法"转换为"构建环境表面"。

**a_bogus 案例的 3 个协作 SDK 文件**（加载顺序严格不可变）：
1. 主 SDK（较小）
2. 运行时/VM 文件（最大，>100KB）
3. 初始化引导文件

### 2. trace_env.js 自愈 Proxy：自动化环境追踪

这是整套工具链最具创新性的环节。传统补环境需要人工反复加载 SDK → 观察报错 → 补齐缺失属性（通常需 3–5 轮手动迭代）。

**核心机制**：

| 组件 | 作用 |
|------|------|
| `guessDefault()` | 内置 ~80 个属性名模式匹配规则。`hardwareConcurrency` → `8`、`onLine` → `false`、动词开头 → 空函数、首字母大写 → 空构造函数 |
| `makeHealer()` | 递归 2 层 Proxy 包裹对象，访问不存在的属性时自动调用 `guessDefault()` 创建桩值，记录访问路径到 `traceLog` |
| 自动重跑 | Proxy 补全仍导致 SDK 崩溃时，解析错误信息的属性路径 → 注入缺失桩 → 重新加载 SDK，默认最多 8 轮 |

**日志示例**：
```
[TRACE] navigator.connection.effectiveType → "4g" (guessed)
[TRACE] navigator.connection.rtt → 50 (guessed)
[TRACE] document.characterSet → "UTF-8" (guessed)
[TRACE] screen.colorDepth → 24 (guessed)
```

输出为 `fake_env.js` —— 一个可直接 `require` 的完整环境桩模块，覆盖 SDK 实际触碰的所有属性。

### 3. 假浏览器环境构建：各层的覆盖策略

基于 trace_env.js 输出构建完整假浏览器表面：

| 层 | 覆盖范围 | 关键约束 |
|----|----------|----------|
| **navigator** | ~40 属性：UA、platform、hardwareConcurrency=8、deviceMemory=8、webdriver=false、connection（effectiveType/rtt/downlink）、userAgentData（brands 含 Chromium 146）、clipboard、permissions、plugins/mimeTypes | `webdriver` 必须为 `false`，`userAgentData.brands` 必须匹配真实 Chrome 版本 |
| **DOM** | `document.createElement` 返回带完整方法的伪元素；canvas 2D/webgl 返回稳定假渲染结果 | `addEventListener` 必须捕获 handler 引用（存入 `__eventHandlers`），这是轨迹注入的前提 |
| **存储** | localStorage/sessionStorage 通过 `Storage` 原型类实现 + 正确 `Symbol.toStringTag` + 原型链 | SDK 检测 `instanceof Storage`**
| **平台类** | Headers、Request、Response、FormData、Blob、AbortController、URL、URLSearchParams | 全部 `typeof === 'function'`，不可用普通 object 替代 |
| **Observer 系列** | IntersectionObserver、MutationObserver、ResizeObserver | 设为合法空类即可 |
| **反重放检测** | `process`、`Deno`、`require`、`global`、`module` 全部显式设为 `undefined` | 防止 SDK 检测到 Node 运行时而拒绝执行 |

### 4. 假 XHR 与签名提取：两个静默故障点

SDK 不暴露 `sign(url)` 这样的公开 API，而是透明 hook `XMLHttpRequest.prototype.send`。捕获签名需要构建假 XHR 对象。

**关键故障点 1 — 运行时 token 响应**：
SDK 初始化时可能 POST 请求运行时 token。fake XHR 的 `responseText` 需返回合法 JSON 并含必要字段（如 `data.d`），否则初始化在 **不抛异常的情况下跳过关键步骤**。

**关键故障点 2 — paths 配置**：
`window.bdms.init({ aid: 6383, paths: ['^/aweme/v1/web/'] })` 中 `paths` 是正则前缀数组，不是字面量路径。配置错误导致签名长度正确、字母表正确、Base64 解码干净——但服务端拒绝。**这是最高频的静默故障点**。

**paths 发现技巧**：在浏览器 DevTools Sources 面板全文搜索 `.init(`，复制线上完整配置对象。

### 5. 轨迹数据注入诊断

`debug_trajectory.js` 检查 SDK 加载并注入轨迹后 `moveList`/`clickList`/`keyList` 数组的实际内容和长度。**"写诊断简单，但想到要做检查才是关键"**——AI 在阅读 SDK 源码时自然产生这个假设，继而自动生成验证脚本。

### 6. 锁定随机性用于调试

签名 SDK 内嵌 `Date.now()` 和 `Math.random()` 调用，每次输出不同。为便于调试和版本对比：

```javascript
Math.random = () => 0.5;
Date.now = () => 1700000000000;
```

**注意**：
- 必须在 SDK 加载前完成锁定（SDK 在加载时缓存引用）
- 生产环境不应锁定随机性（服务端可能校验时间戳新鲜度）

### 7. TLS 指纹绕过：线上验证的强制要求

签名正确性的唯一充分证据是真实 HTTP 往返验证。长度检查、格式检查、Base64 解码检查只是必要条件。

**TLS 指纹模拟是强制要求**：反爬系统在 TLS 握手阶段检测 ClientHello、JA3 指纹、HTTP/2 SETTINGS 帧。同样的签名 URL 和 cookie，Python 的 `requests`/`urllib` 或 Node 的 `https.request` 在 TLS/HTTP-2 层就被识别为非浏览器流量。

**解决方案**：使用 `curl_cffi`（Python）或 `cycletls`（Node）等 TLS 指纹模拟库。

### 8. AI 辅助加速四个关键环节

| 环节 | AI 作用 | 加速倍数 |
|------|---------|----------|
| **环境桩类型修正** | `trace_env.js` 的 `guessDefault()` 可能产出类型错误的桩值（如本该是 number 却返回了 string），AI 读取追踪日志、识别类型不匹配模式、批量修正 | ~10× |
| **自定义 Base64 字母表识别** | AI 快速编写和运行字母表匹配脚本，批量验证不同版本 SDK | ~5× |
| **172 vs 192 系统化实验** | "提出假设 → AI 生成实验脚本 → 批量运行 → 分析结果 → 排除或确认假设"循环压缩到 1–2 小时 | ~20× |
| **模板批量定制** | `core/` 目录下的模板文件（`sign.js`、`fake_env.js`、`persistent_signer.py`）是通用框架，AI 一次性完成所有 TODO 占位符替换 | ~5–10× |

**核心理念**：AI 加速的是"探索循环"（提出假设 → 验证 → 修正），而非"替代人类写代码"。每个环节都需要人类确认产出的正确性。

### 9. 生产级持久化签名架构

对于高频调用场景，每次重载 SDK 不可接受（首次签名约 1500ms）：

```
┌─────────────────────┐     HTTP / IPC      ┌─────────────────────┐
│ persistent_signer.py │ ◄──────────────────► │ sign.js --server     │
│ (Python 客户端)       │                      │ (持久化 Node 进程)    │
│ - 管理生命周期         │                      │ - 加载 SDK 后保持运行  │
│ - 请求签名             │                      │ - 处理签名请求         │
└─────────────────────┘                      └─────────────────────┘
```

- `sign.js --server` 加载 SDK 后保持运行，通过 IPC 或 HTTP 接收签名请求
- `persistent_signer.py` 管理签名服务器的生命周期
- **关键**：SDK 安装的内部心跳定时器和 token 刷新定时器维持了 Node 事件循环——签名完成后必须显式调用 `process.exit(0)`

### 10. SDK 版本管理与实时抓取原则

**永远从目标站点线上实时抓取**，不要从 GitHub 镜像或博客复制。SDK 版本以周为单位变化，过期文件导致签名被静默拒绝。

抓取工具 `capture_sdk.js` 使用 Playwright 打开目标页面，按文件大小（>20KB 阈值）和 URL 正则匹配过滤 JS 响应，保存到 `bundles/` 并生成含 SHA-256 的 `manifest.json`。

URL 正则匹配模式：`vmp|protect|crawler|risk|sec|sdk|runtime|bundler|glue|loader|sign|guard|shield`

## 代码 / 命令

```javascript
// trace_env.js 核心：自愈 Proxy
function makeHealer(target, name, depth = 2) {
  if (depth <= 0) return target;
  return new Proxy(target, {
    get(obj, prop) {
      if (!(prop in obj)) {
        const guessed = guessDefault(prop);
        obj[prop] = guessed;
        traceLog.push(`[TRACE] ${name}.${String(prop)} → ${JSON.stringify(guessed)} (guessed)`);
      }
      const val = obj[prop];
      return (typeof val === 'object' && val !== null)
        ? makeHealer(val, `${name}.${String(prop)}`, depth - 1)
        : val;
    }
  });
}

// guessDefault 核心规则
function guessDefault(prop) {
  const name = String(prop);
  if (/hardwareConcurrency$/i.test(name)) return 8;
  if (/deviceMemory$/i.test(name)) return 8;
  if (/onLine$/i.test(name)) return false;
  if (/webdriver$/i.test(name)) return false;
  if (/^(get|set|create|fetch|query|load|init|open|close|start|stop|send|read|write)/i.test(name)) return () => {};
  if (/^[A-Z]/.test(name)) return function() {};
  return undefined;
}
```

```python
# persistent_signer.py 核心：管理签名服务器生命周期
import subprocess, requests, time

class SignerManager:
    def __init__(self, sign_js_path):
        self.proc = subprocess.Popen(
            ['node', sign_js_path, '--server'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        time.sleep(3)  # 等待 SDK 初始化完成

    def sign(self, url):
        resp = requests.post('http://127.0.0.1:9876/sign', json={'url': url})
        return resp.json()

    def shutdown(self):
        self.proc.terminate()
```

```python
# TLS 指纹绕过：使用 curl_cffi
from curl_cffi import requests as cffi_requests

resp = cffi_requests.get(
    signed_url,
    headers=headers,
    impersonate="chrome120"  # 模拟 Chrome 120 的 TLS 指纹
)
```

## 注意事项

- **先追踪再补全**：凭记忆写 stub 是最大时间陷阱。SDK 实际探测包含 `navigator.connection.effectiveType`、`document.characterSet`、`screen.colorDepth` 等冷门属性，错过任何一个导致签名静默失败
- **URL 参数顺序不可变**：`URLSearchParams.toString()` 按字母序重排参数会破坏签名哈希，务必保持原始 URL 的参数顺序
- **TLS 指纹必须先排查**：签名"看起来正确"但服务端返回 200 空 body 时，第一个排查点是 TLS 指纹而非签名本身
- **必须显式退出进程**：SDK 内部定时器维持事件循环，签名完成后需 `process.exit(0)`
- **假 XHR 响应 JSON 必须完整**：缺少 `data.d` 等字段会导致 SDK 在无异常的情况下静默跳过关键初始化步骤
- **锁定随机性只在调试阶段使用**：生产环境锁定 `Math.random = () => 0.5` 可能导致服务端校验失败

## 相关链接

- [原文：看雪论坛 — JSVMP 类型 a_bogus 本地化复现实践](https://bbs.kanxue.com/thread-291194.htm)
- 项目内：
  - [JSVMP 概述与保护全景](../crawler/2026-06-11-jsvmp-overview-protection-landscape.md) (`KB-CR-20260611-jsvmp-overview-protection-landscape`) — JSVMP 理论基础
  - [JSVMP 虚拟化流水线](../crawler/2026-06-11-jsvmp-virtualization-pipeline.md) (`KB-CR-20260611-jsvmp-virtualization-pipeline`) — AST→字节码编码
  - [JSVMP 虚拟解释器设计](../crawler/2026-06-11-jsvmp-interpreter-design.md) (`KB-CR-20260611-jsvmp-interpreter-design`) — WASM 解释器架构
  - [补环境框架：document.all C++ Addon](../crawler/2026-06-11-sdenv-node-addon-document-all.md) (`KB-CR-20260611-sdenv-node-addon-document-all`) — 补环境对抗的另一路径
  - [AST 还原 JSVMP X-Bogus/_signature 全流程](../crawler/2026-06-11-ast-restore-jsvmp-x-bogus-signature.md) (`KB-CR-20260611-ast-restore-jsvmp-x-bogus-signature`) — **静态还原路径**：与本篇补环境路径互补
  - [AI 白盒还原腾讯 CHAOS VM 验证码](../crawler/2026-06-11-ai-tencent-chaos-vm-captcha-reverse.md) (`KB-CR-20260611-ai-restore-tencent-chaos-vm-captcha`) — 另一篇 AI 辅助 VMP 逆向实战

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-13 | 初稿（ING-20260713-001）：看雪论坛 a_bogus 补环境 + AI 加速全流程 |
