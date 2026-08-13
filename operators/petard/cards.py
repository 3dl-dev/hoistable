#!/usr/bin/env python3
"""petard capability cards: structured ground truth for the grounded answerer.

A raw corpus of harvested lines is a list of commands. A card is the unit that
makes petard answer intent instead: it pairs the operator-facing purpose (plain
words, harvested from the tool's own header or doc) with the exact command to run
and where it came from. The answerer matches intent against purpose, then hands
back the command verbatim. petard never writes a command; it only points at one.

Cards are generated from ground truth, never authored (the petard invariant):
  - shell scripts: the leading comment block is the purpose, a `Usage:` line is
    the command.
  - Makefile targets: a `##` comment block above a target is the purpose,
    `make <target>` is the command.

Standard library only. Extraction is deterministic parsing of the real files.
"""

import argparse
import json
import os
import sys


def _rel(path):
    return path


def extract_script_card(path):
    """One card from a shell script's header block."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i = 1 if lines and lines[0].startswith("#!") else 0
    header = []
    while i < len(lines):
        l = lines[i]
        if l.startswith("#"):
            header.append(l.lstrip("#").strip())
            i += 1
        elif l.strip() == "":
            # a blank line ends the header block (headers are contiguous comments)
            break
        else:
            break
    if not any(header):
        return None
    usage = next((h for h in header if h.lower().startswith("usage:")), None)
    purpose = " ".join(h for h in header if h and h is not usage).strip()
    name = os.path.basename(path)
    if usage:
        command = usage.split(":", 1)[1].strip()
    else:
        command = _rel(path)
    return {
        "id": os.path.splitext(name)[0],
        "purpose": purpose or name,
        "command": command,
        "source": _rel(path),
    }


def extract_help_card(cmd, timeout=30):
    """One card harvested from a tool's own --help. The help text is ground truth
    for a universal infra command (docker compose restart, kubectl rollout
    restart) that no project script wraps."""
    import subprocess
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except Exception:  # noqa: BLE001
        return None
    lines = [l.rstrip() for l in ((p.stdout or "") + (p.stderr or "")).splitlines()]
    desc = next((l.strip() for l in lines
                 if l.strip() and not l.strip().lower().startswith("usage:")), "")
    usage_idx = next((i for i, l in enumerate(lines)
                      if l.strip().lower().startswith("usage:")), None)
    command = ""
    if usage_idx is not None:
        after = lines[usage_idx].split(":", 1)[1].strip()
        if after:
            command = after
        else:  # synopsis is on the following indented line(s)
            for l in lines[usage_idx + 1:]:
                if l.strip():
                    command = l.strip()
                    break
    if not command:
        command = cmd.replace(" --help", "")
    return {
        "id": cmd.replace(" --help", "").replace(" ", "-"),
        "purpose": desc or cmd,
        "command": command,
        "source": cmd,
    }


def extract_makefile_cards(path):
    """One card per documented Makefile target (a `##` block above `target:`)."""
    cards = []
    doc = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f.read().splitlines():
            if line.startswith("##"):
                doc.append(line.lstrip("#").strip())
            elif line and line[0].isalnum() and ":" in line.split()[0]:
                target = line.split(":", 1)[0].strip()
                if doc and target and target != ".PHONY":
                    cards.append({
                        "id": f"make-{target}",
                        "purpose": " ".join(d for d in doc if d).strip(),
                        "command": f"make {target}",
                        "source": f"{_rel(path)}:{target}",
                    })
                doc = []
            elif not line.strip():
                continue
            else:
                doc = []
    return cards


def build_cards(spec, root="."):
    """spec: {scripts: [paths], makefiles: [paths]} relative to root."""
    cards = []
    for rel in spec.get("scripts", []):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            c = extract_script_card(p)
            if c:
                if c["command"] == p:      # no Usage: line; show the relative path
                    c["command"] = rel
                c["source"] = rel
                cards.append(c)
    for rel in spec.get("makefiles", []):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            for c in extract_makefile_cards(p):
                c["source"] = c["source"].replace(p, rel)
                cards.append(c)
    for cmd in spec.get("helpcards", []):
        c = extract_help_card(cmd)
        if c:
            cards.append(c)
    return cards


def main(argv=None):
    ap = argparse.ArgumentParser(description="extract petard capability cards from ground truth")
    ap.add_argument("spec", help="JSON: {scripts:[...], makefiles:[...]}")
    ap.add_argument("--root", default=".", help="base dir the spec paths are relative to")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    with open(args.spec) as f:
        spec = json.load(f)
    cards = build_cards(spec, args.root)
    with open(args.out, "w") as f:
        json.dump(cards, f, indent=2)
    print(f"extracted {len(cards)} cards -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
