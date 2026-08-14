#!/usr/bin/env python3
"""User-level resolution store: persist and share a resolution as a replayable
recipe, not a frozen fact.

A resolution is the output of hoisting an app: which recipe, which profile, which
isolation rung it landed on, against what the target offered at the time. This
module lets an operator keep that resolution at the user level (above any one repo)
and hand it to another machine or teammate, WITHOUT it rotting into a stale belief.

The discipline is the whole point (see hoistable-543/270 and the continuation
model): what persists is a RECIPE plus hints, never a conclusion.

  Persisted, and safe:
    - the recipe reference and its content hash (config_ref + config_sha256), so a
      replay fetches the same recipe and notices if it drifted.
    - the required strength and any policy/pins: the inputs to resolution.
    - secret REFERENCES, never secret values (a secret is a bind resolved on the
      target, per sysop).
    - a manifest snapshot with a timestamp: a hint, re-validated by probe on
      replay, never adopted.

  Recorded as a raw past observation, explicitly non-authoritative:
    - the last outcome and the rung last chosen. Marked "re-derive on replay". A
      replay RE-PROBES the manifest and RE-RESOLVES the rung; it trusts none of
      these stored facts.

Sharing reuses rd's existing signed sync (rd follow / rd invite); this module does
not build a transport. A share-export is the artifact rd carries: the recipe and
references, with the snapshot and outcome facts dropped so the receiver re-resolves
from its own reality. Standard library only.
"""

import argparse
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "envelope"))
import substrate  # noqa: E402


SCHEMA = "hoistable.resolution/v1"


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def default_root():
    """The user-level store: above any repo. Override with HOIST_RESOLUTIONS."""
    return (os.environ.get("HOIST_RESOLUTIONS")
            or os.path.expanduser("~/.config/hoistable/resolutions"))


def build_record(config, config_ref, report, probed_at, manifest=None):
    """Construct a replayable resolution record from a hoist's config and its
    envelope report. The record is a recipe plus hints: the manifest snapshot and
    the last outcome are marked as re-derive-on-replay, never trusted."""
    sub = report.get("substrate") or {}
    # Secrets are carried as references only. A config declares them under
    # "secrets": [{"name": ..., "ref": ...}]; a bare name is its own reference.
    secret_refs = []
    for s in (config.get("secrets") or []):
        if "value" in s:
            raise ValueError(
                f"refusing to record a secret value for {s.get('name')!r}: a "
                "resolution carries references, resolved on the target, not values")
        secret_refs.append({"name": s["name"], "ref": s.get("ref", s["name"])})
    return {
        "schema": SCHEMA,
        "app": config.get("app", "?"),
        "config_ref": config_ref,
        "config_sha256": _sha256_bytes(_canon(config)),
        "profile": report.get("profile"),
        "required_strength": sub.get("required", "host"),
        "policy": config.get("policy", {}),
        "pins": config.get("operators", {}),
        "secret_refs": secret_refs,
        # A HINT, re-validated by probe on replay. Never adopted as fact.
        "manifest_snapshot": {"probed_at": probed_at,
                             "substrates": manifest or []},
        # A RAW OBSERVATION, past tense, explicitly non-authoritative.
        "last_observed": {
            "at": probed_at,
            "outcome": report.get("outcome"),
            "transfer": report.get("transfer"),
            "substrate": sub.get("name"),
            "note": ("observation, not a standing fact; re-derive by re-hoisting. "
                     "Replay re-probes and re-resolves and trusts none of this."),
        },
    }


class ResolutionStore:
    """Save, load, and list resolution records under a user-level root."""

    def __init__(self, root=None):
        self.root = root or default_root()

    def path_for(self, app):
        return os.path.join(self.root, f"{app}.json")

    def save(self, record):
        os.makedirs(self.root, exist_ok=True)
        path = self.path_for(record["app"])
        with open(path, "w") as f:
            json.dump(record, f, indent=2, sort_keys=True)
        return path

    def load(self, app):
        with open(self.path_for(app)) as f:
            return json.load(f)

    def list(self):
        if not os.path.isdir(self.root):
            return []
        return sorted(n[:-5] for n in os.listdir(self.root) if n.endswith(".json"))


