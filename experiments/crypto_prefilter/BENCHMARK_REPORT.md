# Crypto Prefilter Benchmark Report

Date: 2026-03-31

This report benchmarks the exact sweet-spot CDL path where the current implementation is executable,
a deterministic CDL proxy backed by bit-length-gated interval-split chunked prime tables,
and fixed-base Miller-Rabin on deterministic cryptographic-scale odd candidates.

## Configuration

- `sweet_spot_v`: 3.694528049465
- `exact_bits`: 20
- `exact_count`: 256
- `crypto_bits`: 2048
- `crypto_count`: 1024
- `bonus_crypto_bits`: 4096
- `bonus_crypto_count`: 256
- `proxy_trial_prime_limit`: 200003
- `proxy_chunk_size`: 256
- `proxy_tail_prime_limit`: 300007
- `proxy_tail_chunk_size`: 256
- `proxy_deep_tail_prime_limit`: 1000003
- `proxy_deep_tail_chunk_size`: 256
- `proxy_deep_tail_min_bits`: 4096
- `miller_rabin_bases`: [2, 3, 5, 7, 11, 13, 17, 19]
- `truth_check`: False

## Headline Findings

- Sweet-spot Z-space hit the fixed-point band for `29` of `29` calibration primes within numeric tolerance, with `0` fixed-point composites.
- The deterministic proxy hit `29` fixed points on the same calibration corpus with `0` composite fixed points and calibration accuracy `100.00%`.
- On the same `20`-bit calibration corpus, fixed-base Miller-Rabin matched exact primality with accuracy `100.00%`.
- Mean runtime on the calibration corpus was `0.055715` ms per candidate for exact sweet-spot `z_normalize`, `0.010281` ms for the deterministic proxy, and `0.001541` ms for Miller-Rabin.
- On the `2048`-bit control corpus, Miller-Rabin averaged `8.466359` ms per candidate and passed `1` of `1024` odd candidates; first pass index: `354`.
- The deterministic proxy rejected `932` of `1024` cryptographic candidates before Miller-Rabin (`91.02%`), cut the end-to-end pipeline to `2.871545` ms per candidate, and delivered a measured `2.95x` speedup over Miller-Rabin alone on this corpus.
- On the `4096`-bit bonus corpus, the same deterministic proxy rejected `234` of `256` candidates (`91.41%`), reduced mean runtime from `63.627200` ms to `19.086690` ms per candidate, and delivered a measured `3.33x` speedup.
- The current exact CDL path was intentionally not run on `2048`-bit arbitrary candidates because `src/python/cdl.py` computes divisor count by `O(sqrt n)` enumeration; the implied trial space is about `2^1024` divisibility checks per worst-case candidate.

## Exact Calibration

| Metric | Value |
|---|---:|
| Candidate count | 256 |
| Prime count | 29 |
| Composite count | 227 |
| Prime mean kappa | 3.688275 |
| Composite mean kappa | 16.754550 |
| Separation ratio | 4.542652 |
| Algebraic fixed points | 29 |
| Numeric fixed points | 29 |
| Numeric false fixed points | 0 |
| Strict composite contractions | 227 |
| Mean exact `z_normalize` time (ms) | 0.055715 |
| Mean Miller-Rabin time (ms) | 0.001541 |

## Proxy Calibration

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Tail prime limit | 300007 |
| Tail prime count | 8013 |
| Tail chunk size | 256 |
| Deep tail prime limit | 1000003 |
| Deep tail prime count | 52501 |
| Deep tail chunk size | 256 |
| Deep tail minimum bits | 4096 |
| Fixed points | 29 |
| Composite false fixed points | 0 |
| Strict composite contractions | 227 |
| Accuracy | 100.000000% |
| Precision | 100.000000% |
| Recall | 100.000000% |
| Mean proxy time (ms) | 0.010281 |

## Crypto Control

