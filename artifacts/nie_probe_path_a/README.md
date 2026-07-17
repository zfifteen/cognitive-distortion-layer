# Path A probe: Kappa vs divisor Gap-Winner divergence

Executable empirical probe for NIE Path A.

## Run

```bash
cd /Users/velocityworks/IdeaProjects/cognitive-distortion-layer
PYTHONPATH=src/python python3 artifacts/nie_probe_path_a/probe_kappa_vs_d_gap_winner.py --limit 1000000
```

Writes `results.json` beside the script (or `--out PATH`).

## Hypothesis

Inside prime gap `(p,q)`, Gap Winner under pure `d(n)` and under
`kappa(n)=d(n)*ln(n)/e^2` coincide on short gaps but systematically diverge when
gap length lets `ln(n)` variation compete with discrete `d(n)` jumps.

## Verdict (measured)

**FALSIFIED** on primes up to 1e6 (78496 gaps):

- `n_differ = 0` (never `w_k != w_d`)
- `n_inversion_feasible_by_ln_span = 0`
- mean intensity `I = (ln_span-1)/(1/d_min) ~ 6e-5`, max I ~ 0.32 < 1

## Files

| File | Role |
| --- | --- |
| `probe_kappa_vs_d_gap_winner.py` | executable probe |
| `results.json` | last run metrics + falsifier payload |
| `PROTOCOL.md` | Z-map, prior art, rephrase trap, 3 attacks |
| `INSIGHT.md` | surviving product (explicit failure) |

## Definitions

- `w_d`: leftmost `n` in `(p,q)` minimizing `d(n)` (PGS Gap Winner)
- `w_k`: leftmost `n` in `(p,q)` minimizing `kappa(n)`
- Inversion only possible leftward, and only if some earlier higher-d `m` has
  `d(m)/d(w_d) < ln(w_d)/ln(m)`
