# storyboard-consistency-check

storyboard-consistency-check is a **text-only** entity continuity checker for storyboard scripts: register your characters, props, and scenes once, then it flags unknown names, alias collisions, type mix-ups, scene-numbering defects, and continuity gaps across scenes. It never reads or processes image files. Confidence: High (≥80%) for the nine rules, per the 65-case suite.

## Problem

Long storyboard scripts drift: a character appears in scene 1, vanishes in scene 2, and is back in scene 3 holding a prop nobody declared; "ali" and "Alice" and "ALICE" are treated as three people; scene numbers repeat after a reorder. Continuity errors are exactly the kind of thing humans are bad at tracking across hundreds of scenes — and exactly what a mechanical registry check is good at.

## How it works

1. **Registry** — a `[entities]` header block declares each entity: `name: type=character|prop|scene, aliases=a,b`. Aliases map to one canonical name; a shared alias is an `alias-collision` error.
2. **Scenes** — `## S1`-style headings split the body; each scene lists `Characters:`, `Props:`, `Scene:` lines plus free-text `Notes:`.
3. **Rules** —
   - **unknown-entity** (error): a listed name is not in the registry.
   - **type-mismatch** (error): entity listed under the wrong line (a prop under Characters).
   - **alias-collision** (error): one alias points at two entities.
   - **duplicate-scene** / **scene-order** (error/warning): numbering repeats / decreases.
   - **empty-scene** (error): scene with no tracked content.
   - **undeclared-use** (warning): an entity is mentioned in Notes but not listed in that scene.
   - **continuity-gap** (warning): entity present in scene *i*, absent in *i+1*, back in *i+2*.
   - **unused-entity** (warning): registry entity never used anywhere.
4. **Mention matching** — boundary-aware, case-insensitive; an adjacent ASCII letter/digit blocks the match, while CJK and punctuation count as boundaries, so space-less CJK sentences match correctly.
5. **Exit contract** — 0 clean or warnings, 1 errors, 2 I/O failure. Text in, text out; no image handling of any kind.

## Quickstart (~2 min)

```bash
# step 1: check a script (~0.1 s for small scripts)
python storyboard_check.py storyboard.txt
# step 2: CI mode
python storyboard_check.py storyboard.txt --json
# step 3: stdin
cat storyboard.txt | python storyboard_check.py -
# full suite (~1 s)
python self_test.py   # SUMMARY: PASS 65/65 [Measured]
```

Library use: `check_text(text)` → `{"scenes": int, "entities": int, "findings": [dict]}`.

## Why not X? (as of 2026-10-13)

**No direct equivalent found as of 2026-10-13** — no standalone stdlib-only, registry-driven entity continuity checker for text storyboard scripts was located in the searched space. Nearest adjacent options:

- **Final Draft / screenplay continuity software** — commercial, GUI-bound, and geared to screenplays; no scriptable exit-code contract, no plain-text registry format.
- **NER-based consistency tools (spaCy pipelines)** — they *guess* entities from free text and hallucinate; this tool inverts the model: you declare the ground truth and the checker enforces it, deterministically.
- **General linters (markdownlint / vale)** — prose-quality checks with no entity registry, no alias resolution, no cross-scene state tracking.
- **Continuity spreadsheets** — the manual status quo: no enforcement, no diffing, and errors are found when the episode ships.

## Performance

All numbers [Measured] on this machine (Windows, Python 3.x, single run):

| Input | Time | Command |
|---|---|---|
| 2,795 KB, 3,000 scenes, 52 entities, 5,741 findings | 1.128 s | see repro below |
| 65-case self-test suite | 0.237 s | `python self_test.py` |

Repro:

```bash
python -c "import time,storyboard_check as m; reg='[entities]\n'+''.join('c%d: type=character\n'%i for i in range(50))+'prop1: type=prop\n\n---\n\n'; t=reg+'\n\n'.join('## S%d\nCharacters: c%d\nProps: prop1\nNotes: c%d moves prop1'%(i,i%50,i%50) for i in range(1,3001)); t0=time.perf_counter(); r=m.check_text(t); print('%.3f s'%(time.perf_counter()-t0), r['scenes'],'scenes')"
```

## Minimal Fallback (PLAN B)

No Python: `grep -n "Characters:" storyboard.txt | sort -t: -k3` and eyeball for missing names between scenes; `grep -c "^## S" storyboard.txt` checks scene count. You lose alias resolution, type checking, gap detection, and the exit-code contract.

## Design Trade-offs

Priority order: **deterministic-over-clever > explainable findings > zero-dependency > recall**. The registry-driven model refuses to guess entities from prose — a false "missing character" alert from fuzzy NER would burn trust faster than the missed ones it catches. `undeclared-use` and `continuity-gap` are warnings, not errors, because deliberate off-screen absences are normal storytelling. Only the *first* gap per entity is reported to keep output scannable. Full NLP was rejected on purpose: the tool is a spreadsheet with teeth, not a critic.

## Limits & Second-order Effects

- Registry-driven: anything not declared is invisible; an author who forgets to register a character gets "unknown-entity", which is the intended failure direction (loud, not silent).
- Mention matching is lexical: pronouns ("she"), nicknames not registered as aliases, and indirect references are not tracked.
- Continuity gaps use scene *order*, not story-time; flashbacks will false-positive — register them as their own scenes or ignore the warning.
- Second-order: teams may over-register minor extras to silence warnings, growing the registry until it needs its own maintenance; keep the registry to entities that matter (speaking roles, plot props).
- The tool checks text only — visual continuity (costume, lighting) is out of scope by design; no image file is ever read.

## FAQ

**Q: Does it process images or video files?**
No. It is a pure text checker by contract — the only inputs are the script text and the registry; filenames mentioned in notes are treated as inert text.

**Q: Can I use it for novels or game scripts?**
Yes — the format is generic: register entities, split into sections with headings, list appearances.

**Q: Why is a continuity gap only a warning?**
Because absence is often intentional (off-screen characters); the tool surfaces it, you judge it.

**Q: When NOT to use this tool?**
If your script has fewer than ~10 scenes, manual review is cheaper. If your entities cannot be enumerated up front (discovery-driven writing), the registry becomes churn. If you need visual/media continuity, this is the wrong layer entirely.

**Q: Does it handle CJK text?**
Yes — entity names, aliases, and notes are all tested with CJK fixtures; mention matching treats CJK characters as boundaries.

## [Core Assumptions]

1. Storyboard scripts can be structured as heading-separated scenes with per-scene entity lists plus free-text notes.
2. A human-declared registry is a better ground truth than inferred entities for continuity checking.
3. Continuity is defined on scene *order*; non-linear timelines are the author's responsibility to model.
4. The checker is text-only: no image, audio, or video file is ever read, so it runs anywhere plain text does.

Confidence: High (≥80%) for the nine rules (65-case suite incl. CJK); Medium (60–79%) for real-world usefulness beyond ~50-scene scripts — the threshold where manual tracking demonstrably fails is anecdotal. Data as of 2026-10-13.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 105 purpose-built AI-engineering tools across neglected niches.

Related tools: [multimodal-asset-manifest](https://github.com/chenhz01/multimodal-asset-manifest) · [experiment-registry-schema](https://github.com/chenhz01/experiment-registry-schema) · [image-alt-check](https://github.com/chenhz01/image-alt-check)
