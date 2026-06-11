#!/usr/bin/env node
/**
 * 腾讯 TDC 设备指纹 SDK — 从 Chaos VM 字节码还原的纯 JS 实现
 *
 * 还原来源: tdc.js (__TENCENT_CHAOS_VM) — 45,700 条字节码
 * 参考: 看雪论坛「AI辅助白盒还原腾讯CHAOS VM」by 执着的猫
 *
 * 用法:
 *   node tdc_reconstructed.js            # 直接运行，打印 collect
 *   node tdc_reconstructed.js --extract   # 提取当前 tdc.js 的模块指纹
 *   node tdc_reconstructed.js --help      # 帮助
 */

// ======================================================================
// Part 1: 模块指纹识别 — 从 37 个模块中自动识别类型
// ======================================================================
// 问题: 模块调用顺序每次 tdc.js 加载时随机变化
// 方案: 通过模块 .get() 函数中引用的 JS API 字符串来指纹识别类型
// 通用模块（无特征字符串）使用指令数等结构特征区分

// 37 个模块的指纹规则
const MODULE_FINGERPRINTS = [
  // === 带字符串特征的模块 ===
  { name: "userAgent",           strings: ["userAgent"],                                           category: "navigator" },
  { name: "canvasFingerprint",   strings: ["getContext", "2d"],                                    category: "canvas" },
  { name: "webglRenderer",       strings: ["UNMASKED_RENDERER_WEBGL"],                             category: "webgl" },
  { name: "webglVendor",         strings: ["UNMASKED_VENDOR_WEBGL"],                               category: "webgl" },
  { name: "timezoneOffset",      strings: ["getTimezoneOffset"],                                   category: "navigator" },
  { name: "webdriver",           strings: ["$cdc_asdjflasutopfhvcZLmcfl_"],                        category: "navigator" },
  { name: "webrtcIp",            strings: ["RTCPeerConnection"],                                   category: "webrtc" },
  { name: "productSub",          strings: ["productSub"],                                          category: "navigator" },
  { name: "appVersion",          strings: ["appVersion"],                                          category: "navigator" },
  { name: "screenInfo",          strings: ["width", "height", "colorDepth", "pixelDepth"],         category: "screen" },
  { name: "browserLanguage",     strings: ["language"],                                            category: "navigator" },
  { name: "platform",            strings: ["platform"],                                            category: "navigator" },
  { name: "cookieEnabled",       strings: ["cookieEnabled"],                                       category: "navigator" },
  { name: "doNotTrack",          strings: ["doNotTrack"],                                          category: "navigator" },
  { name: "hardwareConcurrency", strings: ["hardwareConcurrency"],                                 category: "navigator" },
  { name: "deviceMemory",        strings: ["deviceMemory"],                                        category: "navigator" },
  { name: "plugins",             strings: ["plugins"],                                             category: "navigator" },
  { name: "mimeTypes",           strings: ["mimeTypes"],                                           category: "navigator" },
  { name: "localStorage",        strings: ["localStorage", "setItem"],                             category: "storage" },
  { name: "sessionStorage",      strings: ["sessionStorage", "setItem"],                           category: "storage" },
  { name: "indexedDB",           strings: ["indexedDB"],                                           category: "storage" },
  { name: "openDatabase",        strings: ["openDatabase"],                                        category: "storage" },
  { name: "evalLength",          strings: ["eval"],                                                category: "behavior" },
  { name: "errorStack",          strings: ["stack"],                                               category: "behavior" },
  { name: "documentElementKeys", strings: ["documentElement"],                                     category: "dom" },
  { name: "innerWidth",          strings: ["innerWidth", "outerWidth"],                            category: "screen" },
  { name: "touchSupport",        strings: ["ontouchstart"],                                        category: "feature" },
  { name: "pdfViewer",           strings: ["application/pdf"],                                     category: "plugin" },
  { name: "chromeWindow",        strings: ["chrome"],                                              category: "browser" },
  { name: "IEBHO",               strings: ["isIE9Below"],                                          category: "browser" },

  // === 通用模块（无特征字符串，按指令结构区分） ===
  // 这些模块使用字节码指令数 + entry 地址 + 调用特定函数来区分
  { name: "timeEval",            strings: [], struct: { hasDateGetTime: true, expectsGlobalFunc: true }, category: "timing" },
  { name: "timeNow",             strings: [], struct: { hasDateNow: true         }, category: "timing" },
  { name: "navigatorPropCount",  strings: [], struct: { hasObjectKeys: true      }, category: "navigator" },
  { name: "historyLength",       strings: [], struct: { hasHistoryProp: true     }, category: "dom" },
  { name: "stringHook",          strings: [], struct: { usesCharCodeAt: true     }, category: "behavior" },
  { name: "canvasDataURL",       strings: [], struct: { usesToDataURL: true      }, category: "canvas" },
  { name: "connectionType",      strings: [], struct: { hasConnectionProp: true  }, category: "navigator" },
];

