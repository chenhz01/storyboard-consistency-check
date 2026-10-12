#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""storyboard-consistency-check — text-only entity continuity checker for
storyboard scripts. It never reads or processes image files: input and output
are plain text.

Script format (plain text / Markdown):

    [entities]
    alice: type=character, aliases=ali
    key: type=prop
    castle: type=scene

    ---

    ## S1
    Characters: alice, bob
    Props: key
    Scene: castle
    Notes: ali finds the key near the gate

Rules:
  unknown-entity    (error)   a listed name is not in the registry
  alias-collision   (error)   one alias maps to two registry entities
  type-mismatch     (error)   entity listed under the wrong line type
  duplicate-scene   (error)   two scenes carry the same number
  empty-scene       (error)   scene has no tracked lines at all
  undeclared-use    (warning) entity mentioned in Notes but not listed this scene
  continuity-gap    (warning) entity present in scene i, absent in i+1, back in i+2
  scene-order       (warning) scene numbers decrease
  unused-entity     (warning) registry entity never appears in any scene

Exit codes: 0 clean-or-warnings, 1 errors, 2 I/O failure.
Pure stdlib. Python 3.8+.
"""
import argparse
import json
import re
import sys

__version__ = "0.1.1"

TYPES = ("character", "prop", "scene")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
NUM_RE = re.compile(r"(\d+)\s*$")
LIST_LINE_RE = re.compile(r"^\s*(Characters|Props|Scene)\s*:\s*(.*)$", re.I)
NOTES_LINE_RE = re.compile(r"^\s*(Notes?|Description|Action)\s*:\s*(.*)$", re.I)


def parse_registry(text):
    """Parse the [entities] block into {name: {"type": t, "aliases": [...]}}."""
    registry = {}
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower() == "[entities]":
            in_block = True
            continue
        if not in_block:
            continue
        if line == "---" or HEADING_RE.match(raw):
            break
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([^:：]+)\s*[:：]\s*(.*)$", line)
        if not m:
            continue
        name = m.group(1).strip()
        fields = {}
        last_key = None
        for part in m.group(2).split(","):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                last_key = k.strip().lower()
                fields[last_key] = v.strip()
            elif part and last_key == "aliases":
                fields["aliases"] += "," + part
        etype = fields.get("type", "character").lower()
        if etype not in TYPES:
            etype = "character"
        aliases = [a.strip() for a in re.split(r"[;,]", fields.get("aliases", ""))
                   if a.strip()]
        registry[name] = {"type": etype, "aliases": aliases}
    return registry


def _scene_number(label):
    m = NUM_RE.search(label)
    return int(m.group(1)) if m else None


def _alias_index(registry):
    idx = {}
    collisions = []
    for name, meta in registry.items():
        for a in [name] + meta["aliases"]:
            key = a.lower()
            if key in idx and idx[key] != name:
                collisions.append((key, idx[key], name))
            idx.setdefault(key, name)
    return idx, collisions


def _mentions(text, registry):
    """Return set of registry names whose name/alias appears in text.

    Boundary rule: an ASCII letter/digit/underscore adjacent to the token
    blocks the match; any CJK or punctuation char counts as a boundary, so
    space-less CJK sentences ("小明等小红") match correctly.
    """
    found = set()
    for name, meta in registry.items():
        for token in [name] + meta["aliases"]:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])",
                         text, re.I):
                found.add(name)
                break
    return found


def check_text(text):
    """Check script text; return {"scenes": int, "findings": [dict]}."""
    findings = []

    def add(rule, severity, line, msg):
        findings.append({"rule": rule, "severity": severity,
                         "line": line, "message": msg})

    if text.startswith("\ufeff"):
        text = text[1:]
    registry = parse_registry(text)
    alias_idx, collisions = _alias_index(registry)
    for key, first, second in collisions:
        add("alias-collision", "error", 0,
            "alias '%s' maps to both '%s' and '%s'" % (key, first, second))

    scenes = []  # (line_no, number, label, lists, notes, order_idx)
    current = None
    for idx, raw in enumerate(text.splitlines(), 1):
        if raw.strip().lower() == "[entities]":
            current = None
            continue
        hm = HEADING_RE.match(raw)
        if hm:
            label = hm.group(1)
            if label.lower().startswith("entities"):
                current = None
                continue
            current = {"line": idx, "label": label,
                       "number": _scene_number(label),
                       "chars": set(), "props": set(), "loc": set(),
                       "notes": [], "tracked": False}
            scenes.append(current)
            continue
        if current is None:
            continue
        lm = LIST_LINE_RE.match(raw)
        if lm:
            kind = lm.group(1).lower()
            target = {"characters": current["chars"],
                      "props": current["props"],
                      "scene": current["loc"]}[kind]
            for item in re.split(r"[,，;]", lm.group(2)):
                item = item.strip()
                if item:
                    target.add(item)
                    current["tracked"] = True
            continue
        nm = NOTES_LINE_RE.match(raw)
        if nm:
            current["notes"].append(nm.group(2))
            current["tracked"] = True
            continue
        if raw.strip() and current["notes"] is not None and raw.strip() != "---":
            current["notes"].append(raw.strip())
            current["tracked"] = True

    seen_numbers = {}
    prev_num = None
    used_entities = set()
    for scene in scenes:
        ln = scene["line"]
        if scene["number"] is not None:
            if scene["number"] in seen_numbers:
                add("duplicate-scene", "error", ln,
                    "scene number %d repeats scene at line %d"
                    % (scene["number"], seen_numbers[scene["number"]]))
            else:
                seen_numbers[scene["number"]] = ln
            if prev_num is not None and scene["number"] < prev_num:
                add("scene-order", "warning", ln,
                    "scene number %d follows %d" % (scene["number"], prev_num))
            prev_num = scene["number"]
        if not scene["tracked"]:
            add("empty-scene", "error", ln,
                "scene '%s' has no tracked content" % scene["label"])
        for kind, names in (("character", scene["chars"]),
                            ("prop", scene["props"]),
                            ("scene", scene["loc"])):
            for n in names:
                canon = alias_idx.get(n.lower())
                if canon is None:
                    add("unknown-entity", "error", ln,
                        "'%s' is not in the [entities] registry" % n)
                else:
                    used_entities.add(canon)
                    want = registry[canon]["type"]
                    if want != kind:
                        add("type-mismatch", "error", ln,
                            "'%s' is a %s but listed under %s"
                            % (n, want, kind))
        notes_text = " ".join(scene["notes"])
        listed_canon = {alias_idx.get(x.lower())
                        for xs in (scene["chars"], scene["props"], scene["loc"])
                        for x in xs}
        listed_canon.discard(None)
        if notes_text:
            for canon in _mentions(notes_text, registry):
                used_entities.add(canon)
                if canon not in listed_canon:
                    add("undeclared-use", "warning", ln,
                        "'%s' mentioned in notes but not listed this scene"
                        % canon)
    # continuity gaps: entity in scene i, absent i+1, back in i+2+
    presence = []
    for scene in scenes:
        all_listed = {alias_idx.get(x.lower())
                      for x in scene["chars"] | scene["props"] | scene["loc"]}
        all_listed.discard(None)
        all_listed |= {c for c in _mentions(" ".join(scene["notes"]), registry)}
        presence.append(all_listed)
    for name in registry:
        for i in range(len(presence) - 2):
            if name in presence[i] and name not in presence[i + 1] \
                    and name in presence[i + 2]:
                add("continuity-gap", "warning", scenes[i + 2]["line"],
                    "'%s' appears in scene %d, absent in %d, back in %d"
                    % (name, i + 1, i + 2, i + 3))
                break
    for name in registry:
        if name not in used_entities:
            add("unused-entity", "warning", 0,
                "registry entity '%s' never appears in any scene" % name)
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return {"scenes": len(scenes), "entities": len(registry),
            "findings": findings}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="storyboard-consistency-check",
        description="Text-only entity continuity checker for storyboard "
                    "scripts (never touches image files).")
    p.add_argument("file", help="script text file ('-' for stdin)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + __version__)
    args = p.parse_args(argv)
    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, "r", encoding="utf-8-sig") as f:
                text = f.read()
    except OSError as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print("error: cannot read %s: %s" % (args.file, e), file=sys.stderr)
        return 2
    result = check_text(text)
    errors = [f for f in result["findings"] if f["severity"] == "error"]
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for f in result["findings"]:
            print("%-16s %-7s line %s: %s"
                  % (f["rule"], f["severity"], f["line"], f["message"]))
        print("checked %d scenes, %d entities: %d error(s), %d warning(s)"
              % (result["scenes"], result["entities"], len(errors),
                 len(result["findings"]) - len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
