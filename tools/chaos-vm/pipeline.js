#!/usr/bin/env node
/**
 * Chaos VM → collect 全自动 pipeline
 *
 * 输入: tdc.js（同目录下）
 * 输出: 当前 tdc.js 的模块排列 + 可用的 collect 构造参数
 *
 * 用法: node pipeline.js [--profile=profile.json]
 */

const fs = require("fs"), path = require("path");

// ====== Step 0: load bytecodes ======
const bcFile = process.env.TMPDIR + "/bc.json";
if (!fs.existsSync(bcFile)) {
  console.error("Run first: node extract_bytecode.js 2>/dev/null > $TMPDIR/bc.json");
  process.exit(1);
}
const bc = JSON.parse(fs.readFileSync(bcFile, "utf-8"));

// ====== Step 1: parse helper ======
function parse(B, D) { const o = B[D++], p = [];
  if ([4,5,11,12,17,21,23,26,32,37,41,47,57,66].includes(o)) { p.push(B[D++]); }
  else if (o === 68) { p.push(B[D++], B[D++], B[D++]); }
  else if (o === 45) { const v = B[D++], c = B[D++], a = B[D++]; p.push(v,c,a);
    for (let i = 0; i < c*2; i++) p.push(B[D++]);
    for (let i = 0; i < a; i++) p.push(B[D++]); }
  return { op: o, ops: p, end: D };
}

// ====== Step 2: Find the 37 CD push IDs ======
// The reconstruct output gave us: [8,9,12,13,14,16,18,22,23,24,25,26,27,1,28,29,30,31,32,33,36,43,44,45,42,46,47,48,49,50,51,52,53,54,55,56,58]
// But this is just ONE version. Let's find it dynamically from bytecode.
//
// Pattern: a dense cluster of CALL_WITH_THIS(57, argc=1) calls.
// Each call's module ID is in a preceding PUSH_WRAPPED_IMM(66).

function findModuleOrder() {
  // Step A: collect all 57(argc=1) addresses
  const allCalls = [];
  for (let D = 0; D < bc.length; ) { const {op,ops,end} = parse(bc,D);
    if (op === 57 && ops[0] === 1) allCalls.push(D);
    D = end;
  }

  // Step B: find densest cluster (30+ calls in <2000 span)
  let bestCluster = null;
  for (let i = 0; i < allCalls.length - 30; i++) {
    for (let j = i + 30; j < Math.min(allCalls.length, i + 50); j++) {
      const span = allCalls[j] - allCalls[i];
      if (span < 3000) {
        if (!bestCluster || (j - i > bestCluster.count)) {
          bestCluster = { start: i, end: j, count: j - i + 1, span, startAddr: allCalls[i], endAddr: allCalls[j] };
        }
      }
    }
  }

  if (!bestCluster) {
    console.error("[warn] no dense cluster found, using known fallback");
    return [8,9,12,13,14,16,18,22,23,24,25,26,27,1,28,29,30,31,32,33,36,43,44,45,42,46,47,48,49,50,51,52,53,54,55,56,58];
  }

  console.error("[modules] cluster: %d calls, span=%d bytes, addr %d-%d",
    bestCluster.count, bestCluster.span, bestCluster.startAddr, bestCluster.endAddr);

  // Step C: extract module IDs from PUSH_WRAPPED_IMM(66) before each call
  const ids = [];
  const contextWindow = 200; // look back up to 200 bytecodes

  for (let ci = bestCluster.start; ci <= bestCluster.end && ids.length < 40; ci++) {
    const callAddr = allCalls[ci];
    // scan backwards for nearest 66
    let back = callAddr - 1;
    let found = false;
    while (back > Math.max(0, callAddr - contextWindow)) {
      const p = parse(bc, back);
      if (p.op === 66) { ids.push(bc[back + 1]); found = true; break; }
      back--;
    }
  }

  if (ids.length === 37) {
    console.error("[modules] %d IDs: %s", ids.length, ids.join(","));
    return ids;
  }

  // fallback: take first 37
  console.error("[modules] got %d IDs, using first 37", ids.length);
  return ids.slice(0, 37);
}

const moduleOrder = findModuleOrder();

