#!/usr/bin/env python3
"""
palette solver — 正準実装（single source of truth）

このファイルだけが色を決める。生成物:
  pages/palette.css    … サイトと適用先が読む CSS 変数
  pages/suisou.data.js … 切替 UI が読む構造（色は持たない）
  spec-tables.md       … 仕様書 §6/§7/§8/§11 に差し込む表

手で書いた表を仕様書に置かない。ドリフトの原因はそれだった。

使い方:
  python3 solve.py          # 生成して差分を表示
  python3 solve.py --check  # 生成せず検証だけ（破綻があれば exit 1）
"""
import json, math, sys, os

# ============================================================ OKLCH core
def to_srgb(L, C, H):
    a = C * math.cos(math.radians(H)); b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    return (+4.0767416621*l - 3.3077115913*m + 0.2309699292*s,
            -1.2684380046*l + 2.6097574011*m - 0.3413193965*s,
            -0.0041960863*l - 0.7034186147*m + 1.7076147010*s)

def in_gamut(L, C, H):
    return all(-1e-4 <= c <= 1+1e-4 for c in to_srgb(L, C, H))

def _enc(c):
    c = min(max(c, 0), 1)
    return 12.92*c if c <= 0.0031308 else 1.055*c**(1/2.4) - 0.055

def hexof(L, C, H):
    return "#" + "".join("%02x" % round(_enc(c)*255) for c in to_srgb(L, C, H))

def lum(L, C, H):
    r, g, b = [min(max(c, 0), 1) for c in to_srgb(L, C, H)]
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast(x, y):
    a, b = lum(*x), lum(*y)
    if a < b: a, b = b, a
    return (a + 0.05) / (b + 0.05)

_MC = {}
def maxC(L, H):
    k = (round(L, 4), round(H, 2))
    if k in _MC: return _MC[k]
    lo, hi = 0.0, 0.5
    for _ in range(48):
        m = (lo + hi) / 2
        if in_gamut(L, m, H): lo = m
        else: hi = m
    _MC[k] = lo
    return lo

def _lab(L, C, H):
    return (L, C*math.cos(math.radians(H)), C*math.sin(math.radians(H)))

def dE(c1, c2):
    a, b = _lab(*c1), _lab(*c2)
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

# ============================================================ 定義（人が決めるもの）
# 面の階段。bg < panel < item < overlay の順に明るく（＝手前に）なる。
# item は「面の上に載るもの」。入力欄だけでなく、入れ子の容れ物やタグにも使う。
# Akuarium も同じ概念を item と呼んでいた（--item-bd-l / .blackish-item-bg）。
# ★tint は面の階段（bg < panel < item < overlay）の段ではない。
#   選択と意味色の「下地」の明度で、上に載る罫（line-weak / line-strong）から
#   決まる。36 だったときは誰も検査していなかったので line-weak が 1.36:1 で
#   割れていた。33 まで下げて 1.50:1 / 3.08:1 を確保している。
#   overlay(34) より下になるが、別の軸なので順序の問題ではない。
LADDERS = {
    # dark … 通常のダーク
    "dark": {"bg":.15, "panel":.22, "item":.28, "overlay":.34, "tint":.33,
             "line-weak":.44, "line-strong":.61, "text-disabled":.62,
             "accent":.74, "text-sub":.78, "text-main":.94},
    # dim … ライト志向のユーザーに投げる明るめの階段。極性は反転しない。
    #        bg を L30 より上げると本文 4.5:1 を満たす L が色域外に出る。
    "dim":  {"bg":.26, "panel":.33, "item":.39, "overlay":.45, "tint":.44,
             "line-weak":.55, "line-strong":.73, "text-disabled":.74,
             "accent":.80, "text-sub":.90, "text-main":.955},
}
SEM_HUE = {"error": 22, "warning": 90, "success": 155}
SEM_L = {
    "dark": {"error":.73, "warning":.82, "success":.76},
    "dim":  {"error":.85, "warning":.85, "success":.83},
}
# テーマ名は水域。深いほど光が届かず、面の色が薄くなる。
# 階段の名前（dark / dim）とは別物。shoal が dim 階段を使うだけで、名前は衝突しない。
THEMES = [
    {"name":"hadal",  "jp":"超深海層", "ladder":"dark", "h":286, "cs":0.006, "ar":0.85},  # ほぼ無彩色
    {"name":"trench", "jp":"海溝",     "ladder":"dark", "h":265, "cs":0.018, "ar":0.65},
    {"name":"fjord",  "jp":"峡湾",     "ladder":"dark", "h":272, "cs":0.030, "ar":0.60},  # 最も色づく（旧 nord-ish）
    {"name":"shoal",  "jp":"浅瀬",     "ladder":"dim",  "h":265, "cs":0.020, "ar":0.60},  # 唯一明るい階段
]
ACCENTS = [("clown",55),("turtle",122),("teal",188),("jelly",212),("blue",255),
           ("indigo",282),("coral",308),("magenta",332),("seal",355)]
