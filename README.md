# Cognitive Model: Curvature Diagnostics and Traversal-Rate Recovery for Number-Theoretic Distortion

![Cognitive Distortion Layer Banner](assets/readme-banners/banner.png)

## Overview

This repository presents a theoretical and computational framework for analyzing discrete integer sequences through a geometry-inspired curvature model. By drawing a pedagogical analogy to relativistic distortions, it defines a **forward diagnostic map** that highlights structural irregularities—especially those arising from divisor density—and a calibrated recovery path that infers traversal rate `v` from observed `Z` sequences under an explicit support prior. The model remains **pointwise forward in n** and does not perform blind inversion of unknown integers, but it is now **distributionally inverse in v** when the source regime is calibrated.

**🆕 The Cognitive Distortion Layer (CDL)** standardizes κ(n) as the shared curvature signal across the Z Framework, providing unified primitives for prime diagnostics, QMC sampling, and signal normalization. Source modules now live under [`src/python/`](src/python), with specifications in [`docs/specification/CDL_SPECIFICATION.md`](docs/specification/CDL_SPECIFICATION.md) and [`docs/specification/INTEGRATION.md`](docs/specification/INTEGRATION.md).

## Key Concepts

1. **Curvature Function**

   $$
   \kappa(n) = \frac{d(n) \cdot \ln(n)}{e^2}
   $$

   * **d(n)**: Divisor count of $n$ (i.e., $\sigma_0(n)$).
   * **ln(n)**: Natural logarithm of $n$.
   * **Normalization**: Constant $e^2$ determined empirically.
   * **Interpretation**: Higher divisor counts and larger values yield greater local "curvature".

2. **Distortion Mapping (Forward Model)**

   $$
   \Delta_n = v \cdot \kappa(n)
   $$

   * **v**: A traversal-rate parameter. In forward use it may be user-supplied. In recovery use it is inferred from observed `Z` values relative to a calibrated support prior.
   * **$\Delta_n$**: Modeled distortion at $n$.
   * **Purpose**: Encodes how rapid progression through integers skews apparent structure.

3. **Perceived Value**

   $$
   n_{\text{perceived}} = n \times \exp\bigl(\Delta_n\bigr)
   $$

   * Applies exponential scaling to the true integer based on $\Delta_n$.
   * Emphasizes how distortion amplifies structural irregularities in composites.

4. **Z-Transformation (Context-Dependent Normalization)**

   $$
   Z(n) \;=\; \frac{n}{\exp\bigl(v \cdot \kappa(n)\bigr)}
   $$

   * **Pointwise forward in $n$**: Assumes knowledge of $n$ and $v$ to normalize a specific integer.
   * **Distributionally inverse in $v$**: Under a calibrated support or sequence prior, observed `Z` values recover traversal rate through moment matching, MLE, or distributional fingerprints.
   * **Outcome**: Reveals underlying structural stability and exposes the process regime that generated the observed distortion pattern.

## Empirical Validation

* **Prime vs. Composite Curvature (n = 2–49)**

  * Prime average curvature: \~0.739
  * Composite average curvature: \~2.252
  * Ratio: Composites ≈3.05× higher curvature

* **Classification Test**

  * Simple threshold on $\kappa(n)$ yields \~83% accuracy distinguishing primes from composites.

These results demonstrate that primes appear as "minimal-curvature geodesics" within the discrete sequence, providing a quantitative diagnostic measure of number complexity.

## Implementation

* **Language**: Python 3
* **Source Layout**:

  * `src/python/cdl.py`: Canonical CDL primitives
  * `src/python/cdl_continuous.py`: Continuous-domain CDL extensions
  * `src/python/v_recovery.py`: Traversal-rate inference
  * `src/python/cognitive_pilot.py`: Sprint 6 cognitive pilot pipeline

* **Repository Layout**:

  * `docs/`: Specifications, summaries, roadmap, and concept notes
  * `data/`: Reference data and generated simulation traces
  * `artifacts/`: Generated reports and figures
  * `experiments/`: Research sprint outputs and benchmarks
  * `scripts/`: Demo, dashboard, report, and reproduction utilities
  * `tests/`: Reorganized pytest suite

### Quick Start with CDL

The Cognitive Distortion Layer provides production-ready primitives:

```python
import cdl

# Core primitive 1: Curvature signal
kappa_value = cdl.kappa(17)  # Returns κ(n)

# Core primitive 2: Threshold classifier
classification = cdl.classify(17, threshold=1.5)  # "prime" or "composite"

# Core primitive 3: Z-normalization
z_value = cdl.z_normalize(17, v=1.0)  # Returns Z(n)

# Integration helpers
likely_primes, likely_composites = cdl.prime_diagnostic_prefilter(candidates)
biased_candidates = cdl.qmc_sampling_bias(candidates, bias_strength=0.8)
normalized_signals = cdl.signal_normalize_pipeline(raw_signals, v=1.0)
```

