#!/usr/bin/env python3
"""Resolve a config's operator pin to a local kit directory (build-rule 4).

A config pins the operators it uses: {"operators": {"version", "url", "sha256"}}.
This fetches that release artifact, verifies its sha256 (the pin's integrity), and
extracts it into a version-keyed cache, returning the kit directory. The same pin
resolves to identical operators every time; a tampered or wrong artifact is
rejected, not run. An unpinned config resolves to None: dev mode, use the local
repo. file:// and plain paths work too, so the mechanism is testable offline and a
GitHub release URL slots in unchanged.

Standard library only.
"""

import hashlib
import io
import os
import shutil
import tarfile
import urllib.request


def _cache_root():
    return os.environ.get("HOIST_CACHE") or os.path.expanduser("~/.cache/hoist/operators")


def _fetch(url):
    if url.startswith("file://"):
        url = url[len("file://"):]
    if "://" not in url:
        with open(url, "rb") as f:
            return f.read()
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - operator-supplied
        return r.read()


def _safe_extract(tar, dest):
    root = os.path.realpath(dest)
    for m in tar.getmembers():
        p = os.path.realpath(os.path.join(dest, m.name))
        if p != root and not p.startswith(root + os.sep):
            raise SystemExit(f"refusing unsafe path in operator kit: {m.name}")
    tar.extractall(dest)


def resolve_operators(config, cache_root=None):
    """Return the kit dir for a pinned config, fetching+verifying+extracting once
    and caching by version. Return None if the config pins nothing (dev mode)."""
    pin = config.get("operators") or {}
    url = pin.get("url")
    if not url:
        return None
    version = pin.get("version", "unpinned")
    cache_root = cache_root or _cache_root()
    dest = os.path.join(cache_root, version)
    marker = os.path.join(dest, ".resolved")
    if os.path.isfile(marker):
        return dest

    data = _fetch(url)
    sha = hashlib.sha256(data).hexdigest()
    expected = pin.get("sha256")
    if expected and sha != expected:
        raise SystemExit(
            f"operator pin checksum mismatch for {version}: expected {expected}, got {sha}. "
            "Refusing to run unverified operators."
        )
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        _safe_extract(tar, dest)
    with open(marker, "w") as f:
        f.write(sha)
    return dest
