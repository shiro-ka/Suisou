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
        attr = f"data-suisou-{name}" if name else "data-suisou"
        L.append(f"| `{attr}` | {' '.join(f'`{v}`' for v in vals) if vals else '（値なし）'} |")
    L.append("")
    L.append("- 値は空白区切りで併記できる（`~=` で当たる）")
    L.append("- 値には段つき版がある（`s` 768px / `m` 1024px / `l` 1280px）。"
             "**記号は不等号**で、段が左・画面幅が右 ―― "
             "`s:row` は `s <= 画面`（768px 以上）、`s>none` は `s > 画面`（768px 未満）。"
             "境界のちょうど 768px は `s:` 側")
    L.append("- `theme` は**水域1つ＋生き物1つ**を空白区切りで書く（例 `\"hadal jelly\"`）。順不同")
    L.append("  - 水域だけ … アクセントの4トークンが未定義になる（焦点の輪が消える）")
    L.append("  - 生き物だけ／未宣言 … **色が全部未定義**になる（白地・黒文字・罫なし）")
    L.append("  - 同じ種類を2つ以上 … **未定義**。`palette.css` の並び順で後が勝つ")
    L.append("  - 知らない語 … 無視される")
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
    L.append("- `theme` を宣言しない要素は色を持たない（既定の色は無い）")
    L.append("- layout はモードを1つ書いて初めて `display` が入る。"
             "子側の語（`grow`）だけでは並びは変わらない")
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
    L.append("- **v2 → v3**（2026-09-15〜16）… 属性を2つ減らし、既定の色をやめ、"
             "layout の語彙を 29 語から 20 語に削った")
    L.append("  - **色**: `data-suisou-accent` を `data-suisou-theme` に畳んで**組を1つの属性**にし、"
             "`data-suisou-root` を `data-suisou-body` に改名し、"
             "`:root` の既定色を**廃止**した（宣言しなければ色が付かない）")
    L.append("    - 直し方: `theme=\"hadal\" accent=\"clown\"` → `theme=\"hadal clown\"`、"
             "`data-suisou-root` → `data-suisou-body`。どちらも機械的な置換で済む")
    L.append("    - 理由: 組を別々の属性に置くと**片方だけ書いた事故が静かに起きる**ため、"
             "掟と lint で守っていた。1属性なら構造的に起きない")
    L.append("  - **layout**: `pin` / `frame` / 区画4語（`aside` `head` `body` `foot`）/ "
             "`cols` / `share` / `hold` / `nowrap` を落とし、`cols` は `grid` として作り直し、"
             "`scroll` は `scroll-y` に改名して中身を変え、`scroll-x` を足し、"
             "`container` を4語に割って `--suisou-measure` を廃止し、"
             "`start` と `even` を落とし、`screen` を `min-screen` に改名し、"
             "`grow` の基準を `auto` から `0` に変えた")
    L.append("    - 直し方: `pin` → `stack center middle`、"
             "`frame` + 区画 → `row screen` + `stack grow`、"
             "`cols` + `--suisou-cols: N` → `grid` + "
             "`--suisou-grid-cols: repeat(N, minmax(0,1fr))`、"
             "`share` → `grow`（`--suisou-share` → `--suisou-grow`）")
    L.append("    - ★**`grow` は目で確認すること。** 基準が `auto`（中身の幅から余りを配る）から "
             "`0`（中身を無視して比で割る）に変わったので、"
             "**`grow` が2つ以上ある親は見た目が変わる**")
    L.append("    - `hold` / `nowrap` は打ち消し専用の語だったが、"
             "打ち消す相手（`grow` / `wrap`）が同じ画面幅にいると意味が無く、"
             "**現場での有効な使用が0件**だった。要るようになったら足す")
    L.append("    - `scroll`（`overflow: auto` ＝ 両軸）→ `scroll-y`"
             "（`overflow-x: hidden; overflow-y: auto; scrollbar-gutter: stable both-edges`）。"
             "**両軸に流したい実例が0件**で、横に流すものは `table=\"scroll\"` と "
             "`code` が自分で持っていた。★`scrollbar-gutter` を焼き込んだので"
             "**溢れても幅が動かない**")
    L.append("    - `screen` → `min-screen` に改名。実体が `min-height: 100dvh` なのに"
             "「ぴったり画面の高さ」と読めたため。★**横の版は持たない** ―― "
             "ブロック要素は既定で横幅いっぱいなので、`min-width` を画面に合わせたい実測が0件"
             "（`100dvw` の4件は全部 overlay の `width` で `surface` の領分）。"
             "軸が1つしかないので接尾辞で分けない")
    L.append("    - `even` を落とした。`grow` の基準を `auto` から `0` に変えたことで、"
             "`even` が子に撒く `flex: 1 1 0` と `grow` が**同じ値**になり、"
             "「余りを配る `grow` と違って中身の幅の差が残らない」という存在理由が消えた。"
             "★**layout で子に規則を撒く唯一の語**でもあったので、落とすとモードが "
             "`stack` / `row` / `grid` の3つに揃う")
    L.append("      - 直し方: `even` → `row` ＋ 子に `grow`、"
             "`stack md:even`（v2 の書き方）→ `stack s:row` ＋ 子に **`s:grow`**。"
             "★**素の `grow` を書くと狭い画面（`stack`）で縦に伸びる**ので接頭辞が要る")
    L.append("    - ★**段つきの記法を全部変えた。** 接頭辞 `md:` / `lg:` を "
             "`s:`(768) / `m:`(1024) に改名し、`l:`(1280) を新設して**3段**にした。"
             "さらに `show` の `under-md` / `under-lg` を廃止し、"
             "**「段 + 記号 + 語」の後置で記号を不等号として読む**形に統一した ―― "
             "段が左の被演算子、画面幅が右。`s:row` ＝ `s <= 画面`、"
             "`s>none` ＝ `s > 画面`。★`<` を使わないのは現場の制約で、"
             "Blogger の XML テーマが属性値中の `<` を禁止しており、"
             "SSR も `<` だけを `&lt;` に escape するため（`>` と `:` は素通り）")
    L.append("      - 直し方: `md:` → `s:`、`lg:` → `m:`。"
             "`show=\"md\"` → `show=\"s>none\"`、`show=\"under-md\"` → `show=\"s:none\"`。"
             "★**show は旧が「出る範囲」・新が「消える範囲」で逆転している**")
    L.append("    - `start`（`justify-content: flex-start`）を落とした。"
             "**flex の既定値**なので `row` でも `stack` でも空振りし、実使用0件だった。"
             "★置き方で残る空振り（`row center` / `stack stretch`）は"
             "**片方のモードでは必ず効く**ので残す ―― `row` と `stack` で交差軸の既定が"
             "違う以上、命名では消せない")
    L.append("    - `container` … `max-width: var(--suisou-measure)`（既定 64rem）1本だったのを、"
             "`container`（`clamp(46rem, 90vw, 80rem)` ＝ 画面に合わせて 736〜1280px で伸び縮み）と "
             "`container-s` / `-m` / `-l`（46 / 64 / 80rem の固定）に割った。"
             "**`--suisou-measure` は廃止** ―― 現場が任意の値を渡す口は持たない")
    L.append("      - ★**無印は親が画面幅の場所で使う。** `90vw` は画面基準なので、"
             "サイドバーの内側などに置くと親を超えて上限が効かない。"
             "親が狭い場所では固定の3つを使う")
    L.append("    - `scroll-x`（`overflow-x: auto; overflow-y: hidden`）を足した。"
             "`scroll-x s:scroll-y` で「狭いと横に流し、広いと縦に積む」。"
             "★**高さはバーの出入りで動く** ―― `scrollbar-gutter` が効くのは左右の端だけで、"
             "上下は仕様の範囲外（CSS Overflow 3）。"
             "**余白の補正は焼き込まない**（`layout` は `padding` を持たない層で、"
             "`surface.css` が後に読まれるので上書きされる）")
    L.append("- **v1 → v2**（2026-09-10）… `center` の意味を変えた。"
             "v1 では grid のモード（`display: grid; place-items: center`）、"
             "v2 では交差軸の中央に寄せるふるまい（`align-items: center`）。"
             "grid のモードは `pin` に改名した")
    L.append("  - 直し方: `layout=\"center\"` を単体で書いていたら `layout=\"pin\"` に。"
             "`stack` や `row` と併用したかった場所は、そのまま `center` が使えるようになる")
    L.append("")

    L.append("## 明文化した割り切り")
    L.append("")
    L.append("- **accent を文字に使う場所**（`button=\"accent\"` のラベル、`tag=\"accent\"`）は "
             "3.0:1 の保証（文字の 4.5 ではない）。意味色の文字は 4.5。"
             "アクセントは常に枠・下線・配置と併用する前提")
    L.append("- **ダーク専用**。純粋なライトは作らない。明るめは `shoal`（dim 階段）")
    L.append("- **JS を要求する部品は作らない**（`<link>` 1本が配布の形）")
    L.append("")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    sys.stdout.write(render())
