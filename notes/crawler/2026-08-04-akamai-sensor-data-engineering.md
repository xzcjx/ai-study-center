---
id: "KB-CR-20260804-akamai-sensor-data-engineering"
module: crawler
module_id: MOD-CR
title: "Akamai sensor_data 全参数拆解与工程实现"
source:
  type: url
  url: "https://mp.weixin.qq.com/s/Sy5GLlnNpR4LQljfhfljGg"
  accessed: "2026-08-04"
  author: "王平"
  account: "猿人学Python"
  reliability: requests-fetched
tags: [akamai, sensor-data, anti-crawler, device-fingerprint, js-reverse, ast, browser-emulation, hook, mouse-fingerprint, jsvmp, ai-assisted, real-case]
difficulty: advanced
status: active
related: [KB-CR-20260713-jsvmp-reverse-master-guide, KB-CR-20260713-amap-alibaba-security-reverse, KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated]
ingest_id: "ING-20260804-001"
updated: "2026-08-04"
---

# Akamai sensor_data 全参数拆解与工程实现

## TL;DR

- Akamai `sensor_data` 不是单次计算，而是“页面 HTML → 动态 JS → 连续三次 POST”的状态化生成流程；同一份 JS 的字段顺序和格式需要以当前样本为准。
- 还原重点应放在 `din`、`ajr`、`dvc`、`ver`、`previousValue` 等中间对象，而不是一开始就试图复刻最终加密字符串。
- 面对动态属性访问和混淆代码，可以采用“记录运行时属性 → AST 替换明文属性 → 再次执行验证”的迭代解混淆流程。
- 参数主要来自浏览器环境、鼠标轨迹、语音合成能力、GPU/Worker、时间戳和随机数；补环境应围绕实际消费点按需补齐。
- 工程化路线可概括为：AST 锁点 + 条件去干扰 + VM 补环境执行 + Hook 截取结果，并用多份 JS 样本验证规则的稳定性。

## 适用场景

**何时用：**

- 对自有或已获授权的站点进行反爬兼容性测试、协议互操作和安全研究。
- 需要分析 Akamai 类浏览器指纹参数的来源、字段变化和多阶段请求状态。
- 需要在动态混淆 JS 中定位关键对象，并将浏览器端生成逻辑迁移到可测试的工程环境。

**何时不用：**

- 已有合法 SDK、服务端接口或测试环境可以直接完成业务调用时，不应为了复刻前端保护而逆向。
- 目标不是 Akamai 或类似浏览器指纹链路时，不要直接套用字段名、顺序和固定值。
- 未取得目标方授权时，不应使用这些方法绕过访问控制、验证码或风控策略。

## 知识要点

### 1. 先还原整体请求状态机

文章将流程拆成三个阶段：从页面 HTML 提取 Akamai JS 地址，加载并执行 JS，随后连续发送三次 `sensor_data`。第一次请求建立初始状态，第二、三次请求会继续携带鼠标轨迹、时间差和更多浏览器指纹字段。

因此工程实现不应只写一个“输入 UA、输出字符串”的纯函数，而应保存 `startTs`、请求序号、鼠标轨迹、时间差、随机值和前序结果等状态。每次获取新的 HTML/JS 后，还要重新确认字段顺序和参数格式。

### 2. 用运行时记录破解动态属性访问

典型混淆代码会把明文属性隐藏在动态表达式中，例如 `a[x()[b(c)]]`。可以先将表达式改写为带记录的赋值形式：运行时记录实际计算出的 key，再导出“表达式 → 明文属性”的映射。

随后用 AST 将动态访问替换成字符串属性访问，例如把 `a[x()[b(c)]]` 替换为 `a["charCodeAt"]`。重新执行、补充映射、再次替换，逐轮扩大可读代码范围。未被替换的位置通常表示当前执行路径没有覆盖到，不能直接判定为无效代码。

### 3. 重点追踪 `13b`、`din` 与 `ajr`

定位 `sensor_data` 生成链时，可以从 XHR 断点和调用栈向上追踪到关键对象。文章建议重点分析中间对象，而非直接分析最终加密结果：

- `ajr`：由启动时间、设备数据、鼠标数据、速度和时间差等组合生成，格式可能随当天 JS 版本变化。
- `din`：包含屏幕尺寸、UA、语言、窗口尺寸、时间戳、随机数等字段，字段顺序本身是输入的一部分。
- `dvc`：前半部分通常来自 VMP，后缀与环境检测/条件分支相关，需要分别定位。
- `ver` 与 `previousValue`：参与后续 `sensor_data` 加解密或状态衔接，应从消费点反向追踪声明位置。

### 4. 参数来源应按类别建立采集表

将字段按来源分类，比逐个记忆字段名更容易迁移到新样本：

