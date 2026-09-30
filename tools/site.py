#!/usr/bin/env python3

import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
PAGES = os.path.join(ROOT, "pages")

CURRENT = ["dist", "v2"]
FROZEN = {"v1": "07c066f"}

def git(*args, **kw):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, **kw)

def build(src, version):
    env = dict(os.environ, SUISOU_VERSION=version)
    subprocess.run([sys.executable, "tools/solve.py"], cwd=src, check=True, capture_output=True)
    subprocess.run([sys.executable, "tools/bundle.py"], cwd=src, check=True, capture_output=True, env=env)
    for d in (os.path.join(src, "pages", "dist"), os.path.join(src, "dist")):
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
    if len(sys.argv) != 2:
        sys.exit("使い方: python3 tools/site.py <出力先>")
    site = os.path.abspath(sys.argv[1])
    head = git("rev-parse", "--short=7", "HEAD", text=True).stdout.strip()
    dist = build(ROOT, head)

    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(PAGES, site, ignore=lambda d, names: ["dist"] if d == PAGES else [])
    for name in CURRENT:
        shutil.copytree(dist, os.path.join(site, name))
    for name, sha in FROZEN.items():
        if not build_at(sha, sha, os.path.join(site, name)):
            sys.exit(f"{name}（{sha}）を組めなかった")

    built, skipped = 0, 0
    for sha in git("rev-list", "HEAD", text=True).stdout.split():
        if git("ls-tree", sha, "tools/bundle.py", text=True).stdout.strip() == "":
            continue
        short = sha[:7]
        if build_at(sha, short, os.path.join(site, "v", short)):
            built += 1
        else:
            skipped += 1

    print(f"{site}: HEAD {head} → {' '.join('/' + n + '/' for n in CURRENT)}")
    print(f"凍結: {' '.join(f'/{n}/ ← {s}' for n, s in FROZEN.items())}")
    print(f"固定 URL: {built} 版（組めなかった {skipped} 版）")

if __name__ == "__main__":
    main()
