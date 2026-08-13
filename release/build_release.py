#!/usr/bin/env python3
"""Package the operator kit for a versioned release (build-rule 4: repeatability).

A hoistable project's Layer 2 config does not vendor the operators; it PINS a
version and pulls it from the Layer 0 release. This builds that release artifact:
a deterministic tarball of the operator kit (envelope + hoist + operators) plus a
manifest, ready to upload to a GitHub release. The tarball's sha256 is the pin's
integrity check, so a config that pins {url, sha256} resolves to identical
operators every time.

Deterministic: file mtimes/uids are zeroed and entries sorted, so the same kit
content always produces the same sha256. Standard library only.

Usage: build_release.py --version 0.0.1 [--out-dir dist] [--kit envelope hoist operators]
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _entries(kit_dirs):
    files = []
    for d in kit_dirs:
        base = os.path.join(REPO, d)
        for root, _, names in os.walk(base):
            for n in sorted(names):
                if n.endswith((".pyc",)) or "__pycache__" in root:
                    continue
                full = os.path.join(root, n)
                files.append((full, os.path.relpath(full, REPO)))
    return sorted(files, key=lambda x: x[1])


def build(version, out_dir, kit_dirs):
    os.makedirs(out_dir, exist_ok=True)
    tar_path = os.path.join(out_dir, f"hoistable-operators-{version}.tgz")
    files = _entries(kit_dirs)

    def _reset(ti):
        ti.mtime = 0
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        return ti

    with tarfile.open(tar_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        # a manifest first, so the kit is self-describing
        manifest = {
            "version": version,
            "kit": kit_dirs,
            "files": [rel for _, rel in files],
        }
        data = json.dumps(manifest, indent=2, sort_keys=True).encode()
        ti = tarfile.TarInfo("MANIFEST.json")
        ti.size = len(data)
        _reset(ti)
        tar.addfile(ti, io.BytesIO(data))
        for full, rel in files:
            tar.add(full, arcname=rel, filter=_reset)

    sha = hashlib.sha256(open(tar_path, "rb").read()).hexdigest()
    with open(tar_path + ".sha256", "w") as f:
        f.write(sha + "\n")
    return tar_path, sha


def main(argv=None):
    ap = argparse.ArgumentParser(description="package the operator kit for a release")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out-dir", default=os.path.join(REPO, "dist"))
    ap.add_argument("--kit", nargs="+", default=["envelope", "hoist", "operators"])
    ap.add_argument("--repo-slug", default="baron-3dl/hoistable",
                    help="for printing the gh release command")
    args = ap.parse_args(argv)
    tar_path, sha = build(args.version, args.out_dir, args.kit)
    print(f"built {tar_path}")
    print(f"sha256 {sha}")
    print("pin this in a config's \"operators\":")
    url = (f"https://github.com/{args.repo_slug}/releases/download/"
           f"v{args.version}/{os.path.basename(tar_path)}")
    print(json.dumps({"operators": {"version": args.version, "url": url, "sha256": sha}}, indent=2))
    print("\npublish with:")
    print(f"  gh release create v{args.version} {tar_path} "
          f"--repo {args.repo_slug} --title 'operators v{args.version}' --notes 'operator kit'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
