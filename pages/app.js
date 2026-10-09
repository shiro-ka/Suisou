const menu = document.querySelector('nav[popover]');

const PAGES = {
  import: {},
  theme: {},
  palette: {},
  body: {},
  layout: {},
  tray: {},
  item: {},
  'circle-square': {},
  tag: {},
  notice: {},
  field: {},
  media: {},
  button: {},
  input: {},
  loading: {},
  text: {},
  typeset: {},
  toc: {},
  utilities: {},
  responsive: {},
  chat: { bleed: true },
  list: { bleed: true },
  blog: {},
};

const cache = {};

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

async function load(name) {
  if (!(name in PAGES)) name = 'import';
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
  const words = (box.dataset.suisou ?? '').split(' ').filter((w) => w && w !== 'p-0');
  if (PAGES[name].bleed) words.push('p-0');
  box.dataset.suisou = words.join(' ');
  box.scrollTo(0, 0);
  for (const a of menu.querySelectorAll('a')) {
    a.setAttribute('aria-current', a.hash === `#${name}` ? 'page' : 'false');
  }
}

const root = document.documentElement;
const pickPrimary = document.querySelector('.theme-primary');
const pickAccent = document.querySelector('.theme-accent');

function setTheme(primary, accent) {
  if (!SUISOU.themes.some((t) => t.name === primary)) primary = SUISOU.default.theme;
  if (!SUISOU.accents.some((a) => a.name === accent)) accent = SUISOU.default.accent;
  root.dataset.suisouTheme = `${primary} ${accent}`;
  pickPrimary.value = primary;
  pickAccent.value = accent;
  try { localStorage.setItem('suisou-theme', root.dataset.suisouTheme); } catch (e) {}
}

for (const t of SUISOU.themes) pickPrimary.append(new Option(t.name, t.name));
for (const a of SUISOU.accents) pickAccent.append(new Option(a.name, a.name));
setTheme(...root.dataset.suisouTheme.split(' '));
pickPrimary.addEventListener('change', () => setTheme(pickPrimary.value, pickAccent.value));
pickAccent.addEventListener('change', () => setTheme(pickPrimary.value, pickAccent.value));

addEventListener('hashchange', () => load(location.hash.slice(1)));
menu.addEventListener('click', (e) => { if (e.target.closest('a')) menu.hidePopover(); });

load(location.hash.slice(1) || 'import');
