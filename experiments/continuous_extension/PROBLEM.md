# Continuous Geodesic Extension (Sprint 5)

This experiment extends the CDL from exact integer curvature into a smooth real-valued surrogate.

Canonical smooth signal:

```text
κ_smooth(x) = ((ln x + 2γ − 1) ln x) / e²
Z(x) = x / exp(v · κ_smooth(x))
```

Acceptance targets for the local reproduction:
- κ_smooth tracks large-scale composite curvature with low relative error.
- Continuous normalization preserves large variance collapse.
- `v` recovery transfers to smooth sequences with bounded degradation.

