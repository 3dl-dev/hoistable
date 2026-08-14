#!/usr/bin/env python3
"""Validate the just-in-time-authored k3s rung against a real cluster.

The JIT loop's first product: a substrate adapter authored to match an operator's
standing reality (a kubectl-reachable cluster), graded against that reality. This
runs a trivial workload in a uniquely-named throwaway namespace, confirms it ran,
and verifies teardown deletes the namespace so the cluster is left untouched
(non-destructive: it only ever touches its own namespace, never existing ones).

Gated on a reachable cluster; when none is reachable, asserts the honest failure
(provision fails, nothing created) rather than skipping.

Run: python3 tests/test_k3s.py
"""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "envelope"))
import substrate  # noqa: E402


def _k3s_ok():
    try:
        r = subprocess.run("kubectl version -o json --request-timeout=5s",
                          shell=True, capture_output=True, timeout=15)
        return r.returncode == 0 and b'"serverVersion"' in r.stdout
    except Exception:  # noqa: BLE001
        return False


HAS_K3S = _k3s_ok()


class K3sRung(unittest.TestCase):

    def test_authored_rung_hoists_a_workload_and_leaves_the_cluster_clean(self):
        sub = substrate.K3sSubstrate(app="k3stest")

        if not HAS_K3S:
            ok, _ = sub.provision()
            self.assertFalse(ok, "no cluster should fail provision, creating nothing")
            return

        ok, ns = sub.provision()
        self.assertTrue(ok, ns)
        self.assertTrue(ns.startswith("hoist-sbx-k3stest-"))
        try:
            # deploy a trivial workload into OUR namespace only
            rc, out = sub.exec(
                'kubectl -n "$HOIST_NS" create job hoisted --image=busybox:1.36 '
                '-- sh -c "echo hoisted-ok"', "/tmp", {}, 60)
            self.assertEqual(rc, 0, out)
            # health: the job runs to completion in the cluster
            rc, out = sub.exec(
                'kubectl -n "$HOIST_NS" wait --for=condition=complete '
                'job/hoisted --timeout=120s', "/tmp", {}, 150)
            self.assertEqual(rc, 0, out)
            # acceptance: its real output, harvested from the cluster
            rc, out = sub.exec('kubectl -n "$HOIST_NS" logs job/hoisted', "/tmp", {}, 60)
            self.assertIn("hoisted-ok", out)
            # the workload ran off-host, in the cluster, in our namespace
            self.assertIn("k3s", sub.name)
            self.assertEqual(sub.strength, "cluster")
        finally:
            ok, detail = sub.teardown()
        # teardown deleted the namespace; the cluster is left as we found it
        self.assertTrue(ok, detail)
        self.assertEqual(sub.residue(), [],
                        "the k3s rung left a namespace behind on the cluster")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_k3s ({result.testsRun} case; "
              f"cluster={'yes' if HAS_K3S else 'no'})")
        sys.exit(0)
    print("FAIL test_k3s")
    sys.exit(1)
