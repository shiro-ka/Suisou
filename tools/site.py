#!/usr/bin/env python3

import os, shutil, subprocess, sys, tempfile

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

def main():
    site = os.path.join(ROOT, "_site")
    head = git("rev-parse", "--short=7", "HEAD", text=True).stdout.strip()
    dist = build(ROOT, head)

    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(PAGES, site, ignore=lambda d, names: [CURRENT] if d == PAGES else [])
    shutil.copytree(dist, os.path.join(site, CURRENT))
    for name, sha in FROZEN.items():
        if not build_at(sha, sha, os.path.join(site, name)):
            sys.exit(f"{name}（{sha}）を組めなかった")

    print(f"{site}: HEAD {head} → /{CURRENT}/")
    print(f"凍結: {' '.join(f'/{n}/ ← {s}' for n, s in FROZEN.items())}")

if __name__ == "__main__":
    main()
