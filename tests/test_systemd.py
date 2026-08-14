#!/usr/bin/env python3
"""Validate the just-in-time-authored systemd rung against real sandboxing.

The JIT loop's third product (after dind and k3s): a substrate adapter authored
to match a host that offers neither a spare docker daemon nor a cluster, but DOES
run systemd and grant passwordless sudo -- and where the obvious unprivileged path
(`unshare --user`) is blocked by AppArmor's unprivileged-userns restriction. The
system manager, as root, is the one thing left that can stand up real mount/net
namespaces, so the rung confines each step inside a throwaway systemd transient
service (PrivateNetwork, ProtectSystem=strict + ReadWritePaths=workroot,
ProtectHome, PrivateTmp, PrivateDevices, NoNewPrivileges).

This runs a real two-step workload in a uniquely-named throwaway workroot under
/run: step one writes an app artifact AND actively attacks host state; step two
health-checks that the artifact persisted in the shared workroot. It asserts the
attack was confined (a host file the step tried to overwrite survives) and that
teardown reclaims the workroot so the host is left as we found it.

Gated on the mechanism being available (passwordless sudo + systemd-run); when it
is not, asserts the honest failure (provision fails, nothing created) rather than
skipping.

Honest strength under test is 'confined', NOT 'environmental': the confinement is
real for network egress and host writes, but the deploy DRIVER runs as root on the
host via sudo and the step shares the host kernel and can READ the host fs. See the
SystemdSubstrate docstring.

Run: python3 tests/test_systemd.py
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "envelope"))
import substrate  # noqa: E402


def _systemd_sandbox_ok():
    """The mechanism is available iff passwordless sudo can drive systemd-run.
    Probed, not assumed (continuation identity: the environment is re-derived)."""
    try:
        r = subprocess.run("sudo -n systemd-run --version",
                          shell=True, capture_output=True, timeout=15)
        return r.returncode == 0 and b"systemd" in r.stdout
    except Exception:  # noqa: BLE001
        return False


HAS_SYSTEMD = _systemd_sandbox_ok()


class SystemdRung(unittest.TestCase):

    def test_authored_rung_confines_a_workload_and_leaves_the_host_clean(self):
        sub = substrate.SystemdSubstrate(app="sdtest")

        if not HAS_SYSTEMD:
            ok, _ = sub.provision()
            self.assertFalse(ok, "no sandbox should fail provision, creating nothing")
            self.assertEqual(sub.residue(), [], "a failed provision left residue")
            return

        # A host file the workload will try to overwrite from inside the sandbox.
        host_dir = tempfile.mkdtemp(prefix="hoist-sd-host-")
        sentinel = os.path.join(host_dir, "precious.txt")
        with open(sentinel, "w") as f:
            f.write("DO-NOT-TOUCH\n")

        ok, wr = sub.provision()
        self.assertTrue(ok, wr)
        self.assertTrue(wr.startswith("/run/hoist-sbx-sdtest-"))
        try:
            # step one (bringup): stand up an app artifact in the workroot AND
            # actively attack host state -- overwrite the sentinel, reach the network.
            rc, out = sub.exec(
                'echo "listening on :0" > server.log; '
                'echo "ARTIFACT=ok" > app.state; '
                'echo net=$(ip -o link show 2>/dev/null | wc -l); '
                'echo PWNED > "%s" 2>&1 || echo host-write-blocked' % sentinel,
                sub.workroot(), {}, 60)
            self.assertEqual(rc, 0, out)
            # the network was isolated: loopback only (1 interface), no host egress
            self.assertIn("net=1", out, out)

            # step two (health): the artifact from step one persisted in the SHARED
            # workroot, proving successive steps land in the same confined place.
            rc, out = sub.exec(
                'test -f server.log && grep -q ARTIFACT app.state '
                '&& echo HEALTHY || echo UNHEALTHY',
                sub.workroot(), {}, 60)
            self.assertEqual(rc, 0, out)
            self.assertIn("HEALTHY", out, out)

            # acceptance: the attack was confined. The host sentinel is untouched --
            # the overwrite ran where it could not reach host state.
            self.assertTrue(os.path.exists(sentinel),
                           "a confined step deleted a host file")
            with open(sentinel) as f:
                self.assertEqual(f.read(), "DO-NOT-TOUCH\n",
                                "a confined step overwrote a host file")

            # honest labelling: confined, not environmental.
            self.assertEqual(sub.name, "systemd")
            self.assertEqual(sub.strength, "confined")
            self.assertNotIn(
                sub.name, [r[0] for r in substrate.ENVIRONMENTAL_LADDER],
                "a merely-confined rung was wired into the environmental ladder")
        finally:
            ok, detail = sub.teardown()
            os.path.exists(sentinel) and os.remove(sentinel)
            os.path.isdir(host_dir) and os.rmdir(host_dir)
        # teardown reclaimed the workroot; the host is left as we found it.
        self.assertTrue(ok, detail)
        self.assertEqual(sub.residue(), [],
                        "the systemd rung left a workroot behind under /run")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_systemd ({result.testsRun} case; "
              f"sandbox={'yes' if HAS_SYSTEMD else 'no'})")
        sys.exit(0)
    print("FAIL test_systemd")
    sys.exit(1)
