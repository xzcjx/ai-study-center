#!/usr/bin/env python3
"""AI 学习中心 · 工具查询、安装与工作流引擎（解析 registry YAML，无第三方依赖）。"""
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


CATALOG_INTENT_WORDS = ("汇总", "导航", "清单", "大全", "有哪些", "catalog", "awesome", "工具体系")

# 笔记表格工具名 → tools-registry id（可安装）
INSTALLABLE_NAME_MAP = {
    "taste skill": "taste-skill",
    "impeccable": "impeccable",
    "anthropic frontend design skill": "anthropic-frontend-design",
}

# H13b：仅解析「工具清单表」，跳过对比/实验/变更类表格
TOOL_TABLE_HEADER_CELLS = frozenset({"工具", "资源", "站点"})
SKIP_SECTION_KEYWORDS = ("矩阵", "对比", "选型", "实验", "症状", "变更", "控制变量", "拨盘", "Install name")
SKIP_ROW_NAMES = frozenset({
    "工具", "思路", "对比维度", "典型代表", "实验", "配色方案", "风格",
    "步骤", "动作", "效果", "维度", "实验 1 基础", "实验 2 +Skill",
    "---", "对比维度", "需求", "页面类型", "策略", "资源", "站点",
    "日期", "症状", "配色", "装饰", "布局", "气质", "上手难度",
    "结果可预期性", "工具切换", "适合页面", "与本库工具", "拨盘",
    "Install name", "多模态解析倾向", "零约束", "设计 Prompt", "纯截图",
    "语义结构（导航在哪、栅格关系）", "高频 UI 库默认样式「幻觉补偿」",
})
SKIP_SUMMARY_HEADERS = frozenset({
    "表现", "含义", "特点", "适合", "说明", "设定", "丢失项", "用途",
    "机制", "要点", "维度", "步骤", "效果", "动作", "对比维度", "最低", "高", "无", "—",
})
GENERIC_CATALOG_IDS = frozenset({"tool", "tool-2", "ui", "prompt", "install-name"})


def _is_catalog_intent(query: str) -> bool:
    q = query.lower()
    return any(w in q for w in CATALOG_INTENT_WORDS)


def _score_note_for_query(fm: dict[str, Any], text: str, query: str) -> float:
    q = query.lower()
    score = 0.0
    title = fm.get("title", "").lower()
    tags = [t.lower() for t in fm.get("tags", [])]
    if "awesome-list" in tags and _is_catalog_intent(query):
        score += 20.0
    if "frontend-design" in tags:
        score += 5.0
    for term in q.split():
        if term and term in title:
            score += 4.0
        if term in tags:
            score += 3.0
        if term in text.lower():
            score += 0.5
    if "汇总" in q or "导航" in q:
        if "导航" in title or "汇总" in title or "awesome" in tags:
            score += 15.0
    return score


def _search_notes(kb_root: Path, query: str, limit: int = 8) -> list[tuple[Path, dict[str, Any], float]]:
    hits: list[tuple[Path, dict[str, Any], float]] = []
    notes_dir = kb_root / "notes"
    if not notes_dir.is_dir():
        return hits
    for note_path in notes_dir.rglob("*.md"):
        fm = _parse_note_frontmatter(note_path)
        if not fm:
            continue
        text = note_path.read_text(encoding="utf-8")
        score = _score_note_for_query(fm, text, query)
        if score > 0:
            hits.append((note_path, fm, score))
    hits.sort(key=lambda x: x[2], reverse=True)
    return hits[:limit]


def _extract_link_name_url(cell: str) -> tuple[str, str]:
    m = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", cell)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return cell.strip(), ""


def _extract_catalog_entries(note_path: Path) -> list[dict[str, str]]:
    text = note_path.read_text(encoding="utf-8")
    entries: list[dict[str, str]] = []
    current_category = "其他"
    skip_section = False
    in_tool_table = False

    for line in text.splitlines():
        if line.startswith("### "):
            sec = line[4:].strip()
            skip_section = any(kw in sec for kw in SKIP_SECTION_KEYWORDS)
            in_tool_table = False
            if "Skills" in sec or "技能" in sec:
                current_category = "Skills"
            elif "Apps" in sec or "应用" in sec:
                current_category = "Apps"
            elif "MCP" in sec:
                current_category = "MCP"
            elif "Design Tools" in sec:
                current_category = "Design Tools"
            elif "Resources" in sec:
                current_category = "Resources"
            elif "方法" in sec:
                current_category = "方法论"
            elif any(k in sec for k in ("工具箱", "Prompt", "截图", "灵感", "三件套")):
                current_category = "Resources"
            continue

        if skip_section:
            continue

        if re.match(r"^\|\s*-+\s*\|", line):
            continue

        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            in_tool_table = False
            continue

        first, summary = cells[0], cells[1]
        if first in TOOL_TABLE_HEADER_CELLS:
            in_tool_table = True
            continue

        link_name, homepage = _extract_link_name_url(first)
        has_http_link = bool(homepage)

        if not has_http_link and not in_tool_table:
            continue

        name = link_name.replace("⭐️", "").strip()
        if not name or name.startswith("---") or len(name) > 80:
            continue
        if name in SKIP_ROW_NAMES or summary in SKIP_SUMMARY_HEADERS:
            continue
        if summary.startswith("---"):
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}$", name):
            continue
        if name.startswith("喂") and current_category == "其他":
            continue
        if name.startswith("实验") or name.startswith("方法"):
            continue
        if not has_http_link and (len(summary) < 6 or name.startswith("`")):
            continue

        installable = INSTALLABLE_NAME_MAP.get(name.lower().replace(".style", "").strip())
        if not installable:
            for key, tid in INSTALLABLE_NAME_MAP.items():
                if key in name.lower():
                    installable = tid
                    break

        entries.append(
            {
                "category": current_category,
                "name": name,
                "summary": summary[:120],
                "starred": "⭐️" in first,
                "installable_id": installable or "",
                "homepage": homepage,
            }
        )
    return entries