| 类别 | 典型来源 | 工程关注点 |
|---|---|---|
| 页面与时间 | `startTs`、当前时间、页面 URL、JS 地址 | 同一 JS 生命周期内保持一致 |
| 浏览器环境 | `screen`、`navigator`、`window`、语言、UA | 只补实际消费到的属性 |
| 鼠标行为 | `MouseEvent`、轨迹点、速度、轨迹时间 | 第一次请求可为空，后续请求需更新 |
| 能力指纹 | `speechSynthesis.getVoices()`、权限 API、GPU/Worker | 结果通常与运行环境强相关 |
| 随机与状态 | `Math.random()`、请求序号、前序结果 | 不要误当成固定常量 |

例如 `fpt/fpc` 可由一组浏览器能力与屏幕属性拼接后计算；`din` 中的尺寸、UA、语言、窗口大小则应按原始字段顺序写入。对于 `nfas` 一类能力指纹，应记录 API 是否存在，而不是贸然调用不存在的 API。

### 5. 用结构特征定位条件去干扰点

动态 JS 中常见一类环境检测位于 `try / if / else / catch` 结构内。经过多份样本对比后，可使用 AST 按结构约束筛选候选，再观察该候选是否在多个位置重复出现，并验证它是否控制 `dvc` 后缀等关键结果。

在授权测试环境中，可以将确认过的检测条件替换为等长的恒真表达式，以减少格式化检测干扰；但替换前必须保留原始 JS、记录命中位置，并在另一份样本上验证规则，避免把业务逻辑误当成环境检测。

### 6. 三次请求的差异是调试线索

对三次请求 JSON 做字段级 diff，可以快速划分固定字段、随机字段和状态字段：

- `ajr` 会变化，但生成结构不一定变化，常见变化来源是速度或时间差。
- `ran` 属于随机值，应在每次请求重新生成。
- `din` 字段顺序通常保持不变，不能随意用无序对象重排。
- 第二次和第三次会出现不同的 `ajt`、鼠标轨迹和更多指纹信息。
- 第三次可能增加 `dsi`、`sww` 等 iframe、Worker、GPU 和内存相关数据。

这种差异表比单次样本更能帮助判断某个字段是固定配置、环境值还是请求状态。

### 7. AI 与 AST 的协作边界

AI 适合根据少量样本生成 AST 匹配器、属性替换器和日志注入器，也适合解释陌生 Web API。但生成代码必须配套验证：用一份样本生成规则，用另一份不同混淆结果验证命中率，并检查替换前后语法树和运行结果。

最终目标是找到最可能产生 `din` 的调用点，在最小补环境中直接 Hook 截取中间结果。无需一开始完整实现整个浏览器原型链，也不应把未经验证的固定值写成通用算法。

## 代码 / 命令

### 纯 requests 获取公众号正文

```python
import requests
from bs4 import BeautifulSoup

url = "https://mp.weixin.qq.com/s/Sy5GLlnNpR4LQljfhfljGg"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.50"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://mp.weixin.qq.com/",
}

response = requests.get(
    url,
    params={"scene": "25"},
    headers=headers,
    timeout=20,
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
title = soup.select_one("#activity-name").get_text(" ", strip=True)
content = soup.select_one("#js_content").get_text("\n", strip=True)
print(title)
print(content)
```

### 记录动态属性映射的伪代码

```javascript
const resolved = {};
const key = x()[b(c)];
resolved["x()[b(c)]"] = key;
const value = a[key];
```

先在授权调试环境记录 `resolved`，再通过 AST 把原始动态访问替换为 `a["实际属性名"]`，并对替换结果做语法和行为验证。

## 注意事项

- 本文涉及浏览器指纹、反爬参数和环境检测，仅适用于自有或明确授权的安全研究、兼容性测试与协议互操作。
- Akamai 下发的 HTML 和 JS 会变化；`ajr` 格式、`din` 顺序、固定值和环境字段都必须以当前样本验证，不能照抄旧样本。
- `Math.random()`、时间戳、鼠标轨迹和前序响应属于动态状态，不能简单硬编码。
- 任何请求样本、Cookie、Key、IV、设备标识和个人信息都不得进入知识库或日志。
- 只替换已确认的环境检测条件；替换业务条件可能破坏流程并造成错误结论。

## 相关链接

- [原文：Akamai sensor_data 全参数拆解与工程实现](https://mp.weixin.qq.com/s/Sy5GLlnNpR4LQljfhfljGg)
- 项目内：[JSVMP 逆向方法论总纲](2026-07-13-jsvmp-reverse-master-guide.md)（`KB-CR-20260713-jsvmp-reverse-master-guide`）
- 项目内：[某德地图阿里系安全防护逆向实战](2026-07-13-amap-alibaba-security-reverse.md)（`KB-CR-20260713-amap-alibaba-security-reverse`）
- 项目内：[a_bogus 补环境与 AI 加速实践](2026-07-13-a-bogus-env-spoofing-ai-accelerated.md)（`KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated`）

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-08-04 | 初稿（ING-20260804-001） |
