#!/usr/bin/env node
/**
 * 腾讯 Chaos VM 字节码反汇编器 v2 — 正确处理 opcode + operand 混合编码
 *
 * 用法: node disasm2.js [--full] [--start=N] [--limit=N]
 *   先运行 extract_bytecode.js 生成 bytecode.json
 *   或直接 --bc=bytecode.json
 */

const fs = require("fs");
const path = require("path");

// ====== Opcode 定义 (索引 -> {name, operandFn}) ======
// operandFn 接收 (bytecode, cursor) 返回 {count: N, values: [...]}
const OPS = {};

function noOp() { return {count: 0, values: []}; }
function oneImm(bc, D) { return {count: 1, values: [bc[D]]}; }
function twoImm(bc, D) { return {count: 2, values: [bc[D], bc[D+1]]}; }
function threeImm(bc, D) { return {count: 3, values: [bc[D], bc[D+1], bc[D+2]]}; }

// 0-17
OPS[0]  = {name:'GET_PROP_PREP',   desc:'push [obj_ref, prop_ref]', arity: noOp};
OPS[1]  = {name:'PUSH_CTX',        desc:'push [H, U.pop()]', arity: noOp};
OPS[2]  = {name:'GET_PROP',        desc:'U.push(obj[prop])', arity: noOp};
OPS[3]  = {name:'SET_PROP',        desc:'obj[prop] = val', arity: noOp};
OPS[4]  = {name:'STR_BUILD_CHAR',  desc:'U[top] += String.fromCharCode(ch)', arity(bc,D) { const ch = bc[D]; return {count:1, values:[ch], note:`string += '${String.fromCharCode(ch)}'`}; }};
OPS[5]  = {name:'LOAD_EXT_VAR',    desc:'push U[g[idx]]', arity(bc,D) { return {count:1, values:[bc[D]], note:`U[${bc[D]}]`}; }};
OPS[6]  = {name:'SHR',             desc:'a >> b', arity: noOp};
OPS[7]  = {name:'PUSH_EMPTY_STR',  desc:'push ""', arity: noOp};
OPS[8]  = {name:'GTE',             desc:'a >= b', arity: noOp};
OPS[9]  = {name:'RETURN_SIGNAL',   desc:'return !!Q (loop break)', arity: noOp};
OPS[10] = {name:'OP_IN',           desc:'a in b', arity: noOp};
OPS[11] = {name:'STACK_ROTATE',    desc:'rotate stack', arity(bc,D) { return {count:1, values:[bc[D]], note:`offset=${bc[D]}`}; }};
OPS[12] = {name:'JMP_IF_TRUE',     desc:'if (U[top]) D = target', arity(bc,D) { return {count:1, values:[bc[D]], note:`jmp_if_true -> ${bc[D]}`}; }};
OPS[13] = {name:'LOAD_GLOBAL',     desc:'U[top] = H[U[top]]', arity: noOp};
OPS[14] = {name:'LOGICAL_NOT',     desc:'push !U.pop()', arity: noOp};
OPS[15] = {name:'SWAP_PACK',       desc:'push [swap(a,b)]', arity: noOp};
OPS[16] = {name:'EXCEPTION_POP',   desc:'exception stack pop', arity: noOp};
OPS[17] = {name:'CALL_METHOD',     desc:'obj[prop].apply(obj, args)', arity(bc,D) { return {count:1, values:[bc[D]], note:`argc=${bc[D]}`}; }};
// 18 = empty
OPS[19] = {name:'THROW',           desc:'throw U[top]', arity: noOp};
// 20 = empty
OPS[21] = {name:'PUSH_IMM',        desc:'push g[D++]', arity(bc,D) { return {count:1, values:[bc[D]], note:`value=${bc[D]}`}; }};
// 22 = empty
OPS[23] = {name:'NEW_CONSTRUCT',   desc:'new Func(...)', arity(bc,D) { return {count:1, values:[bc[D]], note:`argc=${bc[D]}`}; }};
OPS[25] = {name:'ADD',             desc:'a + b', arity: noOp};
OPS[26] = {name:'JMP',             desc:'unconditional jump', arity(bc,D) { return {count:1, values:[bc[D]], note:`jmp -> ${bc[D]}`}; }};
OPS[27] = {name:'CLEAR_EXCEPTION', desc:'Q = null', arity: noOp};
OPS[28] = {name:'EQ',              desc:'a == b', arity: noOp};
OPS[30] = {name:'BIT_OR',          desc:'a | b', arity: noOp};
OPS[32] = {name:'SET_IMM',         desc:'U[top] = g[D++]', arity(bc,D) { return {count:1, values:[bc[D]], note:`= ${bc[D]}`}; }};
OPS[33] = {name:'BIT_XOR',         desc:'a ^ b', arity: noOp};
OPS[34] = {name:'MUL',             desc:'a * b', arity: noOp};
OPS[35] = {name:'DIV',             desc:'a / b', arity: noOp};
OPS[37] = {name:'SET_STACK_LEN',   desc:'U.length = n', arity(bc,D) { return {count:1, values:[bc[D]], note:`len=${bc[D]}`}; }};
OPS[38] = {name:'PUSH_NULL',       desc:'push null', arity: noOp};
OPS[39] = {name:'BIT_AND',         desc:'a & b', arity: noOp};
OPS[41] = {name:'CALL_FUNC',       desc:'Func.apply(H, args)', arity(bc,D) { return {count:1, values:[bc[D]], note:`argc=${bc[D]}`}; }};
OPS[42] = {name:'TYPEOF',          desc:'push typeof U.pop()', arity: noOp};
OPS[43] = {name:'PUSH_TRUE_SIG',   desc:'return true (VM signal)', arity: noOp};
OPS[44] = {name:'GT',              desc:'a > b', arity: noOp};
OPS[45] = {name:'CREATE_CLOSURE',
  desc:'create child VM closure',
  arity(bc, D) {
    const vmEntry = bc[D];
    const varCount = bc[D+1];
    const paramCount = bc[D+2];
    const captures = [];
    let offset = D + 3;
    for (let i = 0; i < varCount; i++) {
      captures.push(`U[${bc[offset]}]<-U[${bc[offset+1]}]`);
      offset += 2;
    }
    const paramMap = [];
    for (let i = 0; i < paramCount; i++) {
      paramMap.push(bc[offset]);
      offset++;
    }
    const totalOps = offset - D; // includes vmEntry, varCount, paramCount, all captures, paramMap
    return {
      count: totalOps,
      values: [vmEntry, varCount, paramCount, ...captures.flatMap(()=>[]), ...paramMap],
      note: `CLOSURE vm_entry=${vmEntry} vars=${varCount} params=${paramCount} caps=[${captures.join(',')}] pmap=[${paramMap.join(',')}]`
    };
  }
};
OPS[46] = {name:'SHL',             desc:'a << b', arity: noOp};
OPS[47] = {name:'ENSURE_ARRAY',    desc:'safe array init', arity(bc,D) { return {count:1, values:[bc[D]], note:`U[${bc[D]}]`}; }};
OPS[48] = {name:'STRICT_EQ',       desc:'a === b', arity: noOp};
OPS[49] = {name:'DELETE_PROP',     desc:'delete obj[prop]', arity: noOp};
OPS[51] = {name:'GET_PROP_PREP_REV', desc:'push [obj, prop] reversed', arity: noOp};
OPS[54] = {name:'UNSIGNED_SHR',    desc:'a >>> b', arity: noOp};
OPS[55] = {name:'ARRAY_SHIFT',     desc:'array shift head', arity: noOp};
OPS[56] = {name:'ARRAY_IDX_GET',   desc:'U.push(arr[idx])', arity: noOp};
OPS[57] = {name:'CALL_WITH_THIS',  desc:'fn.apply(H, args)', arity(bc,D) { return {count:1, values:[bc[D]], note:`argc=${bc[D]}`}; }};
OPS[58] = {name:'ARRAY_IDX_SET',   desc:'arr[idx] = val', arity: noOp};
OPS[59] = {name:'PUSH_UNDEFINED',  desc:'push undefined', arity: noOp};
OPS[60] = {name:'MOD',             desc:'a % b', arity: noOp};
OPS[62] = {name:'OBJECT_KEYS',     desc:'Object.keys(obj)', arity: noOp};
OPS[63] = {name:'PUSH_FALSE',      desc:'push false', arity: noOp};
OPS[64] = {name:'SUB',             desc:'a - b', arity: noOp};
OPS[66] = {name:'PUSH_WRAPPED_IMM', desc:'push [n]', arity(bc,D) { return {count:1, values:[bc[D]], note:`[${bc[D]}]`}; }};
OPS[67] = {name:'POP',             desc:'discard top', arity: noOp};
OPS[68] = {name:'REGISTER_HANDLER', desc:'register exception handler', arity(bc,D) {
  const addr = bc[D], stackLvl = bc[D+1], catchVar = bc[D+2];
  return {count:3, values:[addr, stackLvl, catchVar], note:`handler@${addr} restore=${stackLvl} catch=${catchVar}`};
}};
OPS[69] = {name:'DUP',             desc:'duplicate top', arity: noOp};

