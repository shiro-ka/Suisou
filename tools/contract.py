#!/usr/bin/env python3

import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
UI = os.path.join(ROOT, "pages", "ui")

sys.path.insert(0, HERE)
import solve

COMMENT = re.compile(r"/\*.*?\*/", re.S)
ATTR = re.compile(r'\[data-suisou(-[a-z-]+)?(?:(~?)="([^"]*)")?\]')
STATE = re.compile(r"\[(aria-[a-z-]+|disabled|popover|open|type|hidden)(?:[~^]?=[^\]]*)?\]")
TOKEN_DEF = re.compile(r"(--suisou-[a-z0-9-]+)\s*:")
VAR = re.compile(r"--suisou-[a-z0-9-]+")

def ui_files():
    return [os.path.join(UI, n) for n in sorted(os.listdir(UI)) if n.endswith(".css")]

def collect():
    attrs, staged, states, names = {}, {}, set(), []
    for p in ui_files():
        css = COMMENT.sub("", open(p, encoding="utf-8").read())
        for mt in ATTR.finditer(css):
            name, val = (mt.group(1) or "")[1:], mt.group(3)
            vals = attrs.setdefault(name, [])
            if mt.group(0).endswith('=""]'):
                if "" not in vals:
                    vals.insert(0, "")
                continue
            if not val:
                continue
            m = re.match(r"([sml])([:>])(.+)", val)
            if m:
                words = staged.setdefault(name, {}).setdefault(m.group(2), [])
                if m.group(3) not in words:
                    words.append(m.group(3))
            elif val not in vals:
                vals.append(val)
        states |= set(STATE.findall(css))
        for n in VAR.findall(css):
            if n not in names:
                names.append(n)

    attrs["theme"] = ([t["name"] for t in solve.THEMES]
                      + [n for n, _ in solve.ACCENTS])
    base = COMMENT.sub("", open(os.path.join(UI, "base.css"), encoding="utf-8").read())
    dims = []
    root = re.search(r":root\s*\{(.*?)\}", base, re.S).group(1)
    for name in TOKEN_DEF.findall(root):
        if name not in dims:
            dims.append(name)
    palette = {f"--suisou-{n}" for n in solve.SHARED_TOKENS + solve.GRAY_VARS + solve.THEME_TOKENS + solve.ACCENT_TOKENS}
    others = [n for n in names if n not in palette and n not in dims]
    return attrs, staged, sorted(states), dims, others

def render():
    attrs, staged, states, dims, others = collect()

    L = ["# Suisou", ""]

    L.append("## 属性と値")
    L.append("")
    L.append("| 属性 | 値 | 段つき |")
    L.append("|---|---|---|")
    for name in sorted(attrs):
        vals = " ".join("（値なし）" if v == "" else f"`{v}`" for v in attrs[name])
        st = staged.get(name, {})
        stv = " / ".join(f"`{k}` " + " ".join(f"`{w}`" for w in st[k]) for k in (":", ">") if k in st)
        attr = f"data-suisou-{name}" if name else "data-suisou"
        L.append(f"| `{attr}` | {vals} | {stv} |")
    L.append("")

    L.append("## 標準属性")
    L.append("")
    L.append(" ".join(f"`{s}`" for s in states))
    L.append("")

    L.append("## トークン")
    L.append("")
    L.append("`palette.css`")
    L.append("")
    L.append("- " + " ".join(f"`--suisou-{n}`" for n in solve.SHARED_TOKENS))
    L.append("- " + " ".join(f"`--suisou-{n}`" for n in solve.GRAY_VARS + solve.THEME_TOKENS))
    L.append("- " + " ".join(f"`--suisou-{n}`" for n in solve.ACCENT_TOKENS))
    L.append("")
    L.append("`ui/base.css`")
    L.append("")
    L.append("- " + " ".join(f"`{n}`" for n in dims))
    L.append("")
    L.append("`ui/*.css`")
    L.append("")
    L.append("- " + " ".join(f"`{n}`" for n in others))
    L.append("")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    sys.stdout.write(render())
