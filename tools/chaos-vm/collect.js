#!/usr/bin/env node
/**
 * TDC collect 计算器 — Node.js CLI
 *
 * 输入: tdc.js 源码 + 指纹 profile (JSON)
 * 输出: collect 字段值 (stdout)
 *
 * 用法:
 *   node collect.js < tdc.js                          # stdin 读取 tdc.js
 *   node collect.js --tdc=tdc.js --profile=profile.json
 *   node collect.js --tdc=tdc.js --auto               # 自动生成随机指纹
 *
 * Python 调用:
 *   result = subprocess.run(["node", "collect.js", "--tdc=tdc.js", "--auto"],
 *                            capture_output=True, text=True)
 *   collect = result.stdout.strip()
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// ====== 命令行参数 ======
const args = process.argv.slice(2);
function getArg(prefix) {
  for (const a of args) if (a.startsWith(prefix)) return a.substring(a.indexOf("=") + 1);
  return null;
}
const tdcFile = getArg("--tdc=");
const profileFile = getArg("--profile=");
const autoMode = args.includes("--auto");
const help = args.includes("--help") || args.includes("-h");

if (help) {
  console.error(`
TDC collect 计算器

用法:
  node collect.js --tdc=tdc.js --auto              自动生成随机指纹
  node collect.js --tdc=tdc.js --profile=p.json    使用指定 profile

输出:
  collect 字段值 (stdout)
`);
  process.exit(0);
}

if (!tdcFile) {
  console.error("错误: 需要 --tdc=tdc.js 参数");
  process.exit(1);
}

// ====== Step 1: 读取 tdc.js ======
const tdcSrc = fs.readFileSync(tdcFile, "utf-8");

// ====== Step 2: 提取字节码 ======
// Patch tdc.js: 在 return g(), R 之前插入 globalThis.__BC__ = R
const patched = tdcSrc.replace(
  /(return\s+g\(\),\s*R)(\s*\})/,
  "globalThis.__BC__ = R; $1$2"
);

// Node.js 环境: 提供 window
globalThis.window = globalThis;
try {
  eval(patched);
} catch(e) {
  console.error("错误: tdc.js 执行失败:", e.message);
  process.exit(1);
}

const bc = globalThis.__BC__;
if (!bc) {
  console.error("错误: 无法提取字节码");
  process.exit(1);
}
console.error("[提取] %d 字节码", bc.length);

// ====== Step 3: 解析指令 ======
function parse(B, D) {
  const o = B[D++], p = [];
  if ([4, 5, 11, 12, 17, 21, 23, 26, 32, 37, 41, 47, 57, 66].includes(o)) p.push(B[D++]);
  else if (o === 68) { p.push(B[D++], B[D++], B[D++]); }
  else if (o === 45) {
    const v = B[D++], c = B[D++], a = B[D++]; p.push(v, c, a);
    for (let i = 0; i < c * 2; i++) p.push(B[D++]);
    for (let i = 0; i < a; i++) p.push(B[D++]);
  }
  return { op: o, ops: p, end: D };
}

// ====== Step 4: 提取所有字符串 ======
function extractAllStrings(bc) {
  const strs = [];
  for (let D = 0; D < bc.length;) {
    if (bc[D] === 7 && D + 1 < bc.length && bc[D + 1] === 4) {
      let i = D + 1, chars = [];
      while (i < bc.length && bc[i] === 4) { chars.push(bc[i + 1]); i += 2; }
      if (chars.length > 0) strs.push(String.fromCharCode(...chars));
      D = i;
    } else D = parse(bc, D).end;
  }
  return strs;
}

let allStrings = extractAllStrings(bc);
allStrings = [...new Set(allStrings)];
console.error("[字符串] %d 个", allStrings.length);

// ====== Step 5: 加载/生成 fingerprint profile ======
/** 默认随机指纹 profile */
function randomProfile() {
  const uaChoices = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
  ];
  return {
    userAgent: uaChoices[Math.floor(Math.random() * uaChoices.length)],
    platform: "MacIntel",
    language: "zh-CN",
    hardwareConcurrency: [4, 8, 12][Math.floor(Math.random() * 3)],
    deviceMemory: [4, 8, 16][Math.floor(Math.random() * 3)],
    screenWidth: [1440, 1680, 1920][Math.floor(Math.random() * 3)],
    screenHeight: [900, 1050, 1080][Math.floor(Math.random() * 3)],
    colorDepth: 24,
    pixelDepth: 24,
    innerWidth: 1680,
    outerWidth: 1680,
    pluginsCount: [3, 5, 7][Math.floor(Math.random() * 3)],
    mimeTypesCount: 2,
    touchSupport: false,
    pdfViewerEnabled: true,
    chromeDetected: true,
    historyLength: 1,
    connectionType: "unknown",
    canvasHash: Array.from({ length: 16 }, () =>
      "0123456789abcdef"[Math.floor(Math.random() * 16)]
    ).join(""),
    webglRenderer: "ANGLE (Apple, Apple M1, OpenGL 4.1)",
    webglVendor: "Google Inc. (Apple)",
    webdriver: "false",
    doNotTrack: "1",
    productSub: "20030107",
    appVersion: "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    webrtcCandidates: "",
    timeEval: String(Math.floor(Math.random() * 100)),
    timeNow: String(Date.now()),
    timeGetTime: String(new Date().getTime()),
    timezoneOffset: String(new Date().getTimezoneOffset()),
    documentKeys: "location",
    errorStackTrace: "",
    stringHookResult: "",
    localStorageEnabled: "true",
    sessionStorageEnabled: "true",
    indexedDBEnabled: "true",
  };
}

let profile;
if (profileFile) {
  profile = JSON.parse(fs.readFileSync(profileFile, "utf-8"));
} else {
  profile = randomProfile();
  console.error("[profile] 自动生成随机指纹");
}