**See [`docs/specification/INTEGRATION.md`](docs/specification/INTEGRATION.md) for complete integration examples.**

### Quick Start with Traversal-Rate Recovery

The distributional recovery path treats `v` as an observable once the source regime is calibrated:

```python
import numpy as np
from v_recovery import VRecovery, generate_z_sequence

rng = np.random.default_rng(321)
recovery = VRecovery(
    calibration_n_max=3000,
    sample_size=500,
    sequence_type="random",
    reference_trials=10,
    random_seed=321,
)

z_sequence, _ = generate_z_sequence(
    numbers=recovery.numbers,
    kappas=recovery.kappas,
    rng=rng,
    v=1.5,
    sample_size=500,
    sequence_type="random",
    prime_mask=recovery.prime_mask,
)

estimate = recovery.infer_v(z_sequence, method="fingerprint")
print(estimate.v_estimate)
```

The same recovery path is used in `src/python/cognitive_pilot.py` to recover participant-level `v` values from observed response traces.

### Deterministic Cryptographic Prime Generation

The geodesic prime prefilter has moved to the standalone repository [`geodesic-prime-prefilter`](https://github.com/zfifteen/geodesic-prime-prefilter).

CDL remains the research home for the core curvature primitives and the broader Z Framework. The standalone repository now carries the production Python package, golden vectors, manual validation flow, and the multi-language porting surface for the prefilter.

### Quick Start with Self-Contained Gist

The standalone gist lives at `scripts/demos/curvature_gist.py` and has **only numpy** as a dependency:

```bash
# Basic usage (n = 2-50, default parameters)
python scripts/demos/curvature_gist.py

# Extended analysis with 10,000 numbers
python scripts/demos/curvature_gist.py --max-n 10000

# Custom v-parameter for Z-transformation
python scripts/demos/curvature_gist.py --max-n 1000 --v-param 0.5

# Fewer bootstrap samples for faster execution
python scripts/demos/curvature_gist.py --max-n 100 --bootstrap-samples 500
```

**Key Features**:
- Instant computation for custom n ranges
- Built-in primality checks and bootstrap CI reporting
- Extensible v-parameter tuning for Z-normalization
- Outputs `data/reference/kappas.csv` with (n, κ(n), Z(n)) data
- ~83% classification accuracy for prime vs composite

The gist can also be imported as a module:

### Full Model Example

```bash
# Run complete cognitive model with visualizations
python scripts/demos/main.py
```

Generates curvature statistics, writes figures into `artifacts/figures/`, and writes CSV traces into `data/simulated/`.

### Validation & Testing

```bash
# Run CDL test suite
python tests/test_suite.py

# Generate baseline validation report
python scripts/reports/baseline_report.py

# Generate visualization dashboards
python scripts/dashboards/generate_cdl_dashboards.py

# Run the full Sprint 1–6 local reproduction
python scripts/reproduce_sprints.py
```

**Validation Results:**
- Seed set (n=2-49): Prime avg κ = 0.739, Composite avg κ = 2.252, Accuracy = 83.7%
- Hold-out (n=50-10K): Accuracy = 88.2%, maintains separation pattern
- Z-normalization: 99.2% variance reduction
- v recovery: integer-space tests meet MLE `±0.05`, fingerprint `±0.10`, and moment-match `±0.10` tolerances; continuous recovery meets fingerprint `±0.05`; the deterministic cognitive pilot recovers participant `v` within `±0.15`
- All acceptance criteria met ✓

The baseline report is written to `artifacts/reports/baseline_report.json`.

## Limitations & Scope

1. **No Standalone Inverse for Unknown Integers**

   * The Z-transformation **requires** known $n$ and rate $v$ for pointwise normalization. It **does not** recover unknown integers from isolated observed values.
2. **Distributional Recovery Requires Calibration**

   * Traversal rate `v` is recoverable from observed `Z` sequences only relative to an explicit support prior or calibrated sequence regime. Prior mismatch can shift the recovered value.
3. **Process Channel Exposure**

   * Because `Z` distributions retain information about `v`, normalized outputs can fingerprint the generating or perceptual pipeline when the support law is known.
4. **Metaphorical Analogy**

   * References to relativity and geodesics are pedagogical. The core mathematics stands independently of physical interpretations.

## Future Directions

* **Prior-Robust Recovery**: Infer `v` reliably when the support law is only partially known, and characterize identifiability under prior mismatch.
* **Process Fingerprinting**: Use recovered `v` and `Z` fingerprints to audit samplers, detect drift, and compare generation regimes.
* **Divisor-Family Resonances**: Characterize the fixed-point law `v = e^2 / d` across exact divisor-count families beyond the prime `d = 2` band.
* **Enhanced Classification**: Integrate curvature features into machine-learning classifiers for primality testing.
* **Theoretical Extensions**: Investigate connections between divisor-based curvature and deeper analytic number theory.
