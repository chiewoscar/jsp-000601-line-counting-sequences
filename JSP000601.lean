import ErdosProblems.Erdos733

/-!
Dedicated JSP-000601 interface to the pinned existing proof.
No mathematical or first-formalization priority is claimed here.
-/

namespace JSP000601

/-- The number of compatible line-cardinality counting sequences on `n`
planar points is finite and at most `exp (C * sqrt n)`. -/
theorem solution :
    ∃ C : ℝ, 0 < C ∧ ∀ n : ℕ,
      (Erdos733.compatibleSequences n).Finite ∧
        ((Erdos733.compatibleSequences n).ncard : ℝ) ≤
          Real.exp (C * Real.sqrt n) :=
  Erdos733.erdos_733

end JSP000601