# 確定した名前だけ和名を持つ。無いものは仮名（まだ生き物になっていない）。
# seal は旧 pink（2026-08-21 確定）。
ACCENT_JP = {"clown":"カクレクマノミ", "turtle":"ウミガメ", "jelly":"クラゲ",
             "coral":"サンゴ", "seal":"アザラシ"}

# 制約のしきい値
FLOOR = {"hover":0.03, "selected":0.055, "semantic":0.055, "textSub":0.08}
SEM_OFFSET = 0.15      # 意味色はアクセントより常にこれだけ強い（経験値）
ACTIVE_DL  = -0.03
SCRIM_ALPHA = 0.72
SURFACES = ["panel", "item", "overlay"]   # item … 面の上に載るもの（入力欄・入れ子の容れ物など）
JND = 0.02

PAIRS = [  # (ink, surface, 必要比, 用途)
    ("line-weak","overlay",1.5,"装飾罫"),
    ("line-strong","overlay",3.0,"入力枠 1.4.11"),
    ("line-strong","item",3.0,"入力枠 1.4.11"),
    ("text-sub","overlay",4.5,"本文"),
    ("text-main","overlay",4.5,"本文"),
    ("accent","overlay",3.0,"UI 部品"),
    ("accent","panel",3.0,"UI 部品"),
    ("accent-active","overlay",3.0,"UI 部品(押下)"),
    ("text-main","selected-surface",4.5,"選択行の文字"),
    ("text-main","hover-surface",4.5,"hover 行の文字"),
    ("line-weak","hover-surface",1.5,"hover 行の装飾罫"),
    ("line-strong","hover-surface",3.0,"hover 行の入力枠 1.4.11"),
    # ★選択下地の上に載るもの。ここが長らく未検査で、掟2 の違反が隠れていた。
    #   選択行の中の Tag の罫がまさに line-weak on selected-surface。
    ("line-weak","selected-surface",1.5,"選択行の装飾罫"),
    ("line-strong","selected-surface",3.0,"選択行の入力枠 1.4.11"),
    ("line-weak","selected-neutral-surface",1.5,"選択行(中立)の装飾罫"),
    ("line-strong","selected-neutral-surface",3.0,"選択行(中立)の入力枠 1.4.11"),
    ("text-main","selected-neutral-surface",4.5,"選択行(中立)の文字"),
    ("error","overlay",4.5,"状態文言"),
    ("warning","overlay",4.5,"状態文言"),
    ("success","overlay",4.5,"状態文言"),
    # ★4.5 なのは枠(3.0)と文字の兼用だから。danger ボタンは hover で
    #   error-surface を敷き、その上のラベルが error のまま ―― 文字の基準で縛る。
    #   以前は 3.0（枠）でしか縛っておらず、実測 4.88 で「守っているのに
    #   約束していない」状態だった。階段を動かしたときに CI が守れるようにする。
    ("text-main","error-surface",4.5,"バナーの文字"),
    ("error","error-surface",4.5,"バナーの枠 / danger ボタンの文字"),
    ("error-active","error-surface",3.0,"danger ボタン(押下)"),
    ("error-active","overlay",3.0,"danger ボタン(押下)"),
]

# ============================================================ 導出
def resolve_text_main(t):
    """目標 L から下げて、色域に入る最大 L を返す"""
    L = LADDERS[t["ladder"]]["text-main"]
    while L > 0.80 and not in_gamut(L, t["cs"], t["h"]):
        L -= 0.005
    return round(L, 3)