| Metric | Value |
|---|---:|
| Candidate count | 1024 |
| Miller-Rabin pass count | 1 |
| Miller-Rabin pass rate | 0.097656% |
| First pass index | 354 |
| Mean Miller-Rabin time (ms) | 8.466359 |

## Proxy + Miller-Rabin Pipeline

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Tail prime limit | 300007 |
| Tail prime count | 8013 |
| Tail chunk size | 256 |
| Deep tail prime limit | 1000003 |
| Deep tail prime count | 52501 |
| Deep tail chunk size | 256 |
| Deep tail minimum bits | 4096 |
| Rejected before Miller-Rabin | 932 |
| Rejection rate | 91.015625% |
| Survivors to Miller-Rabin | 92 |
| Survivor rate | 8.984375% |
| Miller-Rabin passes after proxy | 1 |
| First pass index after proxy | 354 |
| Mean proxy time (ms) | 0.234366 |
| Mean survivor Miller-Rabin time (ms) | 29.352956 |
| Mean pipeline time (ms) | 2.871545 |
| Speedup vs MR-only | 2.948363x |

## 4096-bit Bonus Control

| Metric | Value |
|---|---:|
| Candidate count | 256 |
| Miller-Rabin pass count | 0 |
| Miller-Rabin pass rate | 0.000000% |
| First pass index | none in corpus |
| Mean Miller-Rabin time (ms) | 63.627200 |

## 4096-bit Bonus Proxy + Miller-Rabin Pipeline

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Tail prime limit | 300007 |
| Tail prime count | 8013 |
| Tail chunk size | 256 |
| Deep tail prime limit | 1000003 |
| Deep tail prime count | 52501 |
| Deep tail chunk size | 256 |
| Deep tail minimum bits | 4096 |
| Rejected before Miller-Rabin | 234 |
| Rejection rate | 91.406250% |
| Survivors to Miller-Rabin | 22 |
| Survivor rate | 8.593750% |
| Miller-Rabin passes after proxy | 0 |
| First pass index after proxy | none in corpus |
| Mean proxy time (ms) | 0.938619 |
| Mean survivor Miller-Rabin time (ms) | 211.177544 |
| Mean pipeline time (ms) | 19.086690 |
| Speedup vs MR-only | 3.333590x |

## Calibration Timing Ratios

| Ratio | Value |
|---|---:|
| Exact CDL / Miller-Rabin | 36.158211x |
| Exact CDL / Proxy | 5.419067x |
| Proxy / Miller-Rabin | 6.672405x |

## Reproduction

Run the benchmark again with:

```bash
python3 experiments/crypto_prefilter/benchmark.py --exact-bits 20 --exact-count 256 --crypto-bits 2048 --crypto-count 1024 --bonus-crypto-bits 4096 --bonus-crypto-count 256 --proxy-trial-prime-limit 200003 --proxy-chunk-size 256 --proxy-tail-prime-limit 300007 --proxy-tail-chunk-size 256 --proxy-deep-tail-prime-limit 1000003 --proxy-deep-tail-chunk-size 256 --proxy-deep-tail-min-bits 4096 --mr-bases 2 3 5 7 11 13 17 19
```

The JSON artifact in this directory is the machine-readable record of the run.

## End-to-End RSA Key Generation

- Baseline generated `300` deterministic `2048`-bit keypairs in `291938.126792` ms total (`1.027615` keypairs/s).
- The accelerated path generated the same `300` keypairs in `139942.831833` ms total (`2.143733` keypairs/s) for a measured `2.09x` speedup.
- The proxy removed `196864` Miller-Rabin calls (`90.97%` of baseline MR work) while preserving identical deterministic keypairs across both paths.
- Timing buckets in the accelerated path broke down into `31637.561032` ms proxy filtering (`22.61%`), `96950.562244` ms survivor Miller-Rabin (`69.28%`), `10265.828585` ms RSA assembly/validation (`7.34%`), and `1088.879972` ms residual search overhead (`0.78%`).
- Final keypair primes were confirmed by `sympy.isprime`; under the sweet-spot closed form, all `600` confirmed factors remain exactly on the `Z = 1.0` fixed-point band.