// ====== Step 3: Extract strings from each module's .get() closure ======
// For each module ID, find which CREATE_CLOSURE is closest to the push,
// then scan that closure's bytecode range for string literals.

// First, collect ALL closures with their entry addresses
const closures = {};
for (let D = 0; D < bc.length; ) {
  const { op, ops, end } = parse(bc, D);
  if (op === 45) closures[ops[0]] = { addr: D, entry: ops[0], varCount: ops[1], paramCount: ops[2] };
  D = end;
}

// Then, for each module ID, find the closure used as its handler
// The pattern: module_register(module_id, closure_entry)
// In bytecode: PUSH_WRAPPED_IMM(66) module_id → ... → CREATE_CLOSURE(45) entry → SET_PROP
const modules = [];
for (let i = 0; i < moduleOrder.length; i++) {
  const mid = moduleOrder[i];
  // Find a CREATE_CLOSURE immediately before or after the PUSH_WRAPPED_IMM for this mid
  // Scan for 66 with value == mid
  let foundClosure = null;
  for (let D = 0; D < bc.length; D = parse(bc, D).end) {
    const { op, ops } = parse(bc, D);
    if (op === 66 && ops[0] === mid) {
      // scan forward ~50 instrs for 45
      let scan = D + 1;
      for (let s = 0; s < 80 && scan < bc.length; s++) {
        const p = parse(bc, scan);
        if (p.op === 45) { foundClosure = closures[p.ops[0]]; break; }
        scan = p.end;
      }
      if (foundClosure) break;
    }
  }
  modules.push({ id: mid, closure: foundClosure });
}

// Extract strings from each closure's bytecode range
for (const m of modules) {
  if (!m.closure) { m.fingerprint = "(unknown)"; continue; }
  // Find the closure's function body range
  // Closures in Chaos VM store: the entry address IS the bytecode offset where the child VM starts
  const entry = m.closure.entry;
  let endAddr = entry + 1000; // rough upper bound
  // Scan the range for string literals
  let D = entry;
  const strs = [];
  while (D < Math.min(entry + 5000, bc.length) && D < endAddr) {
    if (bc[D] === 7 && bc[D+1] === 4) {
      let i = D + 1, chars = [];
      while (i < bc.length && bc[i] === 4) { chars.push(bc[i+1]); i += 2; }
      if (chars.length > 0) strs.push(String.fromCharCode(...chars));
      D = i;
    } else {
      D = parse(bc, D).end;
    }
  }
  m.fingerprint = strs.join(",");
}

// ====== Step 4: XTEA key extraction info ======
// Cannot fully extract key statically (14 sub-functions involved).
// But we can find the key buffer address and the delta:
let xteaDelta = 0x9E3779B9, xteaAddr = -1;
for (let D = 0; D < bc.length; D++) {
  if (bc[D] === 0x9E3779B9) { xteaDelta = bc[D]; xteaAddr = D; break; }
}

// ====== Step 5: Output ======
const result = {
  version: "1.0",
  bytecodeLength: bc.length,
  moduleOrder,
  modules: modules.map(m => ({ id: m.id, fingerprint: m.fingerprint, closureEntry: m.closure?.entry || -1 })),
  xtea: { delta: xteaDelta, deltaAddr: xteaAddr },
  collectStructure: "base64(xtea(chunk1_24pad)) + base64(xtea(trajectory)) + base64(xtea(chunk2_24pad)) + base64(xtea(sd_nopad))",
};

// Human-readable + JSON output
console.log("=".repeat(70));
console.log("  Chaos VM → collect pipeline");
console.log("=".repeat(70));
console.log("Bytecodes: %d | XTEA delta: 0x%s @ [%d]",
  bc.length, xteaDelta.toString(16).toUpperCase(), xteaAddr);
console.log("");
console.log("37 模块排列（当前 tdc.js）:");
console.log("  " + moduleOrder.join(", "));
console.log("");
console.log("模块指纹（前 10 个）:");
for (const m of modules.slice(0, 10)) {
  console.log("  module %s: entry=%d fp=%s",
    String(m.id).padStart(2), m.closure?.entry || -1,
    (m.fingerprint || "(unknown)").substring(0, 80));
}
console.log("");
console.log("--- JSON ---");
console.log(JSON.stringify(result, null, 2));
