#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mini-YAML — strict reader for a YAML subset (pure stdlib).

Why this file exists: the ORVYREN core is stdlib-only (DOC4 §1.4,
"stdlib-only for the core") and `policy_v1.yaml` must remain the source of
truth for the *parameters* (DOC2 §5.5.3). PyYAML is therefore ruled out;
this reader accepts ONLY the subset used by the project's parameter files,
and refuses everything else with an explicit message (fail-closed).

Supported subset:
  - `#` comments (whole line or end of line, outside quotes);
  - `key: value` mappings, nested by indentation (spaces only);
  - `- element` lists (scalars) and lists of mappings (`- key: value`);
  - scalars: integers, floats, `true`/`false`, `null`, bare strings or
    quoted strings (double quotes: backslash escapes for quote and backslash;
    single quotes: literal);
  - empty lists `[]` and empty mappings `{}`.

Refused (explicit error, never a guessed interpretation): tabs,
anchors/aliases `&`/`*`, tags `!`, nested flow style, multi-line literals
`|`/`>`, duplicate keys, inconsistent indentation, missing value.

Usage:
    from orvyren.policy.miniyaml import load, load_file, MiniYamlError
    data = load_file("policy_v1.yaml")
"""

from __future__ import annotations

import re

__all__ = ["load", "load_file", "MiniYamlError"]

MAP_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
FORBIDDEN_RE = re.compile(r"^[&*!|>@`]")


class MiniYamlError(ValueError):
    """Syntax error, or a feature outside the supported subset."""


def _strip_inline_comment(text: str) -> str:
    """Strip a `#` comment outside quotes; keep the rest as is."""
    out = []
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        else:
            if ch in ("'", '"'):
                quote = ch
                out.append(ch)
            elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
                break
            else:
                out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _parse_scalar(text: str, lineno: int):
    if FORBIDDEN_RE.match(text):
        raise MiniYamlError(f"line {lineno}: '&', '*', '!', '|', '>' forbidden (outside the subset)")
    if text.startswith('"'):
        if len(text) < 2 or not text.endswith('"'):
            raise MiniYamlError(f"line {lineno}: unterminated double quote")
        body = text[1:-1]
        return body.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise MiniYamlError(f"line {lineno}: unterminated single quote")
        return text[1:-1]
    if text in ("null", "~"):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if INT_RE.match(text):
        return int(text)
    if FLOAT_RE.match(text):
        return float(text)
    return text


def _is_map_entry(text: str) -> bool:
    key, sep, rest = text.partition(":")
    if not sep or not MAP_KEY_RE.match(key):
        return False
    return rest == "" or rest.startswith(" ")


def _split_map_entry(text: str, lineno: int):
    key, sep, rest = text.partition(":")
    key = key.strip()
    if not sep or not MAP_KEY_RE.match(key):
        raise MiniYamlError(f"line {lineno}: invalid key {key!r}")
    return key, rest.strip()


def _collect_lines(text: str):
    rows = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise MiniYamlError(f"line {lineno}: tab forbidden (indent with spaces)")
        content = _strip_inline_comment(raw)
        if not content.strip():
            continue
        stripped = content.lstrip(" ")
        if stripped.startswith("---") or stripped.startswith("..."):
            raise MiniYamlError(f"line {lineno}: document markers not supported")
        indent = len(content) - len(stripped)
        rows.append((lineno, indent, stripped.rstrip()))
    return rows


def _parse_block(rows, pos: int, indent: int):
    lineno, ind, content = rows[pos]
    if ind != indent:
        raise MiniYamlError(f"line {lineno}: indentation {ind}, expected {indent}")
    if content.startswith("- "):
        return _parse_list(rows, pos, indent)
    return _parse_map(rows, pos, indent)


def _parse_map(rows, pos: int, indent: int):
    result = {}
    while pos < len(rows):
        lineno, ind, content = rows[pos]
        if ind < indent:
            break
        if ind > indent:
            raise MiniYamlError(f"line {lineno}: unexpected indentation")
        if content.startswith("- "):
            raise MiniYamlError(f"line {lineno}: list item without a parent key")
        key, rest = _split_map_entry(content, lineno)
        if key in result:
            raise MiniYamlError(f"line {lineno}: duplicate key {key!r}")
        if rest:
            if rest == "[]":
                result[key] = []
            elif rest == "{}":
                result[key] = {}
            else:
                result[key] = _parse_scalar(rest, lineno)
            pos += 1
        else:
            if pos + 1 < len(rows) and rows[pos + 1][1] > ind:
                child_indent = rows[pos + 1][1]
                child, pos = _parse_block(rows, pos + 1, child_indent)
                result[key] = child
            else:
                raise MiniYamlError(f"line {lineno}: missing value for {key!r}")
    return result, pos


def _parse_list(rows, pos: int, indent: int):
    items = []
    while pos < len(rows):
        lineno, ind, content = rows[pos]
        if ind != indent or not content.startswith("- "):
            break
        item = content[2:].strip()
        if not item:
            raise MiniYamlError(f"line {lineno}: empty list item")
        if _is_map_entry(item):
            sub = [(lineno, indent + 2, item)]
            j = pos + 1
            while j < len(rows) and rows[j][1] > indent:
                if rows[j][1] < indent + 2:
                    raise MiniYamlError(f"line {rows[j][0]}: inconsistent indentation in a list")
                sub.append(rows[j])
                j += 1
            value, consumed = _parse_block(sub, 0, indent + 2)
            if consumed != len(sub):
                raise MiniYamlError(f"line {lineno}: invalid list structure")
            items.append(value)
            pos = j
        else:
            items.append(_parse_scalar(item, lineno))
            pos += 1
    return items, pos


def load(text: str) -> dict:
    """Load a document from a string; return a mapping."""
    rows = _collect_lines(text)
    if not rows:
        raise MiniYamlError("empty document")
    root, pos = _parse_block(rows, 0, rows[0][1])
    if pos != len(rows):
        raise MiniYamlError(f"line {rows[pos][0]}: unconsumed content (indentation)")
    if not isinstance(root, dict):
        raise MiniYamlError("the root must be a mapping")
    return root


def load_file(path) -> dict:
    """Load a document from a UTF-8 file."""
    with open(path, "r", encoding="utf-8") as handle:
        return load(handle.read())
