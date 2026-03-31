# Crypto Prefilter Benchmark Report

Date: 2026-03-31

This report benchmarks the exact sweet-spot CDL path where the current implementation is executable,
a deterministic CDL proxy backed by a chunked prime table,
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
- `miller_rabin_bases`: [2, 3, 5, 7, 11, 13, 17, 19]
- `truth_check`: False

## Headline Findings

- Sweet-spot Z-space hit the fixed-point band for `29` of `29` calibration primes within numeric tolerance, with `0` fixed-point composites.
- The deterministic proxy hit `29` fixed points on the same calibration corpus with `0` composite fixed points and calibration accuracy `100.00%`.
- On the same `20`-bit calibration corpus, fixed-base Miller-Rabin matched exact primality with accuracy `100.00%`.
- Mean runtime on the calibration corpus was `0.056189` ms per candidate for exact sweet-spot `z_normalize`, `0.007240` ms for the deterministic proxy, and `0.001680` ms for Miller-Rabin.
- On the `2048`-bit control corpus, Miller-Rabin averaged `8.499067` ms per candidate and passed `1` of `1024` odd candidates; first pass index: `354`.
- The deterministic proxy rejected `929` of `1024` cryptographic candidates before Miller-Rabin (`90.72%`), cut the end-to-end pipeline to `2.916409` ms per candidate, and delivered a measured `2.91x` speedup over Miller-Rabin alone on this corpus.
- On the `4096`-bit bonus corpus, the same deterministic proxy rejected `232` of `256` candidates (`90.62%`), reduced mean runtime from `64.039271` ms to `20.255317` ms per candidate, and delivered a measured `3.16x` speedup.
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
| Mean exact `z_normalize` time (ms) | 0.056189 |
| Mean Miller-Rabin time (ms) | 0.001680 |

## Proxy Calibration

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Fixed points | 29 |
| Composite false fixed points | 0 |
| Strict composite contractions | 227 |
| Accuracy | 100.000000% |
| Precision | 100.000000% |
| Recall | 100.000000% |
| Mean proxy time (ms) | 0.007240 |

## Crypto Control

| Metric | Value |
|---|---:|
| Candidate count | 1024 |
| Miller-Rabin pass count | 1 |
| Miller-Rabin pass rate | 0.097656% |
| First pass index | 354 |
| Mean Miller-Rabin time (ms) | 8.499067 |

## Proxy + Miller-Rabin Pipeline

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Rejected before Miller-Rabin | 929 |
| Rejection rate | 90.722656% |
| Survivors to Miller-Rabin | 95 |
| Survivor rate | 9.277344% |
| Miller-Rabin passes after proxy | 1 |
| First pass index after proxy | 354 |
| Mean proxy time (ms) | 0.169739 |
| Mean survivor Miller-Rabin time (ms) | 29.606213 |
| Mean pipeline time (ms) | 2.916409 |
| Speedup vs MR-only | 2.914223x |

## 4096-bit Bonus Control

| Metric | Value |
|---|---:|
| Candidate count | 256 |
| Miller-Rabin pass count | 0 |
| Miller-Rabin pass rate | 0.000000% |
| First pass index | none in corpus |
| Mean Miller-Rabin time (ms) | 64.039271 |

## 4096-bit Bonus Proxy + Miller-Rabin Pipeline

| Metric | Value |
|---|---:|
| Trial prime limit | 200003 |
| Trial prime count | 17984 |
| Chunk size | 256 |
| Rejected before Miller-Rabin | 232 |
| Rejection rate | 90.625000% |
| Survivors to Miller-Rabin | 24 |
| Survivor rate | 9.375000% |
| Miller-Rabin passes after proxy | 0 |
| First pass index after proxy | none in corpus |
| Mean proxy time (ms) | 0.234499 |
| Mean survivor Miller-Rabin time (ms) | 213.555394 |
| Mean pipeline time (ms) | 20.255317 |
| Speedup vs MR-only | 3.161603x |

## Calibration Timing Ratios

| Ratio | Value |
|---|---:|
| Exact CDL / Miller-Rabin | 33.441443x |
| Exact CDL / Proxy | 7.761329x |
| Proxy / Miller-Rabin | 4.308726x |

## Reproduction

Run the benchmark again with:

```bash
python3 experiments/crypto_prefilter/benchmark.py --exact-bits 20 --exact-count 256 --crypto-bits 2048 --crypto-count 1024 --bonus-crypto-bits 4096 --bonus-crypto-count 256 --proxy-trial-prime-limit 200003 --proxy-chunk-size 256 --mr-bases 2 3 5 7 11 13 17 19
```

The JSON artifact in this directory is the machine-readable record of the run.

