/* 手書き。色も px も値としては持たない。
   色は palette.css、タイポの px は ui/type.css、
   テーマ・アクセントの構造は suisou.data.js（生成物）。

   ページの中身は content/*.html にある。ここがやるのは
   「差し替え」と「効いている値を読んで並べる」だけ。

   ページを1枚足す手順:
     1. content/<name>.html を置く
     2. 下の PAGES に1行足す
   静的なページなら enhance は要らない。 */

const root = document.documentElement;
const app = document.querySelector('.app');
const slot = (name, scope = document) => scope.querySelector(`[data-slot="${name}"]`);

const PAGES = {
  palette:    { group: '土台', label: 'Palette',    enhance: enhancePalette },
  typography: { group: '土台', label: 'Typography', enhance: enhanceTypography },
  button:     { group: '部品', label: 'Button' },
  panel:      { group: '部品', label: 'Panel' },
  chat:       { group: '作例', label: 'チャット', bleed: true },
  list:       { group: '作例', label: '一覧と詳細', bleed: true },
};

/* ── Palette の並び。トークンの意味づけであって、値は持たない ── */
const GROUPS = [
  { title: '面と文字', tokens: ['bg', 'panel', 'item', 'floating',
                                'line-weak', 'line-strong',
                                'text-disabled', 'text-sub', 'text-main'] },
  { title: 'アクセント', tokens: SUISOU.accentTokens },
  { title: '意味色', tokens: ['error', 'warning', 'success',
                              'error-surface', 'warning-surface', 'success-surface'] },
  { title: 'その他', tokens: ['on-accent', 'scrim'] },
];

/* ── Typography の構造。どの役割がどの段か、であって px ではない ──
   px は ui/type.css の [data-suisou-text] が持つ。根拠は type-spec §3〜§6。 */
const SCALE = [12, 14, 16, 20, 24, 28, 32];
const WEIGHTS = [400, 500, 600, 700];
const ROLES_UI = [
  ['h1', 20, 700], ['h2', 16, 600], ['h3', 14, 600],
  ['p', 14, 400], ['small', 12, 400],
];
const ROLES_DOC = [
  ['h1', 28, 700], ['h2', 24, 700], ['h3', 20, 600], ['h4', 16, 600],
  ['h5', 16, 500, 'rule'], ['h6', 14, 600, 'rule-weak'],
  ['p', 16, 400], ['small', 14, 400],
];
const SAMPLE = '水槽 Suisou — あいうえお ABCDEfg 0123';

const theme = () => root.dataset.suisouTheme;
const accent = () => root.dataset.suisouAccent;
const themeOf = (name) => SUISOU.themes.find((t) => t.name === name);

let current = null;
const cache = {};

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

/* 色コードは palette.css が --suisou-<token>-hex として持っている。
   CSS は変数を文字として表示できないので、ここで読んで textContent に入れる。
   カスケードで解決された値が返るため、テーマを変えれば自動的に変わる。 */
function hexOf(token) {
  const v = getComputedStyle(root).getPropertyValue(`--suisou-${token}-hex`).trim();
  return v.replace(/^"|"$/g, '');
}

/* 実際に効いている値を読む。CSS に書いた px を JS 側でも書くとずれるので、
   書かずに読む。表示されてからでないと当てにできない。 */
function metricsOf(node) {
  const s = getComputedStyle(node);
  const px = (v) => Math.round(parseFloat(v));
  return `${px(s.fontSize)} / ${px(s.lineHeight)} / ${s.fontWeight}`;
}

/* ── Palette ────────────────────────────────── */

function enhancePalette(scope) {
  const t = themeOf(theme());
  slot('summary', scope).textContent =
    `${t.name}（${t.jp}）× ${accent()}。色は tools/solve.py が制約から解いた値で、`
    + '手で置いた色は1つも無い。';

  // 使えない組はそもそも CSS に無いので押せなくする
  const row = slot('accents', scope);
  for (const a of SUISOU.accents) {
    const usable = t.available.includes(a.name);
    const chip = el('button', 'accent-chip', a.jp ? `${a.name}（${a.jp}）` : a.name);
    chip.type = 'button';
    chip.style.setProperty('--c', 'var(--suisou-accent)');
    chip.dataset.suisouTheme = theme();
    chip.dataset.suisouAccent = a.name;
    chip.disabled = !usable;
    if (a.name === accent()) chip.setAttribute('aria-pressed', 'true');
    if (!usable) chip.title = `${theme()} では使えない組み合わせ`;
    chip.addEventListener('click', () => { root.dataset.suisouAccent = a.name; render(); });
    row.append(chip);
  }
  const short = SUISOU.accents.length - t.available.length;
  slot('accent-note', scope).textContent =
    short ? `${short} 色は制約を満たさないので出していない。` : '';

  const box = slot('tokens', scope);
  for (const g of GROUPS) {
    const wrap = el('div', 'group');
    wrap.append(el('h2', null, g.title));
    const list = el('div', 'tokens');
    for (const name of g.tokens) {
      const hex = hexOf(name);
      const item = el('div', hex ? 'token' : 'token is-missing');
      const chip = el('div', 'token-chip');
      chip.style.setProperty('--c', `var(--suisou-${name})`);
      item.append(chip, el('div', 'token-name', name), el('div', 'token-hex', hex || '—'));
      list.append(item);
    }
    wrap.append(list);
    box.append(wrap);
  }
}

