# Verification status — JSP-000601

## Completed while preparing this package

- local file generation;
- Python verifier syntax compilation;
- fail-closed static scan of the local Lean wrapper and audit;
- upstream source SHA-256 pinning into `UPSTREAM.lock.json` (8 modules);
- live official PR-title collision search for `JSP-000601`;
- upstream theorem, comparator, and scope inspection.

## Verified in CI

GitHub Actions run `35265939128` at commit
`416fedd346f62bd5851e9203f4ad6d3e0f8cee08` completed with `"status": "pass"`:
pinned source hashes matched, `lake build ErdosProblems.Erdos733` compiled the
eight-module upstream proof and its transitive Util dependencies, the wrapper
and audit compiled, axioms for `JSP000601.solution` and `Erdos733.erdos_733`
are `[propext, Classical.choice, Quot.sound]`, and `leanchecker` replayed both
modules.

To reproduce locally:

```bash
python3 scripts/verify.py --clean
```

Note: a fresh local run on Windows may fail inside `lake exe cache get` while
checking out a dependency that contains a colon in a filename; the CI run on
Ubuntu is the reference verification.
