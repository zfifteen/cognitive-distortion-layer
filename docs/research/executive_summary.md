# Executive Summary: Curvature and Perception in Mathematics

## Overview

This research introduces a novel computational framework for understanding cognitive distortions in mathematical number perception using geometry-inspired curvature models. The work demonstrates that prime numbers exhibit minimal "cognitive curvature" while composite numbers show increasingly complex distortion patterns.

## Key Findings

### 1. Prime Numbers as Cognitive Geodesics
- **Prime numbers show 3.09× lower curvature** than composite numbers (0.739 vs 2.279 average)
- **22.4× lower perceptual distortion** under standard conditions (32.7 vs 731.1 average)
- Primes consistently cluster in the minimal-curvature region, supporting their role as fundamental mathematical building blocks

### 2. Composite Number Complexity Scaling
- **Highly composite numbers show extreme curvature** (up to 5.239 for n=48)
- **Numbers with rich factorizations** (48, 36, 42, 40, 30) dominate the high-curvature regime
- Curvature correlates strongly with divisor density and structural complexity

### 3. Cognitive Load Effects
- **Systematic amplification** of distortion under increasing cognitive load
- **347% increase** in average distortion from baseline (0.0) to high load (0.7)
- **Preserved relative ordering** between primes and composites across all load levels

### 4. Traversal-Rate Recovery
- **Traversal rate is recoverable** from observed `Z` sequences once the support prior is calibrated
- **Implemented recovery methods** include moment matching, MLE, and a 20-dimensional distributional fingerprint
- The framework therefore measures both integer structure and process regime

### 5. Machine Learning Validation
- **99.5% classification accuracy** using raw curvature features for prime/composite distinction
- **Simple threshold methods** achieve ~83% accuracy based on curvature alone
- Framework provides practical tools for automated mathematical classification

## Mathematical Framework

The core innovation is the cognitive curvature function:

```
κ(n) = d(n) · ln(n) / e²
```

Where d(n) is the divisor count and ln(n) provides magnitude scaling. This captures the intuitive notion that numbers with more divisors and larger magnitude impose greater cognitive burden.

## Practical Applications

### Education
- **Curriculum sequencing**: Introduce low-curvature concepts first
- **Difficulty assessment**: Quantitative measures for problem complexity
- **Adaptive learning**: Systems that account for cognitive load

### Algorithm Design
- **Prime generation**: Exploit structural regularity patterns
- **Factorization approaches**: Based on divisor density analysis
- **Feature engineering**: Curvature-based representations for ML

### Calibration and Auditing
- **Adaptive normalization**: Recover `v` before applying `Z` in unknown-rate settings
- **Process fingerprinting**: Distinguish generators or samplers by their `Z`-distribution geometry
- **Participant inference**: Treat `v` as a measurable property of observed response traces

### Artificial Intelligence
- **Mathematical reasoning**: Cognitive load modeling in AI systems
- **Biomimetic approaches**: Human-like mathematical intuition
- **Classification systems**: Enhanced number-theoretic tasks

## Technical Implementation

The complete framework is implemented in Python with:
- `src/python/cdl.py` for canonical curvature, classification, and Z-normalization
- `src/python/v_recovery.py` for calibrated traversal-rate recovery
- `src/python/cdl_continuous.py` for continuous-domain recovery transfer
- `src/python/cognitive_pilot.py` for participant-level inference from observed traces

## Impact and Significance

This work bridges pure mathematics, cognitive science, and computational modeling by:

1. **Providing quantitative measures** for mathematical complexity intuition
2. **Validating geometric approaches** to discrete mathematical structures
3. **Enabling practical applications** in education and algorithm design
4. **Opening an inverse research direction** in which traversal rate becomes an observable

## Future Directions

- **Extended range studies** for larger numbers and special classes
- **Cross-cultural validation** of cognitive curvature patterns
- **Prior-robust recovery** and joint inference of support law with `v`
- **Divisor-family fixed-point studies** beyond the prime band
- **Theoretical connections** to analytic number theory

## Conclusion

The curvature-based framework successfully quantifies the cognitive experience of mathematical number processing, providing both theoretical insights and practical tools. Prime numbers emerge as natural "geodesics" in mathematical space, while composite numbers create increasingly complex cognitive landscapes. The implemented recovery path shows that traversal rate is not only a user choice but also a measurable property of observed distortion patterns when the support regime is calibrated. This geometric perspective opens new avenues for understanding the intersection of mathematics, cognition, and computation.

---

*For complete technical details, experimental data, and implementation code, see the full white paper and accompanying computational framework.*