/* ── Typography ─────────────────────────────── */

function typeRow(key, variants, note) {
  const row = el('div', 't-row');
  const sample = el('div', null, SAMPLE);
  sample.setAttribute('data-suisou-text', variants);
  row.append(el('div', 't-key', key), sample, el('div', 't-meta', ''));
  row.dataset.note = note || '';
  return row;
}

function fill(box, rows) { for (const r of rows) box.append(r); }

function enhanceTypography(scope) {
  fill(slot('scale-ui', scope), SCALE.map((s) => typeRow(`${s}px`, `s${s} w400`)));
  fill(slot('scale-doc', scope), SCALE.map((s) => typeRow(`${s}px`, `s${s} w400 doc`)));
  fill(slot('weights', scope), WEIGHTS.map((n) => typeRow(String(n), `s16 w${n}`)));
  fill(slot('roles-ui', scope), ROLES_UI.map(([n, s, w]) => typeRow(n, `s${s} w${w}`)));
  fill(slot('roles-doc', scope), ROLES_DOC.map(([n, s, w, extra]) =>
    typeRow(n, `s${s} w${w} doc${extra ? ' ' + extra : ''}`, extra ? '左罫線' : '')));

  for (const row of scope.querySelectorAll('.t-row')) {
    const note = row.dataset.note;
    row.children[2].textContent = metricsOf(row.children[1]) + (note ? `　${note}` : '');
  }
}

/* ── 差し替え ───────────────────────────────── */

async function load(name) {
  if (!(name in PAGES)) name = 'palette';
  const box = slot('page');
  if (!cache[name]) {
    try {
      const res = await fetch(`content/${name}.html`);
      if (!res.ok) throw new Error(res.status);
      cache[name] = await res.text();
    } catch (e) {
      box.replaceChildren(el('p', 'note', `content/${name}.html を読めなかった（${e.message}）。`
        + ' file:// で開いていると fetch が弾かれる。簡易サーバ経由で開くこと。'));
      return;
    }
  }
  box.innerHTML = cache[name];
  // 作例は「そのもの」を見せる。解説も余白も挟まない
  box.classList.toggle('is-bleed', !!PAGES[name].bleed);
  box.scrollTop = 0;
  current = name;
  PAGES[name].enhance?.(box);
  for (const b of document.querySelectorAll('.nav-item')) {
    b.setAttribute('aria-current', b.dataset.page === name ? 'page' : 'false');
  }
}

function renderNav() {
  const nav = slot('nav');
  nav.replaceChildren();
  let seen = null;
  for (const [name, p] of Object.entries(PAGES)) {
    if (p.group !== seen) { nav.append(el('div', 'nav-group', p.group)); seen = p.group; }
    const b = el('button', 'nav-item', p.label);
    b.type = 'button';
    b.dataset.page = name;
    b.addEventListener('click', () => { location.hash = name; });
    nav.append(b);
  }
}

/* テーマを一巡させる。切り替え先で今のアクセントが使えないなら使える先頭に寄せる。
   CSS は存在しない組に無反応なので、放っておくと静かに既定色へ落ちて理由が分からなくなる。 */
function cycleTheme() {
  const names = SUISOU.themes.map((t) => t.name);
  const next = themeOf(names[(names.indexOf(theme()) + 1) % names.length]);
  root.dataset.suisouTheme = next.name;
  if (!next.available.includes(accent())) root.dataset.suisouAccent = next.available[0];
  render();
}

function renderSwitch() {
  const t = themeOf(theme());
  const b = document.querySelector('.theme-switch');
  b.replaceChildren();
  b.append(el('span', null, t.name), el('span', 'sub', `${t.jp} — 押すと次のテーマへ`));
}

function render() {
  renderSwitch();
  load(current ?? location.hash.slice(1) ?? 'palette');
}

document.querySelector('.theme-switch').addEventListener('click', cycleTheme);
document.querySelector('.menu-close').addEventListener('click', () => app.classList.add('is-menu-closed'));
document.querySelector('.menu-open').addEventListener('click', () => app.classList.remove('is-menu-closed'));
addEventListener('hashchange', () => load(location.hash.slice(1)));

renderNav();
renderSwitch();
load(location.hash.slice(1) || 'palette');