def resolve_hover(t):
    """hover 下地。面の色相のまま暗い側へ下げ、全面と ΔE >= フロアになる最大の L。

    アクセントの色相を使わない = アクセントに依存しない。テーマ層のトークンになるので、
    アクセントを足しても hover は解き直しにならない。

    明るい側に下げない理由は実測。明るくすると hover した面の上で line-weak が
    1.34:1 / line-strong が 2.74:1 まで落ちる（必要値 1.5 / 3.0）。
    暗い側なら載るインクのコントラストはむしろ上がる。
    """
    D = LADDERS[t["ladder"]]
    faces = ["bg"] + SURFACES
    L = D["tint"]
    while L > 0.02 and min(dE((L, t["cs"], t["h"]), (D[s], t["cs"], t["h"]))
                           for s in faces) < FLOOR["hover"]:
        L -= 0.001
    return round(L, 3)

def resolve_tint(t, h, floor):
    """載りうる全面に対して ΔE >= floor を満たす最小 C。

    ★フロアに届かない場合も None を返さず、色域内で届く限りの最大 C を返す。
      「その色は出せない」ではなく「その色では区別しにくい」が実態なので、
      値は出しておいて、推奨しない理由として警告に載せる（掟2 の運用を参照）。"""
    D = LADDERS[t["ladder"]]
    L, ceil = D["tint"], maxC(D["tint"], h)
    worst = lambda C: min(dE((L, C, h), (D[s], t["cs"], t["h"])) for s in SURFACES)
    if worst(ceil) < floor: return ceil        # 届かない。届く限りを返す
    lo, hi = 0.0, ceil
    for _ in range(48):
        m = (lo + hi) / 2
        if worst(m) < floor: lo = m
        else: hi = m
    return hi

def tint_reaches(t, h, floor):
    """resolve_tint の返り値がフロアを満たしているか。警告の判定に使う"""
    D = LADDERS[t["ladder"]]
    L = D["tint"]
    C = resolve_tint(t, h, floor)
    return min(dE((L, C, h), (D[s], t["cs"], t["h"])) for s in SURFACES) >= floor - 1e-9

def sem_ratio(ar):
    return min(0.95, ar + SEM_OFFSET)

def tokens(t, acc_name, acc_h):
    D = LADDERS[t["ladder"]]
    o = {}
    for k in ["bg","panel","item","overlay","line-weak","line-strong","text-disabled","text-sub"]:
        o[k] = (D[k], t["cs"], t["h"])
    o["text-main"] = (resolve_text_main(t), t["cs"], t["h"])
    o["scrim"]     = (0.08, t["cs"], t["h"])
    o["accent"]        = (D["accent"], maxC(D["accent"], acc_h) * t["ar"], acc_h)
    o["accent-active"] = (D["accent"]+ACTIVE_DL, maxC(D["accent"]+ACTIVE_DL, acc_h) * t["ar"], acc_h)
    o["focus-ring"]    = o["accent"]
    o["hover-surface"] = (resolve_hover(t), t["cs"], t["h"])   # 中立。アクセントに依存しない
    # 選択の下地は2つ出す。現場が「色で示す」か「明るさだけで示す」かを選ぶ。
    # 明度はどちらも tint で同じ。違うのは彩度だけ（hadal で 0.053 と 0.006）。
    o["selected-surface"] = (D["tint"], resolve_tint(t, acc_h, FLOOR["selected"]), acc_h)
    o["selected-neutral-surface"] = (D["tint"], t["cs"], t["h"])       # 中立。アクセントに依存しない
    sr = sem_ratio(t["ar"])
    for n, h in SEM_HUE.items():
        L = SEM_L[t["ladder"]][n]
        o[n] = (L, maxC(L, h) * sr, h)
        # 押下色。accent-active と同じ作り（同じだけ暗くして彩度を再クランプ）。
        # danger ボタンが押しても色を変えられなかったのはこれが無かったため。
        o[n+"-active"] = (L+ACTIVE_DL, maxC(L+ACTIVE_DL, h) * sr, h)
        o[n+"-surface"] = (D["tint"], resolve_tint(t, h, FLOOR["selected"]), h)
    return o

# ============================================================ 制約チェック
def accent_blocking(t, acc_name, acc_h):
    """出せない理由。色域外だけ。ここが空でない組は CSS に出さない。

    色域外は「意図した色が表示できない」＝ブラウザが勝手に丸めるので、
    Suisou が保証している値と実際に出る色が食い違う。これは出せない。
    見るのは CSS に出すトークンだけ ―― 計算だけして出さないもの（棚卸しで
    落とした warning-active など）が組み合わせを道連れにしないようにする。"""
    k = tokens(t, acc_name, acc_h)
    return [f"{n} が色域外" for n, v in k.items()
            if v and (n in THEME_TOKENS or n in ACCENT_TOKENS) and not in_gamut(*v)]


