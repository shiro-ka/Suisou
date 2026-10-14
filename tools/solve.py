#!/usr/bin/env python3

import json, math, sys, os

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

def from_srgb(r, g, b):
    l = (0.4122214708*r + 0.5363325363*g + 0.0514459929*b) ** (1/3)
    m = (0.2119034982*r + 0.6806995451*g + 0.1073969566*b) ** (1/3)
    s = (0.0883024619*r + 0.2817188376*g + 0.6299787005*b) ** (1/3)
    L = 0.2104542553*l + 0.7936177850*m - 0.0040720468*s
    a = 1.9779984951*l - 2.4285922050*m + 0.4505937099*s
    b = 0.0259040371*l + 0.7827717662*m - 0.8086757660*s
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)

def _dec(c):
    return c/12.92 if c <= 0.04045 else ((c + 0.055)/1.055) ** 2.4

def over(top, alpha, base):
    t = [_enc(c) for c in to_srgb(*top)]
    u = [_enc(c) for c in to_srgb(*base)]
    return from_srgb(*[_dec(x*alpha + y*(1 - alpha)) for x, y in zip(t, u)])

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

def face(L, t):

    return (L, min(t["cs"], maxC(L, t["h"])), t["h"])

def _lab(L, C, H):
    return (L, C*math.cos(math.radians(H)), C*math.sin(math.radians(H)))

def dE(c1, c2):
    a, b = _lab(*c1), _lab(*c2)
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

LADDERS = {

    "dark": {"bg":.18, "panel":.22, "item":.28, "tint":.33,
             "text-disabled":.62,
             "accent":.74, "text-sub":.78, "text-main":.94},

    "dim":  {"bg":.29, "panel":.33, "item":.39, "tint":.44,
             "text-disabled":.74,
             "accent":.80, "text-sub":.90, "text-main":.955},
}
SEM_HUE = {"error": 22, "warning": 90, "success": 155}
SEM_L = {
    "dark": {"error":.73, "warning":.82, "success":.76},
    "dim":  {"error":.85, "warning":.85, "success":.83},
}

THEMES = [
    {"name":"hadal",  "jp":"超深海層", "ladder":"dark", "h":286, "cs":0.006, "ar":0.85, "lift":0.03},

    {"name":"trench", "jp":"海溝",     "ladder":"dark", "h":270, "cs":0.040, "ar":0.85, "lift":0.03, "ct":0.015},

    {"name":"fjord",  "jp":"峡湾",     "ladder":"dark", "h":281, "cs":0.037, "ar":0.85, "lift":0.015, "ct":0.025},
    {"name":"shoal",  "jp":"浅瀬",     "ladder":"dim",  "h":265, "cs":0.020, "ar":0.60},
]
ACCENTS = [("clown",55),("turtle",122),("teal",188),("jelly",212),("blue",255),
           ("indigo",282),("coral",308),("magenta",332),("seal",355)]

ACCENT_JP = {"clown":"カクレクマノミ", "turtle":"ウミガメ", "jelly":"クラゲ",
             "coral":"サンゴ", "seal":"アザラシ"}

FLOOR = {"selected":0.055, "semantic":0.055, "textSub":0.08, "tintHue":0.05}
SEM_OFFSET = 0.15
WHITE = (1.0, 0.0, 0)
SHARED = {
    "color-hover":       ((0.55, 0.0, 0), 0.10),
    "color-line-weak":   (WHITE, 0.15),
    "color-line-strong": (WHITE, 0.25),
    "color-field":       (WHITE, 0.07),
    "color-backdrop":       ((0.0, 0.0, 0), 0.72),
}
SURFACES = ["panel", "item"]
JND = 0.02

PAIRS = [

    ("line-weak-on-bg","color-bg",1.5),
    ("line-weak-on-panel","color-panel",1.5),
    ("line-weak-on-item","color-item",1.5),
    ("line-strong-on-bg","color-bg",2.0),
    ("line-strong-on-panel","color-panel",2.0),
    ("line-strong-on-item","color-item",2.0),
    ("color-accent","color-panel",3.0),
    ("color-text","color-accent-tint",4.5),
    ("color-text","hover-on-panel",4.5),
    ("color-text","hover-on-item",4.5),

    ("color-text","color-tint",4.5),

    ("color-text","color-error-tint",4.5),
    ("color-error","color-error-tint",3.0),
    ("color-warning","color-warning-tint",3.0),
    ("color-success","color-success-tint",3.0),
    ("color-accent","color-accent-tint",3.0),
    ("color-text","hover-on-accent-tint",4.5),
    ("color-text","hover-on-tint",4.5),
]

