/**
 * 内存提取: patch tdc.js 源码，注入钩子后 eval，不写文件
 */
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/tdc.js", "utf-8");

// 在 return g(), R 之前插入捕获代码
// 找: n.push(U), D++ ... return g(), R
// 直接将 return g(), R 改为 global.__BC__ = R; return g(), R
const patched = src.replace(
  /(return\s+g\(\),\s*R)(\s*\})/,
  'globalThis.__BC__ = R; $1$2'
);

// Node.js 环境: 提供 window 全局
globalThis.window = globalThis;

// eval the patched source directly (no file write needed)
eval(patched);

// 现在 globalThis.__BC__ 应该被填充
const bc = globalThis.__BC__;
if (!bc) {
  console.error("FAILED: bytecode not captured from eval");
  process.exit(1);
}

console.error("bytecode length:", bc.length);
console.error("bytecode[0..30]:", JSON.stringify(bc.slice(0, 30)));
console.error("bytecode[-10..]:", JSON.stringify(bc.slice(-10)));

// Opcode 统计
const stats = {};
for (let i = 0; i < bc.length; i++) {
  stats[bc[i]] = (stats[bc[i]] || 0) + 1;
}
const sorted = Object.entries(stats).sort((a,b) => parseInt(a[0]) - parseInt(b[0]));
console.error("unique values:", sorted.length);

const realOps = sorted.filter(([k]) => parseInt(k) <= 82);
console.error("--- Opcodes 0~82 ---");
for (const [op, cnt] of realOps) {
  console.error(`  OP_${String(op).padStart(2,' ')}: ${cnt}`);
}

const dataVals = sorted.filter(([k]) => parseInt(k) > 82).sort((a,b) => b[1] - a[1]);
console.error(`--- Data values > 82 (${dataVals.length} unique, top 10) ---`);
for (const [op, cnt] of dataVals.slice(0, 10)) {
  console.error(`  val_${op}: ${cnt}`);
}

// 输出 JSON 到 stdout
console.log(JSON.stringify(bc));
