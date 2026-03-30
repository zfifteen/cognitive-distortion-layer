# EXECUTIVE SUMMARY: CDL Hypothesis Falsification Experiment

## Critical Finding: Hypothesis FALSIFIED

**The CDL prime diagnostic hypothesis as stated is FALSE for the RSA-129 factor range.**

### Key Results (n = 50–10,000)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Accuracy** | 88.19% | Misleading - driven by class imbalance |
| **Precision** | 100.00% | Perfect when classifying as prime |
| **Recall** | 3.21% | **CRITICAL FAILURE: Misses 96.79% of primes** |
| **F1 Score** | 6.23% | Reveals severe imbalance in practical utility |

### The Falsification

The hypothesis claims: *"CDL κ(n) threshold classifier with τ=1.5 provides useful prime diagnostic capabilities with ~88% accuracy for RSA-129 factor range (n=50-10K)"*

**Why this is FALSE:**

1. **Recall Catastrophe**: The classifier identifies only **39 out of 1,214 primes** (3.21%). This means it **fails to detect 96.79% of actual primes**.

2. **Accuracy Illusion**: The 88.19% accuracy is a statistical artifact:
   - Dataset: 1,214 primes (12.2%) vs 8,737 composites (87.8%)
   - A trivial "always predict composite" classifier would achieve 87.8% accuracy
   - The CDL classifier adds only 0.4% improvement over this baseline

3. **Threshold Breakdown**: The threshold τ=1.5 optimized for small primes (n=2-49, avg κ≈0.739) fails catastrophically at larger scales:
   - Prime avg κ at n=50-10K: **2.197** (2.97× higher than seed)
   - All but 39 primes exceed the 1.5 threshold
   - The curvature signal κ(n) grows with ln(n), making fixed thresholds ineffective

4. **False Negatives Dominate**: 1,175 false negatives vs 39 true positives creates a 30:1 failure ratio for the stated prime diagnostic use case.

### Curvature Statistics

- **Prime mean κ**: 2.197 (vs seed baseline 0.739)
- **Composite mean κ**: 11.753 (vs seed baseline 2.252)
- **Separation ratio**: 5.35× (improved from seed 3.05×)
- **Bootstrap 95% CI**: [87.56%, 88.79%]

### Confusion Matrix

```
                Predicted
                Prime   Composite
Actual Prime      39      1,175    (96.8% missed)
       Composite   0      8,737    (100% correct)
```

## Conclusion

While κ(n) shows theoretical promise (5.35× separation ratio), the **fixed threshold approach fails for practical prime diagnostics** at larger scales. The hypothesis is falsified due to:

1. Catastrophic recall failure (3.21%)
2. Fixed threshold incompatibility with ln(n) growth
3. Misleading accuracy metric driven by class imbalance
4. Practical uselessness: misses 96.8% of target primes

**Recommendation**: Scale-adaptive or machine learning approaches required for κ(n) to provide useful prime diagnostics beyond the seed range.
