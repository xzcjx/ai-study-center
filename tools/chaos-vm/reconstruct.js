#!/usr/bin/env node
/**
 * Chaos VM → JS 伪代码还原 v4 — 重写符号执行引擎
 *
 * 核心改进:
 *   1. 每个基本块独立栈，无cross-block污染
 *   2. pending_str 延迟resolve: 只在被用作属性名/函数名时才转为字符串
 *   3. CALL时pair自动拆分: [obj, "method"] → obj.method(...)
 *   4. 块间: 最终效果通过 SET_PROP / U[idx]= 追踪
 *   5. 字符串字典嵌入注释
 *
 * 用法: node reconstruct.js [--start=N] [--limit=N]
 */

const fs = require("fs"), path = require("path");

function loadBC() {
  const f = process.env.TMPDIR + "/bc.json";
  if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf-8"));
  const f2 = path.join(__dirname, "bytecode.json");
  if (fs.existsSync(f2)) return JSON.parse(fs.readFileSync(f2, "utf-8"));
  const { execSync } = require("child_process");
  return JSON.parse(execSync(
    `node "${__dirname}/extract_bytecode.js" 2>/dev/null`,
    { encoding: "utf-8", timeout: 30000, maxBuffer: 100 * 1024 * 1024 }
  ).trim());
}

// ====== 指令解析器 ======
function parseInstr(bc, D) {
  const op = bc[D++];
  const ops = [];
  if ([4, 5, 11, 12, 17, 21, 23, 26, 32, 37, 41, 47, 57, 66].includes(op)) {
    ops.push(bc[D++]);
  } else if (op === 68) {
    ops.push(bc[D++], bc[D++], bc[D++]);
  } else if (op === 45) {
    const entry = bc[D++], vc = bc[D++], pc = bc[D++];
    ops.push(entry, vc, pc);
    for (let i = 0; i < vc * 2; i++) ops.push(bc[D++]);
    for (let i = 0; i < pc; i++) ops.push(bc[D++]);
  }
  return { addr: D - 1 - (ops.length), op, ops, end: D };
}

// ====== CFG 构建 ======
function buildCFG(bc, maxAddr = Infinity) {
  const blocks = [], visited = new Set(), queue = [0];
  while (queue.length) {
    const start = queue.shift();
    if (visited.has(start) || start >= bc.length || start > maxAddr) continue;
    visited.add(start);
    let D = start, next = [], type = "normal";
    while (D < bc.length && D <= maxAddr) {
      const { op, ops, end } = parseInstr(bc, D);
      if (op === 26) { next.push(ops[0]); type = "jmp"; D = end; break; }
      if (op === 12) { next.push(ops[0], end); type = "cond"; D = end; break; }
      if (op === 9 || op === 19 || op === 43) { type = "ret"; D = end; break; }
      if (op === 45 && ops[0] > 0 && ops[0] < bc.length) queue.push(ops[0]);
      D = end;
    }
    blocks.push({ id: blocks.length, start, end: D, next, type });
    for (const n of next) if (!visited.has(n) && n < bc.length && n <= maxAddr) queue.push(n);
    if (type === "normal" && D < bc.length && D <= maxAddr && !visited.has(D)) queue.push(D);
  }
  return blocks.sort((a, b) => a.start - b.start);
}

// ====== 字符串重建（精确匹配 push_empty + str_build_char 序列）=====
function findStrings(bc) {
  const result = [], open = {};
  for (let D = 0; D < bc.length; ) {
    if (bc[D] === 7 && D + 1 < bc.length) {
      let i = D + 1, chars = [];
      while (i < bc.length && bc[i] === 4) { chars.push(bc[i + 1]); i += 2; }
      if (chars.length) {
        const s = String.fromCharCode(...chars);
        result.push(s);
        open[D] = s;
      }
      D = i;
    } else {
      D = parseInstr(bc, D).end;
    }
  }
  return { list: [...new Set(result)], byAddr: open };
}

