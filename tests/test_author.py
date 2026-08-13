#!/usr/bin/env python3
"""Self-test for hoist author (config drafting). Hermetic, stdlib only."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hoist"))
import author  # noqa: E402


def _repo(files):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".git"))
    for rel, content in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
    return d


class Author(unittest.TestCase):

    def test_hermetic_python_repo_becomes_isolation_none_with_test_checks(self):
        d = _repo({"tests/test_thing.py": "print('ok')\n", "core.py": "x = 1\n"})
        cfg = author.author(d, app="thing")
        prof = cfg["profiles"]["default"]
        self.assertTrue(prof["isolation"].get("none"))
        checks = [c["check"] for c in prof["acceptance"]]
        self.assertIn("python3 tests/test_thing.py", checks)

    def test_compose_repo_gets_real_isolation_and_bringup(self):
        d = _repo({"docker-compose.yml": "services:\n  web:\n    image: x\n"})
        cfg = author.author(d, app="svc")
        prof = cfg["profiles"]["default"]
        self.assertEqual(prof["isolation"]["namespace_env"], "COMPOSE_PROJECT_NAME")
        self.assertIn("compose", prof["bringup"][0]["run"])
        # a machine cannot infer what "it works" means for a service: left as TODO
        import json
        self.assertIn("_TODO", json.dumps(prof))

    def test_binds_track_what_was_detected(self):
        d = _repo({"tests/test_x.py": "print(1)\n"})
        names = [b["name"] for b in author.author(d)["binds"]]
        self.assertIn("git", names)
        self.assertIn("python3", names)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_author ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_author")
    sys.exit(1)
