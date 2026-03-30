# Discrete Curvature κ(n) Gist

Self-contained Python snippet for computing discrete curvature and Z-transformation with bootstrap CI analysis for prime vs composite classification.

## Overview

This gist implements the core **κ(n) curvature signal** and **Z-transformation** from cognitive-number-theory, enabling forward diagnostics for prime/composite patterns with empirical validation.

### Key Metrics

- **Primes**: avg κ ≈ 0.739
- **Composites**: avg κ ≈ 2.252  
- **Ratio**: ~3.05× (composites have >2× higher curvature)
- **Classification Accuracy**: ~83% using threshold-based method

## Requirements

- Python 3.6+
- numpy (only dependency)

```bash
pip install numpy
```

## Quick Start

### As a Command-Line Tool

```bash
# Basic usage (n = 2-50)
python curvature_gist.py

# Extended analysis
python curvature_gist.py --max-n 10000

# Custom v-parameter for Z-transformation
python curvature_gist.py --max-n 1000 --v-param 0.5

# Control bootstrap samples
python curvature_gist.py --bootstrap-samples 500
```

### As a Module

```python
import curvature_gist as cg

# Compute curvature for specific numbers
kappa_7 = cg.kappa(7)      # Prime: low curvature (~0.527)
kappa_12 = cg.kappa(12)    # Composite: high curvature (~1.785)

# Z-transformation
z_value = cg.z_transform(10, v=1.0)

# Check primality
is_prime_7 = cg.is_prime(7)  # True

# Run full analysis
results = cg.run_analysis(max_n=100, v_param=1.0, n_bootstrap=1000)
cg.print_results(results)
```

## Core Functions

### `divisor_count(n)`
Returns the number of divisors of n.

```python
divisor_count(12)  # Returns 6 (divisors: 1,2,3,4,6,12)
```

### `kappa(n)`
Computes discrete curvature: **κ(n) = d(n) × ln(n) / e²**

```python
kappa(7)   # ~0.527 (prime, low curvature)
kappa(12)  # ~1.785 (composite, high curvature)
```

### `z_transform(n, v=1.0)`
Z-transformation for normalization: **Z(n) = n / exp(v × κ(n))**

```python
z_transform(10, v=1.0)  # ~2.875
z_transform(10, v=0.5)  # ~5.369 (lower v = less normalization)
```

### `is_prime(n)`
Simple primality test.

```python
is_prime(7)   # True
is_prime(12)  # False
```

### `bootstrap_ci(data, n_resamples=1000, confidence=95)`
Bootstrap confidence interval for the mean.

```python
data = [1.0, 2.0, 3.0, 4.0, 5.0]
ci = bootstrap_ci(data)  # Returns (lower, upper) bounds
```

### `classify_by_curvature(kappa_value, threshold=1.5)`
Classify as 'prime' or 'composite' based on curvature threshold.

```python
classify_by_curvature(0.5)  # 'prime'
classify_by_curvature(2.0)  # 'composite'
```

### `run_analysis(max_n=50, v_param=1.0, n_bootstrap=1000, output_csv=True)`
Run comprehensive analysis and return results dictionary.

## Output Format

### Console Output

```
======================================================================
COGNITIVE NUMBER THEORY: CURVATURE ANALYSIS
======================================================================

Dataset: n = 2 to 50
  - Primes: 15
  - Composites: 34

Average Curvature κ(n):
  - Primes:     0.739
  - Composites: 2.279
  - Ratio:      3.08x

95% Bootstrap Confidence Intervals:
  - Prime avg κ:     [0.609, 0.856]
  - Composite avg κ: [1.924, 2.664]

Classification Performance:
  - Threshold: κ = 1.5
  - Accuracy:  83.7%

Z-Transformation Parameter:
  - v = 1.0
======================================================================
```

### CSV Output

File: `kappas.csv`

```csv
n,kappa,z_transform
2,0.187614540011479,1.6578683332273354
3,0.297362010508244,2.228325213912176
4,0.562843620034438,2.2783482782867606
...
```

## Command-Line Options

```
--max-n MAX_N              Maximum n to analyze (default: 50)
--v-param V_PARAM          v-parameter for Z-transformation (default: 1.0)
--bootstrap-samples N      Number of bootstrap resamples (default: 1000)
--no-csv                   Skip CSV output
```

## Theory

The discrete curvature κ(n) quantifies the "complexity" of an integer based on its divisor structure:

- **Primes** have minimal divisors (only 1 and n), yielding low curvature
- **Composites** have more divisors, resulting in higher curvature
- This creates a natural "geodesic" interpretation where primes are minimal-curvature paths

### Mathematical Definition

```
κ(n) = d(n) × ln(n) / e²

where:
  - d(n) = divisor count of n
  - ln(n) = natural logarithm
  - e² ≈ 7.389 (normalization constant)
```

### Z-Transformation

```
Z(n) = n / exp(v × κ(n))

where:
  - v = traversal rate parameter
  - κ(n) = discrete curvature
```

This transformation normalizes for the curvature distortion, revealing underlying structural patterns.

## Use Cases

1. **Number Classification**: Distinguish primes from composites with ~83% accuracy
2. **Structural Analysis**: Quantify complexity of integer sequences
3. **Educational Tool**: Demonstrate connections between divisor theory and geometry
4. **Research**: Explore alternative primality metrics and classification methods

## Citation

If you use this in research, please cite:

```
Cognitive Number Theory: A Forward Diagnostic Framework for Number-Theoretic Distortion
GitHub: zfifteen/cognitive-number-theory
```

## License

See repository LICENSE file.