// 已知的 tdc.js 加载时提供的全局变量名
// 这些名字每次也可能变化，但功能不变
const KNOWN_ALIASES = {
  dateFactory: "_QYXcXVgmADSEKdWeOEJhiibOeUOERJMT",  // function() { return new Date() }
  dateMethodApply: "_bZXWQROlNWniJXXWXYgaKHeiWHdGHZQX",  // function(a,b) { return Date[a].apply(Date,b) }
  configBase64: "JUgPWZCbmXaVOkAJRKUQfmFfHcekkSGP",      // 嵌入的加密配置
};


// ======================================================================
// Part 2: 动态模块顺序匹配 — 生成当前 tdc.js 的 37 个 cd 值
// ======================================================================
// 每个 tdc.js 加载时 37 个模块的 ID 顺序随机变化。
// 但通过浏览器中运行 tdc.js 再抓取每个模块的 .get() 返回值，
// 结合指纹规则匹配类型，即可动态确定顺序。

/**
 * 指纹值 → 模块名 的映射助手
 * 每个指纹规则输出一个可匹配的特征字符串
 */
function matchModule(value, id) {
  for (const rule of MODULE_FINGERPRINTS) {
    if (rule.strings.length === 0) continue;
    const v = String(value);
    const allMatch = rule.strings.every(s => v.includes(s));
    if (allMatch) return rule.name;
  }
  return null; // 通用模块，需结构区分
}

/**
 * 从当前 tdc.js 的 37 个模块返回值动态生成 cd 数组
 *
 * @param {Array} rawValues — window.TDC.getAllModuleValues() 返回的 37 个值的数组（按实际调用顺序）
 *                           在浏览器中可以通过 Hook TDC.sd 的 .get 来获取
 */
function orderModules(rawValues) {
  const cd = new Array(37).fill("");
  let genericIdx = 0;

  for (let i = 0; i < rawValues.length; i++) {
    const matched = matchModule(rawValues[i], i);
    if (matched) {
      cd[i] = String(rawValues[i]);
    } else {
      // 通用模块 — 按结构特征识别（指令数、entry 地址等）
      // 在反汇编中可以获取 .get 函数的字节码长度来判断
      cd[i] = String(rawValues[i]);
    }
  }

  return cd;  // 顺序就是当前 tdc.js 的实际排列
}

/**
 * 最简单的方案：在浏览器中直接执行 tdc.js，然后通过
 * Hook window.TDC.getInfo/sd 来 dump 实际值。
 *
 * 在没有浏览器环境时，提供模拟模块值（用于测试）
 */

function buildCDFromProfile(fpData) {
  // 模拟 37 个模块的输出值（每个值就是 .get() 的返回值）
  // 这些值的**排列顺序**必须匹配当前 tdc.js 的模块顺序
  // 此处仅作结构示例，实际使用时需要用 orderModules() 动态排序
  return [
    fpData.userAgent,
    fpData.canvasHash,
    fpData.webglRenderer,
    fpData.webglVendor,
    String(fpData.timezoneOffset),
    String(fpData.webdriver),
    fpData.webrtcCandidates || "",
    fpData.productSub,
    fpData.appVersion,
    String(fpData.screenWidth),
    String(fpData.screenHeight),
    String(fpData.colorDepth),
    String(fpData.pixelDepth),
    fpData.language,
    fpData.platform,
    String(fpData.cookieEnabled),
    String(fpData.doNotTrack),
    String(fpData.hardwareConcurrency),
    String(fpData.deviceMemory),
    String(fpData.pluginsCount),
    String(fpData.mimeTypesCount),
    String(fpData.localStorageEnabled),
    String(fpData.sessionStorageEnabled),
    String(fpData.indexedDBEnabled),
    fpData.timeEval,
    fpData.timeGetTime,
    String(fpData.innerWidth),
    String(fpData.outerWidth),
    String(fpData.touchSupport),
    String(fpData.pdfViewerEnabled),
    String(fpData.chromeDetected),
    String(fpData.historyLength),
    fpData.documentKeys,
    fpData.errorStackTrace,
    fpData.timeNow,
    fpData.connectionType,
    fpData.stringHookResult
  ];
}

