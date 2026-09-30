#!/usr/bin/env python3

import os, re, sys, gzip

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
PAGES = os.path.join(ROOT, "pages")
DIST = os.path.join(PAGES, "v3")

ORDER = ["base.css", "reset.css", "typeset.css", "button.css", "tray.css",
         "field.css", "item.css", "spinner.css", "layout.css", "text.css", "util.css"]

def ui_order():
    have = sorted(n for n in os.listdir(os.path.join(PAGES, "ui")) if n.endswith(".css"))
    if sorted(ORDER) != have:
        sys.exit(f"ORDER と pages/ui/*.css が合わない: {sorted(set(have) ^ set(ORDER))}")
    return [f"ui/{n}" for n in ORDER]

def slice_palette(text, theme=None, accent=None):

    if theme is None:
        return text
    out, keep, buf = [], True, []

    depth = 0
    for line in text.splitlines(keepends=True):
        if depth == 0 and line.lstrip().startswith("["):
            sel = line.split("{")[0]

            got = re.findall(r'data-suisou-theme~="([a-z]+)"', sel)
            keep = (
                not got
                or (len(got) == 1 and got[0] == theme)
                or (len(got) == 2 and got[0] == theme and got[1] == accent)
            )
        depth += line.count("{") - line.count("}")
        if keep:
            out.append(line)
    return "".join(out)

def strip(css):

    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\n{3,}", "\n\n", css)
    return "\n".join(l.rstrip() for l in css.splitlines() if l.strip())

def build(theme=None, accent=None, version="dev"):
    pal = open(os.path.join(PAGES, "palette.css"), encoding="utf-8").read()
    parts = [slice_palette(pal, theme, accent)]
    for f in ui_order():
        parts.append(open(os.path.join(PAGES, f), encoding="utf-8").read())
    body = strip("\n".join(parts))
    what = "全部入り（テーマ切替あり）" if theme is None else f"{theme} × {accent} のみ（切替なし）"
    head = (f"/*! Suisou {version} — {what}\n"
            f" * https://github.com/shiro-ka/Suisou\n"
            f" * 生成物。編集しない。 */\n")
    return head + body + "\n"

def sizes(css):
    m = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.sub(r"\s+", " ", m)
    return len(css.encode()), len(gzip.compress(m.encode(), 9))

def main():
    os.makedirs(DIST, exist_ok=True)
    sys.path.insert(0, HERE)
    import solve
    data = solve.solve()
    version = os.environ.get("SUISOU_VERSION", "dev")

    full = build(version=version)
    open(os.path.join(DIST, "suisou.css"), "w", encoding="utf-8").write(full)
    raw, gz = sizes(full)
    print(f"  suisou.css                      {raw:6d} → gzip {gz:5d}  全部入り")

    n = 0
    for t in data["themes"]:
        for an, av in t["accents"].items():
            if not av["available"]:
                continue
            css = build(t["name"], an, version)
            name = f"suisou-{t['name']}-{an}.css"
            open(os.path.join(DIST, name), "w", encoding="utf-8").write(css)
            n += 1
            if (t["name"], an) == ("hadal", "jelly"):
                raw, gz = sizes(css)
                print(f"  {name:32}{raw:6d} → gzip {gz:5d}  1組だけ")
    print(f"  組ごと {n} ファイル")

if __name__ == "__main__":
    main()
