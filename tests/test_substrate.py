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
    substrate. A host file and a named host container both survive the attack, and
    the substrate leaves no residue of its own on the host.

Run: python3 tests/test_substrate.py
"""

import os
import shlex
import subprocess
import sys
import tempfile
import uuid
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


class OperateMode(unittest.TestCase):
    """The sysop path: deploy and KEEP the substrate running, distinct from the
    grade-and-teardown default. petard needs a deploy that stays up."""

    def _stub_ladder(self, fake):
        self._saved = substrate.ENVIRONMENTAL_LADDER
        substrate.ENVIRONMENTAL_LADDER = [
            ("fake-env", "environmental", "true", lambda c, t: fake)]

    def tearDown(self):
        if hasattr(self, "_saved"):
            substrate.ENVIRONMENTAL_LADDER = self._saved

    def _config(self):
        return {"app": "toy", "profiles": {"default": {
            "isolation": {"require": "environmental"},
            "bringup": [{"name": "up", "run": "echo up > marker"}],
            "health": [{"name": "h", "check": "test -f marker"}],
            "acceptance": [{"name": "a", "check": "true"}],
        }}}

    def test_operate_keeps_the_substrate_running_until_explicit_teardown(self):
        fake = FakeEnvSubstrate()
        self._stub_ladder(fake)
        report, sub = envelope.operate(self._config())
        # graded like a normal hoist ...
        self.assertEqual(report["outcome"], "built")
        self.assertTrue(report["substrate"]["operating"])
        # ... but NOT torn down: the deploy stays up and we get the live handle
        self.assertFalse(fake.torn_down)
        self.assertIs(sub, fake)
        # the handle is live: we can exec into the still-running deploy
        rc, out = sub.exec("cat marker", sub.workroot(), {}, 30)
        self.assertEqual(rc, 0)
        self.assertIn("up", out)
        # teardown is a separate, explicit call the caller owns
        ok, _ = sub.teardown()
        self.assertTrue(ok)
        self.assertTrue(fake.torn_down)

    def test_grade_path_still_tears_down(self):
        # operate is opt-in; the default path is unchanged (tears down).
        fake = FakeEnvSubstrate()
        self._stub_ladder(fake)
        r = envelope.run_envelope(self._config(), tempfile.mkdtemp())
        self.assertEqual(r["outcome"], "built")
        self.assertTrue(fake.torn_down)
        self.assertNotIn("_substrate_obj", r)


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

        if not HAS_DOCKER:
            r = envelope.run_envelope(config, tempfile.mkdtemp(), timeout=300)
            self.assertEqual(r["outcome"], "cannot-build")
            self.assertIn("no isolation substrate", r["reason"])
            return

        # A named host container the attack ("docker rm -f $(docker ps -aq)") would
        # kill if it could reach the host daemon. It cannot: that command runs on
        # the inner daemon inside dind. We check THIS container by name rather than
        # diffing the whole host daemon, so unrelated containers churning on a busy
        # host cannot turn this into a false alarm.
        sentinel_ctr = f"hoist-blast-sentinel-{uuid.uuid4().hex[:8]}"
        subprocess.run(f"docker run -d --name {sentinel_ctr} alpine sleep 120",
                      shell=True, capture_output=True, timeout=60)
        try:
            r = envelope.run_envelope(config, tempfile.mkdtemp(), timeout=300)
            # The host file is untouched: the attack ran where it could not see it.
            self.assertTrue(os.path.exists(sentinel),
                           "a sandboxed hoist deleted a host file")
            with open(sentinel) as f:
                self.assertEqual(f.read(), "DO-NOT-TOUCH\n",
                                "a sandboxed hoist overwrote a host file")
            # The host sentinel container survived: the attack could not kill it.
            probe = subprocess.run(
                f"docker ps -aq --filter name={sentinel_ctr}",
                shell=True, capture_output=True, text=True, timeout=30)
            self.assertTrue(probe.stdout.strip(),
                           "a sandboxed hoist killed a host container")
            # It ran in an environmental substrate, which was torn down clean: no
            # residue of OUR substrate remains (scoped, not a full-host diff).
            self.assertEqual(r["substrate"]["strength"], "environmental")
            self.assertTrue(r["substrate"].get("torn_down"))
            self.assertIn("blast_radius", r)
            self.assertTrue(r["blast_radius"]["clean"],
                           "the environmental substrate left residue on the host")
            self.assertEqual(r["blast_radius"]["residue"], [])
        finally:
            subprocess.run(f"docker rm -f {sentinel_ctr}", shell=True,
                          capture_output=True, timeout=30)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_substrate ({result.testsRun} cases; "
              f"docker={'yes' if HAS_DOCKER else 'no'})")
        sys.exit(0)
    print("FAIL test_substrate")
    sys.exit(1)
