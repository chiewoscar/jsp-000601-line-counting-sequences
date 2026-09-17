# Verification status — JSP-000601

## Completed while preparing this package

- local file generation;
- Python verifier syntax compilation;
- fail-closed static scan of the local Lean wrapper and audit;
- upstream source SHA-256 pinning into `UPSTREAM.lock.json` (8 modules);
- live official PR-title collision search for `JSP-000601`;
- upstream theorem, comparator, and scope inspection.

## Not claimed in this environment

A new Lean compiler run was **not** completed locally. This package does not
claim its wrapper has already passed `lake` or `leanchecker` here.

Run:

```bash
python3 scripts/verify.py --clean
```

A successful run creates `verification/generated/result.json` with
`"status": "pass"`, source hashes, axiom closures, and replayed modules.
