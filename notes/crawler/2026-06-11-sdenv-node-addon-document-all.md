---
id: KB-CR-20260611-sdenv-node-addon-document-all
module: crawler
module_id: MOD-CR
title: "补环境框架：document.all 的 C++ Node Addon 方案"
source:
  type: url
  url: "https://blog.howduudu.tech/article/00bb5f4a997c39858e25fa962e8cd5b8/"
  accessed: "2026-06-11"
tags: [js-reverse, anti-crawler, sdenv, node-addon, v8, node-gyp, browser-emulation]
difficulty: advanced
status: active
related: [KB-CR-20260611-rs-vmp-dynamic-code-generation, KB-CR-20260611-jsvmp-overview-protection-landscape, KB-CR-20260611-jsvmp-virtualization-pipeline, KB-CR-20260611-jsvmp-interpreter-design, KB-CR-20260713-a-bogus-env-spoofing-ai-accelerated]
ingest_id: ING-20260611-002
updated: "2026-06-11"
---

# 补环境框架：document.all 的 C++ Node Addon 方案

## TL;DR

- `document.all` 是补环境框架中**纯 JS 无法模拟**的浏览器 API，必须借助底层能力
- 不修改 Node 源码，通过 **Node Addon（C++ 插件）** 方案，利用 V8 API 构造 undetectable + callable 对象
- 关键三步：`MarkAsUndetectable()` 让 `typeof` 返回 `undefined`、`SetCallAsFunctionHandler` 让对象可调用、属性拷贝提供类数组行为
- sdenv 项目已开源完整实现：https://github.com/pysunday/sdenv
- 编译需 node-gyp + C++ 编译环境（macOS Xcode / Windows VS），打包产出 `documentAll.node` 二进制文件

## 适用场景

**何时用：**

- 补环境/浏览器模拟时遇到 `document.all` 检测导致反爬触发
- 需要使用 `typeof document.all === 'undefined' && document.all()` 的网站
- 构建 Node.js 端浏览器环境模拟框架（如 sdenv）
- 需要深入 V8 底层绕过纯 JS 限制

**何时不用：**

- 简单 API 签名/参数伪造——不需要补 Document 级别 API
- 已有其他补环境框架且无 `document.all` 检测
- 纯 Python 爬虫场景（本文针对 Node.js 端补环境）

## 知识要点

### 1. 为什么 document.all 纯 JS 无法模拟

`document.all` 是一个极其特殊的浏览器遗留 API（MDN 已不推荐使用但依然存在），有三个无法在 Node 中复现的特性：

| 特性 | 表现 | 纯 JS 困境 |
|------|------|-----------|
| typeof 返回 `"undefined"` | `typeof document.all === "undefined"` 为 true，同时 `document.all == undefined` 也为 true | JS 引擎不可自定义 `typeof` 运算符行为 |
| 原型为 HTMLAllCollection | 具备类数组能力 | Node 无此 DOM 构造器 |
| 可作为函数调用 | `document.all('id')` 返回元素 | JS 普通对象不可被调用 |

这三个特性的叠加，使得 GitHub 上大部分补环境项目要么绕道、要么修改 Node 源码重新编译——而后者在安全上不放心。

### 2. V8 API 方案：MarkAsUndetectable + SetCallAsFunctionHandler

sdenv 的核心思路：不修改 Node 源码，而是利用 Node 官方插件机制（Addon），直接操作 V8 引擎层 API。

**需求二（typeof → undefined）的实现路径：**

追踪 V8 源码 TypeOf 实现（`objects.cc`），发现当 `IsUndetectable(*object)` 为真时，V8 直接返回 `undefined_string`。这意味着只要在 C++ 层把对象标记为 undetectable，JS 侧的 `typeof` 就会返回 `"undefined"`。

V8 API 提供了两个关键方法：

- `v8::ObjectTemplate::MarkAsUndetectable()` — 将对象标记为不可检测，"此时该对象类似 undefined，但可以像普通对象一样访问和调用属性"
- `v8::Object::IsUndetectable()` — 判断对象是否被标记

**需求三（可调用）的实现路径：**

- `v8::ObjectTemplate::SetCallAsFunctionHandler(callback)` — 设置回调函数，使对象实例可像函数一样被调用

### 3. C++ 插件完整实现

