#!/usr/bin/env python3
"""arlo rung 1: slot-fill a real card template.

Rung 0 (translate.rank) selects a card and hands back its command verbatim. Often
the command is a template with a hole: `docker compose restart [service]`,
`reset-password <user>`. Rung 0 hands the operator the blank; rung 1 binds the hole
from the operator's own words ("bounce the deriver" -> service=deriver) so the
answer is the command they actually want to run.

The invariant survives rung 1, and it survives STRUCTURALLY, not by trust:

  - A binder only ever returns slot VALUES (a {name: value} map). It never returns
    a command.
  - fill() is the only thing that assembles a command, and it does so by
    substituting values into the REAL card template. Every non-slot character is
    copied verbatim from ground truth.

So no binder, not the deterministic one here and not a large model wired in behind
llm_binder, can produce a command whose shape differs from the card's. The skeleton
is ground truth; only the slot value is inferred, and the filled slot is shown so
the operator sees exactly what was bound.

Standard library only. A production binder wraps a local model behind a lazy import
(llm_binder), so this module stays importable and testable with no model installed.
"""

import argparse
import json
import re
import sys

# A slot is [name] or <name>: a lowercase-ish identifier in brackets or angles.
_SLOT_RE = re.compile(r"\[([a-zA-Z][\w-]*)\]|<([a-zA-Z][\w-]*)>")

# A slot value fills ONE argument hole. Shell metacharacters would let a value turn
# one grounded command into two (`api; rm -rf /`), so a value carrying them is
# refused and the slot stays unbound. This guards the skeleton's meaning, not just
# its text: even a compromised or hallucinating binder cannot chain a second command
# through a hole. (Full DANGER/CAUTION checking on the assembled command is a
# separate, later layer; this is the minimum a slot value must clear.)
_META_RE = re.compile(r"[;&|`$<>\n\r()\\]|\$\(|&&|\|\|")


def _safe_value(v):
    return not _META_RE.search(str(v))


def slots(command):
    """The slot names in a card's command, in order, e.g.
    'docker compose restart [service]' -> ['service']. A command with no bracketed
    or angled placeholder has no slots and rung 1 leaves it exactly as rung 0."""
    out = []
    for m in _SLOT_RE.finditer(command):
        out.append(m.group(1) or m.group(2))
    return out


def fill(command, bindings):
    """Substitute bound slot values into the real card template. A slot present in
    `bindings` is replaced by its value; an unbound slot is left as its placeholder
    (the blank the operator fills). Every character outside a slot placeholder is
    copied verbatim, so the command skeleton can never drift from ground truth."""
    def sub(m):
        name = m.group(1) or m.group(2)
        if name in bindings and bindings[name] is not None:
            return str(bindings[name])
        return m.group(0)  # leave the placeholder untouched when unbound
    return _SLOT_RE.sub(sub, command)


def literals(command):
    """The literal segments of a command template, in order: the text OUTSIDE any
    slot. 'docker compose restart [service]' -> ['docker compose restart ', ''].
    This is the command's fixed scaffolding; slot values live between these."""
    return _SLOT_RE.split(command)[0::3]  # _SLOT_RE has two groups, so step past both


def skeleton_intact(template, filled):
    """The structural invariant check: every literal segment of the template appears
    in `filled`, verbatim and in order. If it holds, filling changed only the slots;
    the fixed command scaffolding, the part that IS ground truth, never drifted.
    Independent of how the command was assembled, so it catches a bad binder."""
    pos = 0
    for seg in literals(template):
        if seg == "":
            continue
        idx = filled.find(seg, pos)
        if idx < 0:
            return False
        pos = idx + len(seg)
    return True


# --- deterministic, model-free binder (for tests, CLI demo, and the no-model box) ---

def _words(s):
    return [w for w in re.split(r"[^\w-]+", s.lower()) if len(w) > 2]


def _stem(w):
    return w[:5]


