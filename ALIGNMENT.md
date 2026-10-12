# Alignment Audit (Rules 85-100 / 16 items) — storyboard-consistency-check

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | PASS | No security-domain content; read-only text checker; explicitly never reads image files |
| 2 | Privacy de-identification | PASS | Zero keys/tokens/real names/emails; example entities are fictional placeholders |
| 3 | Copyright boundary | PASS | All text original; LICENSE (MIT) present |
| 4 | Fact-check labeling | PASS | Performance numbers marked [Measured] with repro command |
| 5 | Confidence grading | PASS | README has High and Medium labels with one-line justifications |
| 6 | PLAN B built-in | PASS | "Minimal Fallback" grep/sort workflow without Python |
| 7 | Timeout preset | PASS | Quickstart marked ~2 min; per-step timing; suite ~1 s |
| 8 | Rule-conflict arbitration | PASS | "Design Trade-offs" states: deterministic-over-clever > explainable > zero-dependency > recall |
| 9 | Version changelog | PASS | CHANGELOG v0.1.0 → v0.1.1 with round-2 iteration fixes documented |
| 10 | Exemption instruction | N/A | Session-level rule; static repo marks N/A |
| 11 | External-knowledge cutoff | PASS | why-not-X and confidence dated "as of 2026-10-13" |
| 12 | Assumption explicitness | PASS | [Core Assumptions] lists 4 assumptions |
| 13 | Logic-verification trio | PASS | self_test covers functional (27) / error-path (13) / extreme-edge (25) cases; SUMMARY: PASS 65/65 |
| 14 | Socratic question | PASS | FAQ "When NOT to use this tool?" |
| 15 | Pareto improvement | PASS | Round 2 fixed 4 real defects (BOM registry, CJK mention boundaries, canonical listing, alias parsing) — correctness dimension materially improved, traced in CHANGELOG |
| 16 | Minimalist entry | PASS | First paragraph ≤60 words with what/whether-needed judgment |