// ====== 反汇编引擎 ======
function disasm(bytecodes, startAddr = 0, maxInstrs = 200, showData = true) {
  const lines = [];
  let D = startAddr;
  let instrCount = 0;
  const endAddr = Math.min(startAddr + maxInstrs * 10, bytecodes.length); // safety cap

  // 子VM 收集
  const childVMs = [];

  while (D < bytecodes.length && instrCount < maxInstrs) {
    const addr = D;
    const opcode = bytecodes[D];
    D++;

    const opDef = OPS[opcode];
    let opName, opNote, opValues;

    if (opDef) {
      opName = opDef.name;
      const arityResult = opDef.arity(bytecodes, D);
      opValues = arityResult.values;
      const extraNote = arityResult.note || '';
      opNote = opDef.desc + (extraNote ? ` [${extraNote}]` : '');
      D += arityResult.count;

      // 收集子VM入口地址
      if (opcode === 45 && opValues && opValues.length >= 1) {
        childVMs.push({entry: opValues[0], parentAddr: addr});
      }
    } else {
      // 未知 — 这是数据值或空槽中的值
      opName = `DATA_${opcode}`;
      opNote = `data value: ${opcode} (opcode slot empty)`;
      opValues = [opcode];
    }

    const addrStr = `[${String(addr).padStart(6,' ')}]`;
    const nameStr = opName.padEnd(20);
    const noteStr = opNote || '';

    if (showData || opDef) {
      lines.push(`${addrStr} ${nameStr} ${noteStr}`);
    } else {
      // skip data-only entries
      if (opDef) lines.push(`${addrStr} ${nameStr} ${noteStr}`);
    }
    instrCount++;
  }

  lines.push('');
  lines.push(`--- [共 ${instrCount} 条指令，游标位置: ${D}] ---`);
  return { lines, cursor: D, childVMs };
}

