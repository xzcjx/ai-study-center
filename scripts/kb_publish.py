#!/usr/bin/env python3
"""AI 学习中心 · 笔记 → 平台内容发布 brief 生成器。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


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


def _parse_yaml_block(text: str) -> dict[str, Any]:
    """Minimal YAML parser for platforms-registry.yaml (no PyYAML dep)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    def peek_list_start(idx: int, base_indent: int) -> bool:
        if idx >= len(lines):
            return False
        nxt = lines[idx]
        ni = len(nxt) - len(nxt.lstrip(" "))
        return ni > base_indent and nxt.lstrip().startswith("- ")

    def parse_block(start: int, end: int, base_indent: int) -> tuple[Any, int]:
        if start >= end:
            return {}, start

        first = lines[start]
        fi = len(first) - len(first.lstrip(" "))
        if first.lstrip().startswith("- "):
            items: list[Any] = []
            i = start
            while i < end:
                ln = lines[i]
                li = len(ln) - len(ln.lstrip(" "))
                if li < fi:
                    break
                if not ln.lstrip().startswith("- "):
                    break
                rest = ln.lstrip()[2:].strip()
                if ":" in rest and not rest.startswith('"'):
                    # - key: val  inline map item
                    k, _, v = rest.partition(":")
                    node: dict[str, Any] = {k.strip(): _strip_quotes(v.strip())}
                    j = i + 1
                    while j < end:
                        sub = lines[j]
                        si = len(sub) - len(sub.lstrip(" "))
                        if si <= li:
                            break
                        if sub.lstrip().startswith("- "):
                            break
                        sk, _, sv = sub.lstrip().partition(":")
                        if sk and sv:
                            node[sk.strip()] = _strip_quotes(sv.strip())
                        j += 1
                    items.append(node)
                    i = j
                else:
                    items.append(_strip_quotes(rest))
                    i += 1
            return items, i

        result: dict[str, Any] = {}
        i = start
        while i < end:
            ln = lines[i]
            li = len(ln) - len(ln.lstrip(" "))
            if li < base_indent:
                break
            if li > base_indent:
                i += 1
                continue
            if not ln.lstrip() or ln.lstrip().startswith("- "):
                i += 1
                continue
            key, _, val = ln.lstrip().partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                if peek_list_start(i + 1, li):
                    child, i = parse_block(i + 1, end, li + 2)
                    result[key] = child
                else:
                    child, i = parse_block(i + 1, end, li + 2)
                    result[key] = child if isinstance(child, dict) else {}
            elif val.startswith("["):
                result[key] = _parse_inline_list(val)
                i += 1
            else:
                result[key] = _strip_quotes(val)
                i += 1
        return result, i

    root, _ = parse_block(0, len(lines), 0)
    return root if isinstance(root, dict) else {}


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = _strip_quotes(v.strip())
    return fm, parts[2].lstrip("\n")


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$"
    m = re.search(pattern, body, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^## ", body[start:], re.MULTILINE)
    chunk = body[start : start + nxt.start()] if nxt else body[start:]
    return chunk.strip()


def _extract_bullets(section: str) -> list[str]:
    bullets: list[str] = []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("- "):
            bullets.append(s[2:].strip())
    return bullets


def _resolve_platform(registry: dict[str, Any], token: str) -> dict[str, Any] | None:
    token = token.lstrip("-").lower()
    platforms = registry.get("platforms", {})
    for pid, spec in platforms.items():
        if not isinstance(spec, dict):
            continue
        if pid.lower() == token:
            return {"id": pid, **spec}
        aliases = spec.get("aliases", [])
        if isinstance(aliases, list):
            for a in aliases:
                al = str(a).lstrip("-").lower()
                if al == token or str(a).lower() == token:
                    return {"id": pid, **spec}
    return None


def _sanitize_publish_filename(title: str, max_len: int = 80) -> str:
    """发布成稿文件名：{YYYY-MM-DD}-{中文标题}.md"""
    s = title.strip()
    for ch in r'\/:*?"<>|':
        s = s.replace(ch, "-")
    s = s.replace("：", "-").replace(":", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"


def _load_note(kb_root: Path, note_arg: str) -> Path:
    p = Path(note_arg)
    if not p.is_absolute():
        p = kb_root / note_arg.lstrip("@")
    p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(f"笔记不存在: {p}")
    if "notes" not in p.parts:
        raise ValueError(f"路径须在 notes/ 下: {p}")
    return p


def _build_brief(kb_root: Path, note_path: Path, platform: dict[str, Any]) -> dict[str, Any]:
    text = note_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    tldr = _extract_section(body, "TL;DR")
    scenarios = _extract_section(body, "适用场景")
    key_points = _extract_section(body, "知识要点")
    cautions = _extract_section(body, "注意事项")
    related = _extract_section(body, "相关链接")

    reg_path = kb_root / "knowledge/platforms-registry.yaml"
    registry = _parse_yaml_block(reg_path.read_text(encoding="utf-8"))

    publish_id = f"PUB-{date.today().strftime('%Y%m%d')}-{fm.get('id', note_path.stem)[-3:]}"
    platform_id = platform.get("id", "unknown")
    output_dir = kb_root / "publish" / platform_id
    title_slug = _sanitize_publish_filename(fm.get("title", note_path.stem))
    output_file = output_dir / f"{date.today().isoformat()}-{title_slug}.md"

    template_name = platform.get("output_template", "")
    template_path = kb_root / template_name if template_name else ""

    return {
        "publish_id": publish_id,
        "platform": {
            "id": platform_id,
            "label": platform.get("label", platform_id),
            "type": platform.get("type", "article"),
            "aliases": platform.get("aliases", []),
            "structure": platform.get("structure", []),
            "formatting": platform.get("formatting", []),
            "avoid": platform.get("avoid", []),
            "max_chars": platform.get("max_chars"),
            "ideal_chars": platform.get("ideal_chars"),
            "max_title_chars": platform.get("max_title_chars"),
        },
        "global_style": registry.get("global_style", {}),
        "product_defaults": registry.get("product_defaults", {}),
        "note": {
            "path": str(note_path.relative_to(kb_root)),
            "absolute_path": str(note_path),
            "id": fm.get("id", note_path.stem),
            "title": fm.get("title", note_path.stem),
            "module": fm.get("module", ""),
            "tags": _parse_inline_list(fm.get("tags", "[]")) if fm.get("tags") else [],
            "tldr_bullets": _extract_bullets(tldr),
            "scenarios": scenarios,
            "key_points_excerpt": key_points[:4000],
            "cautions": cautions,
            "related": related,
        },
        "output": {
            "suggested_path": str(output_file.relative_to(kb_root)),
            "template": str(template_path.relative_to(kb_root)) if template_path else "",
        },
        "agent_instructions": _agent_instructions(platform),
    }


def _agent_instructions(platform: dict[str, Any]) -> str:
    pid = platform.get("id", "")
    ptype = platform.get("type", "article")
    label = platform.get("label", pid)
    if ptype == "product":
        return (
            f"将笔记提炼为{label}商品页：标题 SEO/口语化、卖点、交付清单、定价建议。"
            "虚拟资料默认网盘交付；不编造销量与好评；保留笔记中的合规提醒。"
        )
    return (
        f"将笔记改写为可发布的{label}文章：遵循 structure/formatting/avoid，"
        "应用 global_style.anti_ai_slop，保留可核实事实，语气像从业者而非 AI 洗稿。"
    )


def cmd_list(registry: dict[str, Any]) -> None:
    platforms = registry.get("platforms", {})
    rows = []
    for pid, spec in platforms.items():
        if not isinstance(spec, dict):
            continue
        rows.append(
            {
                "id": pid,
                "label": spec.get("label", pid),
                "type": spec.get("type", "article"),
                "aliases": spec.get("aliases", []),
                "command_example": f"/kb-publish -{pid} @notes/{{module}}/xxx.md",
            }
        )
    print(json.dumps({"platforms": rows}, ensure_ascii=False, indent=2))


def cmd_brief(kb_root: Path, platform_token: str, note_arg: str) -> None:
    reg_path = kb_root / "knowledge/platforms-registry.yaml"
    registry = _parse_yaml_block(reg_path.read_text(encoding="utf-8"))
    platform = _resolve_platform(registry, platform_token)
    if not platform:
        known = list(registry.get("platforms", {}).keys())
        raise SystemExit(f"未知平台: {platform_token}。可用: {', '.join(known)}")

    note_path = _load_note(kb_root, note_arg)
    brief = _build_brief(kb_root, note_path, platform)
    print(json.dumps(brief, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="kb-publish brief generator")
    parser.add_argument("--kb-root", default="", help="学习中心根目录")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出支持的平台")
    p_list.set_defaults(func=lambda a: cmd_list(_parse_yaml_block(
        (Path(a.kb_root) / "knowledge/platforms-registry.yaml").read_text(encoding="utf-8")
    )))

    p_brief = sub.add_parser("brief", help="生成 Agent brief JSON")
    p_brief.add_argument("platform", help="平台 id 或 alias，如 redbook / -wechat")
    p_brief.add_argument("note", help="笔记路径")
    p_brief.set_defaults(
        func=lambda a: cmd_brief(Path(a.kb_root), a.platform, a.note)
    )

    args = parser.parse_args()
    if not args.kb_root:
        script_dir = Path(__file__).resolve().parent
        args.kb_root = str(script_dir.parent)
    args.func(args)


if __name__ == "__main__":
    main()