def load_tools_catalog(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    if not path.is_file():
        return [], {}, {}
    text = path.read_text(encoding="utf-8")
    categories: dict[str, str] = {}
    cat_m = re.search(r"categories:\n(.*?)\nentries:", text, re.DOTALL)
    if cat_m:
        for ln in cat_m.group(1).splitlines():
            if ":" in ln and ln.startswith("  "):
                k, v = ln.split(":", 1)
                categories[k.strip()] = _strip_quotes(v.strip())

    filters: dict[str, dict[str, Any]] = {}
    filt_m = re.search(r"catalog_filters:\n(.*)$", text, re.DOTALL)
    if filt_m:
        for alias, body in re.findall(r"^  ([^:]+):\s*\{([^}]+)\}", filt_m.group(1), re.MULTILINE):
            f: dict[str, Any] = {}
            cm = re.search(r"categories:\s*\[([^\]]+)\]", body)
            if cm:
                f["categories"] = _parse_inline_list("[" + cm.group(1) + "]")
            tm = re.search(r"tags_any:\s*\[([^\]]+)\]", body)
            if tm:
                f["tags_any"] = _parse_inline_list("[" + tm.group(1) + "]")
            filters[alias.strip()] = f

    entries: list[dict[str, Any]] = []
    ent_section = re.search(r"entries:\n(.*?)(\ncatalog_filters:|\Z)", text, re.DOTALL)
    if not ent_section:
        return entries, categories, filters
    ent_body = ent_section.group(1).strip()
    for chunk in re.split(r"\n  - id: ", "\n  - id: " + ent_body):
        if not chunk.strip() or chunk.strip().startswith("#"):
            continue
        block = "  - id: " + chunk
        eid = _yaml_item_id(chunk)
        entries.append(
            {
                "id": eid,
                "name": _field(block, "name"),
                "category": _field(block, "category"),
                "positioning": _field(block, "positioning"),
                "summary": _field(block, "summary"),
                "tags": _list_field(block, "tags"),
                "homepage": _field(block, "homepage"),
                "installable": _field(block, "installable") == "true",
                "registry_id": _field(block, "registry_id"),
                "kb_notes": _list_field(block, "kb_notes"),
                "starred": _field(block, "starred") == "true",
            }
        )
    return entries, categories, filters


def _score_catalog_entry(entry: dict[str, Any], query: str, cat_filter: dict[str, Any] | None) -> float:
    score = 0.0
    q = query.lower()
    hay = [
        (entry.get("name", "").lower(), 4.0),
        (entry.get("id", "").lower(), 3.0),
        (entry.get("positioning", "").lower(), 2.0),
        (entry.get("summary", "").lower(), 1.0),
        (entry.get("category", "").lower(), 1.5),
    ]
    for tag in entry.get("tags", []):
        hay.append((tag.lower(), 2.0))
    for term in q.split():
        if not term:
            continue
        for text, weight in hay:
            if term == text or term in text:
                score += weight
    if entry.get("starred"):
        score += 1.0
    if cat_filter:
        cats = cat_filter.get("categories")
        if cats and entry.get("category") not in cats:
            return 0.0
        tags_any = cat_filter.get("tags_any", [])
        if tags_any and any(t in entry.get("tags", []) for t in tags_any):
            score += 3.0
        if score == 0 and cats:
            score = 0.5
    if _is_catalog_intent(query) and score == 0:
        score = 0.3
    return score


def _resolve_catalog_filter(query: str, filters: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    q = query.lower().strip()
    for alias, f in filters.items():
        if alias.lower() in q or q in alias.lower():
            return f
    if _is_catalog_intent(q):
        return filters.get("前端工具汇总")
    return None


def _build_catalog_payload(kb_root: Path, query: str, tools: list[Tool]) -> dict[str, Any]:
    catalog_entries, categories, cat_filters = load_tools_catalog(kb_root / "knowledge/tools-catalog.yaml")
    cat_filter = _resolve_catalog_filter(query, cat_filters)

    ranked: list[tuple[dict[str, Any], float]] = []
    for entry in catalog_entries:
        s = _score_catalog_entry(entry, query, cat_filter)
        if s > 0:
            ranked.append((entry, s))
    ranked.sort(key=lambda x: x[1], reverse=True)
    if not ranked and catalog_entries:
        ranked = [(e, 0.1) for e in catalog_entries]

    installable_list: list[dict[str, Any]] = []
    reference_list: list[dict[str, Any]] = []
    for entry, score in ranked:
        item = {**entry, "score": round(score, 2)}
        if entry.get("installable") and entry.get("registry_id"):
            t = next((x for x in tools if x.id == entry["registry_id"]), None)
            item["registry"] = entry["registry_id"]
            item["has_install"] = True
            if t and not item.get("homepage"):
                item["homepage"] = t.homepage
            installable_list.append(item)
        else:
            item["has_install"] = False
            reference_list.append(item)

    note_hits = _search_notes(kb_root, query)[:5]
    sources = [
        {
            "note_path": str(p.relative_to(kb_root)),
            "title": fm.get("title", ""),
            "kb_id": fm.get("id", ""),
            "score": round(sc, 2),
            "tldr": _read_tldr(p, 2),
        }
        for p, fm, sc in note_hits
    ]

    return {
        "query": query,
        "catalog_mode": True,
        "catalog_ssot": "knowledge/tools-catalog.yaml",
        "categories": categories,
        "sources": sources,
        "installable_catalog": installable_list,
        "reference_catalog": reference_list,
        "total_tools": len(ranked),
    }


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


def _print_catalog_report(catalog: dict[str, Any], installable_payload: list[dict[str, Any]]) -> None:
    print(f"# 工具汇总 · 「{catalog['query']}」\n")
    print(f"> SSOT: `{catalog.get('catalog_ssot', 'knowledge/tools-catalog.yaml')}`")
    print(f"> 共 **{catalog['total_tools']}** 项 · **可安装 {len(catalog['installable_catalog'])}** · **参考 {len(catalog['reference_catalog'])}**\n")

    if installable_payload:
        print("## 可安装（`/kb-install`）\n")
        print("| # | 工具 | 定位 | 安装 id | 分 |")
        print("|---|------|------|---------|-----|")
        for idx, item in enumerate(installable_payload, 1):
            print(f"| {idx} | {item['name']} | {item.get('positioning', '')[:24]} | `{item['id']}` | {item['score']} |")
        print()

    if catalog["reference_catalog"] or catalog["installable_catalog"]:
        print("## 工具总表\n")
        print("| 分类 | 工具 | 定位 | 标签 | 链接 |")
        print("|------|------|------|------|------|")
        for e in catalog["installable_catalog"] + catalog["reference_catalog"]:
            star = "⭐️ " if e.get("starred") else ""
            tags = ", ".join(e.get("tags", [])[:4])
            home = e.get("homepage", "")
            link = f"[主页]({home})" if home else "—"
            install = f" `/kb-install {e['registry_id']}`" if e.get("installable") else ""
            print(f"| {e.get('category', '')} | {star}{e['name']}{install} | {e.get('positioning', '')[:28]} | `{tags}` | {link} |")
        print()

    if catalog["sources"]:
        print("## 关联笔记（深度阅读）\n")
        for s in catalog["sources"][:4]:
            print(f"- [{s['title']}]({s['note_path']}) (`{s['kb_id']}`)")
        print()

    print("---")
    print("编辑总表: `knowledge/tools-catalog.yaml`")
    print("安装: `install-tool.sh <registry_id> --target .`")
    print("方法论: `kb-workflow.sh \"开发前端界面\" --target .`")
    print("入库新工具: `/ingest` → H13b 自动补充总表")


def cmd_query(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    registry = kb_root / "knowledge/tools-registry.yaml"
    tools, aliases = load_registry(registry)
    catalog_mode = _is_catalog_intent(args.query) or "awesome-list" in _expand_query(args.query, aliases)
    results = search_tools(tools, args.query, aliases, args.limit if not catalog_mode else max(args.limit, 10))

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

    catalog = _build_catalog_payload(kb_root, args.query, tools) if catalog_mode else None

    if args.json:
        out: dict[str, Any] = {"query": args.query, "installable_results": payload}
        if catalog:
            out["catalog"] = catalog
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if catalog_mode and catalog and (catalog["total_tools"] > 0 or catalog["sources"]):
        _print_catalog_report(catalog, payload)
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


# --- 工作流（workflows-registry.yaml）---


def _yaml_item_id(chunk: str) -> str:
    first = chunk.splitlines()[0].strip()
    first = re.sub(r"^- id:\s*", "", first)
    return _strip_quotes(first)


def _yaml_scalar_list(block: str, key: str, indent: int = 6, stop_keys: list[str] | None = None) -> list[str]:
    sp = " " * indent
    m = re.search(rf"^{sp}{re.escape(key)}:\s*$", block, re.MULTILINE)
    if not m:
        inline = re.search(rf"^{sp}{re.escape(key)}:\s*(.+)$", block, re.MULTILINE)
        if inline and inline.group(1).strip().startswith("["):
            return _parse_inline_list(inline.group(1))
        return []
    items: list[str] = []
    item_re = re.compile(rf"^{re.escape(sp)}  - (.+)$")
    stop_res = [re.compile(rf"^{re.escape(sp)}{re.escape(k)}:") for k in (stop_keys or [])]
    for ln in block[m.end() :].splitlines():
        if any(sr.match(ln) for sr in stop_res):
            break
        im = item_re.match(ln)
        if im:
            items.append(_strip_quotes(im.group(1).strip()))
        elif ln.strip() and not ln.startswith(sp):
            break
    return items


def _parse_phases(workflow_block: str) -> list[dict[str, Any]]:
    phases: list[dict[str, Any]] = []
    chunks = re.split(r"\n      - id: ", workflow_block)
    for chunk in chunks[1:]:
        pid = _strip_quotes(chunk.splitlines()[0].strip())
        body = "      - id: " + chunk
        phase: dict[str, Any] = {
            "id": pid,
            "name": _field(body, "name", indent=8),
            "gate": _field(body, "gate", indent=8) or "must_pass",
            "instructions": _field(body, "instructions", indent=8),
            "prompt": _field(body, "prompt", indent=8),
            "checklist": _yaml_scalar_list(body, "checklist", indent=8),
            "tool_refs": [],
            "resources": [],
        }
        tr_m = re.search(r"        tool_refs:\n((?:          .+\n)*)", body)
        if tr_m:
            for ref_chunk in re.split(r"\n          - id: ", tr_m.group(1))[1:]:
                ref_body = "          - id: " + ref_chunk
                phase["tool_refs"].append(
                    {
                        "id": _strip_quotes(ref_chunk.splitlines()[0].strip()),
                        "required": _field(ref_body, "required", indent=12) == "true",
                        "default_method": _field(ref_body, "default_method", indent=12),
                        "when": _field(ref_body, "when", indent=12),
                    }
                )
        rs_m = re.search(r"        resources:\n((?:          .+\n)*)", body)
        if rs_m:
            for rchunk in re.split(r"\n          - id: ", rs_m.group(1))[1:]:
                rbody = "          - id: " + rchunk
                phase["resources"].append(
                    {
                        "id": _strip_quotes(rchunk.splitlines()[0].strip()),
                        "name": _field(rbody, "name", indent=12),
                        "url": _field(rbody, "url", indent=12),
                        "type": _field(rbody, "type", indent=12),
                    }
                )
        phases.append(phase)
    return phases


def load_workflows(path: Path, kb_root: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    aliases: dict[str, str] = {}
    am = re.search(r"workflow_aliases:\n(.*)$", text, re.DOTALL)
    if am:
        for ln in am.group(1).splitlines():
            if ":" not in ln or not ln.startswith("  "):
                continue
            key, rest = ln.split(":", 1)
            aliases[key.strip()] = _strip_quotes(rest.strip())

    routers: list[dict[str, Any]] = []
    router_section = re.search(r"routers:\n(.*?)\nworkflows:", text, re.DOTALL)
    if router_section:
        router_body = router_section.group(1).strip()
        for rchunk in re.split(r"\n  - id: ", "\n  - id: " + router_body):
            if not rchunk.strip():
                continue
            rbody = "  - id: " + rchunk
            rid = _yaml_item_id(rchunk)
            routes: list[dict[str, Any]] = []
            for match_raw, wf_id in re.findall(
                r"- match:\s*\[(.*?)\]\s*\n\s*workflow:\s*(\S+)", rbody, re.DOTALL
            ):
                routes.append(
                    {
                        "match": [_strip_quotes(x.strip()) for x in match_raw.split(",") if x.strip()],
                        "workflow": wf_id.strip(),
                    }
                )
            routers.append(
                {
                    "id": rid,
                    "triggers": _yaml_scalar_list(rbody, "triggers", indent=4, stop_keys=["routes", "default"]),
                    "routes": routes,
                    "default": _field(rbody, "default", indent=4),
                }
            )

    workflows: list[dict[str, Any]] = []
    wf_section = re.search(r"workflows:\n(.*?)(\nworkflow_aliases:|\Z)", text, re.DOTALL)
    if wf_section:
        wf_body = wf_section.group(1).strip()
        for wchunk in re.split(r"\n  - id: ", "\n  - id: " + wf_body):
            if not wchunk.strip():
                continue
            wbody = "  - id: " + wchunk
            wid = _yaml_item_id(wchunk)
            wf_resources: list[dict[str, Any]] = []
            wr_m = re.search(r"^    resources:\n((?:      .+\n)*)", wbody, re.MULTILINE)
            if wr_m:
                for rchunk in re.split(r"\n      - id: ", wr_m.group(1))[1:]:
                    rbody = "      - id: " + rchunk
                    wf_resources.append(
                        {
                            "id": _strip_quotes(rchunk.splitlines()[0].strip()),
                            "name": _field(rbody, "name", indent=8),
                            "url": _field(rbody, "url", indent=8),
                            "type": _field(rbody, "type", indent=8),
                        }
                    )
            workflows.append(
                {
                    "id": wid,
                    "name": _field(wbody, "name"),
                    "version": _field(wbody, "version"),
                    "summary": _field(wbody, "summary"),
                    "playbook_notes": _yaml_scalar_list(wbody, "playbook_notes"),
                    "triggers": {
                        "keywords": _yaml_scalar_list(wbody, "keywords", indent=6),
                        "intents": _yaml_scalar_list(wbody, "intents", indent=6),
                    },
                    "resources": wf_resources,
                    "phases": _parse_phases(wbody),
                }
            )

    if kb_root is not None:
        overlay = _load_sync_overlay(kb_root / "knowledge/workflow-ingest-sync.yaml")
        workflows, routers = _merge_workflow_overlay(workflows, routers, overlay)

    return workflows, routers, aliases


def _parse_note_frontmatter(note_path: Path) -> dict[str, Any]:
    text = note_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    fm: dict[str, Any] = {}
    for key in ("id", "module", "module_id", "title", "ingest_id", "updated", "difficulty", "status"):
        val = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
        if val:
            fm[key] = _strip_quotes(val.group(1).strip())
    tags_m = re.search(r"^tags:\s*\[(.*)\]", block, re.MULTILINE)
    if tags_m:
        fm["tags"] = _parse_inline_list("[" + tags_m.group(1) + "]")
    else:
        fm["tags"] = _yaml_scalar_list(block, "tags", indent=0) or []
    return fm


def _load_sync_rules(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    rules: dict[str, Any] = {"tag_to_workflows": {}, "intent_to_tool_refs": {}, "module_default_workflows": {}, "title_keywords_to_router": []}
    ttw_m = re.search(r"tag_to_workflows:\n(.*?)(\n\w|\Z)", text, re.DOTALL)
    if ttw_m:
        for ln in ttw_m.group(1).splitlines():
            if ":" not in ln or not ln.startswith("  "):
                continue
            tag, rest = ln.split(":", 1)
            rules["tag_to_workflows"][tag.strip()] = _parse_inline_list(rest)
    itr_m = re.search(r"intent_to_tool_refs:\n(.*?)(\nmodule_default|\Z)", text, re.DOTALL)
    if itr_m:
        for intent, body in re.findall(r"^  (\S+):\n((?:    - .+\n)*)", itr_m.group(1), re.MULTILINE):
            entries: list[dict[str, str]] = []
            for chunk in re.split(r"\n    - ", body.strip()):
                if not chunk.strip():
                    continue
                cb = "    - " + chunk if not chunk.startswith("{") else chunk
                wf = re.search(r"workflow:\s*(\S+)", chunk)
                ph = re.search(r"phase:\s*(\S+)", chunk)
                req = re.search(r"required:\s*(\S+)", chunk)
                if wf and ph:
                    entries.append({"workflow": wf.group(1), "phase": ph.group(1), "required": req.group(1) if req else "false"})
            rules["intent_to_tool_refs"][intent] = entries
    mdw_m = re.search(r"module_default_workflows:\n(.*?)(\ntitle_keywords|\Z)", text, re.DOTALL)
    if mdw_m:
        for ln in mdw_m.group(1).splitlines():
            if ":" not in ln or not ln.startswith("  "):
                continue
            mod, rest = ln.split(":", 1)
            rules["module_default_workflows"][mod.strip()] = _parse_inline_list(rest)
    tkr_m = re.search(r"title_keywords_to_router:\n(.*?)(\Z)", text, re.DOTALL)
    if tkr_m:
        rules["title_keywords_to_router"] = _yaml_scalar_list("title_keywords_to_router:\n" + tkr_m.group(1), "title_keywords_to_router", indent=0)
        if not rules["title_keywords_to_router"]:
            for ln in tkr_m.group(1).splitlines():
                if ln.strip().startswith("- "):
                    rules["title_keywords_to_router"].append(_strip_quotes(ln.strip()[2:]))
    return rules


def _load_sync_overlay(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    overlay: dict[str, Any] = {"playbook_notes": {}, "keywords": {}, "tool_refs": {}, "router_triggers": {}, "sync_log": []}
    for section, key in (("playbook_notes", "playbook_notes"), ("keywords", "keywords")):
        sm = re.search(rf"^{section}:\n(.*?)(\n\w|\Z)", text, re.MULTILINE | re.DOTALL)
        if not sm or sm.group(1).strip() in ("{}", ""):
            continue
        for wf_chunk in re.split(r"\n  (\S+):", "\n" + sm.group(1).strip()):
            if not wf_chunk.strip() or ":" in wf_chunk[:20]:
                continue
        # playbook_notes / keywords: `  wf_id:\n    - item`
        for wf_id, block in re.findall(r"^  (\S+):\n((?:    - .+\n)*)", sm.group(1), re.MULTILINE):
            items = [re.sub(r"^\s*-\s*", "", ln).strip() for ln in block.splitlines() if ln.strip().startswith("-")]
            overlay[key][wf_id] = [_strip_quotes(x) for x in items]
    tr_m = re.search(r"^tool_refs:\n(.*?)(\nrouter_triggers:|\nsync_log:|\Z)", text, re.MULTILINE | re.DOTALL)
    if tr_m and tr_m.group(1).strip() not in ("{}", ""):
        for wf_id, wf_block in re.findall(r"^  (\S+):\n((?:    .+\n)*)", tr_m.group(1), re.MULTILINE):
            overlay["tool_refs"][wf_id] = {}
            for phase_id, phase_block in re.findall(r"^    (\S+):\n((?:      - .+\n)*)", wf_block, re.MULTILINE):
                refs: list[dict[str, Any]] = []
                for ref_chunk in re.split(r"\n      - id: ", phase_block)[1:]:
                    rid = _strip_quotes(ref_chunk.splitlines()[0].strip())
                    rb = "      - id: " + ref_chunk
                    refs.append({
                        "id": rid,
                        "required": _field(rb, "required", indent=8) == "true",
                        "default_method": _field(rb, "default_method", indent=8),
                        "when": _field(rb, "when", indent=8),
                    })
                overlay["tool_refs"][wf_id][phase_id] = refs
    rt_m = re.search(r"^router_triggers:\n(.*?)(\nsync_log:|\Z)", text, re.MULTILINE | re.DOTALL)
    if rt_m and rt_m.group(1).strip() not in ("{}", ""):
        for rid, block in re.findall(r"^  (\S+):\n((?:    - .+\n)*)", rt_m.group(1), re.MULTILINE):
            overlay["router_triggers"][rid] = [_strip_quotes(ln.strip()[2:]) for ln in block.splitlines() if ln.strip().startswith("-")]
    return overlay


def _merge_workflow_overlay(
    workflows: list[dict[str, Any]],
    routers: list[dict[str, Any]],
    overlay: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    wf_map = {w["id"]: w for w in workflows}
    for wf_id, notes in overlay.get("playbook_notes", {}).items():
        if wf_id not in wf_map:
            continue
        existing = wf_map[wf_id].setdefault("playbook_notes", [])
        for n in notes:
            if n not in existing:
                existing.append(n)
    for wf_id, kws in overlay.get("keywords", {}).items():
        if wf_id not in wf_map:
            continue
        trig = wf_map[wf_id].setdefault("triggers", {"keywords": [], "intents": []})
        for kw in kws:
            if kw not in trig["keywords"]:
                trig["keywords"].append(kw)
    for wf_id, phases_map in overlay.get("tool_refs", {}).items():
        if wf_id not in wf_map:
            continue
        for phase in wf_map[wf_id].get("phases", []):
            extra = phases_map.get(phase["id"], [])
            if not extra:
                continue
            existing_ids = {r["id"] for r in phase.get("tool_refs", [])}
            for ref in extra:
                if ref["id"] not in existing_ids:
                    phase.setdefault("tool_refs", []).append(ref)
                    existing_ids.add(ref["id"])
    for router in routers:
        extra = overlay.get("router_triggers", {}).get(router["id"], [])
        for t in extra:
            if t not in router["triggers"]:
                router["triggers"].append(t)
    return workflows, routers


def _uniq_append(lst: list[Any], item: Any) -> None:
    if item not in lst:
        lst.append(item)


def _write_sync_overlay(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 入库自动同步层（H13 产出，与 workflows-registry.yaml 合并后供 kb-workflow 使用）",
        "# 由 scripts/sync-workflow.sh 维护",
        "",
        'version: "1.0"',
        f"last_ingest_id: {json.dumps(data.get('last_ingest_id'), ensure_ascii=False)}",
        "",
        "playbook_notes:",
    ]
    pb = data.get("playbook_notes") or {}
    if not pb:
        lines.append("  {}")
    else:
        for wf_id in sorted(pb):
            lines.append(f"  {wf_id}:")
            for note in pb[wf_id]:
                lines.append(f"    - {note}")
    lines.append("")
    lines.append("keywords:")
    kws = data.get("keywords") or {}
    if not kws:
        lines.append("  {}")
    else:
        for wf_id in sorted(kws):
            lines.append(f"  {wf_id}:")
            for kw in kws[wf_id]:
                lines.append(f"    - {kw}")
    lines.append("")
    lines.append("tool_refs:")
    tr = data.get("tool_refs") or {}
    if not tr:
        lines.append("  {}")
    else:
        for wf_id in sorted(tr):
            lines.append(f"  {wf_id}:")
            for phase_id in sorted(tr[wf_id]):
                lines.append(f"    {phase_id}:")
                for ref in tr[wf_id][phase_id]:
                    lines.append(f"      - id: {ref['id']}")
                    lines.append(f"        required: {str(ref.get('required', False)).lower()}")
                    if ref.get("default_method"):
                        lines.append(f"        default_method: {ref['default_method']}")
    lines.append("")
    lines.append("router_triggers:")
    rt = data.get("router_triggers") or {}
    if not rt:
        lines.append("  {}")
    else:
        for rid in sorted(rt):
            lines.append(f"  {rid}:")
            for t in rt[rid]:
                lines.append(f"    - {t}")
    lines.append("")
    lines.append("sync_log:")
    for entry in data.get("sync_log", [])[-30:]:
        lines.append(f"  - ingest_id: {entry.get('ingest_id')}")
        lines.append(f"    note: {entry.get('note')}")
        lines.append(f"    kb_id: {entry.get('kb_id')}")
        lines.append(f"    workflows: {json.dumps(entry.get('workflows', []), ensure_ascii=False)}")
        lines.append(f"    at: {entry.get('at')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_workflows_for_note(fm: dict[str, Any], rules: dict[str, Any], tool: Tool | None) -> set[str]:
    targets: set[str] = set()
    tags = [t.lower() for t in fm.get("tags", [])]
    for tag in tags:
        for wf_id in rules.get("tag_to_workflows", {}).get(tag, []):
            targets.add(wf_id)
    if not targets:
        mod = fm.get("module", "")
        for wf_id in rules.get("module_default_workflows", {}).get(mod, []):
            targets.add(wf_id)
    if not targets:
        targets.add("fe-full-pipeline")
    return targets


def _slugify_tool_id(name: str) -> str:
    s = name.lower().replace(".style", "").strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "tool"


def _append_catalog_entries_to_yaml(catalog_path: Path, new_entries: list[dict[str, Any]]) -> int:
    if not new_entries:
        return 0
    text = catalog_path.read_text(encoding="utf-8")
    insert_at = text.find("\ncatalog_filters:")
    if insert_at < 0:
        insert_at = len(text)
    blocks: list[str] = []
    for e in new_entries:
        blocks.append(
            "\n".join(
                [
                    f"  - id: {e['id']}",
                    f"    name: {e['name']}",
                    f"    category: {e.get('category', 'resources')}",
                    f"    positioning: {e.get('positioning', '待补充')}",
                    f"    summary: {e.get('summary', '')}",
                    f"    tags: [{', '.join(e.get('tags', []))}]" if e.get("tags") else "    tags: []",
                    f"    homepage: {e.get('homepage', '')}",
                    "    installable: false",
                    f"    kb_notes: [{e.get('kb_note', '')}]",
                    f"    ingest_ids: [{e.get('ingest_id', '')}]",
                ]
            )
        )
    addition = "\n".join(blocks) + "\n"
    catalog_path.write_text(text[:insert_at] + addition + text[insert_at:], encoding="utf-8")
    return len(new_entries)


def validate_catalog_file(catalog_path: Path, baseline_path: Path | None = None) -> tuple[bool, list[str]]:
    """H13b 质量门禁：校验 tools-catalog.yaml 结构与增量条目。"""
    errors: list[str] = []
    if not catalog_path.is_file():
        errors.append(f"文件不存在: {catalog_path}")
        return False, errors

    text = catalog_path.read_text(encoding="utf-8")

    if re.search(r"catalog_filters:\s+- id:", text):
        errors.append("catalog_filters 区块被 entries 污染（YAML 结构损坏）")
    if "catalog_filters:" not in text:
        errors.append("缺少 catalog_filters 区块")
    elif "\ncatalog_filters:\n" not in text:
        errors.append("catalog_filters 未独立成行（可能与 entries 粘连）")

    entries, _, filters = load_tools_catalog(catalog_path)
    if not filters and "catalog_filters:" in text:
        errors.append("catalog_filters 解析为空，YAML 可能已损坏")

    ids = [e["id"] for e in entries if e.get("id")]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"重复 id: {dupes}")

    baseline_ids: set[str] = set()
    if baseline_path and baseline_path.is_file():
        baseline_entries, _, _ = load_tools_catalog(baseline_path)
        baseline_ids = {e["id"] for e in baseline_entries if e.get("id")}

    new_entries = [e for e in entries if e.get("id") not in baseline_ids]
    draft_new = [e for e in new_entries if "待补充（H13b 自动入库）" in e.get("positioning", "")]

    if len(draft_new) > 8:
        errors.append(
            f"单次 sync 新增 {len(draft_new)} 条 H13b 草稿，超过阈值 8，疑似 Markdown 表格误解析"
        )

    for e in draft_new:
        name = e.get("name", "")
        eid = e.get("id", "")
        if eid in GENERIC_CATALOG_IDS:
            errors.append(f"可疑草稿 id `{eid}`（名称: {name}）")
        if name in SKIP_ROW_NAMES:
            errors.append(f"可疑草稿名称 `{name}`（像表格表头/对比维度行）")
        if name.startswith("`") and name.endswith("`"):
            errors.append(f"可疑草稿名称 `{name}`（像 Skill 参数名而非工具）")

    return len(errors) == 0, errors


def cmd_validate_catalog(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    catalog_path = kb_root / "knowledge/tools-catalog.yaml"
    baseline = Path(args.baseline) if args.baseline else None
    ok, errors = validate_catalog_file(catalog_path, baseline)
    if ok:
        print(f"✅ catalog 校验通过: {catalog_path.relative_to(kb_root)}")
        if baseline:
            print(f"   baseline: {baseline}")
        return 0
    print(f"❌ catalog 校验失败: {catalog_path.relative_to(kb_root)}", file=sys.stderr)
    for err in errors:
        print(f"   - {err}", file=sys.stderr)
    print("\n修复：手改 tools-catalog.yaml 或修正笔记工具表格后重跑 sync-catalog。", file=sys.stderr)
    return 1


def cmd_sync_catalog(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    ingest_id = args.ingest_id
    catalog_path = kb_root / "knowledge/tools-catalog.yaml"
    entries, _, _ = load_tools_catalog(catalog_path)
    tools, _ = load_registry(kb_root / "knowledge/tools-registry.yaml")
    tool_by_kb = {t.kb_id: t for t in tools}
    known_ids = {e["id"] for e in entries}
    known_names = {e["name"].lower() for e in entries}
    updated_notes = 0
    appended: list[dict[str, Any]] = []

    for raw in args.notes:
        note_path = Path(raw)
        if not note_path.is_file():
            continue
        rel = str(note_path.relative_to(kb_root)) if note_path.is_relative_to(kb_root) else str(note_path)
        fm = _parse_note_frontmatter(note_path)
        kb_id = fm.get("id", "")

        if kb_id in tool_by_kb:
            tid = tool_by_kb[kb_id].id
            for e in entries:
                if e.get("registry_id") == tid or e["id"] == tid:
                    if rel not in e.get("kb_notes", []):
                        e.setdefault("kb_notes", []).append(rel)
                        updated_notes += 1

        cat_map = {"Skills": "skills", "Apps": "apps", "MCP": "mcp", "Design Tools": "design-tools", "Resources": "resources"}
        for row in _extract_catalog_entries(note_path):
            name = row["name"]
            if name.lower() in known_names:
                continue
            eid = _slugify_tool_id(name)
            if eid in known_ids:
                eid = f"{eid}-2"
            appended.append(
                {
                    "id": eid,
                    "name": name,
                    "category": cat_map.get(row.get("category", ""), "resources"),
                    "positioning": "待补充（H13b 自动入库）",
                    "summary": row.get("summary", "")[:200],
                    "tags": fm.get("tags", [])[:5],
                    "homepage": row.get("homepage", ""),
                    "kb_note": rel,
                    "ingest_id": ingest_id,
                }
            )
            known_names.add(name.lower())
            known_ids.add(eid)

    added = _append_catalog_entries_to_yaml(catalog_path, appended)

    print(f"## H13b SyncCatalog · {ingest_id}\n")
    print(f"- 总表路径: `{catalog_path.relative_to(kb_root)}`")
    print(f"- 新增条目: **{added}**")
    print(f"- 关联笔记更新: **{updated_notes}**（需手改总表 kb_notes 或下次全量编辑）")
    if appended:
        for a in appended:
            print(f"  - `{a['id']}` — {a['name']}")
    print(f"\n验证: `query-tools.sh \"前端工具汇总\"`")
    return 0


def cmd_sync_workflow(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    ingest_id = args.ingest_id
    note_paths = [Path(p) for p in args.notes]
    rules = _load_sync_rules(kb_root / "knowledge/workflow-sync-rules.yaml")
    tools, _ = load_registry(kb_root / "knowledge/tools-registry.yaml")
    tool_by_kb = {t.kb_id: t for t in tools}
    sync_path = kb_root / "knowledge/workflow-ingest-sync.yaml"
    overlay = _load_sync_overlay(sync_path)
    if not overlay.get("playbook_notes"):
        overlay = {"playbook_notes": {}, "keywords": {}, "tool_refs": {}, "router_triggers": {}, "sync_log": []}

    report_entries: list[dict[str, Any]] = []

    for note_path in note_paths:
        if not note_path.is_file():
            print(f"⚠️  跳过不存在: {note_path}", file=sys.stderr)
            continue
        rel = str(note_path.relative_to(kb_root)) if note_path.is_relative_to(kb_root) else str(note_path)
        fm = _parse_note_frontmatter(note_path)
        if not fm:
            print(f"⚠️  无法解析 frontmatter: {note_path}", file=sys.stderr)
            continue
        kb_id = fm.get("id", "")
        tool = tool_by_kb.get(kb_id)
        wf_targets = _resolve_workflows_for_note(fm, rules, tool)

        for wf_id in wf_targets:
            overlay["playbook_notes"].setdefault(wf_id, [])
            _uniq_append(overlay["playbook_notes"][wf_id], rel)
            overlay["keywords"].setdefault(wf_id, [])
            for tag in fm.get("tags", []):
                _uniq_append(overlay["keywords"][wf_id], tag)

        if tool:
            for intent in tool.intents:
                for ref in rules.get("intent_to_tool_refs", {}).get(intent, []):
                    wf_id = ref["workflow"]
                    ph = ref["phase"]
                    overlay["tool_refs"].setdefault(wf_id, {}).setdefault(ph, [])
                    existing = {r["id"] for r in overlay["tool_refs"][wf_id][ph]}
                    if tool.id not in existing:
                        overlay["tool_refs"][wf_id][ph].append({
                            "id": tool.id,
                            "required": ref.get("required") == "true",
                            "default_method": tool.install_default,
                            "when": "",
                        })

        title = fm.get("title", "")
        for kw in rules.get("title_keywords_to_router", []):
            if kw in title:
                overlay["router_triggers"].setdefault("frontend-ui-router", [])
                _uniq_append(overlay["router_triggers"]["frontend-ui-router"], kw)

        entry = {
            "ingest_id": ingest_id,
            "note": rel,
            "kb_id": kb_id,
            "workflows": sorted(wf_targets),
            "at": fm.get("updated", ""),
        }
        overlay["sync_log"].append(entry)
        report_entries.append(entry)

    overlay["last_ingest_id"] = ingest_id
    _write_sync_overlay(sync_path, overlay)

    print(f"## H13 SyncWorkflow · {ingest_id}\n")
    for r in report_entries:
        print(f"- **笔记**: `{r['note']}` (`{r['kb_id']}`)")
        print(f"  - 已同步工作流: {', '.join(f'`{w}`' for w in r['workflows'])}")
    print(f"\n✅ 已更新 `{sync_path.relative_to(kb_root)}`")
    print("验证: `scripts/kb-workflow.sh \"<场景>\" --list`")
    return 0


def _route_via_router(router: dict[str, Any], q: str) -> tuple[str, str]:
    for route in router.get("routes", []):
        if any(m.lower() in q for m in route.get("match", [])):
            return route["workflow"], f"router:{router['id']}"
    default = router.get("default", "fe-full-pipeline")
    return default, f"router:{router['id']}:default"


def _resolve_workflow_id(
    query: str,
    workflows: list[dict[str, Any]],
    routers: list[dict[str, Any]],
    wf_aliases: dict[str, str],
) -> tuple[str, str]:
    q = _normalize(query)
    for alias, router_or_wf in wf_aliases.items():
        if _normalize(alias) in q or q in _normalize(alias):
            if router_or_wf.endswith("-router") or router_or_wf.endswith("router"):
                router = next((r for r in routers if r["id"] == router_or_wf or r["id"].endswith(router_or_wf)), None)
                if router:
                    return _route_via_router(router, q)
                return "fe-full-pipeline", f"alias:{router_or_wf}:fallback"
            wf_ids = {w["id"] for w in workflows}
            if router_or_wf in wf_ids:
                return router_or_wf, "alias"
            return router_or_wf, "alias"

    for router in routers:
        if any(t.lower() in q for t in router.get("triggers", [])):
            return _route_via_router(router, q)

    best_id = "fe-full-pipeline"
    best_score = 0.0
    for wf in workflows:
        score = 0.0
        for kw in wf.get("triggers", {}).get("keywords", []):
            if kw.lower() in q:
                score += 3.0
        for intent in wf.get("triggers", {}).get("intents", []):
            if intent.lower() in q:
                score += 2.0
        if _normalize(wf["name"]) in q or wf["id"] in q:
            score += 5.0
        if score > best_score or (
            score == best_score
            and score > 0
            and best_id == "fe-full-pipeline"
            and wf["id"] != "fe-full-pipeline"
        ):
            best_score = score
            best_id = wf["id"]
    return best_id, "scored" if best_score > 0 else "default"


def _substitute(text: str, ctx: dict[str, str]) -> str:
    for key, val in ctx.items():
        text = text.replace("{" + key + "}", val)
    return text


def _build_workflow_payload(
    kb_root: Path,
    workflow: dict[str, Any],
    tools: list[Tool],
    ctx: dict[str, str],
) -> dict[str, Any]:
    tool_map = {t.id: t for t in tools}
    phases_out: list[dict[str, Any]] = []
    install_commands: list[str] = []
    agent_prompts: list[str] = []

    for phase in workflow.get("phases", []):
        tools_resolved: list[dict[str, Any]] = []
        for ref in phase.get("tool_refs", []):
            t = tool_map.get(ref["id"])
            if not t:
                continue
            preview_cmd = f'{kb_root}/scripts/install-tool.sh {t.id} --target "{ctx["project"]}"'
            install_cmd = f'{kb_root}/scripts/install-tool.sh {t.id} --yes --target "{ctx["project"]}"'
            install_commands.append(preview_cmd)
            tools_resolved.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "required": ref.get("required", False),
                    "when": ref.get("when", ""),
                    "default_method": ref.get("default_method") or t.install_default,
                    "preview_cmd": preview_cmd,
                    "install_cmd": install_cmd,
                    "usage_prompt": t.usage_prompt.strip(),
                }
            )

        instructions = _substitute(phase.get("instructions", ""), ctx)
        prompt = _substitute(phase.get("prompt", ""), ctx)
        if prompt.strip():
            agent_prompts.append(f"### {phase['id']} {phase['name']}\n{prompt.strip()}")

        phases_out.append(
            {
                "id": phase["id"],
                "name": phase["name"],
                "gate": phase.get("gate", "must_pass"),
                "instructions": instructions,
                "prompt": prompt,
                "checklist": phase.get("checklist", []),
                "tools": tools_resolved,
                "resources": phase.get("resources", []),
            }
        )

    playbooks: list[dict[str, Any]] = []
    for note_rel in workflow.get("playbook_notes", []):
        note_path = kb_root / note_rel
        playbooks.append({"path": str(note_rel), "tldr": _read_tldr(note_path, 5)})

    # fe-from-scratch：注入默认 skill 调用
    if workflow["id"] == "fe-from-scratch" and "{skill_invoke}" in json.dumps(phases_out):
        skill = "Follow design-taste-frontend skill."
        for p in phases_out:
            p["prompt"] = p["prompt"].replace("{skill_invoke}", skill)

    combined_prompt = "\n\n".join(agent_prompts)
    combined_prompt = _substitute(combined_prompt, ctx)

    return {
        "workflow_id": workflow["id"],
        "workflow_name": workflow["name"],
        "version": workflow.get("version", "1.0"),
        "summary": workflow.get("summary", ""),
        "phases": phases_out,
        "playbooks": playbooks,
        "resources": workflow.get("resources", []),
        "install_commands": install_commands,
        "agent_prompt_bundle": combined_prompt,
        "context": ctx,
    }


def cmd_workflow(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root).resolve()
    tools, tool_aliases = load_registry(kb_root / "knowledge/tools-registry.yaml")
    workflows, routers, wf_aliases = load_workflows(kb_root / "knowledge/workflows-registry.yaml", kb_root)

    wf_id, route_reason = _resolve_workflow_id(args.query, workflows, routers, wf_aliases)
    workflow = next((w for w in workflows if w["id"] == wf_id), None)
    if not workflow:
        print(f"❌ 未找到工作流: {wf_id}", file=sys.stderr)
        return 1

    target = str(Path(args.target).resolve())
    ctx = {
        "kb": str(kb_root),
        "project": target,
        "target_files": args.target_files or "（请填写待改文件路径）",
        "stack": args.stack or "（请填写技术栈，如 Vue 3 + Vite）",
        "brand_tone": args.brand or "专业、克制、开发者友好",
        "page_brief": args.brief or args.query,
        "color_palette": args.colors or "（可选：从 coolors.co 粘贴 CSS 变量）",
        "aesthetic_direction": args.aesthetic or "Minimalism",
        "skill_invoke": "Follow design-taste-frontend skill.",
        "reference_source": "（粘贴 aura.build 参考源码）",
        "current_files": "（粘贴或描述当前页面代码路径）",
        "target_page": args.brief or "首页",
        "shell_path": "（下载的 UI 壳层路径）",
        "business_requirements": args.brief or args.query,
        "scenario": args.query,
    }

    payload = _build_workflow_payload(kb_root, workflow, tools, ctx)
    payload["route_reason"] = route_reason
    payload["query"] = args.query

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.prompt_only:
        print(payload["agent_prompt_bundle"] or "（本工作流无预置 Prompt，请按阶段 instructions 执行）")
        return 0

    print(f"# 方法论工作流 · {payload['workflow_name']}")
    print(f"> **ID**: `{payload['workflow_id']}` v{payload['version']} · 路由: {route_reason}")
    print(f"> **场景**: {args.query}")
    print(f"> **目标项目**: {target}\n")
    print(f"## 摘要\n\n{payload['summary']}\n")

    if payload["playbooks"]:
        print("## 关联 Playbook（学习中心笔记）\n")
        for pb in payload["playbooks"]:
            print(f"- `{pb['path']}`")
            for b in pb["tldr"]:
                print(f"  - {b}")
        print()

    if payload["resources"]:
        print("## 外部资源\n")
        for r in payload["resources"]:
            print(f"- **{r['name']}**: {r['url']} ({r['type']})")
        print()

    print("## 执行阶段（严格顺序，勾选后进入下一步）\n")
    for phase in payload["phases"]:
        gate = "🔴 必过" if phase["gate"] == "must_pass" else "🟡 可选"
        print(f"### {phase['id']} · {phase['name']} [{gate}]\n")
        if phase["instructions"]:
            print(phase["instructions"])
            print()
        if phase["tools"]:
            print("**工具安装**（预览 → 确认后加 `--yes`）：\n")
            for t in phase["tools"]:
                req = "必需" if t["required"] else "可选"
                print(f"- `{t['id']}` ({req}) — {t['name']}")
                if t.get("when"):
                    print(f"  - 适用：{t['when']}")
                print(f"  - 预览：`{t['preview_cmd']}`")
                print(f"  - 安装：`{t['install_cmd']}`")
            print()
        if phase["checklist"]:
            print("**Checklist**:\n")
            for item in phase["checklist"]:
                print(f"- [ ] {item}")
            print()
        if phase["prompt"]:
            print("**本阶段 Prompt**:\n```")
            print(phase["prompt"].strip())
            print("```\n")

    print("---\n")
    print("## 一键 Agent Prompt（复制到 Cursor / Claude Code）\n")
    if payload["agent_prompt_bundle"]:
        print("```")
        print(payload["agent_prompt_bundle"].strip())
        print("```")
    else:
        print("（按上方各阶段 Prompt 与 instructions 分步执行）")

    print("\n---")
    print("仅输出 Prompt：`kb-workflow.sh \"{query}\" --prompt-only`")
    print("JSON 供 Agent 解析：`kb-workflow.sh \"{query}\" --json`")
    return 0


def cmd_list_workflows(args: argparse.Namespace) -> int:
    kb_root = Path(args.kb_root)
    workflows, _, aliases = load_workflows(kb_root / "knowledge/workflows-registry.yaml", kb_root)
    if args.json:
        print(json.dumps({"workflows": workflows, "aliases": aliases}, ensure_ascii=False, indent=2))
        return 0
    print("# 可用工作流\n")
    for wf in workflows:
        print(f"- `{wf['id']}` — {wf['name']}")
        print(f"  {wf.get('summary', '')[:120]}...")
    print("\n## 快捷别名\n")
    for k, v in aliases.items():
        print(f"- 「{k}」→ `{v}`")
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

    wf = sub.add_parser("workflow", help="生成方法论工作流 playbook")
    wf.add_argument("query", help="场景描述，如「开发前端界面」「优化丑组件」")
    wf.add_argument("--target", default=".", help="业务项目根目录")
    wf.add_argument("--stack", default="", help="技术栈，填入 prompt 模板")
    wf.add_argument("--brand", default="", help="品牌调性")
    wf.add_argument("--brief", default="", help="页面/任务 brief")
    wf.add_argument("--target-files", default="", help="待改文件路径")
    wf.add_argument("--colors", default="", help="配色 CSS 变量")
    wf.add_argument("--aesthetic", default="", help="美学方向")
    wf.add_argument("--json", action="store_true")
    wf.add_argument("--prompt-only", action="store_true", help="仅输出可复制的 Agent Prompt")
    wf.set_defaults(func=cmd_workflow)

    lw = sub.add_parser("list-workflows", help="列出全部工作流")
    lw.add_argument("--json", action="store_true")
    lw.set_defaults(func=cmd_list_workflows)

    sw = sub.add_parser("sync-workflow", help="H13：入库笔记同步到方法论")
    sw.add_argument("ingest_id")
    sw.add_argument("notes", nargs="+", help="notes 路径")
    sw.set_defaults(func=cmd_sync_workflow)

    sc = sub.add_parser("sync-catalog", help="H13b：入库笔记同步到 tools-catalog.yaml")
    sc.add_argument("ingest_id")
    sc.add_argument("notes", nargs="+")
    sc.set_defaults(func=cmd_sync_catalog)

    vc = sub.add_parser("validate-catalog", help="H13b：校验 tools-catalog.yaml")
    vc.add_argument("--baseline", default="", help="sync 前 catalog 快照，仅校验增量")
    vc.set_defaults(func=cmd_validate_catalog)

    args = parser.parse_args()
    if args.cmd == "install" and not args.yes:
        args.dry_run = True
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
