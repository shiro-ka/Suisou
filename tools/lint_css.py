#!/usr/bin/env python3
"""手書き CSS/HTML/JS が掟を破っていないか検査する。

  1. 色の値が直接書かれていないか（#rrggbb / oklch() / rgb() / hsl() …）
  2. 参照している --suisou-* が palette.css に実在するか
  3. data-suisou-surface が「段」をちょうど1つ持っているか
  4. data-suisou-layout の「モード」が2つ以上書かれていないか
  5. data-suisou-theme が「水域1つ＋生き物1つ」の組になっているか

生成物（palette.css）は検査対象から外す。あれだけが色を持ってよい。

使い方:
  python3 tools/lint_css.py    # 破綻があれば exit 1
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))

GENERATED = {"palette.css", "suisou.data.js"}    # 生成物。検査しない
TARGET_DIRS = ["pages"]
TARGET_EXT = (".css", ".html", ".js")

# 面の段。必ず1つ書く。装飾（bare）だけでは「どの段か」を言っていない
SURFACE_STEPS = {"panel", "item", "none"}   # overlay は段ではなく機能の語（2026-09-18）

sys.path.insert(0, HERE)
import solve
THEME_NAMES = {t["name"] for t in solve.THEMES}
ACCENT_NAMES = {a[0] for a in solve.ACCENTS}


COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:oklch|oklab|lab|lch|rgba?|hsla?|color)\s*\(", re.I)
COMMENT_CSS = re.compile(r"/\*.*?\*/", re.S)
COMMENT_HTML = re.compile(r"<!--.*?-->", re.S)
# <code> と <pre> の中身は「表示される文字」であってマークアップではない。
# 説明のために書いた見本を実物と誤読しないよう、中身だけ落とす。
# 開始タグは残すので、そこに付いた属性はこれまで通り検査される。
# 行番号がずれないよう、落とした分は改行で埋める。
CODE_HTML = re.compile(r"(<(code|pre)\b[^>]*>)(.*?)(</\2>)", re.S | re.I)


def layout_modes():
    """並びのモードを ui/layout.css から導く。

    ★手で持たない。even を足したとき集合に入れ忘れて "stack even" が素通りし、
      縦積みを頼んだのに横に並ぶ状態になった（外部の現場が発見）。
      掟1「真実の源泉は1つ」と同じ形にして、モードを足しても直さなくて済むようにする。

    判定は「display か flex-direction を敷いているか」。これが検査の目的そのもの
    ―― 2つ書くと片方が黙って死ぬのは、その2つのプロパティを取り合うときだけ。

    ★2026-09-09 から row も集合に入る。row が flex-direction を持つように
      なったため（それまでは align-items だけで、検査の対象外だった）。
      **この関数は直していない** ―― 規則が CSS から導いているので、
      layout.css を直しただけで検査が追随した。掟1 の形が効いた実例。
    """
    path = os.path.join(ROOT, "pages", "ui", "layout.css")
    css = COMMENT_CSS.sub("", open(path, encoding="utf-8").read())
    modes = set()
    for val, body in re.findall(r'\[data-suisou-layout~="([^"]+)"\][^{]*\{([^}]*)\}', css):
        if re.search(r"(?:^|[;{\s])(?:display|flex-direction)\s*:", body):
            modes.add(re.split(r"[:>]", val)[-1])  # s: / s> の段つきは落とす
    return modes


LAYOUT_MODES = layout_modes()


def walk(d):
    """pages/ 配下を再帰的に見る。部品は pages/ui/ に1ファイルずつ置いてある。"""
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
    # 定義は palette.css（色）と手書きの CSS（余白・タイポ）の両方にある。
    # 未定義参照を拾うのが目的なので、両方を集める。
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

        # ★フォールバック付き var(--x, …) は検査しない（2026-09-17）。
        #   未定義でも動く書き方で、現場が値を渡す口はこの形になる。
        #   フォールバック無しのタイポは宣言ごと無効になるので、そちらだけ見る。
        # JS のテンプレート（var(--suisou-space-${n})）は名前が途中で切れて
        # ハイフンで終わるので、それだけ除く。
        for name in sorted({m.group(1) for m in
                            re.finditer(r"var\(\s*(--suisou-[a-z0-9-]+)\s*\)", body)}):
            if name.endswith("-"):
                continue
            if name not in defined:
                problems.append(f"{rel}: 未定義の変数 … {name}")

        if path.endswith(".html"):
            for i, line in enumerate(body.splitlines(), 1):
                for m in re.finditer(r'data-suisou-surface(?:="([^"]*)")?', line):
                    steps = SURFACE_STEPS & set((m.group(1) or "").split())
                    if len(steps) != 1:
                        got = m.group(1) if m.group(1) is not None else "（値なし）"
                        problems.append(
                            f"{rel}:{i}: surface の段が {len(steps)} 個 … \"{got}\" "
                            f"（{' / '.join(sorted(SURFACE_STEPS))} から1つ書く）")

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
                    # 段ごとに数える。s: の中で2つ書くのも同じく事故なので、
                    # 素の値と s:/m:/l: をそれぞれ別の集合として見る
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
