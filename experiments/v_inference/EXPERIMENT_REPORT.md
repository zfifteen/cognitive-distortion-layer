# v-Inference Benchmark Experiment Report

Date: 2026-03-30

This report is generated from a local benchmark run in this repository.

## Configuration

- `n_max_precomputed`: 10000
- `trials_per_cell`: 12
- `sample_sizes`: [100, 1000, 5000]
- `sequence_types`: ['random', 'consecutive', 'prime_biased', 'composite_heavy']
- `methods`: ['moment_match', 'mle', 'fingerprint']
- `noise_level`: 0.03
- `v_values`: [0.5, 1.0, 1.5, 2.0, 2.5]

## Headline Findings

- Best aggregate cell: `mle` on `random` at `M=5000` with MAE `0.0131`.
- Fingerprint recovery reaches MAE `0.0157` on `random` at `M=5000`.
- MLE reaches MAE `0.0131` on `random` at `M=5000`.
- Moment matching is prior-sensitive but usable in its best calibrated regime, reaching MAE `0.0275` on `prime_biased` at `M=5000`.
- Composite-heavy sequences shift the ranking: the best method there is `fingerprint` with MAE `0.0637` at `M=5000`.
- `8` aggregate cells clear a 90% success rate threshold in this run.

## Metrics by Cell

| Sample Size | Sequence Type | Method | MAE | RMSE | Bias | Success Rate |
|---|---|---|---:|---:|---:|---:|
| 100 | random | moment_match | 0.2146 | 0.2263 | -0.1991 | 21.67% |
| 100 | random | mle | 0.0183 | 0.0211 | -0.0085 | 98.33% |
| 100 | random | fingerprint | 0.1163 | 0.1447 | 0.0172 | 28.33% |
| 100 | consecutive | moment_match | 0.1885 | 0.2178 | -0.1704 | 41.67% |
| 100 | consecutive | mle | 0.0318 | 0.0451 | -0.0163 | 86.67% |
| 100 | consecutive | fingerprint | 0.1287 | 0.1738 | -0.0411 | 38.33% |
| 100 | prime_biased | moment_match | 0.1111 | 0.1337 | -0.0200 | 35.00% |
| 100 | prime_biased | mle | 0.0337 | 0.0366 | -0.0252 | 91.67% |
| 100 | prime_biased | fingerprint | 0.1080 | 0.1378 | -0.0099 | 33.33% |
| 100 | composite_heavy | moment_match | 0.4783 | 0.4813 | -0.4743 | 21.67% |
| 100 | composite_heavy | mle | 0.2302 | 0.2927 | -0.2248 | 58.33% |
| 100 | composite_heavy | fingerprint | 0.0946 | 0.1080 | 0.0017 | 31.67% |
| 1000 | random | moment_match | 0.1995 | 0.2023 | -0.1961 | 33.33% |
| 1000 | random | mle | 0.0139 | 0.0144 | -0.0073 | 100.00% |
| 1000 | random | fingerprint | 0.0462 | 0.0564 | 0.0048 | 55.00% |
| 1000 | consecutive | moment_match | 0.1977 | 0.2207 | -0.1897 | 33.33% |
| 1000 | consecutive | mle | 0.0374 | 0.0523 | -0.0204 | 83.33% |
| 1000 | consecutive | fingerprint | 0.1075 | 0.1534 | -0.0321 | 43.33% |
| 1000 | prime_biased | moment_match | 0.0353 | 0.0432 | -0.0273 | 71.67% |
| 1000 | prime_biased | mle | 0.0254 | 0.0262 | -0.0205 | 100.00% |
| 1000 | prime_biased | fingerprint | 0.0644 | 0.0847 | 0.0339 | 53.33% |
| 1000 | composite_heavy | moment_match | 0.4761 | 0.4768 | -0.4754 | 20.00% |
| 1000 | composite_heavy | mle | 0.2255 | 0.2321 | -0.2194 | 60.00% |
| 1000 | composite_heavy | fingerprint | 0.0671 | 0.0771 | 0.0095 | 48.33% |
| 5000 | random | moment_match | 0.1950 | 0.1961 | -0.1939 | 40.00% |
| 5000 | random | mle | 0.0131 | 0.0133 | -0.0074 | 100.00% |
| 5000 | random | fingerprint | 0.0157 | 0.0187 | 0.0057 | 98.33% |
| 5000 | consecutive | moment_match | 0.1686 | 0.1739 | -0.1652 | 36.67% |
| 5000 | consecutive | mle | 0.0142 | 0.0163 | -0.0011 | 98.33% |
| 5000 | consecutive | fingerprint | 0.0470 | 0.0543 | 0.0127 | 61.67% |
| 5000 | prime_biased | moment_match | 0.0275 | 0.0311 | -0.0227 | 81.67% |
| 5000 | prime_biased | mle | 0.0257 | 0.0259 | -0.0197 | 100.00% |
| 5000 | prime_biased | fingerprint | 0.0413 | 0.0524 | -0.0032 | 61.67% |
| 5000 | composite_heavy | moment_match | 0.4772 | 0.4775 | -0.4767 | 20.00% |
| 5000 | composite_heavy | mle | 0.2456 | 0.2481 | -0.2395 | 60.00% |
| 5000 | composite_heavy | fingerprint | 0.0637 | 0.0815 | 0.0238 | 61.67% |

## Reproduction

Run the benchmark again with:

```bash
python3 experiments/v_inference/benchmark.py --n-max 10000 --trials 12 --sample-sizes 100 1000 5000 --v-values 0.5 1.0 1.5 2.0 2.5 --methods moment_match mle fingerprint --sequence-types random consecutive prime_biased composite_heavy --noise-level 0.03 --seed 20260330
```

The JSON artifact in this directory is the machine-readable record of the run.

