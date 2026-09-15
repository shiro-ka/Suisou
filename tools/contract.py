#!/usr/bin/env python3
"""語彙の目録を CSS と solve.py から導いて標準出力に出す。

  python3 tools/contract.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
UI = os.path.join(ROOT, "pages", "ui")

sys.path.insert(0, HERE)
import solve

COMMENT = re.compile(r"/\*.*?\*/", re.S)
ATTR = re.compile(r'\[data-suisou-([a-z-]+)(?:~="([^"]+)")?\]')
STATE = re.compile(r"\[(aria-[a-z-]+|disabled|popover|open)(?:[~^]?=[^\]]*)?\]")
TOKEN_DEF = re.compile(r"(--suisou-[a-z0-9-]+)\s*:")


def ui_files():
    return [os.path.join(UI, n) for n in sorted(os.listdir(UI)) if n.endswith(".css")]


def collect():
    attrs, states = {}, set()
    for p in ui_files():
        css = COMMENT.sub("", open(p, encoding="utf-8").read())
        for name, val in ATTR.findall(css):
            vals = attrs.setdefault(name, [])
            if val:
                base = val.split(":")[-1]          # md: / lg: は同じ値の接頭辞版
                if base not in vals:
                    vals.append(base)
        states |= set(STATE.findall(css))
    # theme / accent は生成物（palette.css）側の属性なので solve から足す
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
    fixed = [n for n, _ in solve.ACCENTS if n in solve.ACCENT_JP]
    provisional = [n for n, _ in solve.ACCENTS if n not in solve.ACCENT_JP]

    L = ["# Suisou 語彙の目録"]
    L.append("")
    L.append("`pages/ui/*.css` と `tools/solve.py` から導いた一覧。"
             "**破壊的変更 ＝ ここにある名前・値・既定を変える／消すこと**（足すだけなら非破壊）。")
    L.append("")

    L.append("## 属性と値")
    L.append("")
    L.append("| 属性 | 値 |")
    L.append("|---|---|")
    for name in sorted(attrs):
        vals = attrs[name]
        L.append(f"| `data-suisou-{name}` | {' '.join(f'`{v}`' for v in vals) if vals else '（値なし）'} |")
    L.append("")
    L.append("- 値は空白区切りで併記できる（`~=` で当たる）")
    L.append("- `layout` の値には `md:` / `lg:` の接頭辞版がある（768px / 1024px、min-width）")
    L.append("- `theme` は**水域1つ＋生き物1つ**を空白区切りで書く（例 `\"hadal jelly\"`）。"
             "片方だけだとアクセント層が既定のまま残る")
    L.append(f"- 生き物のうち仮名（まだ名前が付いていない）: "
             f"{' '.join(f'`{n}`' for n in provisional)}。確定: {' '.join(f'`{n}`' for n in fixed)}")
    L.append("")

    L.append("## 借りる標準属性（状態）")
    L.append("")
    L.append("自前の data-* を発明せず、これらを見る: " + " ".join(f"`{s}`" for s in states))
    L.append("")

    L.append("## トークン")
    L.append("")
    L.append("色（`palette.css`。値を決めるのは solve.py だけ）:")
    L.append("")
    L.append("- テーマ層: " + " ".join(f"`--suisou-{n}`" for n in solve.THEME_TOKENS))
    L.append("- アクセント層: " + " ".join(f"`--suisou-{n}`" for n in solve.ACCENT_TOKENS))
    L.append("")
    L.append("寸法・書体・モーション（`ui/base.css`）:")
    L.append("")
    L.append("- " + " ".join(f"`{n}`" for n in dims))
    L.append("")

    L.append("## 既定")
    L.append("")
    L.append(f"- 属性が無いとき: `{solve.DEFAULT_THEME}` × `{solve.DEFAULT_ACCENT}`")
    L.append("- layout はモードを1つ書いて初めて `display` が入る。"
             "子側の語（`grow` / `share` / `hold`）だけでは並びは変わらない")
    L.append("- layout の子は動かない（`flex: none`）。伸びるものだけ `grow` と名指す")
    L.append("- `button=\"block\"` は左寄せ（全幅のボタンはメニューの行）")
    L.append("")

    L.append("## 配布")
    L.append("")
    L.append("- `dist/suisou.css` … 全部入り（テーマ切替できる）／"
             "`dist/suisou-<theme>-<accent>.css` … 選んだ組だけ")
    L.append("- `/v3/…` … **いま使う版**。v3 系の最新で、直せば全現場に行き渡る")
    L.append("- `/v2/…` … **凍結済み**（2026-09-15）。"
             "`theme` と `accent` が別の属性で、根が `data-suisou-root` だった頃の版")
    L.append("- `/v1/…` … **凍結済み**（2026-09-10、`07c066f` で停止）。"
             "`center` が grid のモードだった頃の版")
    L.append("- `/v/<sha7>/…` … 固定 URL。動かない")
    L.append("- **フォントは利用側が読み込む**。既定の書体は Zen Maru Gothic の 400 / 500 / 700")
    L.append("- `helpers.css` は契約外（任意。他にユーティリティが無いときだけ）。"
             "`suisou.data.js` は配布物ではない")
    L.append("")

    L.append("## 版が変わった理由")
    L.append("")
    L.append("- **v2 → v3**（2026-09-15）… 属性を2つ減らした。"
             "`data-suisou-accent` を `data-suisou-theme` に畳んで**組を1つの属性**にし、"
             "`data-suisou-root` を `data-suisou-body` に改名した")
    L.append("  - 直し方: `theme=\"hadal\" accent=\"clown\"` → `theme=\"hadal clown\"`、"
             "`data-suisou-root` → `data-suisou-body`。どちらも機械的な置換で済む")
    L.append("  - 理由: 組を別々の属性に置くと**片方だけ書いた事故が静かに起きる**ため、"
             "掟と lint で守っていた。1属性なら構造的に起きない")
    L.append("- **v1 → v2**（2026-09-10）… `center` の意味を変えた。"
             "v1 では grid のモード（`display: grid; place-items: center`）、"
             "v2 では交差軸の中央に寄せるふるまい（`align-items: center`）。"
             "grid のモードは `pin` に改名した")
    L.append("  - 直し方: `layout=\"center\"` を単体で書いていたら `layout=\"pin\"` に。"
             "`stack` や `row` と併用したかった場所は、そのまま `center` が使えるようになる")
    L.append("")

    L.append("## 明文化した割り切り")
    L.append("")
    L.append("- **accent を文字に使う場所**（outline ボタンのラベル、`tag=\"accent\"`）は "
             "3.0:1 の保証（文字の 4.5 ではない）。意味色の文字は 4.5。"
             "アクセントは常に枠・下線・配置と併用する前提")
    L.append("- **ダーク専用**。純粋なライトは作らない。明るめは `shoal`（dim 階段）")
    L.append("- **JS を要求する部品は作らない**（`<link>` 1本が配布の形）")
    L.append("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.stdout.write(render())
