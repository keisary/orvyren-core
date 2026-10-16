#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mini-YAML — lecteur strict d'un sous-ensemble YAML (stdlib pure).

Pourquoi ce fichier existe : le cœur d'ORVYREN est stdlib-only (DOC4 §1.4,
« stdlib-only pour le cœur ») et `policy_v1.yaml` doit rester la source de
vérité des *paramètres* (DOC2 §5.5.3). PyYAML est donc proscrit ; ce lecteur
n'accepte QUE le sous-ensemble utilisé par les fichiers de paramètres du
projet, et refuse tout le reste avec un message explicite (fail-closed).

Sous-ensemble supporté :
  - commentaires `#` (ligne entière ou fin de ligne, hors guillemets) ;
  - mappings `cle: valeur`, imbriqués par indentation (espaces uniquement) ;
  - listes `- element` (scalaires) et listes de mappings (`- cle: valeur`) ;
  - scalaires : entiers, flottants, `true`/`false`, `null`, chaînes nues ou
    entre guillemets (double : échappements ``\\"`` et ``\\\\`` ; simple :
    littérale) ;
  - listes vides `[]` et mappings vides `{}`.

Refusé (erreur explicite, jamais d'interprétation devinée) : tabulations,
ancres/alias `&`/`*`, tags `!`, style flow imbriqué, littéraux multi-lignes
`|`/`>`, clés dupliquées, indentation incohérente, valeur manquante.

Usage :
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
    """Erreur de syntaxe, ou fonctionnalité hors sous-ensemble supporté."""


def _strip_inline_comment(text: str) -> str:
    """Retire un commentaire `#` hors guillemets ; conserve le reste tel quel."""
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
        raise MiniYamlError(f"ligne {lineno}: '&', '*', '!', '|', '>' interdits (hors sous-ensemble)")
    if text.startswith('"'):
        if len(text) < 2 or not text.endswith('"'):
            raise MiniYamlError(f"ligne {lineno}: guillemet double non fermé")
        body = text[1:-1]
        return body.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise MiniYamlError(f"ligne {lineno}: guillemet simple non fermé")
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
        raise MiniYamlError(f"ligne {lineno}: clé invalide {key!r}")
    return key, rest.strip()


def _collect_lines(text: str):
    rows = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise MiniYamlError(f"ligne {lineno}: tabulation interdite (indenter en espaces)")
        content = _strip_inline_comment(raw)
        if not content.strip():
            continue
        stripped = content.lstrip(" ")
        if stripped.startswith("---") or stripped.startswith("..."):
            raise MiniYamlError(f"ligne {lineno}: marqueurs de document non supportés")
        indent = len(content) - len(stripped)
        rows.append((lineno, indent, stripped.rstrip()))
    return rows


def _parse_block(rows, pos: int, indent: int):
    lineno, ind, content = rows[pos]
    if ind != indent:
        raise MiniYamlError(f"ligne {lineno}: indentation {ind} attendue {indent}")
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
            raise MiniYamlError(f"ligne {lineno}: indentation inattendue")
        if content.startswith("- "):
            raise MiniYamlError(f"ligne {lineno}: élément de liste sans clé parente")
        key, rest = _split_map_entry(content, lineno)
        if key in result:
            raise MiniYamlError(f"ligne {lineno}: clé dupliquée {key!r}")
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
                raise MiniYamlError(f"ligne {lineno}: valeur manquante pour {key!r}")
    return result, pos


def _parse_list(rows, pos: int, indent: int):
    items = []
    while pos < len(rows):
        lineno, ind, content = rows[pos]
        if ind != indent or not content.startswith("- "):
            break
        item = content[2:].strip()
        if not item:
            raise MiniYamlError(f"ligne {lineno}: élément de liste vide")
        if _is_map_entry(item):
            sub = [(lineno, indent + 2, item)]
            j = pos + 1
            while j < len(rows) and rows[j][1] > indent:
                if rows[j][1] < indent + 2:
                    raise MiniYamlError(f"ligne {rows[j][0]}: indentation incohérente dans une liste")
                sub.append(rows[j])
                j += 1
            value, consumed = _parse_block(sub, 0, indent + 2)
            if consumed != len(sub):
                raise MiniYamlError(f"ligne {lineno}: structure de liste invalide")
            items.append(value)
            pos = j
        else:
            items.append(_parse_scalar(item, lineno))
            pos += 1
    return items, pos


def load(text: str) -> dict:
    """Charge un document depuis une chaîne ; retourne un mapping."""
    rows = _collect_lines(text)
    if not rows:
        raise MiniYamlError("document vide")
    root, pos = _parse_block(rows, 0, rows[0][1])
    if pos != len(rows):
        raise MiniYamlError(f"ligne {rows[pos][0]}: contenu non consommé (indentation)")
    if not isinstance(root, dict):
        raise MiniYamlError("la racine doit être un mapping")
    return root


def load_file(path) -> dict:
    """Charge un document depuis un fichier UTF-8."""
    with open(path, "r", encoding="utf-8") as handle:
        return load(handle.read())