def replay(record, resolve_config=None, timeout=30):
    """Re-derive a saved resolution. Re-fetch the recipe and check it has not
    drifted (content hash), re-probe the capability manifest, and re-resolve which
    rung the record's required strength gets NOW. Trusts none of the stored facts:
    the snapshot is compared, not adopted; any difference is reported as stale and
    the current reality wins."""
    result = {"app": record["app"], "stale": False, "drift": [],
              "config_changed": False}

    # 1. recipe drift, by content address.
    if resolve_config is not None:
        try:
            cfg = resolve_config(record["config_ref"])
            if _sha256_bytes(_canon(cfg)) != record["config_sha256"]:
                result["config_changed"] = True
                result["drift"].append("recipe-changed")
        except Exception as e:  # noqa: BLE001
            result["drift"].append(f"recipe-unresolvable:{e}")

    # 2. re-probe the manifest; compare to the snapshot (do not adopt it).
    current = substrate.probe_manifest(timeout)
    result["manifest_now"] = current
    snap = {s["name"]: s.get("available")
            for s in record.get("manifest_snapshot", {}).get("substrates", [])}
    now = {s["name"]: s.get("available") for s in current}
    if snap and snap != now:
        result["stale"] = True
        for name in sorted(set(snap) | set(now)):
            if snap.get(name) != now.get(name):
                result["drift"].append(
                    f"substrate:{name} was={snap.get(name)} now={now.get(name)}")

    # 3. re-resolve the rung from current reality. The stored hint is ignored.
    req = record.get("required_strength", "host")
    chosen = substrate.choose_from_manifest(current, req)
    result["reresolved"] = chosen
    result["feasible"] = chosen is not None
    if not result["feasible"]:
        result["reason"] = (f"no rung on this target now meets required strength "
                            f"{req!r}: an honest cannot-build on replay")
    return result


def share_export(record):
    """The share-safe artifact rd sync carries to another machine or user: the
    recipe and references, with the snapshot and outcome facts DROPPED so the
    receiver re-resolves from its own reality. Carries no secret values and no
    frozen conclusions, by construction and by assertion."""
    for s in record.get("secret_refs", []):
        if "value" in s:
            raise ValueError(
                "refusing to share a resolution carrying a secret value")
    return {
        "schema": record["schema"],
        "app": record["app"],
        "config_ref": record["config_ref"],
        "config_sha256": record["config_sha256"],
        "profile": record.get("profile"),
        "required_strength": record.get("required_strength", "host"),
        "policy": record.get("policy", {}),
        "pins": record.get("pins", {}),
        "secret_refs": record.get("secret_refs", []),
        "share_safe": True,
        "note": ("recipe + references only; carries no secret values, no manifest "
                 "snapshot, and no observed outcome. Re-resolve on receipt."),
    }


def import_shared(export):
    """Receive a shared export on a fresh target: it becomes a local record with an
    empty snapshot, so the first replay re-probes from this target's own reality."""
    if not export.get("share_safe"):
        raise ValueError("not a share-safe export")
    rec = dict(export)
    rec.pop("share_safe", None)
    rec.pop("note", None)
    rec["manifest_snapshot"] = {"probed_at": None, "substrates": []}
    rec["last_observed"] = {"at": None, "outcome": None,
                           "note": "imported; nothing observed on this target yet"}
    return rec


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="user-level resolution store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s_save = sub.add_parser("save", help="build+save a record from a config and a report")
    s_save.add_argument("config")
    s_save.add_argument("report")
    s_save.add_argument("--config-ref", default=None)
    s_save.add_argument("--probed-at", default="unstamped")
    s_replay = sub.add_parser("replay", help="re-derive a saved resolution")
    s_replay.add_argument("app")
    sub.add_parser("list", help="list saved resolutions")
    s_share = sub.add_parser("share", help="print the share-safe export for an app")
    s_share.add_argument("app")
    args = ap.parse_args(argv)

    store = ResolutionStore()
    if args.cmd == "list":
        for app in store.list():
            print(app)
        return 0
    if args.cmd == "save":
        config = _load_json(args.config)
        report = _load_json(args.report)
        rec = build_record(config, args.config_ref or args.config, report,
                          args.probed_at, manifest=substrate.probe_manifest())
        path = store.save(rec)
        print(f"saved resolution for {rec['app']} -> {path}")
        return 0
    if args.cmd == "replay":
        rec = store.load(args.app)
        res = replay(rec)
        print(json.dumps(res, indent=2))
        return 0 if res["feasible"] else 2
    if args.cmd == "share":
        rec = store.load(args.app)
        print(json.dumps(share_export(rec), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
