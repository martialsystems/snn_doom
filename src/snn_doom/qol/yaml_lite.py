# Copyright (c) 2026 Martial Systems LLC
"""Indent YAML subset for QoL proposals. No PyYAML dependency."""
from __future__ import annotations

from typing import Any


def load(text: str) -> Any:
    lines = _preprocess(text)
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, 0)
    return value


def _preprocess(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        out.append((indent, raw.strip()))
    return out


def _parse_block(lines: list[tuple[int, str]], i: int, indent: int) -> tuple[Any, int]:
    if i >= len(lines):
        return {}, i
    _, content = lines[i]
    if content.startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines: list[tuple[int, str]], i: int, indent: int) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    while i < len(lines):
        ind, content = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"bad indent at {content!r}")
        if content.startswith("- "):
            raise ValueError(f"list item in map at {content!r}")
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        i += 1
        if rest == "" or rest == "|":
            if i < len(lines) and lines[i][0] > indent:
                child, i = _parse_block(lines, i, lines[i][0])
                data[key] = child
            else:
                data[key] = "" if rest == "" else rest
        else:
            data[key] = _parse_scalar(rest)
    return data, i


def _parse_list(lines: list[tuple[int, str]], i: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while i < len(lines):
        ind, content = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise ValueError(f"bad indent at {content!r}")
        if not content.startswith("- "):
            break
        rest = content[2:].strip()
        i += 1
        if rest == "" or rest == "|":
            if i < len(lines) and lines[i][0] > indent:
                child, i = _parse_block(lines, i, lines[i][0])
                items.append(child)
            else:
                items.append("" if rest == "" else rest)
        elif ":" in rest and not (rest.startswith('"') or rest.startswith("'")):
            # inline map start: key: value, then possible nested keys at greater indent
            key, _, val = rest.partition(":")
            block = [(ind + 2, rest)]
            while i < len(lines) and lines[i][0] > indent and not lines[i][1].startswith("- "):
                block.append((lines[i][0], lines[i][1]))
                i += 1
            child, _ = _parse_map(block, 0, block[0][0])
            items.append(child)
            del key, val
        else:
            items.append(_parse_scalar(rest))
    return items, i


def _parse_scalar(raw: str) -> Any:
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    if raw in ("true", "True", "yes"):
        return True
    if raw in ("false", "False", "no"):
        return False
    if raw in ("null", "None", "~"):
        return None
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in _split_csv(inner)]
    try:
        if raw.startswith("0") and raw not in ("0", "0.0") and not raw.startswith("0."):
            return raw
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def _split_csv(inner: str) -> list[str]:
    parts: list[str] = []
    buf = []
    quote = None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf or parts:
        parts.append("".join(buf).strip())
    return parts
