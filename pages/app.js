const menu = document.querySelector('nav[popover]');

const PAGES = {
  import: {},
  theme: {},
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
  if (PAGES[name].bleed) box.dataset.suisou = 'p-0';
  else delete box.dataset.suisou;
  box.scrollTo(0, 0);
  for (const a of menu.querySelectorAll('a')) {
    a.setAttribute('aria-current', a.hash === `#${name}` ? 'page' : 'false');
  }
}

addEventListener('hashchange', () => load(location.hash.slice(1)));
menu.addEventListener('click', (e) => { if (e.target.closest('a')) menu.hidePopover(); });

load(location.hash.slice(1) || 'import');