// ====== 主流程 ======
function main() {
  const args = process.argv.slice(2);
  const fullMode = args.includes('--full');
  const startArg = args.find(a => a.startsWith('--start='));
  const limitArg = args.find(a => a.startsWith('--limit='));

  const startAddr = startArg ? parseInt(startArg.split('=')[1]) : 0;
  const limit = limitArg ? parseInt(limitArg.split('=')[1]) : (fullMode ? 50000 : 200);

  // 从 stdin/pipe 或 TMPDIR 或 bytecode.json 加载
  let bytecodes;
  const tmpBc = process.env.TMPDIR + '/bc.json';
  const localBc = path.join(__dirname, 'bytecode.json');
  if (fs.existsSync(tmpBc)) {
    bytecodes = JSON.parse(fs.readFileSync(tmpBc, 'utf-8'));
    console.error(`[加载] ${tmpBc} (${bytecodes.length} 条)`);
  } else if (fs.existsSync(localBc)) {
    bytecodes = JSON.parse(fs.readFileSync(localBc, 'utf-8'));
    console.error(`[加载] ${localBc} (${bytecodes.length} 条)`);
  } else {
    console.error('[提取] 运行 extract_bytecode.js...');
    const {execSync} = require('child_process');
    const raw = execSync(`node "${__dirname}/extract_bytecode.js" 2>/dev/null`, {encoding:'utf-8', timeout: 30000});
    bytecodes = JSON.parse(raw.trim());
    console.error(`[提取] ${bytecodes.length} 条`);
  }

  // 反汇编
  console.error(`[反汇编] start=${startAddr} limit=${limit}`);
  const {lines, cursor, childVMs} = disasm(bytecodes, startAddr, limit);

  // 输出
  const header = [
    '='.repeat(80),
    '  腾讯 Chaos VM (__TENCENT_CHAOS_VM) 字节码反汇编 v2',
    '='.repeat(80),
    `  总字节码: ${bytecodes.length} | 范围: [${startAddr}] ~ [${cursor - 1}] | 共 ${lines.length - 2} 条指令`,
    '',
    '  格式: [地址] 操作码  说明',
    '',
  ];

  const output = [...header, ...lines];

  if (childVMs.length > 0) {
    output.push('');
    output.push('--- 发现的子VM入口 ---');
    for (const vm of childVMs) {
      output.push(`  入口=${vm.entry} (在地址 ${vm.parentAddr} 创建)`);
    }
  }

  process.stdout.write(output.join('\n') + '\n');
}

main();