// ====== 符号化（单基本块） ======
function symBlock(bc, block, strsByAddr) {
  const S = [];  // 符号栈
  const stmts = [];
  let D = block.start;

  // helpers
  function push(v) { S.push(v); }
  function pop() { return S.length > 0 ? S.pop() : { raw: "?" }; }
  function peek() { return S.length > 0 ? S[S.length - 1] : { raw: "?" }; }

  // 格式化: 始终返回 JS 字符串
  function fmt(v) {
    if (v === null || v === undefined) return "?";
    if (typeof v === "string") return v;
    if (typeof v === "number") return String(v);
    if (v.fmt) return v.fmt();
    return String(v.raw || "?");
  }

  // 值对象
  function raw(s) { return { raw: s, fmt() { return s; } }; }
  function lit(v) { return { raw: "lit", fmt() { return JSON.stringify(v); } }; }
  function num(n) { return { raw: "num", fmt() { return String(n); } }; }
  function vref(idx) { return { raw: "v", idx, fmt() { return `v${idx}`; } }; }
  function prop(obj, key) {
    return {
      raw: "prop",
      fmt() {
        // 防止递归 loops
        if (obj === key) return "?";
        const o = fmt(obj), k = fmt(key);
        if (key._lit_str && o !== "?") return `${o}.${key._lit_str}`;
        if (key._lit_str) return key._lit_str;
        if (key.raw === "lit" && o !== "?") return `${o}.${key.fmt()}`;
        if (key.raw === "num") return `${o}[${k}]`;
        return o !== "?" ? `${o}[${k}]` : k;
      }
    };
  }
  function globalRef(s) { return { raw: "global", _lit_str: s, fmt() { return s; } }; }
  function call(fn, args, ctx) {
    return {
      raw: "call",
      fmt() {
        const a = (args || []).map(fmt).join(", ");
        // 如果 fn 是 pair [obj, method]
        if (fn._pair) {
          const o = fmt(fn._pair_obj), m = fmt(fn._pair_method);
          if (fn._pair_method._lit_str) return `${o}.${fn._pair_method._lit_str}(${a})`;
          return `${o}[${m}](${a})`;
        }
        if (ctx) return `${fmt(fn)}.apply(${fmt(ctx)}, [${a}])`;
        return `${fmt(fn)}(${a})`;
      }
    };
  }

  // === 核心: step by step ===
  while (D < block.end) {
    const { addr, op, ops } = parseInstr(bc, D);
    const oldD = D;
    D = parseInstr(bc, D).end;

    // 提前检查: 如果当前 D 位置是 PUSH_EMPTY+STR_BUILD_CHAR 序列，字符串可以直接从 strsByAddr 获取
    function tryResolveString() {
      if (strsByAddr[oldD]) return lit(strsByAddr[oldD]);
      return null;
    }

    switch (op) {
      case 0: { // GET_PROP_PREP: U.push([U[U.pop()][0], B])
        // b = property name, a = object (或 pair whose [0] is used)
        const b = pop(), a = pop();
        if (b._pending_str) { b._lit_str = String.fromCharCode(...b._chars); }
        push({ raw: "pair", _pair: true, _pair_obj: a, _pair_method: b, fmt() { return `${fmt(this._pair_obj)}[${fmt(this._pair_method)}]`; } });
        break;
      }
      case 1: { // PUSH_CTX: H[prop]
        const v = pop(); if (v._pending_str) { v._lit_str = String.fromCharCode(...v._chars); }
        push({ raw: "pair", _pair: true, _pair_obj: raw("H"), _pair_method: v, fmt() { return `H[${fmt(v)}]`; } });
        break;
      }
      case 2: { // GET_PROP
        const p = pop();
        if (p._pair) { push(prop(p._pair_obj, p._pair_method)); }
        else { push(prop(p, raw("undefined"))); }
        break;
      }
      case 3: { // SET_PROP
        const val = pop(), pair = pop();
        if (pair._pair) {
          const p = prop(pair._pair_obj, pair._pair_method);
          stmts.push(`${fmt(p)} = ${fmt(val)};`);
        } else {
          stmts.push(`${fmt(pair)} = ${fmt(val)};`);
        }
        break;
      }
      case 4: { // STR_BUILD_CHAR
        const ch = ops[0];
        const top = peek();
        if (top._pending_str) {
          top._chars.push(ch);
        } else {
          push({ _pending_str: true, _chars: [ch], fmt() { return JSON.stringify(String.fromCharCode(...this._chars)); } });
        }
        break;
      }
      case 5: { push(vref(ops[0])); break; }
      case 7: { push({ _pending_str: true, _chars: [], fmt() { return JSON.stringify(this._chars.length ? String.fromCharCode(...this._chars) : ""); } }); break; }

      // binary ops
      case 6: case 8: case 10: case 25: case 28: case 30: case 33: case 34: case 35:
      case 39: case 44: case 46: case 48: case 54: case 60: case 64: {
        const b = pop(), a = pop();
        const O = {6:">>",8:">=",10:"in",25:"+",28:"==",30:"|",33:"^",34:"*",35:"/",39:"&",44:">",46:"<<",48:"===",54:">>>",60:"%",64:"-"};
        push(raw(`(${fmt(a)} ${O[op] || "?"} ${fmt(b)})`));
        break;
      }

      case 9: { stmts.push(`return ${fmt(peek())};`); break; }
      case 11: { const off = ops[0]; if (off > 0 && S.length >= 2 + off) { const r = S.splice(S.length - 2 - off, 1)[0]; S.push(r); } break; }
      case 12: { const t = ops[0]; stmts.push(`if (${fmt(pop())}) goto ${t};`); break; }
      case 13: { // LOAD_GLOBAL: U[top]=H[U[top]]
        const top = pop();
        if (top._pending_str) { top._lit_str = String.fromCharCode(...top._chars); }
        push(prop(raw("H"), top));
        break;
      }
      case 14: { push(raw(`!${fmt(pop())}`)); break; }
      case 15: { const b = pop(), a = pop(); if (b._pending_str) b._lit_str = String.fromCharCode(...b._chars); push({ raw: "pair", _pair: true, _pair_obj: a, _pair_method: b, fmt() { return `[${fmt(a)}, ${fmt(b)}]`; } }); break; }
      case 16: break; // exception pop

      case 17: case 57: case 41: { // CALL
        const argc = ops[0];
        const args = [];
        for (let i = 0; i < argc; i++) args.unshift(pop());
        const fn = pop();
        const ctx = op === 57 ? raw("H") : null;
        // 如果 fn 不是 pair 而是直接的可调用对象，保持
        const result = call(fn, args, ctx);
        // 如果是 CALL_METHOD (17)，把方法调用的结果格式化为表达式语句
        if (op === 17) {
          // 对于 call 对象，直接推入栈
          push(result);
        } else if (op === 57) {
          // CALL_WITH_THIS: result 是 call 对象
          push(result);
        } else {
          push(result);
        }
        break;
      }

      case 19: { stmts.push(`throw ${fmt(pop())};`); break; }
      case 21: { push(num(ops[0])); break; }
      case 23: { const argc = ops[0]; const args = []; for (let i = 0; i < argc; i++) args.unshift(pop()); stmts.push(`new ${fmt(pop())}(${args.map(fmt).join(", ")});`); break; }
      case 26: { stmts.push(`goto ${ops[0]};`); break; }
      case 27: break;
      case 32: { push(num(ops[0])); break; }
      case 37: { S.length = Math.min(S.length, ops[0]); break; }
      case 38: { push(raw("null")); break; }
      case 43: break; // signal
      case 45: { // CLOSURE
        const entry = ops[0], vc = ops[1], pc = ops[2];
        const caps = [];
        for (let i = 0, j = 3; i < vc; i++, j += 2) caps.push(`v${ops[j]}=v${ops[j+1]}`);
        const params = [];
        for (let i = 0, j = 3 + vc * 2; i < pc; i++, j++) params.push(`a${ops[j]}`);
        stmts.push(`// CLOSURE vm_${entry}(${params.join(",")}) caps[${caps.join(",")}]`);
        push(raw(`closure_vm_${entry}`));
        break;
      }
      case 47: { stmts.push(`v${ops[0]} = v${ops[0]} || [];`); break; }
      case 49: { stmts.push(`delete ${fmt(pop())};`); break; }
      case 51: { // GET_PROP_PREP_REV: U.push([E[0][E[1]], B])
        const b = pop(), a = pop();
        if (b._pending_str) b._lit_str = String.fromCharCode(...b._chars);
        // a is U[idx], we need a[0][a[1]]... approximately U[a_idx][0]
        // but for simplicity, just wrap as pair with deref
        const derefObj = prop(raw("U"), prop(a, num(0)));
        push({ raw: "pair", _pair: true, _pair_obj: derefObj, _pair_method: b, fmt() { return `${fmt(derefObj)}.${b._lit_str || fmt(b)}`; } });
        break;
      }
      case 53: { push(raw("true")); break; }
      case 55: { stmts.push(`${fmt(pop())}.shift();`); break; }
      case 56: { push(raw(`U[${fmt(pop())}[0]]`)); break; }
      case 58: { const val = pop(); stmts.push(`U[?][0] = ${fmt(val)};`); break; }
      case 59: { push(raw("undefined")); break; }
      case 62: { push(raw(`Object.keys(${fmt(pop())})`)); break; }
      case 63: { push(raw("false")); break; }
      case 66: { push(raw(`[${ops[0]}]`)); break; }
      case 67: { pop(); break; }
      case 68: { stmts.push(`// try { } catch(v${ops[2]}) { handler@${ops[0]}; }`); break; }
      case 69: { push(peek()); break; }
    }
  }
  return stmts;
}