def accent_issues(t, acc_name, acc_h):
    """推奨しない理由。★ここが空でなくても CSS には出す（掟2 の運用）。

    どれも「表示できない」ではなく「区別しにくい」。使う側が承知の上で
    選べばいい話なので、値は出しておいて理由だけ添える。"""
    k = tokens(t, acc_name, acc_h)
    bad = []
    if not tint_reaches(t, acc_h, FLOOR["selected"]):
        d = min(dE((LADDERS[t["ladder"]]["tint"], resolve_tint(t, acc_h, FLOOR["selected"]), acc_h),
                   (LADDERS[t["ladder"]][sf], t["cs"], t["h"])) for sf in SURFACES)
        bad.append(f"選択下地が面と近い ΔE {d:.3f}（目標 {FLOOR['selected']}）")
    for st in ("accent", "accent-active"):
        if contrast(k[st], k["overlay"]) < 3.0:
            bad.append(f"{st} のコントラスト不足 {contrast(k[st], k['overlay']):.2f}:1")
        d = dE(k[st], k["text-sub"])
        if d < FLOOR["textSub"]: bad.append(f"{st} が text-sub と近い ΔE {d:.3f}")
    near = min(((dE(k["accent"], k[n]), n) for n in SEM_HUE))
    if near[0] < FLOOR["semantic"]: bad.append(f"{near[1]} と近い ΔE {near[0]:.3f}")
    if dE(k["selected-surface"], k["hover-surface"]) < JND:
        bad.append("hover と選択が近すぎ")
    # 中立版の選択下地も hover と区別がつく必要がある。こちらは同じ色相なので
    # 差は明度だけ（tint と hover の段差）。段を詰めたときに真っ先に壊れる。
    if dE(k["selected-neutral-surface"], k["hover-surface"]) < JND:
        bad.append("hover と選択（中立）が近すぎ")
    return bad

def pair_results(t, acc_name, acc_h):
    k = tokens(t, acc_name, acc_h)
    rows = []
    for a, b, need, note in PAIRS:
        if k.get(a) is None or k.get(b) is None:
            rows.append({"a":a,"b":b,"need":need,"note":note,"value":None,"pass":False})
            continue
        v = contrast(k[a], k[b])
        rows.append({"a":a,"b":b,"need":need,"note":note,"value":round(v,2),"pass":v>=need})
    return rows

def gamut_failures(t, acc_name, acc_h):
    return [n for n, v in tokens(t, acc_name, acc_h).items() if v and not in_gamut(*v)]

# ============================================================ 解いて JSON に
def solve():
    out = {
        "version": "1.4",
        "floors": FLOOR, "semOffset": SEM_OFFSET, "activeDL": ACTIVE_DL,
        "scrimAlpha": SCRIM_ALPHA, "jnd": JND,
        "ladders": LADDERS, "semHue": SEM_HUE, "semL": SEM_L,
        "accentHues": {n: h for n, h in ACCENTS},
        "pairs": [{"a":a,"b":b,"need":n,"note":note} for a,b,n,note in PAIRS],
        "themes": [], "failures": [],
    }
    for t in THEMES:
        entry = {"name":t["name"], "jp":t["jp"], "ladder":t["ladder"], "h":t["h"], "cs":t["cs"],
                 "ar":t["ar"], "semRatio": round(sem_ratio(t["ar"]),3),
                 "textMainL": resolve_text_main(t), "accents": {}}
        for an, ah in ACCENTS:
            block = accent_blocking(t, an, ah)
            bad = accent_issues(t, an, ah)
            tk = tokens(t, an, ah)
            entry["accents"][an] = {
                "hue": ah,
                "available": not block,            # 出すかどうか
                "recommended": not block and not bad,   # 勧めるかどうか
                "blocking": block, "issues": bad,
                "tokens": {n: (None if v is None else
                              {"L":round(v[0],4),"C":round(v[1],4),"H":v[2],"hex":hexof(*v)})
                           for n, v in tk.items()},
                "pairs": pair_results(t, an, ah),
            }
            for g in block:
                out["failures"].append(f"{t['name']}/{an}: {g}")
            for r in pair_results(t, an, ah):
                # ★推奨する組み合わせだけを構造的破綻として数える。
                #   推奨しない組は「見づらいと承知で使うもの」なので、
                #   基準を満たさないのは当たり前。二重に数えない。
                if not r["pass"] and not bad and not block:
                    out["failures"].append(
                        f"{t['name']}/{an}: {r['a']} on {r['b']} "
                        f"{r['value']}:1 < {r['need']}")
            out.setdefault("notRecommended", [])
            if bad and not block:
                out["notRecommended"].append(f"{t['name']}/{an}: {bad[0]}")
        out["themes"].append(entry)
    # 色相カテゴリのリスク（ΔE では測れないもの）
    out["hueCategoryRisk"] = [
        {"accent":an, "semantic":sn, "deg":round(hue_dist(ah, sh))}
        for an, ah in ACCENTS for sn, sh in SEM_HUE.items() if hue_dist(ah, sh) < 40
    ]
    return out

