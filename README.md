# JSP-000601 — Line-multiplicity counting sequences of planar point sets

Dedicated intake, statement-interface, and reproduction package for an existing
public Lean proof. It does not claim a new mathematical result or
first-formalization priority.

## Result

**Catalog question:** How many distinct line-multiplicity counting sequences
can planar point sets determine?

**Pinned formal endpoint:** `Erdos733.erdos_733`.

The compatible line-cardinality counting sequences on `n` planar points form a
finite set of cardinality at most `exp (C * sqrt n)` — the
Szemerédi–Trotter bound.

## What this package contributes

- a direct theorem endpoint named `JSP000601.solution`;
- a commit-pinned upstream lock with per-source SHA-256 for all eight custom
  modules;
- fail-closed local source scanning for proof shortcuts;
- axiom allowlist enforcement and `leanchecker` replay;
- a GitHub Actions workflow.

The mathematical proof and substantive formalization remain attributed to the
upstream contributors.

## Reproduce

```bash
./verify.sh --clean
```

The verifier clones `plby/lean-proofs` at
`8822f7ddef30fadbd92e1c6ab4ed897af356af5e`, checks source hashes, uses Lean
4.33.0, compiles the required modules plus the JSP wrapper and audit, and runs
`leanchecker`.

## Attribution

- **Mathematics:** Endre Szemerédi and William T. Trotter Jr.
- **Existing Lean work:** Codex and GPT-5.6 Sol (upstream notices).
- **This package:** dedicated JSP interface and pinned reproduction.

## Current local status

`verification/STATUS.md` distinguishes checks actually run here from checks to
run after publishing. A claimed green build exists only when
`verification/generated/result.json` records `"status": "pass"`.
