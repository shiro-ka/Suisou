const root = document.documentElement;
const menu = document.querySelector('nav[popover]');
const themeSwitch = document.querySelector('.theme-switch');
const slot = (name, scope = document) => scope.querySelector(`[data-slot="${name}"]`);

const PAGES = {
  palette: { enhance: enhancePalette },
  typography: { enhance: enhanceTypography },
  tokens: { enhance: enhanceTokens },
  tray: {},
  layout: {},
  button: {},
  code: {},
  prose: {},
  field: {},
  icon: {},
  link: {},
  table: {},
  media: {},
  avatar: {},
  tag: {},
  spinner: {},
  banner: {},
  chat: { bleed: true },
  list: { bleed: true },
};

const GROUPS = [
  { title: '面と文字', tokens: ['bg', 'panel', 'item',
                                'hover-surface', 'selected-neutral-surface',
                                'line-weak', 'line-strong',
                                'text-disabled', 'text-sub', 'text-main'] },
  { title: 'アクセント', tokens: SUISOU.accentTokens },
  { title: '意味色', tokens: ['error', 'warning', 'success',
                              'error-surface', 'warning-surface', 'success-surface'] },
  { title: 'その他', tokens: ['scrim'] },
];

const SCALE = [12, 14, 16, 20, 24, 28, 32];
const WEIGHTS = [400, 500, 700];
const ROLES_UI = [
  ['h1', 20, 700], ['h2', 16, 700], ['h3', 14, 700],
  ['p', 14, 400], ['small', 12, 400],
];

const ROLES_DOC = [
  ['h1', 28, 700], ['h2', 24, 700], ['h3', 20, 700], ['h4', 16, 700],
  ['h5', 16, 500], ['h6', 14, 700],
  ['p', 16, 400, true], ['small', 14, 400, true],
];
const SAMPLE = '水槽 Suisou — あいうえお ABCDEfg 0123';

const pairOf = (elm) => (elm.dataset.suisouTheme || '').split(/\s+/).filter(Boolean);
const setPair = (elm, t, a) => { elm.dataset.suisouTheme = `${t} ${a}`; };
const theme = () => pairOf(root)[0];
const accent = () => pairOf(root)[1];
const themeOf = (name) => SUISOU.themes.find((t) => t.name === name);

let current = null;
const cache = {};

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function hexOf(token) {
  return SUISOU.hex[theme()]?.[accent()]?.[token] || '';
}

function metricsOf(node) {
  const s = getComputedStyle(node);
  const px = (v) => Math.round(parseFloat(v));
  return `${px(s.fontSize)} / ${px(s.lineHeight)} / ${s.fontWeight}`;
}

function enhancePalette(scope) {
  const t = themeOf(theme());
  slot('summary', scope).textContent =
    `${t.name}（${t.jp}）× ${accent()}。色は tools/solve.py が制約から解いた値で、`
    + '手で置いた色は1つも無い。';

  const row = slot('accents', scope);
  for (const a of SUISOU.accents) {
    const usable = t.available.includes(a.name);
    const warn = t.warnings?.[a.name];
    const chip = el('button', 'accent-chip', a.jp ? `${a.name}（${a.jp}）` : a.name);
    chip.style.setProperty('--c', 'var(--suisou-accent)');
    setPair(chip, theme(), a.name);
    chip.disabled = !usable;
    if (a.name === accent()) chip.setAttribute('aria-pressed', 'true');
    if (!usable) chip.title = `${theme()} では出せない（色域外）`;
    else if (warn) { chip.classList.add('is-warned'); chip.title = warn; chip.append('　★'); }
    chip.addEventListener('click', () => { setPair(root, theme(), a.name); render(); });
    row.append(chip);
  }
  const warned = Object.entries(t.warnings ?? {});
  const here = t.warnings?.[accent()];
  slot('accent-note', scope).textContent =
    (here ? `★いまの組み合わせは推奨しない … ${here}　` : '')
    + (warned.length
        ? `★の ${warned.length} 色は基準を満たさない。壊れてはいないので選べる（値は CSS に出してある）。　`
        : '')
    + '意味は色だけに載せない（アイコンか文言を添える）。どのアクセントでも同じ。';

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
  fill(slot('scale-ui', scope), SCALE.map((s) => typeRow(`${s}px`, `fs-${s} fw-400`)));
  fill(slot('scale-doc', scope), SCALE.map((s) => typeRow(`${s}px`, `fs-${s} fw-400 typeset`)));
  fill(slot('weights', scope), WEIGHTS.map((n) => typeRow(String(n), `fs-16 fw-${n}`)));
  fill(slot('roles-ui', scope), ROLES_UI.map(([n, s, w]) => typeRow(n, `fs-${s} fw-${w}`)));
  fill(slot('roles-doc', scope), ROLES_DOC.map(([n, s, w, doc]) =>
    typeRow(n, `fs-${s} fw-${w}${doc ? ' typeset' : ''}`)));

  for (const row of scope.querySelectorAll('.t-row')) {
    const note = row.dataset.note;
    row.children[2].textContent = metricsOf(row.children[1]) + (note ? `　${note}` : '');
  }
}