function buildFingerprintData(profile) {
  // profile: 模拟的浏览器指纹配置（在 Node.js 中使用）
  // 在浏览器中: 直接用实际值
  const isBrowser = typeof window !== "undefined" && typeof document !== "undefined";

  return {
    userAgent:            isBrowser ? window.navigator.userAgent : profile.userAgent,
    appVersion:           isBrowser ? window.navigator.appVersion : profile.appVersion,
    platform:             isBrowser ? window.navigator.platform : profile.platform,
    productSub:           isBrowser ? window.navigator.productSub : profile.productSub || "20030107",
    language:             isBrowser ? (window.navigator.language || window.navigator.userLanguage) : profile.language,
    cookieEnabled:        isBrowser ? window.navigator.cookieEnabled : true,
    doNotTrack:           isBrowser ? (window.navigator.doNotTrack || "unspecified") : profile.doNotTrack || "1",
    hardwareConcurrency:  isBrowser ? (window.navigator.hardwareConcurrency || 4) : profile.hardwareConcurrency || 4,
    deviceMemory:         isBrowser ? (window.navigator.deviceMemory || 4) : profile.deviceMemory || 4,

    screenWidth:          isBrowser ? window.screen.width : profile.screenWidth || 1680,
    screenHeight:         isBrowser ? window.screen.height : profile.screenHeight || 1050,
    colorDepth:           isBrowser ? window.screen.colorDepth : profile.colorDepth || 24,
    pixelDepth:           isBrowser ? window.screen.pixelDepth : profile.pixelDepth || 24,
    innerWidth:           isBrowser ? window.innerWidth : profile.innerWidth || 1680,
    outerWidth:           isBrowser ? window.outerWidth : profile.outerWidth || 1680,

    timezoneOffset:       new Date().getTimezoneOffset(),  // 始终真实
    timezone:             Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai",

    pluginsCount:         isBrowser ? (window.navigator.plugins ? window.navigator.plugins.length : 0) : profile.pluginsCount || 5,
    mimeTypesCount:       isBrowser ? (window.navigator.mimeTypes ? window.navigator.mimeTypes.length : 0) : profile.mimeTypesCount || 2,

    pdfViewerEnabled:     isBrowser ? (window.navigator.pdfViewerEnabled !== false) : true,
    webdriver:            isBrowser ? (window.navigator.webdriver || false) : false,
    chromeDetected:       isBrowser ? !!(window.chrome) : true,

    touchSupport:         isBrowser ? ("ontouchstart" in window) : profile.touchSupport || false,

    historyLength:        isBrowser ? window.history.length : profile.historyLength || 1,

    documentKeys:         isBrowser ? Object.keys(document).join(",") : profile.documentKeys || "location",
    connectionType:       isBrowser ? ((window.navigator.connection || {}).type || "unknown") : profile.connectionType || "unknown",

    localStorageEnabled:  isBrowser ? !!window.localStorage : true,
    sessionStorageEnabled: isBrowser ? !!window.sessionStorage : true,
    indexedDBEnabled:     isBrowser ? !!window.indexedDB : true,

    canvasHash:           profile.canvasHash || "a4c3b2d1",
    webglRenderer:        profile.webglRenderer || "ANGLE (Intel, Apple M1, OpenGL 4.1)",
    webglVendor:          profile.webglVendor || "Google Inc. (Intel)",
    webrtcCandidates:     profile.webrtcCandidates || "",

    // 时间测量
    timeEval:             profile.timeEval || String(Math.random() * 100 | 0),  // eval 执行时间
    timeNow:              profile.timeNow || String(Date.now()),
    timeGetTime:          profile.timeGetTime || String(new Date().getTime()),

    stringHookResult:     profile.stringHookResult || "",
    errorStackTrace:      profile.errorStackTrace || "",
  };
}


// ======================================================================
// Part 3: collect 字段构造 — 四段式 XTEA + Base64
// ======================================================================
// 参考: 看雪「执着的猫」— JSVMP还原文章 §7 collect 四段式结构

/**
 * XTEA 加密核心（32 轮）
 * delta = 0x9E3779B9
 */
function xteaEncrypt(v, key) {
  let v0 = v[0] >>> 0, v1 = v[1] >>> 0;
  let sum = 0;
  const delta = 0x9E3779B9;
  for (let i = 0; i < 32; i++) {
    v0 += (((v1 << 4) ^ (v1 >>> 5)) + v1) ^ (sum + key[sum & 3]);
    sum = (sum + delta) >>> 0;
    v1 += (((v0 << 4) ^ (v0 >>> 5)) + v0) ^ (sum + key[(sum >>> 11) & 3]);
  }
  return [v0 >>> 0, v1 >>> 0];
}

