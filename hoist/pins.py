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
import subprocess
import tarfile
import tempfile
import urllib.request


def _cache_root():
    return os.environ.get("HOIST_CACHE") or os.path.expanduser("~/.cache/hoist/operators")


def _fetch_github_release(url):
    """Fetch a GitHub release asset via gh, which authenticates correctly for
    private repos (a raw token on the browser download URL 404s). URL shape:
    https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>."""
    parts = url.split("/")
    i = parts.index("releases")
    owner, repo, tag, asset = parts[i - 2], parts[i - 1], parts[i + 2], parts[i + 3]
    dest = tempfile.mkdtemp()
    subprocess.run(
        ["gh", "release", "download", tag, "--repo", f"{owner}/{repo}",
         "--pattern", asset, "--dir", dest],
        check=True, capture_output=True, text=True,
    )
    with open(os.path.join(dest, asset), "rb") as f:
        return f.read()


def _fetch(url):
    if url.startswith("file://"):
        url = url[len("file://"):]
    if "://" not in url:
        with open(url, "rb") as f:
            return f.read()
    if "github.com" in url and "/releases/download/" in url:
        return _fetch_github_release(url)
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
