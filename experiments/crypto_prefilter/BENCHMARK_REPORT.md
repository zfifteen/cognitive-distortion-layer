# Crypto Prefilter Benchmark Report

Date: 2026-03-31

This report benchmarks the exact sweet-spot CDL path where the current implementation is executable,
and fixed-base Miller-Rabin on deterministic cryptographic-scale odd candidates.

## Configuration

- `sweet_spot_v`: 3.694528049465
- `exact_bits`: 20
- `exact_count`: 256
- `crypto_bits`: 2048
- `crypto_count`: 1024
- `miller_rabin_bases`: [2, 3, 5, 7, 11, 13, 17, 19]
- `truth_check`: False

## Headline Findings

- Sweet-spot Z-space hit the fixed-point band for `29` of `29` calibration primes within numeric tolerance, with `0` fixed-point composites.
- On the same `20`-bit calibration corpus, fixed-base Miller-Rabin matched exact primality with accuracy `100.00%`.
- Mean runtime on the calibration corpus was `0.054233` ms per candidate for exact sweet-spot `z_normalize` versus `0.001440` ms for Miller-Rabin, a ratio of `37.66x`.
- On the `2048`-bit control corpus, Miller-Rabin averaged `8.447843` ms per candidate and passed `1` of `1024` odd candidates; first pass index: `354`.
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
| Mean exact `z_normalize` time (ms) | 0.054233 |
| Mean Miller-Rabin time (ms) | 0.001440 |

## Crypto Control

| Metric | Value |
|---|---:|
| Candidate count | 1024 |
| Miller-Rabin pass count | 1 |
| Miller-Rabin pass rate | 0.097656% |
| First pass index | 354 |
| Mean Miller-Rabin time (ms) | 8.447843 |

## Reproduction

Run the benchmark again with:

```bash
python3 experiments/crypto_prefilter/benchmark.py --exact-bits 20 --exact-count 256 --crypto-bits 2048 --crypto-count 1024 --mr-bases 2 3 5 7 11 13 17 19
```

The JSON artifact in this directory is the machine-readable record of the run.

