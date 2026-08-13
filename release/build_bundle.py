#!/usr/bin/env python3
"""Pack an app's distribution bundle: the unit that lets software ship itself.

build_release.py packs the reusable operator KIT (shared across all apps). This
packs an APP's bundle: its Layer 2 config (with the operator pin injected), its
petard-cards spec (the LOM ground-truth surface), and a manifest -- a deterministic,
liftable tarball. The bundle PINS the operators (build-rule 4), it does not vendor
them: a fresh target resolves the pin from the Layer 0 release, so one repo upgrading
never breaks another.

This is the skillc envelope pattern applied to a whole deployable org: the bundle is
a RECIPE, not a binary. It carries no built instance -- on a fresh target `hoist
<bundle>/config.json` rebuilds the instance and the envelope self-grades it with an
honest transfer score (build-rule 7). Lift it out, resolve its references, and it
runs (build-rule 3); if it cannot, it is not done.

Deterministic (sorted entries, zeroed mtimes) so the same bundle content always
produces the same sha256. Standard library only.

Usage: build_bundle.py <app-dir> [--operators-pin pin.json] [--out-dir dist]
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile

BUNDLE_KIND = "hoistable.bundle/v1"


def _deterministic_tar(tar_path, members):
    """Write members (arcname -> bytes) to a reproducible .tgz: sorted, mtimes and
    ids zeroed, so identical content yields an identical sha256."""
    with tarfile.open(tar_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        for name in sorted(members):
            data = members[name]
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mtime = 0
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            tar.addfile(ti, io.BytesIO(data))
    with open(tar_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_bundle(app_dir, operators_pin=None, out_dir="dist",
                config_name="config.json", spec_name="petard-cards-spec.json"):
    """Pack app_dir's config (+ operator pin) and petard-cards spec into a bundle.
    Returns (tar_path, sha256). operators_pin is {version, url, sha256}; when given
    it is injected into the config so the bundle is self-pinning."""
    with open(os.path.join(app_dir, config_name)) as f:
        config = json.load(f)
    if operators_pin:
        config["operators"] = operators_pin           # pin, do not vendor
    app = config.get("app", "app")

    members = {"config.json": json.dumps(config, indent=2, sort_keys=True).encode()}
    spec_path = os.path.join(app_dir, spec_name)
    if os.path.isfile(spec_path):
        with open(spec_path, "rb") as f:
            members[spec_name] = f.read()

    manifest = {
        "kind": BUNDLE_KIND,
        "app": app,
        "files": sorted(members),
        "operators": config.get("operators"),          # the pin the target resolves
        "note": "a recipe, not a binary: hoist config.json on a clean target; the "
                "envelope rebuilds and self-grades. Operators are pinned, not vendored.",
    }
    members["MANIFEST.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()

    os.makedirs(out_dir, exist_ok=True)
    tar_path = os.path.join(out_dir, f"hoistable-bundle-{app}.tgz")
    sha = _deterministic_tar(tar_path, members)
    with open(tar_path + ".sha256", "w") as f:
        f.write(sha + "\n")
    return tar_path, sha


def main(argv=None):
    ap = argparse.ArgumentParser(description="pack an app's distribution bundle")
    ap.add_argument("app_dir", help="dir with config.json (+ petard-cards-spec.json)")
    ap.add_argument("--operators-pin", default=None,
                    help="JSON file with {version, url, sha256} to pin operators")
    ap.add_argument("--out-dir", default="dist")
    args = ap.parse_args(argv)
    pin = None
    if args.operators_pin:
        with open(args.operators_pin) as f:
            pin = json.load(f)
        pin = pin.get("operators", pin)
    tar_path, sha = build_bundle(args.app_dir, pin, args.out_dir)
    print(f"built {tar_path}")
    print(f"sha256 {sha}")
    print("lift it onto a clean target and run:  python3 <kit>/hoist/hoist.py "
          "<extracted-bundle>/config.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
