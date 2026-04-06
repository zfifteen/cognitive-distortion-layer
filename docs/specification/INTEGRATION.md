# CDL Integration Guide

This document explains how to integrate the Cognitive Distortion Layer (CDL) into your workflows for prime diagnostics, QMC sampling, signal normalization, and calibrated traversal-rate recovery.

## Quick Start

```python
import cdl

# Basic usage
n = 17
kappa_value = cdl.kappa(n)                    # Get curvature
classification = cdl.classify(n)              # Classify prime/composite
z_value = cdl.z_normalize(n, v=1.0)          # Apply Z-normalization
```

When `v` is unknown, recover it from an observed `Z` sequence under the matching support prior before running the downstream normalization pass.

## Integration Port 1: Prime Diagnostics Prefilter

### Problem
Primality testing is expensive for large numbers. Many composites can be identified quickly using structural features before running full tests.

### Solution with κ(n)
Use κ(n) as a fast prefilter to identify likely composites before expensive primality tests.

### Workflow

```python
import cdl

# Scenario: You have a list of candidate numbers to test for primality
candidates = [1009, 1010, 1011, 1012, 1013, 1014, 1015]

# Step 1: Fast prefilter using κ(n)
likely_primes, likely_composites = cdl.prime_diagnostic_prefilter(
    candidates,
    threshold=cdl.lookup_adaptive_threshold(max(candidates)),
    full_test_threshold=False  # Set True to verify with full test
)

print(f"Likely primes (need full test): {likely_primes}")
print(f"Likely composites (skip test):  {likely_composites}")

# Step 2: Only run expensive tests on likely_primes
actual_primes = [n for n in likely_primes if cdl.is_prime(n)]
```

### Performance Impact

**Without CDL prefilter:**
- Test all N candidates with full primality test
- Cost: N × O(√n) or worse

**With CDL prefilter:**
- Fast κ(n) screening: N × O(√n) for divisor counting
- Full test only on low-κ candidates: ~15% of N (based on prime density)
- Cost reduction: ~85% fewer expensive primality tests

### Rationale

**Why κ(n) helps:**
- Composites have higher divisor counts → higher κ
- Range-adaptive τ keeps the prefilter aligned with scale
- False negatives (primes called composite) are acceptable for a prefilter
- False positives (composites called prime) get caught by full test

**When to use:**
- Batch primality testing
- Prime enumeration over ranges
- Factorization algorithms that need prime candidates
- Any scenario where you can afford to skip testing obvious composites

### Example Results

```python
# Test on range 1000-1100
candidates = list(range(1000, 1101))
likely_primes, likely_composites = cdl.prime_diagnostic_prefilter(candidates)

# Results:
# - 101 candidates
# - 16 likely primes (need full test)
# - 85 likely composites (skip test)
# - Reduction: 84% fewer full tests
```

---

## Integration Port 1B: Cryptographic Key Generation

### Problem
RSA, Diffie-Hellman, and ECC key generation spend most of their search time on composite candidates that never need a full Miller-Rabin path.