# ============================================================ 生成
HERE = os.path.dirname(os.path.abspath(__file__))

# CSS の層分け。どちらに属するかは値の依存関係で決まっていて、任意ではない。
#   テーマ層   … 全アクセントで同値。面・文字・意味色
#   アクセント層 … アクセントで変わる。かつテーマをまたぐと値も変わるので、
#                 テーマとの組でしか定義できない（複合セレクタになる理由）
# ★出すのは使っているものだけ（2026-08-20 棚卸し）。
#   on-accent … 塗るボタンが無いので載せる文字が無い。チェックボックスのレの字は
#               ブラウザが accent-color から自動で決める（base.css）。
#   warning-active / success-active … 押せる意味色は danger（error）だけ。
#   計算は tokens() が全部やっている。使う部品ができたらここに足すだけで出る。
THEME_TOKENS = ["bg", "panel", "item", "overlay", "hover-surface", "selected-neutral-surface",
                "line-weak", "line-strong", "text-disabled", "text-sub", "text-main",
                "scrim",
                "error", "warning", "success",
                "error-active",
                "error-surface", "warning-surface", "success-surface"]
ACCENT_TOKENS = ["accent", "accent-active", "focus-ring", "selected-surface"]

# 属性が無いときの既定。色ではなく「どれを既定に見せるか」の選択なので、ここに置く。
DEFAULT_THEME  = "hadal"
DEFAULT_ACCENT = "jelly"

def css_color(v, alpha=None):
    L, C, H = v
    a = "" if alpha is None else f" / {alpha}"
    return f"oklch({L*100:.2f}% {C:.4f} {H}{a})"

def css_block(selector, names, tk, indent=""):
    """色と、その色コードを文字列として持つ変数を並べて出す。

    CSS は変数の値を文字として表示できない。かといって色コードを手で書けば
    掟1違反になる。ここで両方を出しておき、表示側は -hex を読むだけにする。
    """
    L = [f"{indent}{selector} {{"]
    for n in names:
        d = tk[n]
        if d is None:                       # 解が無かったトークンは出さない
            L.append(f"{indent}  /* --suisou-{n}: 解なし */")
            continue
        alpha = SCRIM_ALPHA if n == "scrim" else None
        L.append(f"{indent}  --suisou-{n}: {css_color((d['L'], d['C'], d['H']), alpha)};")
        L.append(f'{indent}  --suisou-{n}-hex: "{d["hex"]}";')
    L.append(f"{indent}}}")
    return L

