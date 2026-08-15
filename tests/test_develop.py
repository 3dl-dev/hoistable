#!/usr/bin/env python3
"""Self-test for develop's git topology. Hermetic, stdlib only, local git."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "operators", "develop"))
import tree  # noqa: E402
import guide  # noqa: E402


def _q(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init(d):
    _q("git", "init", "-b", "main", d)
    _q("git", "-C", d, "config", "user.email", "t@example.com")
    _q("git", "-C", d, "config", "user.name", "t")


def _commit(d, fname, content, msg):
    with open(os.path.join(d, fname), "w") as f:
        f.write(content)
    _q("git", "-C", d, "add", "-A")
    _q("git", "-C", d, "commit", "-m", msg)


def _mkdtemp(test):
    """A throwaway dir torn down when the case finishes (hermetic: the suite leaves
    no shared state in /tmp)."""
    d = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


def _upstream_with_v1(test):
    up = _mkdtemp(test)
    _init(up)
    _commit(up, "README", "v1\n", "v1")
    return up


def _clone(test, up):
    user = _mkdtemp(test)
    _q("git", "clone", up, user)
    _q("git", "-C", user, "config", "user.email", "u@example.com")
    _q("git", "-C", user, "config", "user.name", "u")
    return user


class Develop(unittest.TestCase):

    def test_adopt_sets_upstream_and_fork_remotes(self):
        up = _upstream_with_v1(self)
        user = _clone(self, up)
        fork = _mkdtemp(self)
        out = tree.adopt(user, up, mode="fork", fork_url=fork)
        self.assertEqual(out["remotes"]["upstream"], up)
        self.assertEqual(out["remotes"]["origin"], fork)

    def test_pull_upstream_is_clean_and_brings_the_change(self):
        up = _upstream_with_v1(self)
        user = _clone(self, up)
        tree.adopt(user, up, mode="separate")
        _commit(up, "README", "v2\n", "v2")            # upstream moves ahead
        r = tree.pull_upstream(user, branch="main")
        self.assertTrue(r["clean"])
        with open(os.path.join(user, "README")) as f:
            self.assertEqual(f.read(), "v2\n")

    def test_pull_upstream_reports_conflict_honestly(self):
        up = _upstream_with_v1(self)
        user = _clone(self, up)
        tree.adopt(user, up, mode="separate")
        _commit(user, "README", "mine\n", "local change")
        _commit(up, "README", "theirs\n", "upstream change")
        r = tree.pull_upstream(user, branch="main")
        self.assertFalse(r["clean"])  # a real conflict, not silently merged

    def test_contribute_creates_a_branch(self):
        up = _upstream_with_v1(self)
        user = _clone(self, up)
        out = tree.contribute(user, "fix-thing")
        self.assertTrue(out["ok"])
        head = subprocess.run(["git", "-C", user, "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(head, "fix-thing")

    def test_diverge_report_counts_ahead_behind(self):
        up = _upstream_with_v1(self)
        user = _clone(self, up)
        tree.adopt(user, up, mode="separate")
        _commit(user, "local.txt", "x\n", "local only")   # 1 ahead
        _commit(up, "up.txt", "y\n", "upstream only")      # 1 behind
        d = tree.diverge_report(user, branch="main")
        self.assertEqual(d["ahead"], "1")
        self.assertEqual(d["behind"], "1")


class Guide(unittest.TestCase):

    def test_harvests_test_command_contributing_and_ci(self):
        d = _mkdtemp(self)
        with open(os.path.join(d, "Makefile"), "w") as f:
            f.write("## run the tests\ntest:\n\tpytest\n")
        with open(os.path.join(d, "CONTRIBUTING.md"), "w") as f:
            f.write("how to contribute\n")
        os.makedirs(os.path.join(d, ".github", "workflows"))
        with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w") as f:
            f.write("name: ci\n")
        g = guide.dev_guide(d)
        self.assertIn("make test", g["test"])
        self.assertEqual(g["contributing"], "CONTRIBUTING.md")
        self.assertIn("ci.yml", g["ci"])

    def test_harvests_python_test_files(self):
        d = _mkdtemp(self)
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "test_x.py"), "w") as f:
            f.write("print(1)\n")
        self.assertIn("python3 tests/test_x.py", guide.dev_guide(d)["test"])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=0).result
    if result.wasSuccessful():
        print(f"PASS test_develop ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_develop")
    sys.exit(1)
