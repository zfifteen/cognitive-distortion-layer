# ANALYTIC_CONNECTIONS.md — Theoretical Grounding of κ(n)

## Derived Asymptotics

E[κ(n)] ∼ ((ln n + 2γ − 1) ln n) / e²

E[κ(p)] ≈ 2 ln x / e²

## Local Empirical Checks

- Up to `100000`: prime mean `2.813`, composite mean `18.213`, ratio `6.47×`, κ_smooth error vs composite mean `0.19%`.
- Up to `500000`: prime mean `3.254`, composite mean `23.608`, ratio `7.26×`, κ_smooth error vs composite mean `0.13%`.

## Sensitivity Scenarios

- Working unconditional floor carried through the local reproduction: `2.8×`.
- Working RH-style floor carried through the local reproduction: `3.4×`.
- Smooth large-x projection at `10^7`: `8.14×`.

## Integration Impact

- Port 1 can route candidates with range-aware τ from the Sprint 1 threshold map.
- Port 3 can use asymptotic priors when calibrating `v` across wider scales.
- Sprint 5 inherits `κ_smooth(x)` directly from this document.