const rootStyle = () => getComputedStyle(root);
const declared = (token) => rootStyle().getPropertyValue(`--suisou-${token}`).trim();

function pxOf(token) {
  const probe = el('div');
  probe.style.cssText =
    `position:absolute;visibility:hidden;height:0;width:var(--suisou-${token})`;
  document.body.append(probe);
  const v = probe.getBoundingClientRect().width;
  probe.remove();
  return Math.round(v * 10) / 10;
}

function tokenRow(scope, token, sample, note) {
  const row = el('div', 'tk-row');
  row.append(el('div', 'tk-name', `--suisou-${token}`),
             el('div', 'tk-val', declared(token)),
             el('div', 'tk-px', note ?? `${pxOf(token)}px`));
  const box = el('div', 'tk-sample');
  box.append(sample);
  row.append(box);
  slot(scope).append(row);
}

function enhanceTokens() {
  const t = themeOf(theme());
  slot('summary').textContent =
    `色以外のトークン。単位は rem で、名前の数字は「ルートが ${pxOf('size-16')}px のときの px」。`
    + ' 左が宣言値、その右が解決後の実寸。ブラウザの文字サイズ設定を変えると右だけが動く。';

  for (const n of [1, 2, 3, 4]) {
    const bar = el('div', 'tk-bar');
    bar.style.width = `var(--suisou-space-${n})`;
    tokenRow('space', `space-${n}`, bar);
  }

  for (const [name, label] of [['radius-small', '行内コード'], ['radius', '面・ボタン・入力欄'],
                               ['radius-pill', 'Avatar・Tag・見出しの帯']]) {
    const box = el('div', 'tk-round', label);
    box.style.borderRadius = `var(--suisou-${name})`;
    tokenRow('radius', name, box);
  }

  const ICON = 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0';
  for (const name of ['icon', 'icon-small']) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('data-suisou-text', name === 'icon-small' ? 'fs-16' : 'fs-20');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', ICON);
    svg.append(path);
    tokenRow('icon', name, svg);
  }

  for (const [name, use] of [['motion-fast', '色だけ動くもの'], ['motion', '現れる・消えるもの']]) {
    const box = el('div', 'tk-motion', 'カーソルを乗せる');
    box.style.transitionDuration = `var(--suisou-${name})`;
    tokenRow('motion', name, box, use);
  }
  const ease = el('div', 'tk-motion', 'カーソルを乗せる');
  ease.style.transitionDuration = 'var(--suisou-motion)';
  tokenRow('motion', 'ease', ease, 'イージング');

  for (const [name, sample] of [['font', '水槽 Suisou — あいうえお ABCDEfg'],
                                ['mono', 'FLOOR["hover"] = 0.03']]) {
    const box = el('div', null, sample);
    box.style.fontFamily = `var(--suisou-${name})`;
    tokenRow('misc', name, box, '書体');
  }
  const ring = el('button', 'tk-focus', 'Tab で辿ると輪が出る');
  tokenRow('misc', 'focus', ring, 'アクセント色と同じ');
}

async function load(name) {
  if (!(name in PAGES)) name = 'palette';
  const box = document.querySelector('main');
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
  box.classList.toggle('is-bleed', !!PAGES[name].bleed);
  scrollTo(0, 0);
  current = name;
  PAGES[name].enhance?.(box);
  for (const a of menu.querySelectorAll('a')) {
    a.setAttribute('aria-current', a.hash === `#${name}` ? 'page' : 'false');
  }
}

function cycleTheme() {
  const names = SUISOU.themes.map((t) => t.name);
  const next = themeOf(names[(names.indexOf(theme()) + 1) % names.length]);
  const a = next.available.includes(accent()) ? accent() : next.available[0];
  setPair(root, next.name, a);
  render();
}

function renderSwitch() {
  const t = themeOf(theme());
  const sub = el('span', null, `${t.jp} — 押すと次のテーマへ`);
  sub.dataset.suisouText = 'fs-12 sub';
  themeSwitch.replaceChildren(el('span', null, t.name), sub);
}

function render() {
  renderSwitch();
  load(current ?? location.hash.slice(1) ?? 'palette');
}

addEventListener('hashchange', () => load(location.hash.slice(1)));
themeSwitch.addEventListener('click', cycleTheme);
menu.addEventListener('click', (e) => { if (e.target.closest('a')) menu.hidePopover(); });

renderSwitch();
load(location.hash.slice(1) || 'palette');
