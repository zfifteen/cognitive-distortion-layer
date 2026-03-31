# Cognitive Pilot Report — Sprint 6

## Headline Findings

- `50` participants, `200` trials each.
- Hybrid fingerprint recovery reaches MAE `0.0705` with `90.00%` success at `|error| < 0.15`.
- Hybrid fallback reduces recovery error by `88.10%` versus pure continuous calibration.
- Recovered `v` cleanly separates the sharp cluster (`0.80 ± 0.16`) from the compressed cluster (`1.80 ± 0.30`).
- Psychophysical compression correlation: `0.980`.

## Interpretation

- The local pilot reproduces the applied bridge from Sprint 3–5 into perceptual data.
- Exact integer curvature still matters on real human-like sequences; the hybrid path materially outperforms a pure smooth surrogate.
- Style labels are operational: low-v participants stay on sharper geodesics, high-v participants show stronger tail collapse.

