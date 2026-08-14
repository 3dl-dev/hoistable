#!/usr/bin/env python3
"""Self-test for operator pin resolution. Hermetic, stdlib only."""

import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "hoist"))
import pins  # noqa: E402


def _tarball(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, content in files.items():
            data = content.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def _write(data):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "kit.tgz")
    with open(p, "wb") as f:
        f.write(data)
    return p


class Pins(unittest.TestCase):

    def test_unpinned_returns_none(self):
        self.assertIsNone(pins.resolve_operators({}, cache_root=tempfile.mkdtemp()))

    def test_resolves_and_extracts_verified_pin(self):
        data = _tarball({"envelope/envelope.py": "print('kit')\n"})
        sha = hashlib.sha256(data).hexdigest()
        cfg = {"operators": {"version": "1.0", "url": "file://" + _write(data), "sha256": sha}}
        kit = pins.resolve_operators(cfg, cache_root=tempfile.mkdtemp())
        self.assertTrue(os.path.isfile(os.path.join(kit, "envelope", "envelope.py")))

    def test_checksum_mismatch_is_rejected(self):
        data = _tarball({"x.py": "y\n"})
        cfg = {"operators": {"version": "1.0", "url": "file://" + _write(data), "sha256": "deadbeef"}}
        with self.assertRaises(SystemExit):
            pins.resolve_operators(cfg, cache_root=tempfile.mkdtemp())

    def test_second_resolve_uses_cache(self):
        data = _tarball({"a.py": "b\n"})
        sha = hashlib.sha256(data).hexdigest()
        tgz = _write(data)
        cache = tempfile.mkdtemp()
        cfg = {"operators": {"version": "2.0", "url": "file://" + tgz, "sha256": sha}}
        k1 = pins.resolve_operators(cfg, cache_root=cache)
        os.remove(tgz)  # source gone; the cache marker must short-circuit
        k2 = pins.resolve_operators(cfg, cache_root=cache)
        self.assertEqual(k1, k2)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_pins ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_pins")
    sys.exit(1)
