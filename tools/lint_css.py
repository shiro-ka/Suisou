#!/usr/bin/env python3

import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))

GENERATED = {"palette.css", "suisou.data.js"}
TARGET_DIRS = ["pages"]
TARGET_EXT = (".css", ".html", ".js")

SURFACE_STEPS = {"panel"}
ITEM_KINDS = {"media", "avatar", "tile", "field", "tag"}

sys.path.insert(0, HERE)
import solve
THEME_NAMES = {t["name"] for t in solve.THEMES}
ACCENT_NAMES = {a[0] for a in solve.ACCENTS}

COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:oklch|oklab|lab|lch|rgba?|hsla?|color)\s*\(", re.I)
COMMENT_CSS = re.compile(r"/\*.*?\*/", re.S)
COMMENT_HTML = re.compile(r"<!--.*?-->", re.S)

CODE_HTML = re.compile(r"(<(code|pre)\b[^>]*>)(.*?)(</\2>)", re.S | re.I)

def layout_modes():

    path = os.path.join(ROOT, "pages", "ui", "layout.css")
    css = COMMENT_CSS.sub("", open(path, encoding="utf-8").read())
    modes = set()
    for val, body in re.findall(r'\[data-suisou-layout~="([^"]+)"\][^{]*\{([^}]*)\}', css):
        if re.search(r"(?:^|[;{\s])(?:display|flex-direction)\s*:", body):
            modes.add(re.split(r"[:>]", val)[-1])
    return modes

LAYOUT_MODES = layout_modes()

def walk(d):

    base = os.path.join(ROOT, d)
    for dirpath, _, names in os.walk(base):
        for name in sorted(names):
            if name.endswith(TARGET_EXT):
                yield os.path.join(dirpath, name)

def targets():
    for d in TARGET_DIRS:
        for p in walk(d):
            if os.path.basename(p) not in GENERATED:
                yield p

def strip_comments(text, path):
    text = COMMENT_CSS.sub("", text)
    if path.endswith(".html"):
        text = COMMENT_HTML.sub("", text)
        text = CODE_HTML.sub(
            lambda m: m.group(1) + "\n" * m.group(3).count("\n") + m.group(4), text)
    return text

def main():
    palette = os.path.join(ROOT, "pages", "palette.css")
    if not os.path.exists(palette):
        print("palette.css が無い。先に python3 tools/solve.py を実行すること。")
        return 1

    defined = set()
    for p in walk("pages"):
        if p.endswith(".css"):
            with open(p, encoding="utf-8") as f:
                src = COMMENT_CSS.sub("", f.read())
                defined |= set(re.findall(r"--suisou-[a-z0-9-]+(?=\s*:)", src))

    problems = []
    checked = 0
    for path in targets():
        checked += 1
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        rel = os.path.relpath(path, ROOT)
        body = strip_comments(raw, path)

        for i, line in enumerate(body.splitlines(), 1):
            for hit in COLOR.findall(line):
                problems.append(f"{rel}:{i}: 色の直書き … {hit.strip()}")

        for name in sorted({m.group(1) for m in
                            re.finditer(r"var\(\s*(--suisou-[a-z0-9-]+)\s*\)", body)}):
            if name.endswith("-"):
                continue
            if name not in defined:
                problems.append(f"{rel}: 未定義の変数 … {name}")

        if path.endswith(".html"):
            for i, line in enumerate(body.splitlines(), 1):
                for m in re.finditer(r'data-suisou-tray(?:="([^"]*)")?', line):
                    vals = set((m.group(1) or "").split())

                    if "drawer" in vals:
                        continue
                    steps = SURFACE_STEPS & vals
                    if len(steps) != 1:
                        got = m.group(1) if m.group(1) is not None else "（値なし）"
                        problems.append(
                            f"{rel}:{i}: tray の段が {len(steps)} 個 … \"{got}\" "
                            f"（{' / '.join(sorted(SURFACE_STEPS))} を書く）")

                for m in re.finditer(r'data-suisou-item="([^"]*)"', line):
                    kinds = ITEM_KINDS & set(m.group(1).split())
                    if len(kinds) > 1:
                        problems.append(
                            f"{rel}:{i}: item の種類が {len(kinds)} 個 … \"{m.group(1)}\" "
                            f"（{' / '.join(sorted(kinds))} は同時に書けない。media-icon などの位置の語は組める）")

                for m in re.finditer(r'data-suisou-theme(?:="([^"]*)")?', line):
                    vals = (m.group(1) or "").split()
                    ts = [v for v in vals if v in THEME_NAMES]
                    as_ = [v for v in vals if v in ACCENT_NAMES]
                    if len(ts) != 1 or len(as_) != 1 or len(vals) != 2:
                        got = m.group(1) if m.group(1) is not None else "（値なし）"
                        problems.append(
                            f"{rel}:{i}: theme の組が揃っていない … \"{got}\" "
                            f"（水域1つ＋生き物1つを空白区切りで書く）")

                for m in re.finditer(r'data-suisou-layout(?:="([^"]*)")?', line):
                    vals = (m.group(1) or "").split()

                    for pre in ("", "s:", "m:", "l:"):
                        modes = {v[len(pre):] for v in vals
                                 if v.startswith(pre)
                                 and (pre or not re.search(r"[:>]", v))
                                 and v[len(pre):] in LAYOUT_MODES}
                        if len(modes) > 1:
                            label = f"{pre} の" if pre else ""
                            problems.append(
                                f"{rel}:{i}: layout の{label}モードが {len(modes)} 個 … "
                                f"\"{m.group(1)}\" "
                                f"（{' / '.join(sorted(pre + x for x in modes))} は同時に書けない）")

    print(f"検査 {checked} ファイル / --suisou-* の定義 {len(defined)} 種")
    if problems:
        print(f"*** {len(problems)} 件の違反 ***")
        for p in problems:
            print("  " + p)
        print("\n色の値を持てるのは solve.py の生成物だけ。"
              "手書き側は var(--suisou-*) を参照すること。")
        return 1
    print("違反なし")
    return 0

if __name__ == "__main__":
    sys.exit(main())
