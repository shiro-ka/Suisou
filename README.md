<h1 align="center">Suisou</h1>

<p align="center">水槽。水・海・魚をモチーフにしたデザイン体系。</p>

---

複数のプロダクトで「しろかが作った」と分かるデザインパターンを共有するための設計体系です。
UI だけでなく、ブログや規約のような長文コンテンツも適用先に含みます。

**プレビュー** … https://shiro-ka.github.io/Suisou/

## このリポジトリの掟

**色を決めるのは `tools/solve.py` だけ。** CSS にも仕様書にも色の値を手で書きません。

```sh
python3 tools/solve.py          # 生成（palette.css / suisou.data.js / spec-tables.md）
python3 tools/solve.py --check  # 検証のみ。破綻があれば exit 1
```

数値の表は生成物である `tools/spec-tables.md` が持ちます。`.notes/palette-spec.md` は散文と判断の理由だけを持ち、表を持ちません。
真実の源泉を1つにしないと、ツール・仕様書・実装が同じ数値を主張して同期が手作業になります。

CI（`.github/workflows/check_palette.yml`）が、構造的破綻と、生成物が `solve.py` の出力と一致することを検証します。

## 手元で見る

ページの中身は `pages/content/*.html` にあり、`fetch` で差し替えます。
`file://` だと弾かれるので、簡易サーバ経由で開いてください。

```sh
python3 -m http.server -d pages 8000   # http://localhost:8000
```

## 構成

```
pages/  index.html … 骨格だけ。トップバーとサイドバー
        content/*.html … 差し替わるページの中身
        ui/*.css … Suisou の部品。data-suisou-* 属性で当たる
        styles.css / app.js … このサイトだけのもの
        palette.css / suisou.data.js … 生成物（手で編集しない）
tools/  solve.py … 色の唯一の決定者
        lint_css.py … 手書き側に色が混入していないか検査する
        spec-tables.md … 生成物。数値の表と検証結果はここにある
```

## 方針

- **素の HTML / CSS / JS で実装する。** フレームワークも別言語も使わず、JS は最小限に留めます
- **線形デザイン。** 塗らず、CTA すらアウトラインで表現します。テーマ切替を技術的に成立させている柱でもあります
- **ダーク専用。** 純粋なライトテーマは作らず、明るめが好みの場合は `dim` 系統を使います
- **影は実際に浮くものだけ。** 面の分離は border が担保します

## 前身

このリポジトリには前身の Akuarium がありました。`hadal`（超深海層）や `jellyghoti`（jellyfish + ghoti）といった
「テーマ = 水域、アクセント = 海の生き物」という命名体系はそこから引き継いでいます。
実装は HSL ベースで値を手で置く作りだったため、OKLCH と制約解決に作り直しました。