// ====== Step 6: XTEA 加密 ======
function xteaEncrypt(v0, v1, key) {
  v0 = v0 >>> 0; v1 = v1 >>> 0;
  let sum = 0;
  for (let i = 0; i < 32; i++) {
    v0 += (((v1 << 4) ^ (v1 >>> 5)) + v1) ^ (sum + key[sum & 3]);
    v0 = v0 >>> 0;
    sum = (sum + 0x9E3779B9) >>> 0;
    v1 += (((v0 << 4) ^ (v0 >>> 5)) + v0) ^ (sum + key[(sum >>> 11) & 3]);
    v1 = v1 >>> 0;
  }
  return [v0, v1];
}

// ====== Step 7: Base64 ======
const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
function base64Encode(bytes) {
  let r = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i], b = bytes[i + 1] || 0, c = bytes[i + 2] || 0;
    r += B64[a >> 2] + B64[((a & 3) << 4) | (b >> 4)];
    r += i + 1 < bytes.length ? B64[((b & 15) << 2) | (c >> 6)] : "=";
    r += i + 2 < bytes.length ? B64[c & 63] : "=";
  }
  return r;
}

function strToUint8(str) {
  const arr = new Uint8Array(str.length);
  for (let i = 0; i < str.length; i++) arr[i] = str.charCodeAt(i) & 0xFF;
  return arr;
}

function uint32ToUint8(v) {
  return new Uint8Array(new Uint32Array([v]).buffer);
}

// ====== Step 8: build 37 module values ======
function buildModuleValues(profile) {
  return [
    profile.userAgent,
    profile.canvasHash,
    profile.webglRenderer,
    profile.webglVendor,
    profile.timezoneOffset,
    profile.webdriver,
    profile.webrtcCandidates || "",
    profile.productSub,
    profile.appVersion,
    String(profile.screenWidth),
    String(profile.screenHeight),
    String(profile.colorDepth),
    String(profile.pixelDepth),
    profile.language,
    profile.platform,
    String(profile.cookieEnabled !== false),
    profile.doNotTrack,
    String(profile.hardwareConcurrency),
    String(profile.deviceMemory),
    String(profile.pluginsCount),
    String(profile.mimeTypesCount),
    profile.localStorageEnabled,
    profile.sessionStorageEnabled,
    profile.indexedDBEnabled,
    profile.timeEval,
    profile.timeGetTime,
    String(profile.innerWidth),
    String(profile.outerWidth),
    String(profile.touchSupport),
    String(profile.pdfViewerEnabled),
    String(profile.chromeDetected),
    String(profile.historyLength),
    profile.documentKeys,
    profile.errorStackTrace,
    profile.timeNow,
    profile.connectionType,
    profile.stringHookResult,
  ];
}

// ====== Step 9: 加密单个 8 字节块 ======
function encrypt8bytes(str8, key) {
  const bytes = strToUint8(str8.padEnd(8, "\x00").substring(0, 8));
  const v0 = (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3];
  const v1 = (bytes[4] << 24) | (bytes[5] << 16) | (bytes[6] << 8) | bytes[7];
  const [e0, e1] = xteaEncrypt(v0, v1, key);
  return base64Encode(uint32ToUint8(e0)) + base64Encode(uint32ToUint8(e1));
}

// ====== Step 10: 构造 collect ======
function pad24(s) {
  const rem = s.length % 24;
  return rem === 0 ? s : s + " ".repeat(24 - rem);
}

function buildCollect(moduleValues, key, token, trial, eks, trajectory) {
  // chunk1: cd + token + trial
  const chunk1Raw = JSON.stringify({
    cd: moduleValues,
    token: String(token),
    trial: trial || 1,
    ...(eks ? { eks } : {})
  });
  const c1 = pad24(chunk1Raw);
  let r1 = "";
  for (let i = 0; i < c1.length; i += 8) {
    r1 += encrypt8bytes(c1.substring(i, i + 8), key);
  }

  // trajectory
  const t1 = pad24(trajectory || "[]");
  let rt = "";
  for (let i = 0; i < t1.length; i += 8) {
    rt += encrypt8bytes(t1.substring(i, i + 8), key);
  }

  // chunk2: 同 chunk1（无 eks）
  const chunk2Raw = JSON.stringify({
    cd: moduleValues,
    token: String(token),
    trial: trial || 1,
  });
  const c2 = pad24(chunk2Raw);
  let r2 = "";
  for (let i = 0; i < c2.length; i += 8) {
    r2 += encrypt8bytes(c2.substring(i, i + 8), key);
  }

  // sd (不 pad)
  const sdRaw = JSON.stringify({ od: "C", ft: String(Date.now()) });
  let rs = "";
  for (let i = 0; i < sdRaw.length; i += 8) {
    rs += encrypt8bytes(sdRaw.substring(i, i + 8), key);
  }

  return r1 + rt + r2 + rs;
}

// ====== Step 11: 执行 ======
// XTEA Key — 占位符（需从 tdc.js 动态提取）
// 真实方案：Hook window.TDC.getData 来获取 key
const XTEA_KEY = [0xDEADBEEF, 0x12345678, 0xABCDEF01, 0x23456789];
console.error("[警告] XTEA key 是占位符！需从 tdc.js 动态提取。");
console.error("[警告] 提取方法: 在浏览器中 Hook TDC.sd 的 .get 函数，或者");
console.error("[警告]          用 disasm.js 反汇编 key 构建函数区域。");

const moduleValues = buildModuleValues(profile);
const token = String(Date.now()) + ":0";
const collect = buildCollect(moduleValues, XTEA_KEY, token, 1, "", "[]");

console.error("[collect] length=%d", collect.length);
console.log(collect);
