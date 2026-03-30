# Continuous Extension Experiment Report

## Headline Findings

- κ_smooth matches empirical composite curvature within `0.19%` at `x=100000` and `0.13%` at `x=500000`.
- Continuous separation against the prime-geodesic asymptotic runs from `7.33×` at `2e6` to `7.79×` at `5e6`.
- Continuous variance reduction benchmark: `98.74%`.
- Fingerprint-based continuous `v` recovery reaches MAE `0.0064` with `100.00%` success at `M=5000` and `3%` noise.

## Interpretation

- The smooth layer preserves the large-scale distortion geometry while damping local divisor spikes.
- Continuous recovery works best when the calibration support is log-spaced, matching the asymptotic form of κ_smooth.
- The hybrid path keeps exact integer behavior available while enabling real-valued pipelines.