def write_css(data):
    """サイトと適用先が読む CSS 変数。手で色を書かないための生成物。"""
    L = []
    L.append("/* GENERATED by solve.py — 手で編集しない */")
    L.append("/*")
    L.append("  使い方:")
    L.append("")
    L.append(f'    <html data-suisou-theme="{DEFAULT_THEME}" data-suisou-accent="{DEFAULT_ACCENT}">')
    L.append("")
    L.append("  テーマとアクセントは必ず同じ要素に書くこと。")
    L.append("  アクセントの値はテーマごとに違う（面との ΔE で C を解いているため）ので、")
    L.append("  片方だけを別の要素に置くと、噛み合わない組の色が出る。")
    L.append("")
    L.append("  入れ子にすれば領域ごとに別テーマにできる。プレビューはこれで並べている。")
    L.append("*/")
    L.append("")

    themes = {t["name"]: t for t in data["themes"]}
    dt = themes[DEFAULT_THEME]
    dtk = dt["accents"][DEFAULT_ACCENT]["tokens"]
    L.append(f"/* 属性が無いときの既定 … {DEFAULT_THEME} / {DEFAULT_ACCENT} */")
    L += css_block(":root", THEME_TOKENS + ACCENT_TOKENS, dtk)
    L.append("")

    L.append("/* ── テーマ層 ───────────────────────────── */")
    for t in data["themes"]:
        any_tokens = next(iter(t["accents"].values()))["tokens"]
        L.append("")
        L += css_block(f'[data-suisou-theme="{t["name"]}"]', THEME_TOKENS, any_tokens)
    L.append("")

    L.append("/* ── アクセント層（テーマとの組でしか決まらない） ── */")
    skipped, warned = [], []
    for t in data["themes"]:
        L.append("")
        for an, a in t["accents"].items():
            if not a["available"]:
                skipped.append(f"{t['name']}/{an}: {a['blocking'][0]}")
                continue
            sel = f'[data-suisou-theme="{t["name"]}"][data-suisou-accent="{an}"]'
            if not a["recommended"]:
                warned.append(f"{t['name']}/{an}: {a['issues'][0]}")
                L.append(f"/* ★推奨しない … {a['issues'][0]} */")
            L += css_block(sel, ACCENT_TOKENS, a["tokens"])
    L.append("")
    L.append("/* ★推奨しない組み合わせ（値は出してある。見づらいだけで壊れてはいない）:")
    for s in warned:
        L.append(f"     {s}")
    L.append("*/")
    L.append("")
    L.append("/* 出していない組み合わせ（色域外。意図した色が表示できない）:")
    for s in skipped:
        L.append(f"     {s}")
    L.append("   これらを指定しても CSS は無反応で、:root の既定アクセントが残る。")
    L.append("   静かに噛み合わない色になるので、指定する側で避けること。 */")

    # サイトが読む資産なので pages/ に置く。pages/ 単体で開けるようにするため。
    p = os.path.join(HERE, os.pardir, "pages", "palette.css")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    p = os.path.normpath(p)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return p

def _hue_risk(data):
    """{アクセント名: [{semantic, deg}, ...]}。ΔE では測れないリスクの受け渡し用"""
    out = {}
    for r in sorted(data["hueCategoryRisk"], key=lambda x: x["deg"]):
        out.setdefault(r["accent"], []).append({"semantic": r["semantic"], "deg": r["deg"]})
    return out