// ====== 主流程 ======
function main() {
  const args = process.argv.slice(2);
  const start = parseInt((args.find(a => a.startsWith("--start=")) || "--start=0").split("=")[1]);
  const limit = parseInt((args.find(a => a.startsWith("--limit=")) || "--limit=80").split("=")[1]);

  const bc = loadBC();
  const maxAddr = Math.min(bc.length, start + limit * 50);

  const { list: allStrings, byAddr: strsByAddr } = findStrings(bc);
  const blocks = buildCFG(bc, maxAddr);
  const relevant = blocks.filter(b => b.start >= start).slice(0, limit);

  process.stderr.write(`[bc] ${bc.length} | [str] ${allStrings.length} | [blk] total=${blocks.length} shown=${relevant.length}\n`);

  // 字符串表（前60个）
  const strTable = allStrings.slice(0, 60).map((s, i) => `${String(i).padStart(2)} "${s}"`);

  // 逐块 sym
  const body = [];
  for (const block of relevant) {
    const stmts = symBlock(bc, block, strsByAddr);
    if (stmts.length === 0) continue;
    body.push(`// ── B${block.id} [${block.start}~${block.end}] ${block.type}${block.next.length ? " → " + block.next.join(",") : ""}`);
    body.push(...stmts.map(s => `  ${s}`));
    body.push("");
  }

  const output = [
    "=".repeat(80),
    "  Chaos VM → JS 伪代码还原 v4",
    "=".repeat(80),
    `  指令: ${bc.length} | 基本块: ${blocks.length} | 显示: ${relevant.length} 块 | 范围: [${relevant[0]?.start||start}]~[${maxAddr}]`,
    "",
    `--- 字符串字典 (${allStrings.length}) ---`,
    ...strTable,
    allStrings.length > 60 ? `  ... +${allStrings.length - 60} more` : "",
    "",
    "--- 还原 ---",
    "",
    ...body
  ].join("\n");

  process.stdout.write(output + "\n");
}

main();
