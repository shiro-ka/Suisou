<h1 align="center">Suisou</h1>

<p align="center">水槽。水・海・魚をモチーフにしたデザイン体系。</p>

---

複数のプロダクトで「しろかが作った」と分かるデザインパターンを共有するための設計体系です。
UI だけでなく、ブログや規約のような長文コンテンツも適用先に含みます。

**プレビュー** … https://shiro-ka.github.io/Suisou/

## 使う

最小の1枚。`<link>` 1本と `data-suisou-root`、あとは属性で組む。

```html
<!DOCTYPE html>
<html lang="ja" data-suisou-theme="hadal" data-suisou-accent="clown">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- フォントは利用側が読み込む（Suisou は書体を運ばない） -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://shiro-ka.github.io/Suisou/v1/suisou.css">
</head>
<body data-suisou-root>
  <main data-suisou-layout="stack container">
    <div data-suisou-surface="panel">
      <button data-suisou-button="outline">はじめる</button>
    </div>
  </main>
</body>
</html>
```

- **URL は3系統**。普段は `/v1/`（v1 系の最新。直せば自動で行き渡る）。
  見た目を凍結したい現場は `/v/<sha7>/`（固定。動かない）。`/dist/` は常に最新
- **テーマとアクセントは必ず同じ要素に書く**。片方だけだと噛み合わない色が静かに出る
- 切替が要らなければ `suisou-<theme>-<accent>.css`（1組だけ。半分の重さ）
- 属性・値・トークンの全一覧は [CONTRACT.md](CONTRACT.md)

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
        contract.py … 公開契約の目録を導く（生成物: CONTRACT.md）
        bundle.py … 配る形を組み立てる（dist/）
        spec-tables.md … 生成物。数値の表と検証結果はここにある
CONTRACT.md … 生成物。公開 API の目録。破壊的変更はこれで判定する
```

## 方針

- **素の HTML / CSS / JS で実装する。** フレームワークも別言語も使わず、JS は最小限に留めます
- **線形デザイン。** 塗らず、CTA すらアウトラインで表現します。テーマ切替を技術的に成立させている柱でもあります
- **ダーク専用。** 純粋なライトテーマは作らず、明るめが好みの場合は `dim` 系統を使います
- **影は使わない。** ダーク専用では影が機能しない（下地が既に暗い）ため。面の分離は border が担保します

## 前身

このリポジトリには前身の Akuarium がありました。`hadal`（超深海層）や `jellyghoti`（jellyfish + ghoti）といった
「テーマ = 水域、アクセント = 海の生き物」という命名体系はそこから引き継いでいます。
実装は HSL ベースで値を手で置く作りだったため、OKLCH と制約解決に作り直しました。