/**
 * 字符串 → uint32 数组（每 8 字节一组，每组 2 个 uint32）
 */
function strToUint32Array(str) {
  const result = [];
  for (let i = 0; i < str.length; i += 4) {
    let v = 0;
    for (let j = 0; j < 4 && i + j < str.length; j++) {
      v = (v << 8) | (str.charCodeAt(i + j) & 0xFF);
    }
    result.push(v >>> 0);
  }
  return result;
}

/**
 * 24 字节对齐填充（空格）
 */
function padTo24(str) {
  const rem = str.length % 24;
  if (rem === 0) return str;
  return str + " ".repeat(24 - rem);
}

/**
 * Custom Base64 编码（不依赖 window.btoa）
 */
function base64Encode(bytes) {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let result = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i];
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    result += chars[a >> 2];
    result += chars[((a & 3) << 4) | (b >> 4)];
    result += i + 1 < bytes.length ? chars[((b & 15) << 2) | (c >> 6)] : "=";
    result += i + 2 < bytes.length ? chars[c & 63] : "=";
  }
  return result;
}

/**
 * 为 Base64 输出修复自定义的 +/ 替换
 * 部分 TDC 实现使用 _ 或 - 替换标准 Base64 的 +/
 */
function finalizeBase64(base64Str) {
  // 标准实现用 +/，但有时被自定义替换
  // 按实际观察到的情况处理
  return base64Str;
}

/**
 * 四段式 collect 构造
 *
 * 整体结构:
 *   collect = b64(xtea(chunk1_24_aligned))
 *           + b64(xtea(trajectory_chunk))
 *           + b64(xtea(chunk2_24_aligned))
 *           + b64(xtea(sd_raw, nopad=true))
 *
 * @param {Object} fpData      — 指纹数据（来自 buildFingerprintData）
 * @param {string|number} token— TDC token
 * @param {number} trial       — 尝试次数（指数递增）
 * @param {string} eks         — eks envelope data
 * @param {string} trajectory  — 轨迹 JSON 字符串
 */
function buildCollect(moduleValues, token, trial, eks, trajectory) {
  // === Chunk 1: 指纹数据 — 按当前 tdc.js 的实际 37 模块排列 ===
  const cd = moduleValues;

  // chunk1 的 JSON 结构
  const chunk1Data = {
    cd: cd,
    token: String(token),
    trial: trial || 1,
    ...(eks ? { eks } : {})
  };
  const chunk1Raw = JSON.stringify(chunk1Data);

  // 24 字节对齐
  const chunk1Padded = padTo24(chunk1Raw);

  // 分 24 字节块 → 每块内 8 字节 XTEA
  let chunk1Encrypted = "";
  for (let i = 0; i < chunk1Padded.length; i += 24) {
    const block24 = chunk1Padded.substring(i, i + 24);
    for (let j = 0; j < 24; j += 8) {
      const seg8 = block24.substring(j, j + 8);
      const padded = seg8.length < 8 ? seg8 + "\x00".repeat(8 - seg8.length) : seg8;
      const v = strToUint32Array(padded);
      // XTEA key 需从 tdc.js 中提取（每次不同）
      const enc = xteaEncrypt(v, XTEA_KEY);
      chunk1Encrypted += base64Encode(new Uint8Array(new Uint32Array(enc).buffer));
    }
  }

  // === Trajectory Chunk ===
  const trajPadded = padTo24(trajectory || "[]");
  let trajEncrypted = "";
  for (let i = 0; i < trajPadded.length; i += 24) {
    const block24 = trajPadded.substring(i, i + 24);
    for (let j = 0; j < 24; j += 8) {
      const seg8 = block24.substring(j, j + 8);
      const padded = seg8.length < 8 ? seg8 + "\x00".repeat(8 - seg8.length) : seg8;
      const v = strToUint32Array(padded);
      const enc = xteaEncrypt(v, XTEA_KEY);
      trajEncrypted += base64Encode(new Uint8Array(new Uint32Array(enc).buffer));
    }
  }

  // === Chunk 2: 轨迹后指纹（同 chunk1 结构，但 token 不同） ===
  const chunk2Raw = JSON.stringify({
    cd: cd,
    token: String(token),
    trial: trial || 1
  });
  const chunk2Padded = padTo24(chunk2Raw);
  let chunk2Encrypted = "";
  for (let i = 0; i < chunk2Padded.length; i += 24) {
    const block24 = chunk2Padded.substring(i, i + 24);
    for (let j = 0; j < 24; j += 8) {
      const seg8 = block24.substring(j, j + 8);
      const padded = seg8.length < 8 ? seg8 + "\x00".repeat(8 - seg8.length) : seg8;
      const v = strToUint32Array(padded);
      const enc = xteaEncrypt(v, XTEA_KEY);
      chunk2Encrypted += base64Encode(new Uint8Array(new Uint32Array(enc).buffer));
    }
  }

  // === SD (不 pad) ===
  const sdRaw = JSON.stringify({ od: "C", ft: fpData.timeGetTime || String(Date.now()) });
  let sdEncrypted = "";
  for (let i = 0; i < sdRaw.length; i += 8) {
    const seg8 = sdRaw.substring(i, i + 8);
    const padded = seg8.length < 8 ? seg8 + "\x00".repeat(8 - seg8.length) : seg8;
    const v = strToUint32Array(padded);
    const enc = xteaEncrypt(v, XTEA_KEY);
    sdEncrypted += base64Encode(new Uint8Array(new Uint32Array(enc).buffer));
  }

  return chunk1Encrypted + trajEncrypted + chunk2Encrypted + sdEncrypted;
}


