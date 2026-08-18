/* 手書き。色も px も値としては持たない。
   色は palette.css、タイポの px は suisou.css、
   テーマ・アクセントの構造は suisou.data.js（生成物）。
   ここがやるのは「どれを選んでいるか」と「効いている値を読んで並べる」だけ。 */

const root = document.documentElement;
const app = document.querySelector('.app');

/* ── Palette の並び。トークンの意味づけであって、値は持たない ── */
const GROUPS = [
  { title: '面と文字', tokens: ['bg', 'panel', 'input', 'floating',
                                'line-weak', 'line-strong',
                                'text-disabled', 'text-sub', 'text-main'] },
  { title: 'アクセント', tokens: SUISOU.accentTokens },
  { title: '意味色', tokens: ['error', 'warning', 'success',
                              'error-surface', 'warning-surface', 'success-surface'] },
  { title: 'その他', tokens: ['on-accent', 'scrim'] },
];

/* ── Typography の構造。どの役割がどの段か、であって px ではない ──
   px は suisou.css の .t-s* が持つ。根拠は .notes/type-spec.md §3〜§6。 */
const SCALE = [12, 14, 16, 20, 24, 28, 32];
const WEIGHTS = [400, 500, 600, 700];
// [役割, サイズの段, ウェイト, 追加クラス]
const ROLES_UI = [
  ['h1', 20, 700], ['h2', 16, 600], ['h3', 14, 600],
  ['p', 14, 400], ['small', 12, 400],
];
const ROLES_DOC = [
  ['h1', 28, 700], ['h2', 24, 700], ['h3', 20, 600], ['h4', 16, 600],
  ['h5', 16, 500, 't-rule'], ['h6', 14, 600, 't-rule2'],
  ['p', 16, 400], ['small', 14, 400],
];

const SAMPLE = '水槽 Suisou — あいうえお ABCDEfg 0123';

const theme = () => root.dataset.suisouTheme;
const accent = () => root.dataset.suisouAccent;
const themeOf = (name) => SUISOU.themes.find((t) => t.name === name);

let currentPage = 'palette';

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function group(title, ...children) {
  const g = el('div', 'group');
  g.append(el('h2', null, title), ...children);
  return g;
}

/* 色コードは palette.css が --suisou-<token>-hex として持っている。
   CSS は変数を文字として表示できないので、ここで読んで textContent に入れる。
   カスケードで解決された値が返るため、テーマを変えれば自動的に変わる。 */
function hexOf(token) {
  const v = getComputedStyle(root).getPropertyValue(`--suisou-${token}-hex`).trim();
  return v.replace(/^"|"$/g, '');
}

/* 実際に効いている値を読む。CSS に書いた px を JS 側でも書くと
   ずれるので、書かずに読む。 */
function metricsOf(node) {
  const s = getComputedStyle(node);
  const px = (v) => Math.round(parseFloat(v));
  return `${px(s.fontSize)} / ${px(s.lineHeight)} / ${s.fontWeight}`;
}

function typeRow(key, sampleCls, note) {
  const row = el('div', 't-row');
  const sample = el('div', sampleCls, SAMPLE);
  row.append(el('div', 't-key', key), sample, el('div', 't-meta', ''));
  // meta は DOM に入ってからでないと computed 値が取れない
  row.dataset.pending = note || '';
  return row;
}

function fillMetrics(scope) {
  for (const row of scope.querySelectorAll('.t-row')) {
    const sample = row.children[1];
    const note = row.dataset.pending;
    row.children[2].textContent = metricsOf(sample) + (note ? `　${note}` : '');
  }
}

/* ── Palette ページ ─────────────────────────── */

function renderPalette() {
  const page = document.querySelector('.page-palette');
  page.replaceChildren();

  page.append(el('h1', null, 'Palette'));
  page.append(el('p', 'note',
    `${theme()}（${themeOf(theme()).jp}）× ${accent()}。` +
    '色は tools/solve.py が制約から解いた値で、手で置いた色は1つも無い。'));

  // アクセントの切り替え。使えない組はそもそも CSS に無いので押せなくする
  const avail = themeOf(theme()).available;
  const row = el('div', 'accent-row');
  for (const a of SUISOU.accents) {
    const usable = avail.includes(a.name);
    const chip = el('button', 'accent-chip', a.jp ? `${a.name}（${a.jp}）` : a.name);
    chip.type = 'button';
    chip.style.setProperty('--c', 'var(--suisou-accent)');
    chip.dataset.suisouTheme = theme();
    chip.dataset.suisouAccent = a.name;
    chip.disabled = !usable;
    if (a.name === accent()) chip.classList.add('is-current');
    if (!usable) chip.title = `${theme()} では使えない組み合わせ`;
    chip.addEventListener('click', () => setAccent(a.name));
    row.append(chip);
  }
  const g0 = group('アクセント', row);
  if (avail.length < SUISOU.accents.length) {
    g0.append(el('p', 'note',
      `${SUISOU.accents.length - avail.length} 色は制約を満たさないので出していない。`));
  }
  page.append(g0);

  for (const g of GROUPS) {
    const list = el('div', 'tokens');
    for (const name of g.tokens) {
      const hex = hexOf(name);
      const t = el('div', hex ? 'token' : 'token is-missing');
      const chip = el('div', 'token-chip');
      chip.style.setProperty('--c', `var(--suisou-${name})`);
      t.append(chip, el('div', 'token-name', name), el('div', 'token-hex', hex || '—'));
      list.append(t);
    }
    page.append(group(g.title, list));
  }
}