### Solution with the Sweet-Spot Band
This integration port has moved to the standalone repository [`geodesic-prime-prefilter`](https://github.com/zfifteen/geodesic-prime-prefilter).

### Workflow
Use the standalone repository for the production package, benchmark scripts, and manual validation flow. CDL no longer ships the extracted prefilter implementation or its benchmark artifacts.

### Production Result

- Standalone repository: [`geodesic-prime-prefilter`](https://github.com/zfifteen/geodesic-prime-prefilter)
- Production package: `geodesic_prime_prefilter`
- Benchmarked result carried forward there: `2.09x` end-to-end speedup at `2048` bits and `2.82x` at `4096` bits

### Rationale

- The production implementation now evolves independently from the research repo.
- CDL remains the canonical home for `kappa`, `classify`, `z_normalize`, and the broader framework work.

### When to use

- Use the standalone repository when you need the production cryptographic prefilter.
- Use CDL directly when you need the canonical curvature primitives and research integrations.

---

## Integration Port 2: QMC/Factorization Sampling

### Problem
When exploring integer neighborhoods for factorization or quasi-Monte Carlo (QMC) sampling, you want to prioritize structurally simpler candidates that are more likely to yield useful information.

### Solution with κ(n)
Bias exploration toward low-κ candidates, treating them as "geodesics" in the integer space.

### Workflow

```python
import cdl

# Scenario: Factor large semiprime, need to sample candidates near √n
import math
n_to_factor = 1234567
sqrt_n = int(math.sqrt(n_to_factor))

# Generate candidate factors in a window
window = 100
candidates = list(range(sqrt_n - window, sqrt_n + window))

# Step 1: Sort candidates by κ(n) to prioritize low-curvature
biased_candidates = cdl.qmc_sampling_bias(
    candidates,
    bias_strength=0.8  # 0=no bias, 1=fully sorted by κ
)

# Step 2: Try factors in biased order
for candidate in biased_candidates[:20]:  # Try top 20 low-κ first
    if n_to_factor % candidate == 0:
        print(f"Found factor: {candidate}")
        break
```

### Sampling Strategy

**Standard QMC:** Uniform or random sampling
- No structural information
- All candidates treated equally

**κ-biased QMC:** Low-to-high κ sampling
- Prioritizes structurally simple numbers (primes and small composites)
- Matches the intuition that factors tend to be simpler than products
- Maintains QMC properties while adding geometric guidance

### Rationale

**Why κ(n) helps:**
- Factors of n tend to have lower κ than n itself
- Primes (κ ≈ 0.5-1.0) appear more frequently as factors
- High-κ numbers are products of many factors → less likely to be prime factors
- Geometric interpretation: factors are on "shorter paths" in number space

**When to use:**
- Factorization algorithms
- QMC integration over integer domains
- Candidate generation for cryptographic applications
- Exploring neighborhoods around target values

### Example Results

```python
# Factor n = 10403 = 101 × 103
candidates = list(range(90, 110))

# Without bias: Average position of factor 101 in random order ≈ 10
# With κ-bias: Factor 101 appears in top 3 (low κ due to being prime)

biased = cdl.qmc_sampling_bias(candidates, bias_strength=1.0)
print(f"Position of 101: {biased.index(101) + 1}")  # Output: 1 or 2
```

---

## Integration Port 3: Signal Normalization

### Problem
When comparing signals across different integer scales, raw values are dominated by magnitude rather than structural properties. This makes it hard to identify patterns that are scale-invariant.

### Solution with κ(n)
Apply Z-normalization to remove scale-dependent distortion and reveal underlying structure.

### Workflow

```python
import cdl

# Scenario: Analyzing mutation scores across different DNA sequence positions
# Raw scores are affected by position magnitude

# Step 1: Collect raw signal values
raw_signals = {
    100: 45.2,
    500: 203.8,
    1000: 389.4,
    5000: 1834.2,
    10000: 3621.9
}

# Step 2: Apply Z-normalization
normalized_signals = cdl.signal_normalize_pipeline(
    raw_signals,
    v=1.0  # Standard normalization strength
)

# Step 3: Compare normalized values (now scale-independent)
for n in sorted(raw_signals.keys()):
    raw = raw_signals[n]
    norm = normalized_signals[n]
    print(f"Position {n:5}: raw={raw:7.1f}, normalized={norm:7.2f}")
```

### Normalization Effects

**Z(n) = n / exp(v · κ(n))**

| n Type | κ(n) | Z-reduction | Effect |
|--------|------|-------------|--------|
| Small prime | ~0.3 | ~25% | Light correction |
| Large prime | ~1.0 | ~60% | Moderate correction |
| Small composite | ~2.0 | ~85% | Strong correction |
| Large composite | ~5.0 | ~99% | Very strong correction |

### Parameter Guidelines

**v = 0.5:** Light normalization
- Use when: Raw scale contains useful information
- Example: Time series where absolute position matters
- Effect: Gentle correction, preserves most scale information

**v = 1.0:** Standard normalization (recommended)
- Use when: Want balanced correction
- Example: General signal processing, diagnostics
- Effect: Significant correction, good separation

**v = 2.0:** Heavy normalization
- Use when: Scale is pure noise, only structure matters
- Example: Pattern detection, anomaly scoring
- Effect: Aggressive correction, emphasizes structural differences

### Rationale

**Why κ(n) helps:**
- Removes multiplicative scale bias
- Primes remain relatively stable (low correction)
- Composites compress more (high correction)
- Makes cross-range comparisons meaningful
- Variance reduction: 95-99% in typical applications
- Asymptotic priors from Sprint 4 give a scale-aware baseline for wide-range normalization

**If v is not known ahead of time:**
- Recover `v` from a calibration batch of observed `Z` values under the matching support prior
- Reuse that recovered `v` for the downstream normalization pass
- Record the prior used for recovery; wrong priors can shift the estimate

**When to use:**
- Signal processing across integer indices
- Feature engineering for ML models
- Comparing metrics at different scales
- Normalizing biological sequence scores
- Any domain where integer position affects signal

### Example Results

From baseline report (n=2-999):
- Raw signal variance: 8.87×10¹⁰
- Normalized variance: 6.90×10⁸
- **Variance reduction: 99.2%**

---

## Integration Port 4: Traversal-Rate Recovery and Process Fingerprinting

### Problem
In many workflows the traversal rate `v` is not known ahead of time. The project now implements a calibrated inverse path that recovers `v` from the distribution of observed `Z` values.

### Solution with `VRecovery`
Treat the observed `Z` sequence as a process signature. Once the support law is calibrated, recover `v` from moments, density, or a distributional fingerprint.

### Workflow

```python
import numpy as np
from v_recovery import VRecovery

# Scenario: observed Z outputs from a known random-support pipeline
observed_z = np.load("observed_z.npy")

recovery = VRecovery(
    calibration_n_max=10000,
    sample_size=len(observed_z),
    sequence_type="random",
    reference_trials=16,
    random_seed=321,
)

result = recovery.infer_v(observed_z, method="fingerprint")
print(f"Recovered v = {result.v_estimate:.4f} ± {result.confidence_half_width:.4f}")
```

### Calibration Rules

**What must match:**
- The support window or custom support values
- The sequence regime (`random`, `consecutive`, `prime_biased`, `composite_heavy`)
- The expected noise level well enough that the recovered distribution remains comparable

**What does not happen:**
- This does not recover unknown integers from isolated `Z` values
- This does not remove the need to state the prior

### Rationale

**Why recovery works:**
- `Z = n / exp(v · κ(n))` changes the full output distribution, not just one scalar
- Once the support prior is fixed, that distributional shape retains information about `v`
- The same observed `Z` sample can map to very different `v` values under mismatched priors, so prior declaration is load-bearing

### When to use
- Adaptive normalization when `v` is not known up front
- Participant profiling in perceptual or response experiments
- Auditing number-theoretic generators or samplers
- Detecting drift between two runs of the same pipeline
- Comparing whether two observed processes share the same traversal regime

### Example Results
- Integer-space recovery tests meet MLE `±0.05`, fingerprint `±0.10`, and moment-match `±0.10` tolerances
- Continuous-domain recovery meets fingerprint `±0.05`
- The deterministic cognitive pilot recovers participant `v` within `±0.15`

### Operational Note
If normalized outputs are exposed externally, they can reveal the traversal regime when the support law is known. That makes the channel useful for diagnostics and worth treating carefully in deployed pipelines.

---

## Integration Port 5: Continuous Signal Pipelines

### Problem
Some downstream workflows operate on real-valued coordinates or dense manifolds rather than exact integers.

### Solution with κ_smooth(x)
Use the smooth curvature surrogate:

```python
import cdl_continuous

x = 250000.5
kappa_value = cdl_continuous.kappa_smooth(x)
z_value = cdl_continuous.z_normalize_continuous(x, v=0.115)
label = cdl_continuous.hybrid_classify(x, tau=1.5, adaptive=True)
```

### Rationale

**Why κ_smooth(x) helps:**
- Preserves the large-scale curvature envelope derived from the average order of d(n)
- Keeps exact κ(n) available on integer points through the hybrid path
- Extends Z-normalization and v-recovery into continuous domains without changing the canonical integer contract

### When to use
- Continuous number-line or perceptual-scaling tasks
- Real-valued QMC pipelines
- Hybrid ML features spanning integer and non-integer coordinates

---

## Parameter Reference

### κ(n) Curvature
- **No parameters:** Deterministic computation
- **Range:** [0, ∞), typically 0.1-5.0 for n < 10K
- **Interpretation:** Higher = more structural complexity

### Threshold Classifier
- **threshold (τ):** Classification boundary
  - Default: 1.5 (83% seed accuracy, 88% holdout)
  - Range: 0.5-3.0 typical
  - Tune on seed set, validate on holdout
  
### Z-Normalization
- **v parameter:** Correction strength
  - v=0.5: Light (25-40% reduction)
  - v=1.0: Standard (60-85% reduction)  ← **Recommended**
  - v=2.0: Heavy (95-99% reduction)

---

## Performance Characteristics

### Computational Cost

| Operation | Complexity | Time (n < 1M) | Cache Benefit |
|-----------|------------|---------------|---------------|
| divisor_count(n) | O(√n) | < 1 ms | High |
| kappa(n) | O(√n) | < 1 ms | High |
| classify(n) | O(√n) | < 1 ms | High |
| z_normalize(n) | O(√n) | < 1 ms | High |

**Optimization tips:**
- Cache κ(n) values for repeated access
- Precompute for candidate sets
- Use batch functions for efficiency

### Memory Usage

- **Minimal:** κ(n) computed on-demand
- **Optional caching:** Dict[int, float] for hot paths
- **Batch operations:** Linear in number of candidates

---

## Best Practices

### 1. Threshold Selection
```python
# ✓ Good: Fit on seed, validate on holdout
primes_seed = [n for n in range(2, 50) if cdl.is_prime(n)]
composites_seed = [n for n in range(2, 50) if not cdl.is_prime(n)]
threshold, accuracy, _ = cdl.find_optimal_threshold(primes_seed, composites_seed)

# ✗ Bad: Tune on the same data you test on
```

### 2. Parameter Documentation
```python
# ✓ Good: Document v choice
def my_pipeline(data, v=1.0):
    """Process data with Z-normalization.
    
    Args:
        v: Normalization strength (1.0=standard, see INTEGRATION.md)
    """
    return cdl.signal_normalize_pipeline(data, v)

# ✗ Bad: Hidden magic number
normalized = {n: val / math.exp(1.5 * some_score) for n, val in data.items()}
```

### 3. Validation
```python
# ✓ Good: Report both raw and normalized metrics
print(f"Raw accuracy: {raw_acc:.1%}")
print(f"κ-filtered accuracy: {filtered_acc:.1%}")
print(f"Improvement: {filtered_acc - raw_acc:.1%}")

# ✗ Bad: Only report best-case results
```

---

## Error Handling

```python
import cdl

# Safe usage patterns
def safe_classify(n, threshold=1.5):
    """Classify with error handling."""
    if n < 2:
        return "invalid"
    try:
        return cdl.classify(n, threshold)
    except Exception as e:
        print(f"Error classifying {n}: {e}")
        return "error"

# Input validation
def validate_v_parameter(v):
    """Ensure v is in reasonable range."""
    if not (0.0 <= v <= 5.0):
        raise ValueError(f"v={v} outside recommended range [0, 5]")
    return v
```

---

## Summary

| Integration Port | Use Case | Key Benefit | Typical Speedup |
|-----------------|----------|-------------|-----------------|
| **Prime Diagnostics** | Prefilter before primality test | Fewer expensive tests | 5-10× faster |
| **QMC Sampling** | Bias exploration to low-κ | Better factor candidates | 2-3× fewer trials |
| **Signal Normalization** | Remove scale distortion | Variance reduction 99% | Stable comparisons |

**Key Principle:** κ(n) provides a simple, interpretable geometric signal that makes downstream tools agree more often and work more efficiently.

For detailed mathematics and validation results, see:
- `docs/specification/CDL_SPECIFICATION.md` - Core definitions and protocols
- `artifacts/reports/baseline_report.json` - Empirical validation data
- `src/python/cdl.py` - Reference implementation
