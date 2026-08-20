#!/usr/bin/env python3
"""配る形を組み立てる。

  dist/suisou.css                    全部入り（テーマ切替ができる）
  dist/suisou-<theme>-<accent>.css   選んだ組だけ（切替は捨てる）

★読み込み順は pages/index.html から読む。ここに順序をもう1つ書くと必ずズレる
  ―― 真実の源泉を2箇所に置かない。

使い方:
  python3 tools/bundle.py            # dist/ に書き出す
"""
import os, re, sys, gzip

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
PAGES = os.path.join(ROOT, "pages")
DIST = os.path.join(ROOT, "dist")


def ui_order():
    """index.html が並べている順そのまま。palette.css は別扱いなので外す。

    ★パターンはファイル名の形に依存させない。以前は [a-z]+ で、
      ハイフンや数字入りの名前を足すと黙って配布物から欠ける穴だった。"""
    html = open(os.path.join(PAGES, "index.html"), encoding="utf-8").read()
    files = re.findall(r'href="(ui/[^"]+\.css)"', html)
    if not files:
        sys.exit("index.html から ui/*.css の順序を読めなかった")
    return files


def slice_palette(text, theme=None, accent=None):
    """:root と、指定した組に要るブロックだけ残す。"""
    if theme is None:
        return text
    out, keep, buf = [], True, []
    # ブロック単位で走査する。セレクタ行で判定して、閉じ括弧まで持ち越す
    depth = 0
    for line in text.splitlines(keepends=True):
        if depth == 0 and line.lstrip().startswith("["):
            sel = line.split("{")[0]
            t = re.search(r'data-suisou-theme="([a-z]+)"', sel)
            a = re.search(r'data-suisou-accent="([a-z]+)"', sel)
            keep = (t is None or t.group(1) == theme) and (a is None or a.group(1) == accent)
        depth += line.count("{") - line.count("}")
        if keep:
            out.append(line)
    return "".join(out)


def strip(css):
    """コメントと -hex 文字列を落とす。★設計の記録はリポジトリが持つ ―― 配る側は
    ブラウザが読むものなので、根拠まで運ぶ必要はない。
    -hex はプレビューサイトが色コードを表示するためだけの文字列で、
    描画には使われない（全部入りで gzip の2割を占めていた）。"""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = "\n".join(l for l in css.splitlines()
                    if not re.match(r"\s*--suisou-[a-z0-9-]+-hex:", l))
    css = re.sub(r"\n{3,}", "\n\n", css)
    return "\n".join(l.rstrip() for l in css.splitlines() if l.strip())


def build(theme=None, accent=None, version="dev"):
    parts = []
    for f in ui_order():
        parts.append(open(os.path.join(PAGES, f), encoding="utf-8").read())
    pal = open(os.path.join(PAGES, "palette.css"), encoding="utf-8").read()
    parts.append(slice_palette(pal, theme, accent))
    body = strip("\n".join(parts))
    what = "全部入り（テーマ切替あり）" if theme is None else f"{theme} × {accent} のみ（切替なし）"
    head = (f"/*! Suisou {version} — {what}\n"
            f" * https://github.com/shiro-ka/Suisou\n"
            f" * 生成物。編集しない。設計の根拠はリポジトリの ui/*.css と .notes/ にある。 */\n")
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
