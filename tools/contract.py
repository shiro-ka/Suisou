#!/usr/bin/env python3

import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
UI = os.path.join(ROOT, "pages", "ui")

sys.path.insert(0, HERE)
import solve

COMMENT = re.compile(r"/\*.*?\*/", re.S)
ATTR = re.compile(r'\[data-suisou(-[a-z-]+)?(?:~="([^"]+)")?\]')
STATE = re.compile(r"\[(aria-[a-z-]+|disabled|popover|open)(?:[~^]?=[^\]]*)?\]")
TOKEN_DEF = re.compile(r"(--suisou-[a-z0-9-]+)\s*:")

def ui_files():
    return [os.path.join(UI, n) for n in sorted(os.listdir(UI)) if n.endswith(".css")]

def collect():
    attrs, states = {}, set()
    for p in ui_files():
        css = COMMENT.sub("", open(p, encoding="utf-8").read())
        for name, val in ATTR.findall(css):
            name = name[1:] if name else ""
            vals = attrs.setdefault(name, [])
            if val:
                base = re.split(r"[:>]", val)[-1]
                if base not in vals:
                    vals.append(base)
        states |= set(STATE.findall(css))

    attrs["theme"] = ([t["name"] for t in solve.THEMES]
                      + [n for n, _ in solve.ACCENTS])
    base = COMMENT.sub("", open(os.path.join(UI, "base.css"), encoding="utf-8").read())
    dims = []
    for name in TOKEN_DEF.findall(base):
        if name not in dims:
            dims.append(name)
    return attrs, sorted(states), dims

def render():
    attrs, states, dims = collect()

    L = ["# Suisou", ""]

    L.append("## 属性と値")
    L.append("")
    L.append("| 属性 | 値 |")
    L.append("|---|---|")
    for name in sorted(attrs):
        vals = attrs[name]
        attr = f"data-suisou-{name}" if name else "data-suisou"
        L.append(f"| `{attr}` | {' '.join(f'`{v}`' for v in vals)} |")
    L.append("")

    L.append("## 標準属性")
    L.append("")
    L.append(" ".join(f"`{s}`" for s in states))
    L.append("")

    L.append("## トークン")
    L.append("")
    L.append("`palette.css`")
    L.append("")
    L.append("- " + " ".join(f"`--suisou-{n}`" for n in solve.THEME_TOKENS))
    L.append("- " + " ".join(f"`--suisou-{n}`" for n in solve.ACCENT_TOKENS))
    L.append("")
    L.append("`ui/base.css`")
    L.append("")
    L.append("- " + " ".join(f"`{n}`" for n in dims))
    L.append("")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    sys.stdout.write(render())
