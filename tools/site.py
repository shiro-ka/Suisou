#!/usr/bin/env python3

import html, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
PAGES = os.path.join(ROOT, "pages")

CURRENT = "v3"
FROZEN = {"v2": "364c528"}

def git(*args, **kw):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, **kw)

def build(src, version):
    env = dict(os.environ, SUISOU_VERSION=version)
    subprocess.run([sys.executable, "tools/solve.py"], cwd=src, check=True, capture_output=True)
    subprocess.run([sys.executable, "tools/bundle.py"], cwd=src, check=True, capture_output=True, env=env)
    for d in (os.path.join(src, "pages", CURRENT), os.path.join(src, "pages", "dist"), os.path.join(src, "dist")):
        if os.path.isdir(d):
            return d
    raise subprocess.CalledProcessError(1, "bundle.py")

def build_at(sha, version, dest):
    tmp = tempfile.mkdtemp()
    try:
        tar = git("archive", sha).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=tar, check=True)
        shutil.copytree(build(tmp, version), dest)
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

CSS_BLOCK = re.compile(r'<pre><code data-css="([^"]+)"(?: data-css-only="([^"]+)")?></code></pre>')
NESTED = ("@media", "@supports", "@container", "@starting-style", "@layer")

def statements(css):
    out, depth, start = [], 0, 0
    for i, ch in enumerate(css):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(css[start:i + 1])
                start = i + 1
        elif ch == ";" and depth == 0:
            out.append(css[start:i + 1])
            start = i + 1
    return out

def matches(prelude, words):
    values = set(re.findall(r'="([^"]+)"', prelude))
    for w in words:
        if w.startswith("="):
            if values == set(w[1:].split(",")):
                return True
        elif w.startswith("["):
            if w in prelude:
                return True
        elif re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", prelude):
            return True
    return False

def pick(css, words):
    kept = []
    for st in statements(css):
        prelude, _, body = st.partition("{")
        if prelude.strip().startswith(NESTED):
            inner = pick(body[:body.rfind("}")], words)
            if inner:
                kept.append(prelude + "{" + inner + "\n}")
        elif matches(prelude, words):
            kept.append(st)
    return "".join(kept)

def fill_css(site):
    content = os.path.join(site, "content")
    for name in os.listdir(content):
        if not name.endswith(".html"):
            continue
        path = os.path.join(content, name)
        with open(path, encoding="utf-8") as f:
            page = f.read()
        def fill(m):
            css = "\n\n".join(open(os.path.join(site, src), encoding="utf-8").read().strip("\n") for src in m.group(1).split())
            if m.group(2):
                css = pick(re.sub(r"/\*.*?\*/", "", css, flags=re.S), m.group(2).split()).strip("\n")
            return "<pre><code>" + html.escape(css, quote=False) + "</code></pre>"
        filled = CSS_BLOCK.sub(fill, page)
        if filled != page:
            with open(path, "w", encoding="utf-8") as f:
                f.write(filled)

def main():
    site = os.path.join(ROOT, "_site")
    head = git("rev-parse", "--short=7", "HEAD", text=True).stdout.strip()
    dist = build(ROOT, head)

    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(PAGES, site, ignore=lambda d, names: [CURRENT] if d == PAGES else [])
    shutil.copytree(dist, os.path.join(site, CURRENT))
    fill_css(site)
    for name, sha in FROZEN.items():
        if not build_at(sha, sha, os.path.join(site, name)):
            sys.exit(f"{name}（{sha}）を組めなかった")

    print(f"{site}: HEAD {head} → /{CURRENT}/")
    print(f"凍結: {' '.join(f'/{n}/ ← {s}' for n, s in FROZEN.items())}")

if __name__ == "__main__":
    main()
