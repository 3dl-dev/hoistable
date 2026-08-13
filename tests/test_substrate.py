#!/usr/bin/env python3
"""Self-test for the isolation substrate: resolution, honest refusal, and the
environmental guarantee.

Two layers, on purpose:

  - Hermetic (always run, no docker): the substrate is *resolved*, not depended
    on. A required environmental rung that does not resolve is a cannot-build,
    named, that deploys nothing. And the envelope routes every deploy step through
    the resolved substrate's exec, with teardown guaranteed.

  - The real environmental proof (runs when docker resolves on this host; when it
    does not, the same test asserts the honest cannot-build path instead of
    skipping): a config that IGNORES its own isolation and actively tries to
    overwrite a host file, delete a host directory, and kill host containers still
    cannot touch host state, because its steps ran inside a throwaway dind
    substrate. The host file, and the host docker daemon, are byte-identical after.

Run: python3 tests/test_substrate.py
"""

import os
import shlex
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "envelope"))
import envelope  # noqa: E402
import substrate  # noqa: E402


def _docker_ok():
    try:
        return subprocess.run("docker version", shell=True, capture_output=True,
                             timeout=20).returncode == 0
    except Exception:  # noqa: BLE001
        return False


HAS_DOCKER = _docker_ok()


class FakeEnvSubstrate(substrate.Substrate):
    """A stand-in environmental rung with no real isolation: it runs steps in a
    temp 'inside' dir and records that it was used and torn down. It proves the
    *seam* (deploy steps route through exec; teardown always runs), not real
    confinement -- that is dind's job, exercised by the docker-gated test."""

    name = "fake-env"
    strength = "environmental"

    def __init__(self):
        self._root = tempfile.mkdtemp(prefix="fake-substrate-")
        self.exec_calls = []
        self.torn_down = False

    def workroot(self):
        return self._root

    def provision(self):
        return True, "fake"

    def exec(self, cmd, cwd, env_overrides, timeout):
        self.exec_calls.append(cmd)
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (env_overrides or {}).items()})
        p = subprocess.run(cmd, shell=True, cwd=cwd, timeout=timeout,
                          capture_output=True, text=True, env=env)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()[-2000:]

    def teardown(self):
        self.torn_down = True
        return True, ""


class Resolution(unittest.TestCase):

    def test_host_floor_is_always_feasible(self):
        feasible, info = substrate.probe_substrate({}, {})
        self.assertTrue(feasible)
        self.assertEqual(info["strength"], "host")

    def test_unknown_strength_is_not_feasible(self):
        feasible, reason = substrate.probe_substrate(
            {}, {"isolation": {"require": "moon-base"}})
        self.assertFalse(feasible)
        self.assertIn("moon-base", reason)

    def test_resolve_host_returns_host_substrate(self):
        sub, info = substrate.resolve_substrate({"app": "x"}, {}, tempfile.mkdtemp())
        self.assertIsInstance(sub, substrate.HostSubstrate)
        self.assertEqual(info["strength"], "host")

    def test_environmental_required_but_none_resolves_is_cannot_build(self):
        # DONE-WHEN (b): nothing resolves + config requires isolation -> cannot-build,
        # named, deploying NOTHING. Stub the ladder to a rung whose prereq fails.
        saved = substrate.ENVIRONMENTAL_LADDER
        substrate.ENVIRONMENTAL_LADDER = [
            ("never", "environmental", "false", lambda c, t: None)]
        try:
            config = {"app": "toy", "profiles": {"default": {
                "isolation": {"require": "environmental"},
                "bringup": [{"name": "up", "run": "echo should-not-run > /tmp/x"}],
                "health": [{"name": "h", "check": "true"}],
                "acceptance": [{"name": "a", "check": "true"}],
            }}}
            r = envelope.run_envelope(config, tempfile.mkdtemp())
            self.assertEqual(r["outcome"], "cannot-build")
            self.assertIn("no isolation substrate resolved", r["reason"])
            self.assertEqual(r["bringup"], [])  # deployed nothing
        finally:
            substrate.ENVIRONMENTAL_LADDER = saved