def write_site_data(data):
    """サイトの切替 UI が読む構造データ。色は持たない（色は palette.css の担当）。

    可用性をここに出すのは、テーマを切り替えたときに使えないアクセントへ
    落ちるのを防ぐため。CSS 側は存在しない組に無反応なので、静かに既定色へ
    戻ってしまう。それを UI 側で避けられるようにする。
    """
    out = {
        "themes": [{"name": t["name"], "jp": t["jp"], "ladder": t["ladder"],
                    "h": t["h"], "cs": t["cs"],
                    "available": [a for a, v in t["accents"].items() if v["available"]],
                    "recommended": [a for a, v in t["accents"].items() if v["recommended"]],
                    "warnings": {a: v["issues"][0] for a, v in t["accents"].items()
                                 if v["available"] and not v["recommended"]}}
                   for t in data["themes"]],
        "accents": [{"name": n, "jp": ACCENT_JP.get(n, ""), "hue": h} for n, h in ACCENTS],
        # 色相が近い組。ΔE では測れないので別に持つ。アクセントを選ぶ画面で出す
        "hueRisk": _hue_risk(data),
        "themeTokens": THEME_TOKENS,
        "accentTokens": ACCENT_TOKENS,
        "default": {"theme": DEFAULT_THEME, "accent": DEFAULT_ACCENT},
    }
    p = os.path.normpath(os.path.join(HERE, os.pardir, "pages", "suisou.data.js"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("/* GENERATED by solve.py — 手で編集しない */\n")
        f.write("const SUISOU = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    return p

def write_tables(data):
    """仕様書に差し込む表。手書きの表を仕様書から消すための生成物。"""
    L = []
    L.append("<!-- GENERATED by tools/solve.py — 手で編集しない -->\n")
    L.append("### L 階段（2系統）\n")
    keys = ["bg","panel","item","overlay","tint","line-weak","line-strong",
            "text-disabled","accent","text-sub","text-main"]
    L.append("| | dark | dim |\n|---|---|---|")
    for k in keys:
        L.append(f"| {k} | {LADDERS['dark'][k]*100:.0f} | {LADDERS['dim'][k]*100:.0f} |")
    L.append("")
    L.append("### テーマ\n")
    L.append("| テーマ | 階段 | H | 面C | 強さ | 意味色倍率 | text-main | 使えるアクセント |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in data["themes"]:
        ok = [a for a, v in t["accents"].items() if v["recommended"]]
        L.append(f"| `{t['name']}` | {t['ladder']} | {t['h']} | {t['cs']} | ×{t['ar']} | "
                 f"×{t['semRatio']} | L{t['textMainL']*100:.1f} | **{len(ok)}/{len(ACCENTS)}** |")
    L.append("")
    L.append("### アクセント可用性\n")
    L.append("全部の組み合わせを CSS に出している。下の「推奨しない」も選べる ―― "
             "見づらいだけで壊れてはいないため。\n")
    for t in data["themes"]:
        ok = [a for a, v in t["accents"].items() if v["recommended"]]
        ng = [(a, v["issues"][0]) for a, v in t["accents"].items()
              if v["available"] and not v["recommended"]]
        no = [(a, v["blocking"][0]) for a, v in t["accents"].items() if not v["available"]]
        L.append(f"- **{t['name']}** … {', '.join(ok)}")
        if ng:
            L.append(f"  - ★推奨しない: " + " / ".join(f"{a}（{r}）" for a, r in ng))
        if no:
            L.append(f"  - 出していない: " + " / ".join(f"{a}（{r}）" for a, r in no))
    L.append("")
    L.append("### コントラスト検証（全テーマ × 使用可能アクセント中の最悪値）\n")
    worst = {}
    for t in data["themes"]:
        for an, av in t["accents"].items():
            if not av["recommended"]: continue
            for r in av["pairs"]:
                key = (r["a"], r["b"])
                if r["value"] is None: continue
                if key not in worst or r["value"] < worst[key][0]:
                    worst[key] = (r["value"], r["need"], t["name"], an, r["note"])
    L.append("| ペア | 最悪値 | 必要 | 最悪ケース | 用途 |")
    L.append("|---|---|---|---|---|")
    for (a, b), (v, need, tn, an, note) in sorted(worst.items(), key=lambda x: x[1][0]/x[1][1]):
        mark = "" if v >= need else " ⚠"
        L.append(f"| `{a}` on `{b}` | {v:.2f}:1{mark} | {need} | {tn}/{an} | {note} |")
    L.append("")
    L.append("### 色相カテゴリのリスク（ΔE では測れない）\n")
    L.append("| アクセント | 意味色 | 色相差 |")
    L.append("|---|---|---|")
    for r in sorted(data["hueCategoryRisk"], key=lambda x: x["deg"]):
        L.append(f"| `{r['accent']}` | `{r['semantic']}` | {r['deg']}度 |")
    L.append("")
    L.append("<!-- /GENERATED -->")
    p = os.path.join(HERE, "spec-tables.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return p

if __name__ == "__main__":
    data = solve()
    check_only = "--check" in sys.argv
    n_ok = sum(1 for t in data["themes"] for v in t["accents"].values() if v["recommended"])
    n_out = sum(1 for t in data["themes"] for v in t["accents"].values() if v["available"])
    n_all = len(data["themes"]) * len(ACCENTS)
    print(f"themes {len(data['themes'])} / accent combos "
          f"{n_out}/{n_all} 出力 ・ {n_ok}/{n_all} 推奨")
    if data["failures"]:
        print(f"*** {len(data['failures'])} structural failures ***")
        for f_ in data["failures"][:20]: print("  " + f_)
    else:
        print("structural failures: 0")
    if data.get("notRecommended"):
        print(f"not recommended: {len(data['notRecommended'])}")
        for f_ in data["notRecommended"]: print("  ★ " + f_)
    for t in data["themes"]:
        ng = [a for a, v in t["accents"].items() if not v["recommended"]]
        print(f"  {t['name']:9s} text-main L{t['textMainL']*100:.1f}  "
              f"推奨 {len(ACCENTS)-len(ng)}/{len(ACCENTS)}"
              + (f"  ★{', '.join(ng)}" if ng else ""))
    if check_only:
        sys.exit(1 if data["failures"] else 0)
    print("wrote:", write_tables(data))
    print("wrote:", write_css(data))
    print("wrote:", write_site_data(data))