/* ── Typography ページ ──────────────────────── */

function renderTypography() {
  const page = document.querySelector('.page-typography');
  page.replaceChildren();

  page.append(el('h1', null, 'Typography'));
  page.append(el('p', 'note',
    '右端の数値は「サイズ / 行間 / ウェイト」で、CSS に書いた表ではなく '
    + '実際に効いている computed 値を読んで出している。'));

  // サイズスケール（UI と長文の2系統を並べる）
  const scale = el('div');
  for (const s of SCALE) {
    scale.append(typeRow(`${s}px UI`, `t-sample t-s${s} t-w400`));
  }
  page.append(group('サイズスケール — UI（アンカー 14px）', scale,
    el('p', 'note', '14 以外はすべて4の倍数。等比スケールは採らない（§3）。')));

  const scaleDoc = el('div');
  for (const s of SCALE) {
    scaleDoc.append(typeRow(`${s}px 長文`, `t-sample is-doc t-s${s} t-w400`));
  }
  page.append(group('サイズスケール — 長文（アンカー 16px）', scaleDoc,
    el('p', 'note', '行間は UI に +4px するだけ。表ではなく規則として持っている（§6）。')));

  // ウェイト
  const w = el('div');
  for (const n of WEIGHTS) {
    w.append(typeRow(String(n), `t-sample t-s16 t-w${n}`));
  }
  page.append(group('ウェイト', w,
    el('p', 'note', '階層はサイズだけで作らない。実測で最頻出の見出しは「14px + 600」だった（§4）。')));

  // 役割
  const ui = el('div');
  for (const [name, size, weight, extra] of ROLES_UI) {
    ui.append(typeRow(name, `t-sample t-s${size} t-w${weight}${extra ? ' ' + extra : ''}`));
  }
  page.append(group('役割 — UI', ui));

  const doc = el('div');
  for (const [name, size, weight, extra] of ROLES_DOC) {
    doc.append(typeRow(name, `t-sample is-doc t-s${size} t-w${weight}${extra ? ' ' + extra : ''}`,
      extra ? '左罫線' : ''));
  }
  page.append(group('役割 — 長文', doc,
    el('p', 'note', 'h4 は本文と同サイズ。h5/h6 はサイズを増やさず、ウェイトと左罫線で階層を作る（§5）。')));
  // 計測は showPage に任せる。表示されてからでないと当てにできない
}

/* ── 切り替え ───────────────────────────────── */

function setAccent(name) {
  root.dataset.suisouAccent = name;
  render();
}

/* テーマを一巡させる。切り替え先で今のアクセントが使えないなら、
   使える先頭に寄せる。CSS は存在しない組に無反応なので、放っておくと
   静かに既定色へ落ちて理由が分からなくなる。 */
function cycleTheme() {
  const names = SUISOU.themes.map((t) => t.name);
  const next = themeOf(names[(names.indexOf(theme()) + 1) % names.length]);
  root.dataset.suisouTheme = next.name;
  if (!next.available.includes(accent())) root.dataset.suisouAccent = next.available[0];
  render();
}

function showPage(name) {
  currentPage = name;
  for (const p of document.querySelectorAll('.page')) {
    p.classList.toggle('is-current', p.classList.contains(`page-${name}`));
  }
  for (const b of document.querySelectorAll('.nav-item')) {
    b.classList.toggle('is-current', b.dataset.page === name);
  }
  // 測るのは表示されてから。display:none のまま読んだ値は当てにしない
  const shown = document.querySelector('.page.is-current');
  if (shown) fillMetrics(shown);
}

function renderSwitch() {
  const t = themeOf(theme());
  const b = document.querySelector('.theme-switch');
  b.replaceChildren();
  b.append(el('span', null, t.name), el('span', 'sub', `${t.jp} — 押すと次のテーマへ`));
}

function render() {
  renderSwitch();
  renderPalette();
  renderTypography();
  showPage(currentPage);
}

document.querySelector('.theme-switch').addEventListener('click', cycleTheme);
document.querySelector('.sidebar-close').addEventListener('click', () => app.classList.add('is-closed'));
document.querySelector('.topbar-open').addEventListener('click', () => app.classList.remove('is-closed'));
for (const b of document.querySelectorAll('.nav-item')) {
  b.addEventListener('click', () => showPage(b.dataset.page));
}

render();
