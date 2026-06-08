#!/usr/bin/env python3
"""AI 学习中心 · 工具查询与安装引擎（解析 tools-registry.yaml，无第三方依赖）。"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InstallMethod:
    id: str
    label: str
    type: str
    scope: str
    command: str = ""
    instructions: str = ""
    agent: str = ""


@dataclass
class Tool:
    id: str
    name: str
    summary: str
    kb_id: str
    note_path: str
    homepage: str
    module: str
    intents: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    pairs_with: list[str] = field(default_factory=list)
    install_default: str = ""
    install_methods: list[InstallMethod] = field(default_factory=list)
    usage_prompt: str = ""
    requires_download: dict[str, str] = field(default_factory=dict)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _parse_inline_list(line: str) -> list[str]:
    m = re.search(r"\[(.*)\]", line)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    return [_strip_quotes(x.strip()) for x in inner.split(",") if x.strip()]


def _parse_block_scalar(lines: list[str], start: int, base_indent: int) -> tuple[str, int]:
    parts: list[str] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            parts.append("")
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= base_indent and line.strip():
            break
        parts.append(line[base_indent + 2 :] if indent > base_indent else line.strip())
        i += 1
    text = "\n".join(parts).strip()
    return text, i


def _field(block: str, name: str, indent: int = 4) -> str:
    sp = " " * indent
    m = re.search(rf"^{sp}{re.escape(name)}:\s*(.*)$", block, re.MULTILINE)
    if not m:
        return ""
    val = m.group(1).strip()
    if val in (">-", "|"):
        parts: list[str] = []
        after = block[m.end() :]
        for ln in after.splitlines():
            if ln.startswith(sp + "  "):
                parts.append(ln[len(sp) + 2 :].strip())
            elif ln.strip() == "":
                continue
            else:
                break
        return " ".join(parts) if val == ">-" else "\n".join(parts).strip()
    return _strip_quotes(val)


def _list_field(block: str, name: str) -> list[str]:
    m = re.search(rf"^    {name}:\s*$", block, re.MULTILINE)
    if m:
        items: list[str] = []
        for ln in block[m.end() :].splitlines():
            if re.match(r"^\s{2,}- ", ln):
                items.append(_strip_quotes(ln.strip()[2:].strip()))
            elif ln.strip() and not ln.startswith(" "):
                break
            elif ln.strip() and re.match(r"^[a-z_]+:", ln):
                break
            elif ln.strip() and not ln.startswith("  "):
                break
        return items
    inline = _field(block, name)
    if inline.startswith("["):
        return _parse_inline_list(inline)
    return []


def _parse_methods(block: str) -> list[InstallMethod]:
    methods: list[InstallMethod] = []
    chunks = re.split(r"\n        - id: ", block)
    for chunk in chunks[1:]:
        mid = _strip_quotes(chunk.splitlines()[0].strip())
        body = "        - id: " + chunk
        methods.append(
            InstallMethod(
                id=mid,
                label=_field(body, "label", indent=10),
                type=_field(body, "type", indent=10),
                scope=_field(body, "scope", indent=10),
                command=_field(body, "command", indent=10),
                instructions=_field(body, "instructions", indent=10),
                agent=_field(body, "agent", indent=10),
            )
        )
    return methods


def load_registry(path: Path) -> tuple[list[Tool], dict[str, list[str]]]:
    text = path.read_text(encoding="utf-8")
    aliases: dict[str, list[str]] = {}
    alias_m = re.search(r"intent_aliases:\n(.*)$", text, re.DOTALL)
    if alias_m:
        for ln in alias_m.group(1).splitlines():
            if ":" not in ln or not ln.startswith("  "):
                continue
            key, rest = ln.split(":", 1)
            aliases[key.strip()] = _parse_inline_list(rest)

    tools: list[Tool] = []
    tool_chunks = re.split(r"\n  - id: ", text)
    for chunk in tool_chunks[1:]:
        if chunk.strip().startswith("intent_aliases"):
            break
        block = "  - id: " + chunk
        tid = _strip_quotes(chunk.splitlines()[0].strip())
        install_block = ""
        im = re.search(r"    install:\n(?:(?:      .+\n)*)", block)
        if im:
            install_block = im.group(0)

        req_dl: dict[str, str] = {}
        for rk in ("url", "hint"):
            rv = _field(install_block, rk, indent=8) if install_block else ""
            if rv:
                req_dl[rk] = rv

        tools.append(
            Tool(
                id=tid,
                name=_field(block, "name") or tid,
                summary=_field(block, "summary"),
                kb_id=_field(block, "kb_id"),
                note_path=_field(block, "note_path"),
                homepage=_field(block, "homepage"),
                module=_field(block, "module"),
                intents=_list_field(block, "intents"),
                keywords=_list_field(block, "keywords"),
                agents=_list_field(block, "agents"),
                pairs_with=_list_field(block, "pairs_with"),
                install_default=_field(install_block, "default_method", indent=6) if install_block else "",
                install_methods=_parse_methods(install_block) if install_block else [],
                usage_prompt=_field(block, "usage_prompt"),
                requires_download=req_dl,
            )
        )

    return tools, aliases


def _normalize(s: str) -> str:
    return s.lower().strip()


def _expand_query(query: str, aliases: dict[str, list[str]]) -> set[str]:
    q = _normalize(query)
    terms = {q, *q.split()}
    for alias, intents in aliases.items():
        if alias in q or q in alias:
            terms.update(intents)
    return terms


def _score_tool(tool: Tool, terms: set[str]) -> float:
    score = 0.0
    hay: list[tuple[str, float]] = []
    hay.append((_normalize(tool.name), 3.0))
    hay.append((_normalize(tool.id), 3.0))
    hay.append((_normalize(tool.summary), 1.0))
    for intent in tool.intents:
        hay.append((_normalize(intent), 2.5))
    for kw in tool.keywords:
        hay.append((_normalize(kw), 2.0))

    for term in terms:
        if not term:
            continue
        for text, weight in hay:
            if term == text:
                score += weight * 2
            elif term in text or text in term:
                score += weight
    return score


def search_tools(tools: list[Tool], query: str, aliases: dict[str, list[str]], limit: int = 10) -> list[tuple[Tool, float]]:
    terms = _expand_query(query, aliases)
    ranked = [(t, _score_tool(t, terms)) for t in tools]
    ranked = [(t, s) for t, s in ranked if s > 0]
    ranked.sort(key=lambda x: x[1], reverse=True)
    if not ranked and tools:
        # 无命中时返回全部工具供浏览
        return [(t, 0.0) for t in tools[:limit]]
    return ranked[:limit]


def _read_tldr(note_path: Path, max_lines: int = 3) -> list[str]:
    if not note_path.is_file():
        return []
    lines = note_path.read_text(encoding="utf-8").splitlines()
    in_tldr = False
    bullets: list[str] = []
    for line in lines:
        if line.strip() == "## TL;DR":
            in_tldr = True
            continue
        if in_tldr:
            if line.startswith("## "):
                break
            if line.startswith("- "):
                bullets.append(line[2:].strip())
                if len(bullets) >= max_lines:
                    break
    return bullets


def cmd_query(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    registry = kb_root / "knowledge/tools-registry.yaml"
    tools, aliases = load_registry(registry)
    results = search_tools(tools, args.query, aliases, args.limit)

    payload = []
    for tool, score in results:
        note = kb_root / tool.note_path
        payload.append(
            {
                "id": tool.id,
                "name": tool.name,
                "score": round(score, 2),
                "summary": tool.summary,
                "kb_id": tool.kb_id,
                "homepage": tool.homepage,
                "agents": tool.agents,
                "pairs_with": tool.pairs_with,
                "note_path": str(note),
                "tldr": _read_tldr(note),
                "install_methods": [
                    {"id": m.id, "label": m.label, "type": m.type, "scope": m.scope, "agent": m.agent}
                    for m in tool.install_methods
                ],
                "default_method": tool.install_default,
                "usage_prompt": tool.usage_prompt.strip(),
            }
        )

    if args.json:
        print(json.dumps({"query": args.query, "results": payload}, ensure_ascii=False, indent=2))
        return 0

    print(f"# 工具检索 · 「{args.query}」\n")
    if not payload:
        print("未找到匹配工具。请换关键词或浏览 docs/INDEX.md。")
        return 0

    for idx, item in enumerate(payload, 1):
        print(f"## {idx}. {item['name']} (`{item['id']}`)")
        print(f"- **匹配分**: {item['score']}")
        print(f"- **简介**: {item['summary']}")
        if item["tldr"]:
            print("- **笔记 TL;DR**:")
            for b in item["tldr"]:
                print(f"  - {b}")
        print(f"- **KB**: `{item['kb_id']}` · [笔记]({item['note_path']})")
        print(f"- **主页**: {item['homepage']}")
        print(f"- **支持 Agent**: {', '.join(item['agents'])}")
        if item["pairs_with"]:
            print(f"- **常搭配**: {', '.join(item['pairs_with'])}")
        print("- **安装方式**:")
        for m in item["install_methods"]:
            tag = "（默认）" if m["id"] == item.get("default_method") else ""
            print(f"  - `{m['id']}`: {m['label']} [{m['type']}, {m['scope']}] {tag}")
        print()
    print("---")
    print("选择后执行: `scripts/install-tool.sh <tool-id> --dry-run` 预览，确认后加 `--yes` 安装。")
    print("安装完成可将 usage_prompt 填入 Agent 任务。")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    registry = kb_root / "knowledge/tools-registry.yaml"
    tools, _ = load_registry(registry)
    tool = next((t for t in tools if t.id == args.tool_id), None)
    if not tool:
        print(f"❌ 未知工具 id: {args.tool_id}", file=sys.stderr)
        print("可用:", ", ".join(t.id for t in tools), file=sys.stderr)
        return 1

    method = next((m for m in tool.install_methods if m.id == args.method), None)
    if not method:
        method_id = args.method or tool.install_default
        method = next((m for m in tool.install_methods if m.id == method_id), None)
    if not method:
        print(f"❌ 未找到安装方法: {args.method or tool.install_default}", file=sys.stderr)
        return 1

    if args.agent and method.agent and method.agent != args.agent:
        alt = next((m for m in tool.install_methods if m.agent == args.agent), None)
        if alt:
            method = alt
        else:
            print(f"⚠️  方法 {method.id} 非 {args.agent} 专用，继续使用该方法", file=sys.stderr)

    target = Path(args.target).resolve()
    env = os.environ.copy()
    env["TARGET"] = str(target)
    env["HOME"] = str(Path.home())

    print(f"## 安装预览 · {tool.name} (`{tool.id}`)")
    print(f"- 方法: {method.label} (`{method.id}`)")
    print(f"- 类型: {method.type} · 作用域: {method.scope}")
    print(f"- 目标: {target}")
    if tool.requires_download:
        print(f"- ⚠️  需先下载: {tool.requires_download.get('url', '')}")
        print(f"  {tool.requires_download.get('hint', '')}")

    if method.type == "manual":
        print(f"\n### 手动步骤\n{method.instructions}\n")
        if tool.usage_prompt:
            print("### 安装后 Prompt 模板\n```")
            print(tool.usage_prompt.strip())
            print("```")
        return 0

    print(f"\n### 将执行命令\n```bash\n{method.command}\n```\n")

    if args.dry_run or not args.yes:
        print("（预览模式，未执行。确认后加 `--yes`）")
        return 0

    if tool.requires_download and not env.get("IMPECCABLE_DIST"):
        print("❌ 请先设置 IMPECCABLE_DIST 指向 impeccable ZIP 解压后的 dist 目录", file=sys.stderr)
        return 1

    proc = subprocess.run(method.command, shell=True, cwd=target, env=env)
    if proc.returncode != 0:
        print(f"❌ 安装命令失败 (exit {proc.returncode})", file=sys.stderr)
        return proc.returncode

    print(f"✅ 已安装 {tool.name} → {target}")
    if tool.usage_prompt:
        print("\n### 建议 Prompt（可发给 Agent）\n```")
        prompt = tool.usage_prompt.strip()
        if args.prompt:
            prompt = prompt.replace("{用户补充的场景描述}", args.prompt)
        print(prompt)
        print("```")
    return 0


def main() -> int:
    default_root = os.environ.get("AI_LEARNING_CENTER", "")
    if not default_root:
        default_root = str(Path(__file__).resolve().parent.parent)

    parser = argparse.ArgumentParser(description="AI 学习中心工具查询/安装")
    parser.add_argument("--kb-root", default=default_root)
    sub = parser.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="检索工具")
    q.add_argument("query", help="自然语言或关键词")
    q.add_argument("--limit", type=int, default=10)
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_query)

    ins = sub.add_parser("install", help="安装工具")
    ins.add_argument("tool_id")
    ins.add_argument("--method", default="")
    ins.add_argument("--agent", default="", choices=["", "cursor", "claude-code", "codex", "gemini-cli", "chatgpt"])
    ins.add_argument("--target", default=".")
    ins.add_argument("--prompt", default="", help="用户场景描述，填入 usage_prompt 模板")
    ins.add_argument("--dry-run", action="store_true", default=False)
    ins.add_argument("--yes", action="store_true")
    ins.set_defaults(func=cmd_install)

    args = parser.parse_args()
    if args.cmd == "install" and not args.yes:
        args.dry_run = True
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