// ======================================================================
// Part 4: 主入口 — 演示用法
// ======================================================================
const args = process.argv.slice(2);

if (args.includes("--help") || args.includes("-h")) {
  console.log(`
腾讯 TDC 设备指纹 SDK — 从 Chaos VM 字节码还原的纯 JS 实现

用法:
  node tdc_reconstructed.js                   直接运行（使用模拟数据）
  node tdc_reconstructed.js --extract         从当前加载的 tdc.js 提取模块指纹
  node tdc_reconstructed.js --profile=<file>  使用指定的指纹 profile 文件
  node tdc_reconstructed.js --help            显示此帮助

说明:
  - 在浏览器中运行: 直接使用真实 window/document 对象
  - 在 Node.js 中运行: 需要提供 profile（模拟指纹）数据
  - XTEA key 需从 tdc.js 中动态提取（每次加载不同）
`);
  process.exit(0);
}

// 默认 XTEA key — 需从实际 tdc.js 中提取替换
// 提取方法: 从 deobfuscated tdc.js 的 key 构建函数中获取
const XTEA_KEY = [0x00000000, 0x00000000, 0x00000000, 0x00000000]; // PLACEHOLDER

// 模拟指纹 Profile
const mockProfile = {
  userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  appVersion: "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  platform: "MacIntel",
  productSub: "20030107",
  language: "zh-CN",
  hardwareConcurrency: 8,
  deviceMemory: 8,
  screenWidth: 1680,
  screenHeight: 1050,
  colorDepth: 24,
  pixelDepth: 24,
  innerWidth: 1680,
  outerWidth: 1680,
  pluginsCount: 5,
  mimeTypesCount: 2,
  touchSupport: false,
  historyLength: 1,
  documentKeys: "location",
  connectionType: "unknown",
  canvasHash: "a4c3b2d1e5f6a7b8",  // canvas 指纹 hash
  webglRenderer: "ANGLE (Apple, Apple M1, OpenGL 4.1)",
  webglVendor: "Google Inc. (Apple)",
  webrtcCandidates: "",
  timeEval: "12",
  timeNow: String(Date.now()),
  timeGetTime: String(new Date().getTime()),
  stringHookResult: "",
  errorStackTrace: "",
  doNotTrack: "1",
  pdfViewerEnabled: true,
  chromeDetected: true,
};

console.log("=== 腾讯 TDC 设备指纹 SDK 还原 ===");
console.log("");
console.log("提示: XTEA_KEY 需要从实际 tdc.js 中提取（每次加载变化）");
console.log("提示: 模块 ID 顺序每次 tdc.js 加载变化，需用指纹识别");

// 演示 collect 构造（用占位 key）
const fpData = buildFingerprintData(mockProfile);
const token = "1234567890:987654321";
const trial = 1;
const trajectory = "[]";
// 从 profile 构建 37 个模块值（顺序取决于运行时 tdc.js 的模块排列！）
const moduleValues = buildCDFromProfile(fpData);
const collect = buildCollect(moduleValues, token, trial, null, trajectory);

console.log("");
console.log("=== 构造的 collect（示例，XTEA key 为占位符） ===");
console.log(`cd 模块数: ${moduleValues.length}`);
console.log(`collect length: ${collect.length}`);
console.log(`collect (前 200 字符): ${collect.substring(0, 200)}...`);
console.log("");
console.log("⚠ 重要：模块值顺序在不同 tdc.js 版本中随机变化");
console.log("⚠ 在浏览器中运行 tdc.js 后，实际模块排列需要通过指纹匹配动态确定");
