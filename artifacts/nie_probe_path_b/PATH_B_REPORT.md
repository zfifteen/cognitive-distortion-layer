# Path B Probe Report — Dual of v-recovery

Date (UTC): 2026-07-17T00:43:21.630097+00:00
Verdict: **SURVIVOR**

At fixed v*=e^2/2, mixture weights of low-d families are substantially more identifiable from Z samples than from raw magnitude samples of equal size.

## Setup

- Support: integers `n ∈ [2, 20000]`
- Fixed traversal rates: `v* = e²/2 ≈ 3.694528` and attack `v = 1.0`
- Families: d2_primes, d3_p2, d4, d_ge_5
- Trials/cell: 40; sample sizes: [50, 100, 250, 500, 1000, 2000]
- Binary π_prime grid: [0.1, 0.25, 0.4, 0.55]

## Z-map at v*

| Family | Count | mean Z | median Z | frac Z=1 | mean log Z |
|---|---:|---:|---:|---:|---:|
| d2_primes | 2262 | 1 | 1 | 1.000 | 9.227e-18 |
| d3_p2 | 34 | 0.05529 | 0.01667 | 0.000 | -3.725 |
| d4 | 5056 | 0.0005029 | 0.0001034 | 0.000 | -8.855 |
| d_ge_5 | 12647 | 2.848e-06 | 3.864e-18 | 0.000 | -53.98 |

## Binary recovery MAE (mean over π_true) at v*

| M | z_park | z_mle | z_fp | n_mle | n_fp | natural | n_mle/z_mle |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.0525 | 0.0488 | 0.0991 | 0.3399 | 0.2350 | 0.2245 | 6.96 |
| 100 | 0.0353 | 0.0355 | 0.0559 | 0.3262 | 0.2144 | 0.2245 | 9.19 |
| 250 | 0.0196 | 0.0215 | 0.0581 | 0.2213 | 0.1931 | 0.2245 | 10.30 |
| 500 | 0.0141 | 0.0158 | 0.0378 | 0.1722 | 0.1878 | 0.2245 | 10.92 |
| 1000 | 0.0109 | 0.0115 | 0.0225 | 0.1202 | 0.1678 | 0.2245 | 10.45 |
| 2000 | 0.0078 | 0.0082 | 0.0194 | 0.0911 | 0.1313 | 0.2245 | 11.12 |

## Fisher (approx per-observation) at π=0.25, v*

| M | I_Z | I_n | I_Z / I_n |
|---:|---:|---:|---:|
| 50 | 4.586 | 0.03465 | 132.37 |
| 100 | 5.16 | 0.03802 | 135.70 |
| 250 | 4.006 | 0.0457 | 87.66 |
| 500 | 5.762 | 0.04349 | 132.49 |
| 1000 | 6.59 | 0.03964 | 166.26 |
| 2000 | 6.57 | 0.02696 | 243.68 |

## v-sensitivity (binary MLE / park, M=500, π=0.25)

| v | park_frac primes | logZ sep | park MAE | MLE MAE |
|---:|---:|---:|---:|---:|
| 0.500000 | 0.000 | 5.406 | 0.2500 | 0.0259 |
| 1.000000 | 0.000 | 10.98 | 0.2500 | 0.0174 |
| 1.500000 | 0.000 | 16.55 | 0.2500 | 0.0153 |
| 3.694528 ← v* | 1.000 | 41.02 | 0.0151 | 0.0151 |
| 2.500000 | 0.000 | 27.7 | 0.2500 | 0.0142 |
| 3.000000 | 0.000 | 33.27 | 0.2500 | 0.0145 |
| 2.463019 | 0.000 | 27.29 | 0.2484 | 0.0148 |
| 1.847264 | 0.000 | 20.42 | 0.0349 | 0.0166 |

## Multi-family L1 (mean ratios n/z) at v*

- M=100, π=[0.35, 0.05, 0.25, 0.35]: L1_z=0.3866, L1_n=0.9961, ratio=2.58
- M=100, π=[0.15, 0.1, 0.35, 0.4]: L1_z=0.1331, L1_n=0.9552, ratio=7.17
- M=100, π=[0.5, 0.05, 0.2, 0.25]: L1_z=0.5247, L1_n=1.1746, ratio=2.24
- M=500, π=[0.35, 0.05, 0.25, 0.35]: L1_z=0.3359, L1_n=0.6818, ratio=2.03
- M=500, π=[0.15, 0.1, 0.35, 0.4]: L1_z=0.0847, L1_n=0.6923, ratio=8.18
- M=500, π=[0.5, 0.05, 0.2, 0.25]: L1_z=0.4804, L1_n=0.7457, ratio=1.55
- M=2000, π=[0.35, 0.05, 0.25, 0.35]: L1_z=0.3158, L1_n=0.4146, ratio=1.31
- M=2000, π=[0.15, 0.1, 0.35, 0.4]: L1_z=0.0708, L1_n=0.4582, ratio=6.47
- M=2000, π=[0.5, 0.05, 0.2, 0.25]: L1_z=0.4672, L1_n=0.4581, ratio=0.98

## Headline metrics

- median n_mle/z_mle MAE ratio: 10.376
- mean n_mle/z_mle MAE ratio (M≥250): 10.699
- mean multi-family L1 ratio n/z: 3.612
- best v for z_mle (M=500): 2.500000
- v* z_mle MAE: 0.0151
- v* park MAE: 0.0151

## Novelty delta (not restating dfr/cst/dpt/hidden_tuning)

The dual channel claim: with v fixed at the prime fixed-point speed, the **mixture weights**
of known support families become the recoverable parameter from Z alone, with measurable
sample-complexity advantage over raw magnitude. This is the reverse of v_recovery
(recover v under known support prior) and a frozen-v special case distinct from zpf joint (regime,v).

## Adversarial notes (post-run)

1. **Parking ≡ Bernoulli labels at exact v*.**  
   Under exact arithmetic, \(Z=n^{1-d/2}\) so \(Z=1\) iff \(d=2\). Thus `z_park` is the empirical
   prime frequency; its Fisher \(1/(\pi(1-\pi))\) matches the measured \(I_Z\approx 5.3\) at \(\pi=0.25\).
   This is the *mechanism* of the dual channel, not an accidental bug. The dual claim is that this
   structure is available as a process observation when v is known/frozen.

2. **MLE is not unique to v*.**  
   log-Z mean separation grows with v, so calibrated MLE works for a band of large v.
   Best MLE in the sweep was v=2.5 (MAE 0.0142) vs v* (0.0151). What is unique to v* is the
   **model-free park estimator** (no family density calibration).

3. **Multi-family is qualified.**  
   Mean L1 ratio favors Z (~3.6), but some high-π cells at M=2000 approach ratio ~1.
   The d=3 family is tiny on this support (34 integers). Strongest survivor is binary prime mass.

4. **Scope.**  
   Not a primality algorithm (computing Z needs d(n)). It is sample complexity of π given
   observed Z vs observed n magnitudes.

## Falsifier

If at M≥250, mean MAE of best Z estimator is not ≤ 1/2 the mean MAE of best raw-n estimator
across π_true ∈ {0.1,0.25,0.4,0.55}, or if multi-family L1 ratio < 1.5, reject the strong claim.

**This run:** ratio ≈ 10.7, multi L1 ratio ≈ 3.6 → falsifier not triggered.

JSON: `path_b_results.json`  
Insight writeup: `INSIGHT.md`
