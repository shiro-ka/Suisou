#!/usr/bin/env python3

import html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))

GENERATED = {"palette.css", "suisou.data.js"}
TARGET_DIRS = ["pages"]
TARGET_EXT = (".css", ".html", ".js")

TRAY_EDGES = {"right", "left", "top", "bottom"}
ITEM_KINDS = {"media", "avatar", "tile", "field", "tag", "banner"}
BANNER_KINDS = {"error", "warning", "success"}

sys.path.insert(0, HERE)
import solve
import contract
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

HTML_ATTR = re.compile(r"""(?<![\w-])(data-suisou(?:-[a-z]+)*)(?:\s*=\s*(["'])(.*?)\2)?(?![\w-])""", re.S)

HTML_TAG = re.compile(r"<[a-zA-Z][^<>]*>", re.S)

def html_attrs(body):
    for t in HTML_TAG.finditer(body):
        for m in HTML_ATTR.finditer(t.group(0)):
            raw = None if m.group(2) is None else html.unescape(m.group(3))
            yield body.count("\n", 0, t.start() + m.start()) + 1, m.group(1), raw

def vocab():
    attrs, staged, _, _, _ = contract.collect()
    def words(name):
        out = set(attrs.get(name, []))
        for sep, ws in staged.get(name, {}).items():
            out |= {f"{p}{sep}{w}" for p in "sml" for w in ws}
        return out
    known = {f"data-suisou-{n}" if n else "data-suisou" for n in attrs}
    return words(""), words("layout"), known

UTIL_WORDS, LAYOUT_WORDS, KNOWN_ATTRS = vocab()

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
            for i, name, raw in html_attrs(body):
                vals = None if raw is None else raw.split()

                if name not in KNOWN_ATTRS:
                    problems.append(f"{rel}:{i}: Suisou に無い属性 … {name}")

                elif name == "data-suisou-tray":
                    if not vals:
                        continue
                    edges = TRAY_EDGES & set(vals)
                    if set(vals) - TRAY_EDGES != {"drawer"} or len(edges) != 1:
                        problems.append(
                            f"{rel}:{i}: tray の値 … \"{raw}\" "
                            f"（値なしで panel。drawer は {' / '.join(sorted(TRAY_EDGES))} を1つ添える）")

                elif name == "data-suisou-item" and vals:
                    kinds = ITEM_KINDS & set(vals)
                    if len(kinds) > 1:
                        problems.append(
                            f"{rel}:{i}: item の種類が {len(kinds)} 個 … \"{raw}\" "
                            f"（{' / '.join(sorted(kinds))} は同時に書けない。media-icon などの位置の語は組める）")
                    if "banner" in kinds:
                        bk = BANNER_KINDS & set(vals)
                        if len(bk) != 1:
                            problems.append(
                                f"{rel}:{i}: banner の知らせの種類が {len(bk)} 個 … \"{raw}\" "
                                f"（{' / '.join(sorted(BANNER_KINDS))} を1つ書く）")

                elif name == "data-suisou-theme":
                    vals = vals or []
                    ts = [v for v in vals if v in THEME_NAMES]
                    as_ = [v for v in vals if v in ACCENT_NAMES]
                    if len(ts) != 1 or len(as_) != 1 or len(vals) != 2:
                        got = raw if raw is not None else "（値なし）"
                        problems.append(
                            f"{rel}:{i}: theme の組が揃っていない … \"{got}\" "
                            f"（水域1つ＋生き物1つを空白区切りで書く）")

                elif name == "data-suisou-layout":
                    vals = vals or []
                    for pre in ("", "s:", "m:", "l:"):
                        modes = {v[len(pre):] for v in vals
                                 if v.startswith(pre)
                                 and (pre or not re.search(r"[:>]", v))
                                 and v[len(pre):] in LAYOUT_MODES}
                        if len(modes) > 1:
                            label = f"{pre} の" if pre else ""
                            problems.append(
                                f"{rel}:{i}: layout の{label}モードが {len(modes)} 個 … "
                                f"\"{raw}\" "
                                f"（{' / '.join(sorted(pre + x for x in modes))} は同時に書けない）")
                    moved = [v for v in vals if v in UTIL_WORDS and v not in LAYOUT_WORDS]
                    if moved:
                        problems.append(
                            f"{rel}:{i}: layout に data-suisou の語 … {' '.join(moved)} "
                            f"（data-suisou=\"{' '.join(moved)}\" に書く）")

    print(f"検査 {checked} ファイル / --suisou-* の定義 {len(defined)} 種")
    if problems:
        print(f"*** {len(problems)} 件の違反 ***")
        for p in problems:
            print("  " + p)
        if any(": 色の直書き … " in p for p in problems):
            print("\n色の値を持てるのは solve.py の生成物だけ。"
                  "手書き側は var(--suisou-*) を参照すること。")
        return 1
    print("違反なし")
    return 0

if __name__ == "__main__":
    sys.exit(main())
