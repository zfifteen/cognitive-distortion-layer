# Path A result: explicit failure

## Core product

```insight
Kappa and d Gap Winners stay locked on real prime gaps

The log factor inside CDL curvature never moves the prime-gap interior minimizer away from the pure divisor-count Gap Winner on any measured gap.

What looked like a natural refinement (weight low divisor counts by a smooth size factor) cannot reorder that choice because ordinary prime gaps are far too short in log scale to beat a single step up in divisor count.

This is non-obvious only as a research stop rule: it is easy to hope that CDL would paint a different interior champion than PGS, yet the continuous warp is the wrong tool for that job.

We should not expect diverge rates to rise with gap length, and we should not spawn a child program whose identity is "kappa Gap Winner differs from d Gap Winner on long gaps."

The pattern to expect is total agreement of the two selectors, with a measurable intensity far below one, until someone exhibits a gap where the log span ratio exceeds one plus one over the gap minimum divisor count.
```

## Status

- Empirical only (limit 1e6 in `results.json`).
- Not a theorem claim.
- Does not restate PGS GWR as CDL novelty.
- Original Path A divergence hypothesis: **FALSIFIED**.

## Falsifier (for the lock / failure report itself)

The lock reading weakens if a future run finds `n_differ > 0` with rate rising in large `gap_len` bins, or any gap with `ln_span_ratio > min_step_ratio`.

## Decision rule

When proposing CDL extensions of prime-gap interior structure, do not use argmin of kappa as a distinct selector from argmin of d; measure intensity `I` first, and abandon reordering claims while `max I < 1` on the target range.