def ladder(t):
    D = dict(LADDERS[t["ladder"]])
    for k in ("bg", "panel", "item", "tint"):
        D[k] = round(D[k] + t.get("lift", 0), 3)
    return D

def text_theme(t):
    return dict(t, cs=t.get("ct", t["cs"]))

def resolve_text_main(t):

    L = ladder(t)["text-main"]
    while L > 0.80 and not in_gamut(L, text_theme(t)["cs"], t["h"]):
        L -= 0.005
    return round(L, 3)

def resolve_tint(t, h, floor):

    D = ladder(t)
    L, ceil = D["tint"], maxC(D["tint"], h)
    ok = lambda C: (min(dE((L, C, h), face(D[s], t)) for s in SURFACES) >= floor
                    and dE((L, C, h), face(L, t)) >= FLOOR["tintHue"])
    if not ok(ceil): return ceil
    lo, hi = 0.0, ceil
    for _ in range(48):
        m = (lo + hi) / 2
        if ok(m): hi = m
        else: lo = m
    return hi

def tint_reaches(t, h, floor):

    D = ladder(t)
    L = D["tint"]
    C = resolve_tint(t, h, floor)
    return min(dE((L, C, h), face(D[s], t)) for s in SURFACES) >= floor - 1e-9

def sem_ratio(ar):
    return min(0.95, ar + SEM_OFFSET)

def tokens(t, acc_name, acc_h):
    D = ladder(t)
    o = {}
    for k in ["bg","panel","item","tint"]:
        o["color-" + k] = face(D[k], t)
    o["color-text-disabled"] = face(D["text-disabled"], text_theme(t))
    o["color-text-sub"] = face(D["text-sub"], text_theme(t))
    o["color-text"]     = face(resolve_text_main(t), text_theme(t))
    o["color-accent"]   = (D["accent"], maxC(D["accent"], acc_h) * t["ar"], acc_h)
    o["color-accent-tint"] = (D["tint"], resolve_tint(t, acc_h, FLOOR["selected"]), acc_h)
    sr = sem_ratio(t["ar"])
    for n, h in SEM_HUE.items():
        L = SEM_L[t["ladder"]][n]
        o["color-" + n] = (L, maxC(L, h) * sr, h)
        o["color-" + n + "-tint"] = (D["tint"], resolve_tint(t, h, FLOOR["selected"]), h)
    for st in ("bg", "panel", "item", "tint", "accent-tint"):
        under = o["color-" + st]
        o[f"hover-on-{st}"] = over(*SHARED["color-hover"], under)
        o[f"line-weak-on-{st}"] = over(*SHARED["color-line-weak"], under)
        o[f"line-strong-on-{st}"] = over(*SHARED["color-line-strong"], under)
    return o

def accent_blocking(t, acc_name, acc_h):

    k = tokens(t, acc_name, acc_h)
    return [f"{n} が色域外" for n, v in k.items()
            if v and (n in THEME_TOKENS or n in ACCENT_TOKENS) and not in_gamut(*v)]

def accent_issues(t, acc_name, acc_h):

    k = tokens(t, acc_name, acc_h)
    bad = []
    if not tint_reaches(t, acc_h, FLOOR["selected"]):
        d = min(dE((ladder(t)["tint"], resolve_tint(t, acc_h, FLOOR["selected"]), acc_h),
                   (ladder(t)[sf], t["cs"], t["h"])) for sf in SURFACES)
        bad.append(f"選択の tint が surface と近い ΔE {d:.3f}（目標 {FLOOR['selected']}）")
    if contrast(k["color-accent"], k["color-item"]) < 3.0:
        bad.append(f"accent のコントラスト不足 {contrast(k['color-accent'], k['color-item']):.2f}:1")
    d = dE(k["color-accent"], k["color-text-sub"])
    if d < FLOOR["textSub"]: bad.append(f"accent が text-sub と近い ΔE {d:.3f}")
    near = min(((dE(k["color-accent"], k["color-" + n]), n) for n in SEM_HUE))
    if near[0] < FLOOR["semantic"]: bad.append(f"{near[1]} と近い ΔE {near[0]:.3f}")
    for st in SURFACES:
        if dE(k["color-accent-tint"], k[f"hover-on-{st}"]) < JND:
            bad.append(f"{st} の上の hover と選択が近すぎ")

    for st in SURFACES:
        if dE(k["color-tint"], k[f"hover-on-{st}"]) < JND:
            bad.append(f"{st} の上の hover と選択（中立）が近すぎ")
    return bad

