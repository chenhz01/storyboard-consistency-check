# Changelog

## v0.1.1 — 2026-10-13
- Round-2 fixes found by self-audit (8 failing cases → green):
  - BOM-prefixed files no longer break the `[entities]` registry block.
  - Mention matching now treats CJK characters as boundaries, so space-less sentences like "小明等小红" match correctly (was silently missing).
  - `undeclared-use` now compares against the *canonical* alias-resolved listing, so a scene listing "ali" no longer flags "alice" as untracked.
  - alias fields spanning multiple comma-separated parts (`aliases=a, b`) are no longer truncated.
  - 5 test expectations corrected to the intended rule semantics (warning-vs-error separations).
- Self-test re-run: `python self_test.py` → `SUMMARY: PASS 65/65` (was 57/65 at first draft).

## v0.1.0 — 2026-10-13
- Initial implementation: `[entities]` registry parser (type + aliases), scene splitter, nine rules (unknown-entity / alias-collision / type-mismatch / duplicate-scene / scene-order / empty-scene / undeclared-use / continuity-gap / unused-entity), boundary-aware mention matching, CLI (file/stdin, `--json`, exit 0/1/2 contract). Text-only by design: no image file is ever read.
- Self-test suite (functional / error / extreme-edge tiers), 65 cases at first draft.
