# Path A protocol notes (Kappa vs d Gap-Winner divergence)

Status: empirical only. Not theorems. No PGS results restated as CDL novelty.

## Phase 0: Context lock-in

Domain: CDL curvature `kappa(n)=d(n)*ln(n)/e^2` versus PGS Gap Winner
(leftmost minimizer of `d(n)` inside a prime gap `(p,q)`). Question: does the
log factor reorder the interior minimizer when gaps are long?

## Phase 1: Exploration (sole path deep dive)

Only Path A was explored (per task).

Working hypothesis: short gaps keep `w_d = w_k`; long gaps let `ln(n)`
variation compete with discrete `d(n)` jumps so argmins diverge.

## Phase 2: Z-map

| Symbol | Meaning | Measure |
| --- | --- | --- |
| a | selection mismatch rate | `diverge_rate = P(w_k != w_d)` |
| b | log stretch dynamic | `mean(ln(q)/ln(p) - 1)` and per-gap `ln_span_ratio = ln(q-1)/ln(p+1)` |
| c | discrete jump capacity | `min_step_ratio - 1 = 1/d_min` |

Effective intensity:

```
I = (ln_span_ratio - 1) / (min_step_ratio - 1)
```

Low I: log stretch too weak to beat a +1 divisor step. High I near or above 1:
inversion of argmin becomes feasible.

Observed (limit=1e6, see results.json): mean I << 1, max I < 1, a = 0.

## Phase 3: Prior art and novelty check

1. PGS Gap Winner Rule (leftmost min `d(n)`). Overlap: same object `w_d`.
   Difference sought: CDL would define a different selector `w_k`.
2. Slowly varying multipliers in analysis (standard). Overlap: `ln(n)` is slowly
   varying. Difference sought: concrete gap-geometry bound for kappa vs d.
3. CDL kappa as prime/composite classifier (parent repo). Overlap: same kappa.
   Difference sought: interior gap selector, not threshold classification.
4. DNI / raw-Z maximizer = min-d (PGS). Overlap: alternate scores on gaps.
   Difference: kappa is not DNI; test is pure d vs d*ln.
5. Already claimed CDL family (v, dfr, cst, zpf, dpt, acs): do not restate.

Rephrase trap: "a slowly varying factor does not change discrete argmins on
short windows." That proverb captures the failure mode. Path A does not clear
the rephrase trap as a positive novel principle; it dies as systematic
divergence and survives only as a measured lock / negative interface result.

## Phase 4: Three attacks

1. Conventional expert: This is just "slowly varying functions preserve
   discrete minima." Already known; no new mechanism.
2. Edge case: Twin gaps have one interior point so coincidence is forced;
   long Cramér-scale gaps still have `ln_span - 1 ~ gap/(n ln n)` far below
   `1/d_min`. Bound only fails for absurd super-exponential gaps not seen in
   primes.
3. So-what: Even if locked, so what? Answer: it kills a research fork that
   hoped CDL kappa would refine PGS interior selection. Useful as a stop rule.

Attacks succeed against the original positive hypothesis. Surviving product is
explicit failure plus a stop-rule measurement, not a new positive law.

## Phase 5: Falsifier (measurable)

Original claim is false if, on primes up to L:

- `n_differ == 0`, and
- `n_inversion_feasible_by_ln_span == 0`, and
- no rise of diverge rate in large gap_len bins.

All three hold in results.json for L=1e6.

What would revive Path A:

- a gap with `ln(q-1)/ln(p+1) > 1 + 1/d_min`, or
- nonzero diverge rate rising with gap length.

## Phase 6: Checklist

- Revises a hoped CDL-vs-PGS refinement: yes (negatively).
- Escapes proverb without loss: no (positive form fails rephrase trap).
- Falsifiable prediction: yes (diverge_rate, intensity).
- Causal mechanism: yes (inversion inequality).
- Expert surprise: moderate for the total empirical lock; low for the proverb.
- Bounded scope: prime-gap interiors, kappa vs d only.
- Struggle / attacks: yes.

Conclusion: explicit failure of systematic long-gap divergence. Strongest
honest product is the measured argmin lock and research stop rule.