def pair_results(t, acc_name, acc_h):
    k = tokens(t, acc_name, acc_h)
    rows = []
    for a, b, need in PAIRS:
        if k.get(a) is None or k.get(b) is None:
            rows.append({"a":a,"b":b,"need":need,"value":None,"pass":False})
            continue
        v = contrast(k[a], k[b])
        rows.append({"a":a,"b":b,"need":need,"value":round(v,2),"pass":v>=need})
    return rows

def gamut_failures(t, acc_name, acc_h):
    return [n for n, v in tokens(t, acc_name, acc_h).items() if v and not in_gamut(*v)]

def solve():
    out = {
        "version": "1.4",
        "floors": FLOOR, "semOffset": SEM_OFFSET, "jnd": JND,
        "shared": {n: {"L": v[0][0], "alpha": v[1]} for n, v in SHARED.items()},
        "ladders": LADDERS, "semHue": SEM_HUE, "semL": SEM_L,
        "accentHues": {n: h for n, h in ACCENTS},
        "pairs": [{"a":a,"b":b,"need":n} for a,b,n in PAIRS],
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
                "available": not block,
                "recommended": not block and not bad,
                "blocking": block, "issues": bad,
                "tokens": {n: (None if v is None else
                              {"L":round(v[0],4),"C":round(v[1],4),"H":v[2],"hex":hexof(*v)})
                           for n, v in tk.items()},
                "pairs": pair_results(t, an, ah),
            }
            for g in block:
                out["failures"].append(f"{t['name']}/{an}: {g}")
            for r in pair_results(t, an, ah):

                if not r["pass"] and not bad and not block:
                    out["failures"].append(
                        f"{t['name']}/{an}: {r['a']} on {r['b']} "
                        f"{r['value']}:1 < {r['need']}")
            out.setdefault("notRecommended", [])
            if bad and not block:
                out["notRecommended"].append(f"{t['name']}/{an}: {bad[0]}")
        out["themes"].append(entry)

    out["hueCategoryRisk"] = [
        {"accent":an, "semantic":sn, "deg":round(hue_dist(ah, sh))}
        for an, ah in ACCENTS for sn, sh in SEM_HUE.items() if hue_dist(ah, sh) < 40
    ]
    return out

HERE = os.path.dirname(os.path.abspath(__file__))

SHARED_TOKENS = list(SHARED)
THEME_TOKENS = ["color-bg", "color-panel", "color-item", "color-tint",
                "color-text", "color-text-sub", "color-text-disabled",
                "color-error", "color-warning", "color-success",
                "color-error-tint", "color-warning-tint", "color-success-tint"]
ACCENT_TOKENS = ["color-accent", "color-accent-tint"]

DEFAULT_THEME  = "hadal"
DEFAULT_ACCENT = "jelly"

def css_color(v, alpha=None):
    L, C, H = v
    a = "" if alpha is None else f" / {alpha}"
    return f"oklch({L*100:.2f}% {C:.4f} {H}{a})"

def css_block(selector, names, tk, indent=""):

    L = [f"{indent}{selector} {{"]
    for n in names:
        d = tk[n]
        if d is None:
            L.append(f"{indent}  /* --suisou-{n}: 解なし */")
            continue
        L.append(f"{indent}  --suisou-{n}: {css_color((d['L'], d['C'], d['H']))};")
    L.append(f"{indent}}}")
    return L

GRAY_VARS = ["gray-hue", "gray-chroma", "text-chroma"]
GRAY_TOKENS = {"color-bg": "gray-chroma", "color-panel": "gray-chroma",
               "color-item": "gray-chroma", "color-tint": "gray-chroma",
               "color-text": "text-chroma", "color-text-sub": "text-chroma",
               "color-text-disabled": "text-chroma"}

def theme_block(t, tk):

    t = next(x for x in THEMES if x["name"] == t["name"])
    chroma = {"gray-chroma": t["cs"], "text-chroma": t.get("ct", t["cs"])}
    val = dict(chroma, **{"gray-hue": t["h"]})
    L = [f'[data-suisou-theme~="{t["name"]}"] {{',
         *[f'  --suisou-{n}: {val[n]:g};' for n in GRAY_VARS]]
    for n in THEME_TOKENS:
        d = tk[n]
        c = GRAY_TOKENS.get(n)
        if c and d is not None and d["H"] == t["h"] and abs(d["C"] - chroma[c]) < 5e-5:
            L.append(f'  --suisou-{n}: oklch({d["L"]*100:.2f}% var(--suisou-{c}) var(--suisou-gray-hue));')
        else:
            L += css_block("", [n], tk)[1:-1]
    L.append("}")
    return L