| Metric | Baseline | Accelerated |
|---|---:|---:|
| Keypair count | 300 | 300 |
| Total wall time (ms) | 291938.126792 | 139942.831833 |
| Keypairs per second | 1.027615 | 2.143733 |
| Mean time per keypair (ms) | 973.127089 | 466.476106 |
| Mean candidates per prime | 360.670000 | 360.670000 |
| Total candidates tested | 216402 | 216402 |
| Total Miller-Rabin calls | 216402 | 19538 |
| Total proxy rejections | 0 | 196864 |
| Proxy rejection contribution | 0.000000% | 90.971433% |
| Saved Miller-Rabin call rate | 0.000000% | 90.971433% |
| Proxy filtering time (ms) | 0.000000 | 31637.561032 |
| Survivor Miller-Rabin time (ms) | 280573.817575 | 96950.562244 |
| RSA assembly + validation time (ms) | 10027.370039 | 10265.828585 |
| Residual search overhead (ms) | 1336.939178 | 1088.879972 |
| Proxy filtering share | 0.000000% | 22.607490% |
| Survivor Miller-Rabin share | 96.107288% | 69.278691% |
| RSA assembly + validation share | 3.434759% | 7.335730% |
| Residual search overhead share | 0.457953% | 0.778089% |
| Matching deterministic keypairs | 300 | 300 |

## 4096-bit RSA Spot-Check

- Baseline generated `50` deterministic `4096`-bit keypairs in `757750.922792` ms total (`0.065985` keypairs/s).
- The accelerated path generated the same `50` keypairs in `268557.631625` ms total (`0.186180` keypairs/s) for a measured `2.82x` speedup.
- The proxy removed `79752` Miller-Rabin calls (`91.07%` of baseline MR work) while preserving identical deterministic keypairs across both paths.
- Timing buckets in the accelerated path broke down into `20304.792431` ms proxy filtering (`7.56%`), `234816.947269` ms survivor Miller-Rabin (`87.44%`), `12644.407662` ms RSA assembly/validation (`4.71%`), and `791.484263` ms residual search overhead (`0.29%`).
- Final keypair primes were confirmed by `sympy.isprime`; under the sweet-spot closed form, all `100` confirmed factors remain exactly on the `Z = 1.0` fixed-point band.

| Metric | Baseline | Accelerated |
|---|---:|---:|
| Keypair count | 50 | 50 |
| Total wall time (ms) | 757750.922792 | 268557.631625 |
| Keypairs per second | 0.065985 | 0.186180 |
| Mean time per keypair (ms) | 15155.018456 | 5371.152633 |
| Mean candidates per prime | 875.760000 | 875.760000 |
| Total candidates tested | 87576 | 87576 |
| Total Miller-Rabin calls | 87576 | 7824 |
| Total proxy rejections | 0 | 79752 |
| Proxy rejection contribution | 0.000000% | 91.066045% |
| Saved Miller-Rabin call rate | 0.000000% | 91.066045% |
| Proxy filtering time (ms) | 0.000000 | 20304.792431 |
| Survivor Miller-Rabin time (ms) | 743827.968721 | 234816.947269 |
| RSA assembly + validation time (ms) | 12695.092213 | 12644.407662 |
| Residual search overhead (ms) | 1227.861858 | 791.484263 |
| Proxy filtering share | 0.000000% | 7.560683% |
| Survivor Miller-Rabin share | 98.162595% | 87.436334% |
| RSA assembly + validation share | 1.675365% | 4.708266% |
| Residual search overhead share | 0.162040% | 0.294717% |
| Matching deterministic keypairs | 50 | 50 |

## RSA Reproduction

Run the end-to-end RSA benchmark again with:

```bash
python3 experiments/crypto_prefilter/rsa_keygen_benchmark.py --rsa-bits 2048 --rsa-keypair-count 300 --bonus-rsa-bits 4096 --bonus-rsa-keypair-count 50 --public-exponent 65537
```

