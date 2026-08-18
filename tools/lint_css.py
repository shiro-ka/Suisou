#!/usr/bin/env python3
"""手書き CSS/HTML が掟1を破っていないか検査する。

  1. 色の値が直接書かれていないか（#rrggbb / oklch() / rgb() / hsl() …）
  2. 参照している --suisou-* が palette.css に実在するか

生成物（palette.css）は検査対象から外す。あれだけが色を持ってよい。

使い方:
  python3 tools/lint_css.py    # 破綻があれば exit 1
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))

GENERATED = {"palette.css"}                      # 唯一色を持ってよいファイル
TARGET_DIRS = ["site"]
TARGET_EXT = (".css", ".html")

COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:oklch|oklab|lab|lch|rgba?|hsla?|color)\s*\(", re.I)
COMMENT_CSS = re.compile(r"/\*.*?\*/", re.S)
COMMENT_HTML = re.compile(r"<!--.*?-->", re.S)


def targets():
    for d in TARGET_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith(TARGET_EXT) and name not in GENERATED:
                yield os.path.join(base, name)


def strip_comments(text, path):
    text = COMMENT_CSS.sub("", text)
    if path.endswith(".html"):
        text = COMMENT_HTML.sub("", text)
    return text


def main():
    palette = os.path.join(ROOT, "site", "palette.css")
    if not os.path.exists(palette):
        print("palette.css が無い。先に python3 tools/solve.py を実行すること。")
        return 1
    with open(palette, encoding="utf-8") as f:
        defined = set(re.findall(r"--suisou-[a-z-]+(?=\s*:)", f.read()))

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

        for name in sorted(set(re.findall(r"var\((--suisou-[a-z-]+)\)", body))):
            if name not in defined:
                problems.append(f"{rel}: 未定義の変数 … {name}")

    print(f"検査 {checked} ファイル / palette.css の定義 {len(defined)} 種")
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
