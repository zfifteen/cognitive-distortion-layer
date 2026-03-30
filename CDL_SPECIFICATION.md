# Cognitive Distortion Layer (CDL) Specification

**Version:** 1.0  
**Date:** 2025-11-05  
**Status:** Active

## Overview

The Cognitive Distortion Layer (CDL) provides a unified curvature signal κ(n) for analyzing integer structure across the Z Framework. It treats primes as "low-distortion geodesics" and composites as "high-distortion terrain," enabling consistent diagnostics, sampling, and normalization.

## Core Primitives

### 1. Curvature Signal: κ(n)

**Definition:**
```
κ(n) = d(n) · ln(n) / e²
```

**Components:**
- `d(n)`: Divisor count of n (σ₀(n))
- `ln(n)`: Natural logarithm of n
- `e²`: Normalization constant (≈ 7.389)

**Properties:**
- **Domain:** Positive integers n ≥ 2
- **Range:** [0, ∞)
- **Deterministic:** Same input → same output
- **Monotonic within class:** κ grows with ln(n) for fixed divisor count

**Interpretation:**
- Low κ(n) → Structurally simple (prime-like)
- High κ(n) → Structurally complex (composite-like)
- κ tracks "how jagged" an integer is geometrically

**Empirical Baseline (n = 2–49):**
- Prime average: ~0.739
- Composite average: ~2.252
- Separation ratio: ~3.05×

### 2. Threshold Classifier

**Function:**
```
classify(n, threshold) → {"prime", "composite"}
```

**Protocol:**
1. Compute κ(n)
2. Compare to threshold τ
3. Return "prime" if κ(n) < τ, else "composite"

**Default Threshold:**
- τ = 1.5 (yields ~83% accuracy on seed set)

**Configuration:**
- Threshold can be tuned per range/task
- Fit on seed set, validate on hold-out
- Report precision, recall, ROC metrics

**Use Cases:**
- Fast prefilter before expensive primality tests
- Candidate ranking in factorization
- Structural anomaly detection

### 3. Z-Normalization

**Definition:**
```
Z(n) = n / exp(v · κ(n))
```

**Parameters:**
- `n`: Integer to normalize
- `v`: Task-specific scale parameter
- `κ(n)`: Curvature of n

**Parameter Guidelines:**
- `v = 1.0`: Standard normalization (diagnostics)
- `v = 0.5`: Light correction (QMC sampling)
- `v = 2.0`: Heavy correction (signal pipelines)

**Purpose:**
- Convert structural distortion into geometric correction
- Make signals comparable across scales
- Stabilize downstream metrics

**Properties:**
- Z(n) ≤ n (normalization reduces value)
- Stronger correction for high-κ numbers
- Preserves ordering within low-κ neighborhoods

## Integration Ports

### Prime Diagnostics Prefilter

**Workflow:**
1. Compute κ(n) for candidate n
2. If κ(n) < threshold: "likely prime" → run full primality test
3. If κ(n) ≥ threshold: "likely composite" → skip or deprioritize

**Benefit:** Reduces expensive tests on obvious composites

### QMC/Factorization Sampling

**Workflow:**
1. Generate candidate set {n₁, n₂, ..., nₖ}
2. Compute κ(nᵢ) for each candidate
3. Sort by κ (ascending)
4. Bias exploration toward low-κ candidates first

**Benefit:** Prioritizes structurally simpler regions

### Signal Normalization

**Workflow:**
1. Collect raw signal values at {n₁, n₂, ..., nₖ}
2. Apply Z-normalization: Zᵢ = Z(nᵢ)
3. Use {Z₁, Z₂, ..., Zₖ} as stable feature scale

**Benefit:** Removes scale-dependent noise, improves cross-range comparisons

## Validation Protocol

### Seed Set (n = 2–49)
- **Purpose:** Smoke test, baseline establishment
- **Metrics:** Mean κ by class, separation ratio, threshold accuracy
- **Expected:** Prime ~0.739, Composite ~2.252, Accuracy ~83%

### Hold-Out Set (n = 50–10,000)
- **Purpose:** Out-of-sample validation
- **Protocol:** 
  1. Fit threshold on seed only
  2. Apply to hold-out without tuning
  3. Report accuracy, precision, recall, confusion matrix
- **Expected:** Similar separation pattern, accuracy ≥ 75%

### Ablation Study
- **Purpose:** Measure Z-normalization impact
- **Protocol:**
  1. Run pipeline with Z-normalization (v > 0)
  2. Run identical pipeline with Z-normalization off (v = 0)
  3. Compare downstream metric variance
- **Expected:** Z-normalized version shows lower variance

### Stability Check
- **Purpose:** Verify monotonic behavior within classes
- **Protocol:**
  1. Group numbers by divisor count
  2. Plot κ(n) vs ln(n) within each group
  3. Verify linear trend (no wild swings)
- **Expected:** Clean linear relationship within d(n) classes

### Computational Budget
- **Purpose:** Understand performance scaling
- **Protocol:**
  1. Time κ(n) computation for n ∈ {100, 1K, 10K, 100K}
  2. Report operations count (divisor enumeration strategy)
  3. Compare cached vs non-cached performance
- **Expected:** O(√n) per computation, sub-millisecond for n < 1M

## Acceptance Criteria

✓ This specification document exists  
✓ Baseline report reproduces seed results  
✓ Hold-out validation shows consistent separation  
✓ Integration notes document three use cases  
✓ All parameters and thresholds are documented  
✓ No hidden heuristics in code comments  

## Guardrails

- **No overfitting:** Thresholds fit on seed only, validated on hold-out
- **No hidden magic:** All parameters explicitly documented
- **Reproducibility:** Same inputs → same outputs, deterministic
- **Transparency:** Clear rationale for each integration use case
- **Performance:** κ computation scoped to candidate windows, cached aggressively

## Risk Management

| Risk | Mitigation |
|------|------------|
| Small-n bias | Treat seed as smoke test only; require hold-out confirmation |
| Range drift | Publish fit-on-seed protocol; make threshold shifts visible |
| d(n) cost | Scope computation to prefilter windows; cache aggressively |
| Parameter confusion | Document v per task; provide clear guidelines |

## Future Extensions

- Multi-scale threshold maps (adaptive per range)
- Cached divisor lookups for hot paths
- Integration with ML-based primality classifiers
- Cross-framework signal harmonization

---

**Contract:** Same inputs → same outputs. All parameters written down. No surprises.
