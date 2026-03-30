# CDL Hypothesis Falsification Experiment

This directory contains a complete falsification experiment for the Cognitive Distortion Layer (CDL) prime diagnostic hypothesis.

## Quick Start

**Read this first**: [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) - Crystal clear results in 2 minutes

**Then dive deeper**: [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md) - Complete methodology and analysis

## Experiment Overview

- **Hypothesis**: CDL κ(n) threshold classifier provides useful prime diagnostics with ~88% accuracy on RSA-129 factor range
- **Dataset**: n = 50 to 10,000 (9,951 integers: 1,214 primes, 8,737 composites)
- **Method**: Bootstrap validation with 1,000 resamples
- **Result**: **HYPOTHESIS FALSIFIED** - Catastrophic recall failure (3.21%)

## Files

| File | Description |
|------|-------------|
| `EXECUTIVE_SUMMARY.md` | High-level findings - START HERE |
| `EXPERIMENT_REPORT.md` | Complete methodology, analysis, and recommendations |
| `ci.json` | Bootstrap confidence intervals and all metrics |
| `accuracy.csv` | Per-number predictions (n, κ, predicted, actual) |
| `cdl_gist.py` | Reference implementation from problem statement |

## Key Finding

The classifier achieves 88.19% accuracy but **misses 96.8% of primes** (recall = 3.21%). This makes it useless for its stated purpose (prime diagnostic/prefilter). The high accuracy is a statistical artifact of class imbalance (87.8% composites).

## Reproducing Results

```bash
# From repository root
python scripts/bench_cdl.py --range 50 10000 --threshold 1.5 --boot 1000

# Results written to experiments/cdl_falsification/
```

## Confusion Matrix

```
                    Predicted
                    Prime    Composite
Actual Prime          39        1,175   ← 96.8% missed
       Composite       0        8,737
```

## Dependencies

- Python 3.6+
- sympy (divisor computation, primality testing)
- numpy (bootstrap statistics)

```bash
pip install sympy numpy
```

## Metrics Summary

| Metric | Value | Verdict |
|--------|-------|---------|
| Accuracy | 88.19% | Misleading |
| Precision | 100.00% | Too conservative |
| **Recall** | **3.21%** | **CATASTROPHIC FAILURE** |
| F1 Score | 6.23% | Confirms failure |
| Bootstrap 95% CI | [87.56%, 88.79%] | High certainty |

## Why It Failed

1. **Scale non-invariance**: Threshold τ=1.5 optimized for n=2-49 (prime κ≈0.739) fails at n=50-10K (prime κ≈2.197)
2. **Logarithmic drift**: κ(n) ∝ ln(n) causes baseline shift, but threshold is fixed
3. **Class imbalance**: 87.8% composites → "always predict composite" gives 87.8% accuracy
4. **Wrong optimization**: Maximized precision at the expense of recall

## What Actually Works

- **κ(n) signal**: Excellent separation (5.35× ratio composite/prime)
- **Composite detection**: 100% precision, 99.9% recall
- **Feature for ML**: κ(n) could be useful input to learned classifiers

## What Doesn't Work

- **Fixed threshold**: Incompatible with multi-scale data
- **Prime prefilter**: Filters out 96.8% of primes (opposite of goal)
- **Claimed accuracy**: Driven by class imbalance, not model quality

## Recommendations

1. **Documentation**: Add WARNING about fixed threshold limitations
2. **Future work**: Develop scale-adaptive threshold τ(n) = f(ln(n))
3. **Alternative use**: Reposition as "composite detector" instead of "prime diagnostic"
4. **Better metrics**: Always report precision/recall/F1, not just accuracy

## Citation

This experiment implements and tests the CDL Prime Diagnostic Gist from:
- Repository: zfifteen/cognitive-number-theory
- Source: Problem statement dated Dec 2025
- Method: Direct implementation of provided code and specifications

## Status

- **Experiment Status**: ✅ Complete
- **Hypothesis Status**: ❌ Falsified
- **Confidence**: High (tight bootstrap CI)
- **Reproducibility**: Full (deterministic seed, documented environment)

---

**Bottom line**: While κ(n) shows theoretical promise, the fixed threshold approach fails catastrophically for practical prime diagnostics at scale. Accuracy of 88% conceals 97% recall failure.
