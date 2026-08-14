#!/usr/bin/env python3
"""Self-test for the user-level resolution store. Stdlib only, hermetic.

Proves the discipline that makes persisting a resolution safe: what is stored is a
replayable RECIPE, never a frozen fact. The manifest is re-probed on replay, the
rung is re-resolved from current reality, a stale snapshot is caught, secrets are
carried as references and never values, and a share-export drops every fact so the
receiver re-resolves from its own target.

The capability manifest is stubbed per test so the assertions do not depend on
whether docker happens to be on the box: it is the store's DISCIPLINE under test
here, not the substrate probe (that is test_substrate.py's job).

Run: python3 tests/test_resolutions.py
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core", "envelope"))
sys.path.insert(0, os.path.join(HERE, "..", "core", "hoist"))
import substrate  # noqa: E402
import resolutions  # noqa: E402


HONCHO_CONFIG = {
    "app": "honcho",
    "source": {"clone": "https://github.com/plastic-labs/honcho", "dir": "honcho"},
    "profiles": {"minimal": {"isolation": {"require": "environmental"}}},
}
HONCHO_REPORT = {
    "profile": "minimal",
    "substrate": {"name": "dind", "strength": "environmental",
                  "required": "environmental"},
    "outcome": "built", "transfer": [3, 3],
}


def _manifest(dind=True):
    return [{"name": "host", "strength": "host", "available": True},
            {"name": "dind", "strength": "environmental", "available": dind}]


class StoreDiscipline(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="hoist-resolutions-")
        self.store = resolutions.ResolutionStore(root=self.root)
        self._real_probe = substrate.probe_manifest

    def tearDown(self):
        substrate.probe_manifest = self._real_probe

    def _record(self, manifest=None):
        return resolutions.build_record(
            HONCHO_CONFIG, "examples/honcho/config.json", HONCHO_REPORT,
            probed_at="2026-08-13T05:30Z", manifest=manifest or _manifest())

    # --- (a) save + load ---------------------------------------------------
    def test_save_and_load_roundtrips(self):
        rec = self._record()
        path = self.store.save(rec)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(self.store.list(), ["honcho"])
        back = self.store.load("honcho")
        self.assertEqual(back["required_strength"], "environmental")
        self.assertEqual(back["config_sha256"], rec["config_sha256"])
        # the stored outcome is explicitly marked non-authoritative
        self.assertIn("re-derive", back["last_observed"]["note"])

    # --- (b) replay re-probes and trusts no stored fact --------------------
    def test_replay_reresolves_from_current_reality_not_the_stored_hint(self):
        rec = self._record()
        # poison the stored observation: replay must ignore it entirely.
        rec["last_observed"]["substrate"] = "moon-base"
        substrate.probe_manifest = lambda timeout=30: _manifest(dind=True)
        res = resolutions.replay(rec)
        self.assertTrue(res["feasible"])
        self.assertEqual(res["reresolved"]["name"], "dind")  # from live manifest
        self.assertFalse(res["stale"])

    def test_replay_cannot_build_when_target_no_longer_offers_the_strength(self):
        rec = self._record()
        # this target now offers only the host floor; an environmental requirement
        # is an honest cannot-build on replay, not a pretend success.
        substrate.probe_manifest = lambda timeout=30: _manifest(dind=False)
        res = resolutions.replay(rec)
        self.assertFalse(res["feasible"])
        self.assertIsNone(res["reresolved"])
        self.assertIn("cannot-build", res["reason"])

    # --- (d) a stale snapshot is caught and re-resolved --------------------
    def test_stale_snapshot_is_caught_and_reresolved(self):
        # snapshot taken when dind was absent; reality now offers it.
        rec = self._record(manifest=_manifest(dind=False))
        substrate.probe_manifest = lambda timeout=30: _manifest(dind=True)
        res = resolutions.replay(rec)
        self.assertTrue(res["stale"])
        self.assertTrue(any("substrate:dind" in d for d in res["drift"]))
        self.assertEqual(res["reresolved"]["name"], "dind")  # re-resolved to reality

    def test_replay_detects_recipe_drift_by_content_hash(self):
        rec = self._record()
        changed = dict(HONCHO_CONFIG, profiles={"minimal": {
            "isolation": {"require": "host"}}})  # the recipe changed upstream
        substrate.probe_manifest = lambda timeout=30: _manifest()
        res = resolutions.replay(rec, resolve_config=lambda ref: changed)
        self.assertTrue(res["config_changed"])
        self.assertIn("recipe-changed", res["drift"])

    # --- (c) share carries references, never values ------------------------
    def test_share_export_is_reference_only_and_drops_facts(self):
        cfg = dict(HONCHO_CONFIG,
                   secrets=[{"name": "OPENAI_API_KEY", "ref": "vault://honcho/openai"}])
        rec = resolutions.build_record(cfg, "examples/honcho/config.json",
                                      HONCHO_REPORT, "2026-08-13T05:30Z",
                                      manifest=_manifest())
        self.assertEqual(rec["secret_refs"],
                        [{"name": "OPENAI_API_KEY", "ref": "vault://honcho/openai"}])
        export = resolutions.share_export(rec)
        self.assertTrue(export["share_safe"])
        # the reference travels; a value never could
        self.assertEqual(export["secret_refs"][0]["ref"], "vault://honcho/openai")
        self.assertNotIn("value", export["secret_refs"][0])
        # every fact is dropped: the receiver re-resolves from its own reality
        self.assertNotIn("manifest_snapshot", export)
        self.assertNotIn("last_observed", export)

    def test_share_import_roundtrips_and_receiver_reresolves(self):
        rec = self._record()
        export = resolutions.share_export(rec)
        received = resolutions.import_shared(export)          # on another machine
        self.assertEqual(received["manifest_snapshot"]["substrates"], [])
        substrate.probe_manifest = lambda timeout=30: _manifest(dind=True)
        res = resolutions.replay(received)
        self.assertTrue(res["feasible"])
        self.assertFalse(res["stale"])  # empty snapshot: nothing to be stale against
        self.assertEqual(res["reresolved"]["name"], "dind")

    def test_refuses_to_record_a_secret_value(self):
        cfg = dict(HONCHO_CONFIG,
                   secrets=[{"name": "OPENAI_API_KEY", "value": "sk-REAL-SECRET"}])
        with self.assertRaises(ValueError):
            resolutions.build_record(cfg, "ref", HONCHO_REPORT, "t",
                                    manifest=_manifest())

    def test_refuses_to_share_a_secret_value(self):
        rec = self._record()
        rec["secret_refs"] = [{"name": "X", "value": "leaked"}]
        with self.assertRaises(ValueError):
            resolutions.share_export(rec)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    if result.wasSuccessful():
        print(f"PASS test_resolutions ({result.testsRun} cases)")
        sys.exit(0)
    print("FAIL test_resolutions")
    sys.exit(1)