```cpp
#include <node.h>
namespace documentAll {

using v8::Context;
using v8::Function;
using v8::FunctionCallbackInfo;
using v8::FunctionTemplate;
using v8::Isolate;
using v8::Local;
using v8::Number;
using v8::Object;
using v8::ObjectTemplate;
using v8::String;
using v8::Value;
using v8::Null;
using v8::Array;

// 当对象被当作函数调用时触发，返回 null
void MyFunctionCallback(const FunctionCallbackInfo<Value>& args) {
  Isolate* isolate = args.GetIsolate();
  args.GetReturnValue().Set(Null(isolate));
}

// 创建 undetectable + callable 对象，并拷贝入参属性
void GetDocumentAll(const FunctionCallbackInfo<Value>& args) {
  Isolate* isolate = args.GetIsolate();
  Local<Context> context = isolate->GetCurrentContext();

  // 1. 创建 ObjectTemplate
  Local<ObjectTemplate> obj_template = ObjectTemplate::New(isolate);

  // 2. 标记 undetectable → typeof 返回 "undefined"
  obj_template->MarkAsUndetectable();

  // 3. 设置可调用回调 → document.all() 返回 null
  obj_template->SetCallAsFunctionHandler(MyFunctionCallback);

  // 4. 实例化
  Local<Object> obj = obj_template->NewInstance(context).ToLocalChecked();

  // 5. 拷贝入参对象属性（如 length）到新建对象
  if (args.Length() > 0 && args[0]->IsObject()) {
    Local<Object> argObj = args[0]->ToObject(context).ToLocalChecked();
    Local<Array> propertyNames = argObj->GetPropertyNames(context).ToLocalChecked();
    for (uint32_t i = 0; i < propertyNames->Length(); ++i) {
      Local<Value> key = propertyNames->Get(context, i).ToLocalChecked();
      Local<Value> value = argObj->Get(context, key).ToLocalChecked();
      (void)obj->Set(context, key, value);
    }
  }

  args.GetReturnValue().Set(obj);
}

// 导出 getDocumentAll 方法
void Init(Local<Object> exports, Local<Object> module) {
  Isolate* isolate = exports->GetIsolate();
  Local<Context> context = isolate->GetCurrentContext();
  Local<FunctionTemplate> method_template = FunctionTemplate::New(isolate, GetDocumentAll);
  exports->Set(context,
    String::NewFromUtf8(isolate, "getDocumentAll").ToLocalChecked(),
    method_template->GetFunction(context).ToLocalChecked()
  ).FromJust();
}

NODE_MODULE(NODE_GYP_MODULE_NAME, Init)
}
```

**代码结构**：三个方法构成完整链路——`MyFunctionCallback`（调用回调）→ `GetDocumentAll`（构造特殊对象）→ `Init`（注册导出）。

### 4. node-gyp 编译与打包

源码编写完成后必须用 node-gyp 编译为二进制 `addon.node` 文件。需要 `binding.gyp` 配置文件（JSON-like 格式）。

**环境依赖：**

| 环境 | 要求 |
|------|------|
| macOS | Xcode（提供 C++ 编译器） |
| Windows | Visual Studio + 勾选「使用C++的桌面开发」 |
| 通用 | Python（node-gyp 依赖） |

环境装好后：

```bash
npm i                          # 安装依赖（新版无需额外 build）
npm run build                  # mac/linux
npm run build:win              # windows
# 产出 bin/documentAll.node
```

**注意**：`documentAll.node` 是平台绑定的二进制文件，换电脑后必须重新打包。

### 5. 功能测试验证

测试用例验证了 `document.all` 四个关键行为：

```javascript
const getDocumentAll = require('../bin/documentAll.node').getDocumentAll;

describe('模拟document.all检测', () => {
  const da = getDocumentAll({ length: 1 });

  test('属性拷贝：length === 1', () => {
    expect(da.length).toBe(1);
  });

  test('弱等于 undefined', () => {
    expect(da == undefined).toBe(true);
  });

  test('typeof 为 undefined', () => {
    expect(typeof da).toBe('undefined');
  });

  test('可调用：返回 null', () => {
    expect(da()).toBe(null);
  });
});
```

运行：`node node_modules/.bin/jest ./test/documentAll.test.js`

### 6. 补环境框架中纯 JS vs V8 插件的技术选择边界

| 场景 | 方案 |
|------|------|
| 大部分 BOM/DOM API（navigator, window, localStorage 等） | 纯 JS 模拟 |
| `document.all` | **必须** C++ Addon（V8 底层 API） |
| 修改 Node 源码重新打包 | 不推荐（只敢在虚拟机跑） |

**选型原则**：能用纯 JS 不用插件，插件仅用于纯 JS 无法突破的 V8 层限制。

## 代码 / 命令

```bash
# 编译 document.all 插件
npm i
npm run build                      # mac/linux
npm run build:win                  # windows
# 产物：bin/documentAll.node

# 测试
node node_modules/.bin/jest ./test/documentAll.test.js
```

sdenv 项目：https://github.com/pysunday/sdenv

## 注意事项

- `documentAll.node` **平台绑定**：macOS 编译的文件不能直接在 Windows/Linux 上使用，换电脑需重新打包
- node-gyp 依赖 **Python** + **C++ 编译器**，缺一 `npm i` 会报错
- Windows 上安装 Visual Studio 时**必须勾选「使用C++的桌面开发」**，否则编译失败
- `document.all` 虽然能过检测，但补环境框架还需配合其他环境变量模拟（cookie、navigator 等）才能完整过反爬

## 相关链接

- [原文 (一)：补环境框架：document.all的c++方案(一)](https://blog.howduudu.tech/article/00bb5f4a997c39858e25fa962e8cd5b8/)
- [原文 (二)：补环境框架：document.all的c++方案(二)](https://blog.howduudu.tech/article/de942bdea377f7f3ce6878fc04a8c76c/)
- [sdenv 项目仓库](https://github.com/pysunday/sdenv)
- [插件源码 documentAll.cc](https://github.com/pysunday/sdenv/blob/main/bin/documentAll.cc)
- [MDN: Document.all](https://developer.mozilla.org/en-US/docs/Web/API/Document/all)
- [Node Addon 官方文档](https://nodejs.org/api/addons.html)
- [V8 ObjectTemplate API](https://v8.github.io/api/head/classv8_1_1ObjectTemplate.html)
- 项目内：[瑞数vmp动态代码生成原理逆向分析](./2026-06-11-rs-vmp-dynamic-code-generation.md) (`KB-CR-20260611-rs-vmp-dynamic-code-generation`)

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-11 | 初稿（ING-20260611-002）— 合并两篇为单篇笔记 |
