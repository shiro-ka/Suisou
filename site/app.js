/* 手書き。色の値は持たない。
   色は palette.css、構造（テーマ・アクセント・可用性）は suisou.data.js。
   ここがやるのは「どれを選んでいるか」と「読んだ値を並べる」だけ。 */

const root = document.documentElement;
const app = document.querySelector('.app');

// 表示の並び。トークンの意味づけであって、値は持たない。
const GROUPS = [
  { title: '面と文字', tokens: ['bg', 'panel', 'input', 'floating',
                                'line-weak', 'line-strong',
                                'text-disabled', 'text-sub', 'text-main'] },
  { title: 'アクセント', tokens: SUISOU.accentTokens },
  { title: '意味色', tokens: ['error', 'warning', 'success',
                              'error-surface', 'warning-surface', 'success-surface'] },
  { title: 'その他', tokens: ['on-accent', 'scrim'] },
];

const theme = () => root.dataset.suisouTheme;
const accent = () => root.dataset.suisouAccent;
const themeOf = (name) => SUISOU.themes.find((t) => t.name === name);

/* 色コードは palette.css が --suisou-<token>-hex として持っている。
   CSS は変数を文字として表示できないので、ここで読んで textContent に入れる。
   カスケードで解決された値が返るため、テーマを変えれば自動的に変わる。 */
function hexOf(token) {
  const v = getComputedStyle(root).getPropertyValue(`--suisou-${token}-hex`).trim();
  return v.replace(/^"|"$/g, '');
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
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
    chip.style.setProperty('--c', `var(--suisou-accent)`);
    chip.dataset.suisouTheme = theme();
    chip.dataset.suisouAccent = a.name;
    chip.disabled = !usable;
    if (a.name === accent()) chip.classList.add('is-current');
    if (!usable) chip.title = `${theme()} では使えない組み合わせ`;
    chip.addEventListener('click', () => setAccent(a.name));
    row.append(chip);
  }
  const g0 = el('div', 'group');
  g0.append(el('h2', null, 'アクセント'), row);
  if (avail.length < SUISOU.accents.length) {
    g0.append(el('p', 'note',
      `${SUISOU.accents.length - avail.length} 色は制約を満たさないので出していない。`));
  }
  page.append(g0);

  for (const g of GROUPS) {
    const box = el('div', 'group');
    box.append(el('h2', null, g.title));
    const list = el('div', 'tokens');
    for (const name of g.tokens) {
      const hex = hexOf(name);
      const t = el('div', hex ? 'token' : 'token is-missing');
      const chip = el('div', 'token-chip');
      chip.style.setProperty('--c', `var(--suisou-${name})`);
      t.append(chip, el('div', 'token-name', name), el('div', 'token-hex', hex || '—'));
      list.append(t);
    }
    box.append(list);
    page.append(box);
  }
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

function renderSwitch() {
  const t = themeOf(theme());
  const b = document.querySelector('.theme-switch');
  b.replaceChildren();
  b.append(el('span', null, t.name), el('span', 'sub', `${t.jp} — 押すと次のテーマへ`));
}

function render() {
  renderSwitch();
  renderPalette();
}

document.querySelector('.theme-switch').addEventListener('click', cycleTheme);
document.querySelector('.sidebar-close').addEventListener('click', () => app.classList.add('is-closed'));
document.querySelector('.topbar-open').addEventListener('click', () => app.classList.remove('is-closed'));

render();
