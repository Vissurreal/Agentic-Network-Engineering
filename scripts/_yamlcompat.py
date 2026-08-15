"""YAML loading with no hard dependency.

PyYAML is used when present. When it isn't, a restricted parser handles the
subset of YAML that `network.yaml` actually uses. Requiring `pip install` before
a plugin works is a seam, and this removes it.

The restricted grammar deliberately covers only what the schema needs:

    block mappings, arbitrary nesting
    block sequences of scalars and of mappings
    flow sequences on one line          [a, b, c]
    scalars                             str, int, float, bool, null
    quoted scalars                      'single' and "double"
    folded and literal block scalars    > and |
    comments and blank lines

Anything outside that raises RestrictedYAMLError rather than guessing, because a
parser that silently misreads a network specification is worse than one that
refuses. `tests/test_yamlcompat.py` asserts agreement with PyYAML on every
fixture, so drift between the two paths is caught.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["safe_load", "RestrictedYAMLError", "USING_PYYAML"]


class RestrictedYAMLError(ValueError):
    """The fallback parser met something outside its grammar."""


try:
    import yaml as _pyyaml

    USING_PYYAML = True
except ImportError:  # pragma: no cover - exercised on machines without PyYAML
    _pyyaml = None
    USING_PYYAML = False


_INT = re.compile(r"^[+-]?\d+$")
_FLOAT = re.compile(r"^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$")
_KEY = re.compile(r"^([A-Za-z0-9_.\-]+):(?:\s+(.*))?$")


def _scalar(tok: str) -> Any:
    t = tok.strip()
    if not t:
        return None
    if len(t) >= 2 and t[0] == t[-1] == "'":
        # YAML escapes an apostrophe inside a single-quoted scalar by doubling
        # it. Returning the raw interior makes the fallback disagree with every
        # conforming parser on values such as 'the user''s intent'.
        return t[1:-1].replace("''", "'")
    if len(t) >= 2 and t[0] == t[-1] == '"':
        return t[1:-1]
    low = t.lower()
    if low in ("null", "~"):
        return None
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if _INT.match(t):
        return int(t)
    if _FLOAT.match(t):
        return float(t)
    return t


def _flow_seq(tok: str) -> list[Any]:
    inner = tok.strip()[1:-1].strip()
    if not inner:
        return []
    out, buf, quote, depth = [], "", "", 0
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch in "[{":
            depth += 1
            buf += ch
        elif ch in "]}":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            out.append(_scalar(buf))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(_scalar(buf))
    return out


def _strip_comment(tok: str) -> str:
    """Remove a trailing comment, respecting quotes and flow brackets.

    A '#' only opens a comment at the start of the token or after whitespace,
    which is what keeps 'sha256:ab#cd' and "a # b" intact.
    """
    out, quote, depth = "", "", 0
    prev_ws = True
    for ch in tok:
        if quote:
            out += ch
            if ch == quote:
                quote = ""
            prev_ws = False
            continue
        if ch in "\"'":
            quote = ch
            out += ch
            prev_ws = False
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "#" and prev_ws and depth == 0:
            break
        out += ch
        prev_ws = ch.isspace()
    return out.rstrip()


def _value(tok: str) -> Any:
    t = _strip_comment(tok).strip()
    if t.startswith("[") and t.endswith("]"):
        return _flow_seq(t)
    if t.startswith("{"):
        raise RestrictedYAMLError("flow mappings are not supported")
    return _scalar(t)


class _Lines:
    def __init__(self, text: str) -> None:
        self.rows: list[tuple[int, str, int]] = []
        for n, raw in enumerate(text.splitlines(), 1):
            if "\t" in raw[: len(raw) - len(raw.lstrip())]:
                raise RestrictedYAMLError(f"line {n}: tab indentation")
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            self.rows.append((len(raw) - len(raw.lstrip(" ")), stripped, n))
        self.i = 0

    def peek(self):
        return self.rows[self.i] if self.i < len(self.rows) else None

    def take(self):
        row = self.rows[self.i]
        self.i += 1
        return row


def _block_scalar(lines: _Lines, indent: int, indicator: str) -> str:
    """Read a folded (>) or literal (|) block scalar, honouring chomping.

    Blank lines are dropped by _Lines before this point, so a folded scalar
    containing a paragraph break will lose it. That is acceptable here because
    the documents this parses are machine-generated against a fixed schema, and
    PyYAML is preferred whenever it is installed.
    """
    style, chomp = indicator[0], (indicator[1:] or "")
    parts: list[str] = []
    while (row := lines.peek()) is not None and row[0] > indent:
        parts.append(lines.take()[1])
    body = "\n".join(parts) if style == "|" else " ".join(parts)
    if not parts:
        return ""
    if chomp == "-":
        return body
    return body + "\n"  # clip and keep both end with a newline here


def _parse_block(lines: _Lines, indent: int) -> Any:
    row = lines.peek()
    if row is None:
        return None
    if row[1].startswith("- "):
        return _parse_seq(lines, indent)
    return _parse_map(lines, indent)


def _parse_seq(lines: _Lines, indent: int) -> list[Any]:
    out: list[Any] = []
    while (row := lines.peek()) is not None and row[0] == indent and row[1].startswith("- "):
        col, text, n = lines.take()
        body = text[2:].strip()
        m = _KEY.match(body)
        if m:
            # "- key: value" opens a mapping whose remaining keys are indented
            # to the column where `key` began.
            item: dict[str, Any] = {}
            key, rest = m.group(1), m.group(2)
            item[key] = _entry_value(lines, col + 2, rest, n)
            while (nxt := lines.peek()) is not None and nxt[0] == col + 2 and not nxt[1].startswith("- "):
                c2, t2, n2 = lines.take()
                m2 = _KEY.match(t2)
                if not m2:
                    raise RestrictedYAMLError(f"line {n2}: expected 'key: value', got {t2!r}")
                item[m2.group(1)] = _entry_value(lines, c2, m2.group(2), n2)
            out.append(item)
        else:
            out.append(_value(body))
    return out


def _parse_map(lines: _Lines, indent: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    while (row := lines.peek()) is not None and row[0] == indent:
        if row[1].startswith("- "):
            break
        col, text, n = lines.take()
        m = _KEY.match(text)
        if not m:
            raise RestrictedYAMLError(f"line {n}: expected 'key: value', got {text!r}")
        out[m.group(1)] = _entry_value(lines, col, m.group(2), n)
    return out


def _entry_value(lines: _Lines, col: int, rest: str | None, n: int) -> Any:
    stripped = _strip_comment(rest or "").strip()

    if stripped in (">", "|", ">-", "|-", ">+", "|+"):
        return _block_scalar(lines, col, stripped)

    if stripped == "":
        nxt = lines.peek()
        if nxt is None:
            return None
        # PyYAML's safe_dump emits a block sequence at the *same* indent as the
        # key that owns it, so a sibling-indented "- " belongs to this key rather
        # than terminating the mapping.
        if nxt[1].startswith("- ") and nxt[0] >= col:
            return _parse_seq(lines, nxt[0])
        if nxt[0] > col:
            return _parse_block(lines, nxt[0])
        return None

    # A long plain scalar is wrapped across lines by PyYAML's dumper. Any deeper
    # line that is neither a sequence entry nor a "key: value" pair continues it.
    cont: list[str] = []
    while (nxt := lines.peek()) is not None and nxt[0] > col:
        if nxt[1].startswith("- ") or _KEY.match(nxt[1]):
            break
        cont.append(lines.take()[1])
    if cont:
        return " ".join([_strip_comment(rest).strip(), *cont])

    return _value(rest)


def _restricted_load(text: str) -> Any:
    lines = _Lines(text)
    if lines.peek() is None:
        return None
    doc = _parse_block(lines, lines.peek()[0])
    if lines.peek() is not None:
        _, t, n = lines.peek()
        raise RestrictedYAMLError(f"line {n}: unexpected indentation at {t!r}")
    return doc


def safe_load(text: str) -> Any:
    """Parse a YAML document. Uses PyYAML when installed."""
    if USING_PYYAML:
        return _pyyaml.safe_load(text)
    if "---" in text.splitlines():
        raise RestrictedYAMLError("multi-document streams are not supported")
    if "&" in text or "*" in text and re.search(r"(^|\s)\*\w", text):
        raise RestrictedYAMLError("anchors and aliases are not supported")
    return _restricted_load(text)