def write_css(data):

    L = ["[data-suisou-theme] {",
         *[f"  --suisou-{n}: {css_color(*SHARED[n])};" for n in SHARED_TOKENS],
         "}", ""]
    for t in data["themes"]:
        any_tokens = next(iter(t["accents"].values()))["tokens"]
        L += theme_block(t, any_tokens)
        L.append("")
    for t in data["themes"]:
        for an, a in t["accents"].items():
            if not a["available"]:
                continue
            sel = f'[data-suisou-theme~="{t["name"]}"][data-suisou-theme~="{an}"]'
            L += css_block(sel, ACCENT_TOKENS, a["tokens"])
            L.append("")

    p = os.path.join(HERE, os.pardir, "pages", "palette.css")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    p = os.path.normpath(p)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return p

def write_site_data(data):

    out = {
        "themes": [{"name": t["name"], "jp": t["jp"], "ladder": t["ladder"],
                    "h": t["h"], "cs": t["cs"],
                    "available": [a for a, v in t["accents"].items() if v["available"]],
                    "recommended": [a for a, v in t["accents"].items() if v["recommended"]],
                    "warnings": {a: v["issues"][0] for a, v in t["accents"].items()
                                 if v["available"] and not v["recommended"]}}
                   for t in data["themes"]],
        "accents": [{"name": n, "jp": ACCENT_JP.get(n, ""), "hue": h} for n, h in ACCENTS],
        "themeTokens": THEME_TOKENS,
        "accentTokens": ACCENT_TOKENS,
        "sharedTokens": SHARED_TOKENS,
        "default": {"theme": DEFAULT_THEME, "accent": DEFAULT_ACCENT},
        "hex": {t["name"]: {a: {n: (None if d is None else d["hex"]) for n, d in v["tokens"].items()}
                            for a, v in t["accents"].items()}
                for t in data["themes"]},
    }
    p = os.path.normpath(os.path.join(HERE, os.pardir, "pages", "suisou.data.js"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("const SUISOU = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    return p

def write_tables(data):

    L = []
    L.append("### L の並び（2系統）\n")
    keys = ["bg","panel","item","tint",
            "text-disabled","accent","text-sub","text-main"]
    L.append("| | dark | dim |\n|---|---|---|")
    for k in keys:
        L.append(f"| {k} | {LADDERS['dark'][k]*100:.0f} | {LADDERS['dim'][k]*100:.0f} |")
    L.append("")
    L.append("### テーマ\n")
    L.append("| テーマ | L の並び | H | surface C | 強さ | 意味色倍率 | text-main | 使えるアクセント |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in data["themes"]:
        ok = [a for a, v in t["accents"].items() if v["recommended"]]
        L.append(f"| `{t['name']}` | {t['ladder']} | {t['h']} | {t['cs']} | ×{t['ar']} | "
                 f"×{t['semRatio']} | L{t['textMainL']*100:.1f} | **{len(ok)}/{len(ACCENTS)}** |")
    L.append("")
    L.append("### アクセント可用性\n")
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
                    worst[key] = (r["value"], r["need"], t["name"], an)
    L.append("| ペア | 最悪値 | 必要 | 最悪ケース |")
    L.append("|---|---|---|---|")
    for (a, b), (v, need, tn, an) in sorted(worst.items(), key=lambda x: x[1][0]/x[1][1]):
        mark = "" if v >= need else " ⚠"
        L.append(f"| `{a}` on `{b}` | {v:.2f}:1{mark} | {need} | {tn}/{an} |")
    L.append("")
    L.append("### 意味色と同じ色相の家族に入るアクセント\n")
    L.append("| アクセント | 意味色 | 色相差 | accent×意味色の ΔE（最小のテーマ） |")
    L.append("|---|---|---|---|")
    for r in sorted(data["hueCategoryRisk"], key=lambda x: x["deg"]):
        de = min(dE(tokens(t, r["accent"], dict(ACCENTS)[r["accent"]])["color-accent"],
                    tokens(t, r["accent"], dict(ACCENTS)[r["accent"]])["color-" + r["semantic"]])
                 for t in THEMES)
        L.append(f"| `{r['accent']}` | `{r['semantic']}` | {r['deg']}度 | {de:.3f} |")
    L.append("")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    data = solve()
    if "--tables" in sys.argv:
        sys.stdout.write(write_tables(data))
        sys.exit(0)
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
    print("wrote:", write_css(data))
    print("wrote:", write_site_data(data))