def residual_binder(slot_names, card, query):
    """A deterministic binder: bind a slot to the word in the query that the card's
    own purpose/command does NOT already account for. "bounce the deriver" against a
    card whose purpose is "restart a service [service]" leaves "deriver" as the
    residual, so service=deriver.

    It is honest about its limits: it binds a single slot from a clear residual and
    otherwise binds nothing (returns the slot unbound) rather than guess. Multi-slot
    assignment is exactly where a real local model earns its keep (llm_binder); the
    deterministic binder does not pretend to do it.

    This is a genuine binder, not a mock: like translate.bag_of_words_embedder, it
    proves the mechanism deterministically without a model download."""
    if len(slot_names) != 1:
        return {}
    known = {_stem(w) for w in _words(card.get("purpose", "") + " " + card.get("command", ""))}
    residual = [w for w in _words(query) if _stem(w) not in known]
    if not residual:
        return {}
    return {slot_names[0]: residual[-1]}


def llm_binder(generate):
    """Production binder: wrap a local text-generation model. `generate` is any
    callable prompt -> text (the frontier-independent LOM, provisioned at setup).

    The model is asked for slot VALUES ONLY, as JSON, never for a command. fill()
    assembles the command from the real template, so even here the model cannot
    rewrite the skeleton, it can only propose what goes in the holes. Values the
    model does not supply stay unbound.

    Imported behavior is lazy: with no model provisioned, pass no generate and the
    deterministic residual_binder is used instead. This raises only if called with a
    generate that misbehaves, never silently."""
    def bind(slot_names, card, query):
        if not slot_names:
            return {}
        prompt = (
            "You are filling the holes in a known-good shell command. Do NOT write a "
            "command. Return ONLY a JSON object mapping each slot to the value implied "
            "by the request, or omit a slot you cannot determine.\n"
            f"command template: {card.get('command','')}\n"
            f"purpose: {card.get('purpose','')}\n"
            f"slots: {json.dumps(slot_names)}\n"
            f"request: {query}\n"
            "JSON:"
        )
        raw = generate(prompt)
        try:
            data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        except (ValueError, TypeError):
            return {}
        # accept only string/number values for declared slots: the model supplies
        # hole contents, nothing else.
        return {k: data[k] for k in slot_names
                if k in data and isinstance(data[k], (str, int, float))}
    return bind


def slot_fill(bind, card, query):
    """Fill a card's template from the query using `bind`
    (slot_names, card, query) -> {name: value}. Returns the filled command, what was
    bound, and what stayed unbound. skeleton_preserved is the structural invariant
    check: the filled command, with slots blanked back, equals the template blanked."""
    names = slots(card["command"])
    raw = bind(names, card, query) if names else {}
    # uniform guard: a value that is not a single safe argument is dropped, so the
    # slot stays unbound rather than let any binder inject a second command.
    bindings = {k: v for k, v in raw.items() if v is not None and _safe_value(v)}
    filled = fill(card["command"], bindings)
    return {
        "command": filled,
        "template": card["command"],
        "bindings": bindings,
        "unbound": [n for n in names if n not in bindings],
        "skeleton_preserved": skeleton_intact(card["command"], filled),
        "source": card.get("source", ""),
        "purpose": card.get("purpose", ""),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="arlo rung 1: fill a card template's slots from intent")
    ap.add_argument("card", help="a single card JSON ({command, purpose, source})")
    ap.add_argument("query", nargs="+")
    args = ap.parse_args(argv)
    with open(args.card) as f:
        card = json.load(f)
    # no model on the box -> deterministic residual binder
    res = slot_fill(residual_binder, card, " ".join(args.query))
    print(f"RUN:  {res['command']}")
    if res["bindings"]:
        print(f"      bound: {res['bindings']}")
    if res["unbound"]:
        print(f"      still to fill: {res['unbound']}")
    print(f"      template: {res['template']}   source: {res['source']}")
    if not res["skeleton_preserved"]:
        print("      ERROR: skeleton drifted from ground truth -- refusing.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