class Seam(unittest.TestCase):

    def test_deploy_routes_through_substrate_exec_and_tears_down(self):
        # The envelope must run every deploy step through the resolved substrate's
        # exec, and tear the substrate down whatever the outcome.
        fake = FakeEnvSubstrate()
        saved = substrate.ENVIRONMENTAL_LADDER
        substrate.ENVIRONMENTAL_LADDER = [
            ("fake-env", "environmental", "true", lambda c, t: fake)]
        try:
            config = {"app": "toy", "profiles": {"default": {
                "isolation": {"require": "environmental"},
                "bringup": [{"name": "up", "run": "echo up > marker"}],
                "health": [{"name": "marker-in-substrate",
                            "check": "test -f marker"}],
                "acceptance": [{"name": "a", "check": "true"}],
            }}}
            r = envelope.run_envelope(config, tempfile.mkdtemp())
            self.assertEqual(r["outcome"], "built")
            # the bringup ran through the substrate, in the substrate's workroot
            self.assertTrue(any("echo up" in c for c in fake.exec_calls))
            self.assertTrue(os.path.exists(os.path.join(fake.workroot(), "marker")))
            # teardown ran, and the report says so
            self.assertTrue(fake.torn_down)
            self.assertTrue(r["substrate"]["torn_down"])
        finally:
            substrate.ENVIRONMENTAL_LADDER = saved

    def test_teardown_runs_even_on_failure(self):
        fake = FakeEnvSubstrate()
        saved = substrate.ENVIRONMENTAL_LADDER
        substrate.ENVIRONMENTAL_LADDER = [
            ("fake-env", "environmental", "true", lambda c, t: fake)]
        try:
            config = {"app": "toy", "profiles": {"default": {
                "isolation": {"require": "environmental"},
                "bringup": [{"name": "up", "run": "true"}],
                "health": [{"name": "down", "check": "test -f never-created"}],
                "acceptance": [{"name": "a", "check": "true"}],
            }}}
            r = envelope.run_envelope(config, tempfile.mkdtemp())
            self.assertEqual(r["outcome"], "honest-failure")
            self.assertTrue(fake.torn_down)  # torn down despite the failure
        finally:
            substrate.ENVIRONMENTAL_LADDER = saved


class EnvironmentalGuarantee(unittest.TestCase):

    def test_a_config_that_ignores_its_isolation_cannot_touch_host_state(self):
        # DONE-WHEN (c), the heart of hoistable-543. A malicious config that
        # declares only 'require environmental' (no namespace of its own) and whose
        # bringup actively attacks host state. When dind resolves, its steps run
        # inside the throwaway container and the host is left byte-identical. When
        # docker does not resolve, the resolver refuses and deploys nothing -- also
        # a safe outcome, asserted here rather than skipped.
        host_dir = tempfile.mkdtemp(prefix="hoist-host-state-")
        sentinel = os.path.join(host_dir, "precious.txt")
        with open(sentinel, "w") as f:
            f.write("DO-NOT-TOUCH\n")

        config = {"app": "malicious", "profiles": {"default": {
            "isolation": {"require": "environmental"},
            "bringup": [
                {"name": "try-overwrite-host-file",
                 "run": f"echo PWNED > {shlex.quote(sentinel)} 2>/dev/null || true"},
                {"name": "try-delete-host-dir",
                 "run": f"rm -rf {shlex.quote(host_dir)} 2>/dev/null || true"},
                {"name": "try-kill-host-containers",
                 "run": "docker rm -f $(docker ps -aq) 2>/dev/null || true"},
            ],
            "health": [{"name": "substrate-up", "check": "true"}],
            "acceptance": [{"name": "steps-ran", "check": "true"}],
        }}}

        r = envelope.run_envelope(config, tempfile.mkdtemp(), timeout=300)

        if not HAS_DOCKER:
            self.assertEqual(r["outcome"], "cannot-build")
            self.assertIn("no isolation substrate", r["reason"])
            return

        # The host file is untouched: the attack ran somewhere it could not see it.
        self.assertTrue(os.path.exists(sentinel),
                       "a sandboxed hoist deleted a host file")
        with open(sentinel) as f:
            self.assertEqual(f.read(), "DO-NOT-TOUCH\n",
                            "a sandboxed hoist overwrote a host file")
        # It ran in an environmental substrate, which was torn down.
        self.assertEqual(r["substrate"]["strength"], "environmental")
        self.assertTrue(r["substrate"].get("torn_down"))
        # The host docker daemon is byte-identical before and after.
        self.assertIn("blast_radius", r)
        self.assertTrue(r["blast_radius"]["clean"],
                       "host daemon state changed despite the environmental substrate")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_substrate ({result.testsRun} cases; "
              f"docker={'yes' if HAS_DOCKER else 'no'})")
        sys.exit(0)
    print("FAIL test_substrate")
    sys.exit(1)
