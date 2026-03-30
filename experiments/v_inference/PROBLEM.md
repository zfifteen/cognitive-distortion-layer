# v-Inference Problem Statement (Sprint 3)

Sprint 3 asks whether the traversal rate parameter `v` can be recovered from
observed `Z` values alone.

The canonical forward model remains untouched:

```text
κ(n) = d(n) · ln(n) / e²
Z(n) = n / exp(v · κ(n))
```

The inverse task is:

1. Generate or observe a sequence of `Z` values.
2. Infer the unknown `v` without access to the source integers `n`.
3. Characterize identifiability as a function of sample size, sequence prior,
   and measurement noise.

This benchmark treats identifiability as a calibrated inference problem under an
explicit sequence prior. The recovery path is measured, not assumed.

## Acceptance Criteria

- Produce a reproducible benchmark in `experiments/v_inference/benchmark.py`.
- Save machine-readable results in `experiments/v_inference/v_inference_results.json`.
- Save a written report in `experiments/v_inference/EXPERIMENT_REPORT.md`.
- Provide a reusable `v_recovery.py` module with at least `moment_match`,
  `mle`, and `fingerprint` recovery methods.
- Validate the recovery table against canonical `cdl.kappa` values before
  running inference.
- Add tests that exercise at least one successful recovery path locally.

The curvature signal is already validated. This sprint measures how much of the
distortion rate survives into observable `Z` sequences and under which regimes
that information becomes operational.
