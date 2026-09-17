# Statement correspondence — JSP-000601

## Human statement

How many distinct line-multiplicity counting sequences can planar point sets
determine?

## Formal endpoint

- Upstream: `Erdos733.erdos_733`
- Dedicated JSP interface: `JSP000601.solution`

## Correspondence

A compatible counting sequence records, for each line cardinality `i`, how many
distinct determined affine lines realize that cardinality on an `n`-point
planar set. The theorem shows the set of compatible sequences is finite and has
cardinality at most `exp (C * sqrt n)` — the affirmative Szemerédi–Trotter
resolution.

The local theorem is a transparent re-export of the pinned upstream
declaration. `Audit.lean` prints both theorem types and their axiom
dependencies.
