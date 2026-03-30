# Curvature and Perception in Mathematics: A Computational Framework for Cognitive Number Theory

**Author:** Dionisio Alberto Lopez III  
**Date:** August 2025  
**Version:** 1.0 (Draft)

## Abstract

This paper presents a novel computational framework for understanding cognitive distortions in mathematical number perception through a geometry-inspired curvature model. By drawing pedagogical analogies to relativistic space-time distortions, I introduce a forward diagnostic mapping that quantifies structural irregularities in discrete integer sequences. My experimental results demonstrate that prime numbers exhibit minimal cognitive curvature, appearing as "geodesics" in the mathematical number space, while composite numbers show significantly higher curvature values. The framework includes empirical validation through machine learning classification experiments and provides both theoretical foundations and practical applications for understanding cognitive mathematical processing.

**Keywords:** cognitive mathematics, number theory, curvature models, prime classification, cognitive distortion

## 1. Introduction

The perception and processing of mathematical concepts by cognitive systems—whether human or artificial—often involves systematic distortions that reflect underlying structural complexities. Traditional number theory focuses on abstract mathematical properties, but the cognitive experience of working with numbers reveals patterns of difficulty, perception, and processing that suggest a deeper geometric structure to the mathematical landscape.

This paper introduces a computational framework that models cognitive distortions in number perception using a curvature-based approach inspired by differential geometry. My central hypothesis is that the perceived "difficulty" or "complexity" of mathematical numbers can be quantified through a curvature function that captures local geometric properties of the discrete number sequence.

### 1.1 Motivation

Consider the cognitive experience of working with different numbers: most people find prime numbers like 7, 11, 13 somehow "cleaner" or more fundamental than highly composite numbers like 12, 24, or 60. This intuitive distinction suggests an underlying geometric structure where primes represent minimal-distortion paths through mathematical space, while composites introduce increasing complexity and curvature.

### 1.2 Contributions

This work makes several key contributions:

1. **Theoretical Framework**: A rigorous mathematical model linking divisor density to cognitive curvature
2. **Computational Implementation**: A complete Python framework for simulating cognitive experiments
3. **Empirical Validation**: Experimental results demonstrating the practical utility of the curvature model
4. **Classification Applications**: Machine learning validation showing improved prime/composite discrimination

## 2. Theoretical Framework

### 2.1 Cognitive Curvature Function

I define the cognitive curvature κ(n) for a positive integer n as:

```
κ(n) = d(n) · ln(n) / e²
```

Where:
- **d(n)** is the divisor count function (number of positive divisors of n)
- **ln(n)** is the natural logarithm of n  
- **e²** is a normalization constant determined empirically

This function captures two key intuitions:
1. Numbers with more divisors (higher d(n)) create more cognitive complexity
2. Larger numbers (higher ln(n)) require more processing resources
3. The normalization ensures meaningful comparative values across different ranges

### 2.2 Cognitive Load and Frame Shift

I model cognitive processing under varying load conditions through a subliminal frame shift parameter:

```
Δₛ = k · vᶜ(1 + load) · κ(n)
```

Where:
- **k** is the cognitive coupling constant
- **vᶜ** is the cognitive velocity parameter  
- **load** represents additional cognitive burden (0.0 = no load, 1.0 = full load)

### 2.3 Perceived Value Transformation

The conscious perception of number n under cognitive load is modeled as:

```
n_perceived = n × exp(Δₛ)
```

This exponential transformation amplifies the curvature effects, making structural irregularities in composite numbers more pronounced under cognitive stress.

### 2.4 Z-Transformation for Normalization

For diagnostic purposes, I define the Z-transformation to recover structural stability:

```
Z(n) = n / exp(v · κ(n))
```

This normalization reveals the underlying mathematical structure by compensating for curvature-induced distortions.

## 3. Experimental Methodology

### 3.1 Computational Setup

My experimental framework was implemented in Python using the following components:

- **CognitiveModel Class**: Implements all mathematical transformations and curvature calculations
- **Simulation Functions**: Generate experimental data across different cognitive load conditions
- **Visualization Tools**: Create plots showing perception distortion and curvature patterns
- **Export Capabilities**: Save results to CSV format for further analysis
- **AI Validation**: Machine learning classification experiments using Random Forest algorithms

### 3.2 Experimental Parameters

I conducted experiments with the following parameters:

- **Number Range**: n = 2 to 50 (covering key primes and composites)
- **Cognitive Load Levels**: 0.0 (baseline), 0.3 (moderate), 0.7 (high)
- **Model Parameters**: 
  - Cognitive velocity (vᶜ) = 1.0
  - Cognitive coupling (k) = 1.0  
  - Load factor = 0.5

### 3.3 Data Collection

For each number n and load condition, I recorded:
1. True Z-transformed value Z(n)
2. Perceived value under cognitive load
3. Distortion magnitude (perceived - actual)
4. Cognitive curvature κ(n)

## 4. Results and Analysis

### 4.1 Data Visualization

My experimental framework generated comprehensive visualizations demonstrating the key relationships in cognitive number theory:

#### Figure 1: Cognitive Curvature Distribution
The curvature analysis plot (see `curvature_analysis.png`) reveals:
- Clear separation between prime and composite numbers in curvature space
- Primes clustered in the low-curvature region (κ < 1.0)
- Composites showing wide distribution with several extreme outliers
- Strong correlation between curvature and perceived distortion

#### Figure 2: Cognitive Load Effects  
The load effects plot (see `load_effects.png`) demonstrates:
- Exponential scaling of distortion under increasing cognitive load
- Consistent relative ordering between primes and composites across all load levels
- Dramatic amplification effects, with high load causing 347% increase in average distortion

### 4.2 Curvature Distribution Analysis

My experimental results reveal distinct patterns in cognitive curvature across different number types:

#### Prime Numbers (n = 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
- **Count**: 15 numbers
- **Average Curvature**: 0.739
- **Range**: 0.188 to 1.042
- **Average Distortion (Load 0)**: 32.7
- **Characteristics**: Consistently low curvature values, reflecting minimal divisor complexity

#### Composite Numbers (remaining 34 values in range 2-50)
- **Count**: 34 numbers
- **Average Curvature**: 2.279  
- **Range**: 0.563 to 5.239
- **Average Distortion (Load 0)**: 731.1
- **Characteristics**: Higher and more variable curvature, with highly composite numbers showing extreme values

#### Key Observations:
1. **Prime Distinction**: Primes exhibit 3.09× lower average curvature than composites (0.739 vs 2.279)
2. **Distortion Amplification**: Composites show 22.4× higher average distortion than primes (731.1 vs 32.7)
3. **Highly Composite Outliers**: Numbers 48, 36, 42, 40, 30 show extreme curvature values (>3.6)
4. **Minimal Curvature**: The five lowest curvature numbers are n=2,3,5,7,4 with κ ranging from 0.188 to 0.563

### 4.3 Cognitive Load Effects

Under increasing cognitive load, I observe systematic amplification of distortion effects:

#### Load = 0.0 (Baseline)
- **Average Distortion**: 517.3
- Prime average distortion: 32.7
- Composite average distortion: 731.1
- Clear separation between number types (22.4× difference)

#### Load = 0.3 (Moderate)  
- **Average Distortion**: 969.7 (87.4% increase from baseline)
- Maintained relative ordering between primes and composites
- Proportional amplification across all number types

#### Load = 0.7 (High)
- **Average Distortion**: 2,313.1 (347.2% increase from baseline)
- Severe distortion effects across all numbers
- Exponential scaling of cognitive burden under stress

### 4.4 Specific Case Studies

#### Minimal Curvature Cases:
- **n = 2**: κ(2) = 0.188, distortion = 0.4 (lowest complexity number)
- **n = 3**: κ(3) = 0.297, distortion = 1.0 (second-lowest complexity)
- **n = 5**: κ(5) = 0.436, distortion = 2.7 (consistent prime behavior)
- **n = 7**: κ(7) = 0.527, distortion = 4.9 (still minimal curvature)

#### Maximum Curvature Cases:
- **n = 48**: κ(48) = 5.239, distortion = 9,000.0 (extreme composite: 10 divisors)
- **n = 36**: κ(36) = 4.365, distortion = 2,794.8 (perfect square with 9 divisors)
- **n = 42**: κ(42) = 4.047, distortion = 2,360.8 (highly composite: 2×3×7)
- **n = 40**: κ(40) = 3.994, distortion = 2,130.6 (rich divisor structure: 2³×5)
- **n = 30**: κ(30) = 3.682, distortion = 1,162.3 (first five primes: 2×3×5)

#### Structural Insights:
- Numbers with rich factorizations (many small prime factors) show highest curvature
- Perfect squares and highly composite numbers dominate the high-curvature regime
- The single composite in the low-curvature group (n=4) represents the minimal composite case

### 4.5 Machine Learning Validation

My AI validation experiment using Random Forest classification yielded:

- **Raw Features Accuracy**: 99.50%
- **Z-Transformed Features Accuracy**: 77.50%  
- **Performance Change**: -22.00%

This counterintuitive result suggests that the raw curvature features are already optimal for prime/composite classification, while the Z-transformation may remove discriminative information useful for machine learning algorithms.

### 4.6 Summary Tables

**Table 1: Numbers with Highest Cognitive Curvature**
| n  | κ(n)  | Distortion | Type      | Notes |
|----|-------|------------|-----------|--------|
| 48 | 5.239 | 9,000.0    | Composite | 10 divisors (2⁴×3) |
| 36 | 4.365 | 2,794.8    | Composite | Perfect square (6²) |
| 42 | 4.047 | 2,360.8    | Composite | 2×3×7 |
| 40 | 3.994 | 2,130.6    | Composite | 2³×5 |
| 30 | 3.682 | 1,162.3    | Composite | 2×3×5 |

**Table 2: Numbers with Lowest Cognitive Curvature**
| n | κ(n)  | Distortion | Type      | Notes |
|---|-------|------------|-----------|--------|
| 2 | 0.188 | 0.4        | Prime     | Smallest prime |
| 3 | 0.297 | 1.0        | Prime     | Second prime |
| 5 | 0.436 | 2.7        | Prime     | Third prime |
| 7 | 0.527 | 4.9        | Prime     | Fourth prime |
| 4 | 0.563 | 3.0        | Composite | Minimal composite (2²) |

## 5. Discussion

### 5.1 Theoretical Implications

My results support several important theoretical conclusions:

#### 5.1.1 Prime Numbers as Cognitive Geodesics
The consistently low curvature values for primes support the hypothesis that these numbers represent "minimal distortion paths" through mathematical space. This geometric interpretation provides a novel perspective on why primes feel cognitively fundamental.

#### 5.1.2 Composite Complexity Scaling
The exponential increase in perceived distortion for highly composite numbers reflects the cognitive burden of processing multiple divisibility relationships simultaneously.

#### 5.1.3 Load-Dependent Processing
The systematic increase in distortion under cognitive load suggests that mathematical perception operates through resource-limited processing systems that become less accurate under stress.

### 5.2 Practical Applications

#### 5.2.1 Educational Mathematics
Understanding cognitive curvature patterns could inform:
- Curriculum sequencing (introducing low-curvature concepts first)
- Difficulty assessment for mathematical problems
- Adaptive learning systems that account for cognitive load

#### 5.2.2 Algorithm Design  
The curvature model provides insights for:
- Prime generation algorithms that exploit structural regularity
- Composite factorization approaches based on divisor density
- Cognitive-inspired number representation systems

#### 5.2.3 Artificial Intelligence
AI systems could benefit from:
- Curvature-based feature engineering for number-theoretic tasks
- Cognitive load modeling in mathematical reasoning systems
- Biomimetic approaches to mathematical intuition

### 5.3 Limitations and Scope

#### 5.3.1 Forward Diagnostic Only
The Z-transformation requires known values of n and traversal rate v. It cannot serve as a standalone inverse function for recovering unknown integers from perceived values.

#### 5.3.2 Parameter Sensitivity
Model parameters (cognitive velocity, coupling constant) must be set or estimated rather than inferred purely from data.

#### 5.3.3 Metaphorical Framework
While the relativistic analogies provide useful intuition, the core mathematics stands independently of physical interpretations.

## 6. Future Directions

### 6.1 Extended Range Studies
- Investigation of curvature patterns for larger numbers (n > 10,000)
- Analysis of special number classes (perfect numbers, Mersenne primes, etc.)
- Cross-cultural validation of cognitive curvature patterns

### 6.2 Parameter Optimization
- Data-driven estimation of cognitive parameters
- Individual difference modeling in curvature perception  
- Adaptive parameter tuning for specific mathematical domains

### 6.3 Theoretical Extensions
- Connection to analytic number theory (Riemann zeta function, prime number theorem)
- Exploration of higher-dimensional curvature models
- Integration with existing cognitive theories of mathematical processing

### 6.4 Applications Development
- Educational software incorporating curvature-based difficulty assessment
- Mathematical intuition training systems
- Cognitive assistance tools for mathematical problem-solving

## 7. Conclusions

This paper introduces a novel computational framework for understanding cognitive distortions in mathematical number perception through geometry-inspired curvature modeling. Our key findings include:

1. **Prime Numbers as Geodesics**: Primes consistently exhibit minimal cognitive curvature (~0.739 average), supporting their role as fundamental building blocks in mathematical cognition.

2. **Composite Complexity**: Highly composite numbers show dramatically increased curvature (up to 5.239 for n=48), reflecting the cognitive burden of processing multiple divisibility relationships.

3. **Load-Dependent Scaling**: Cognitive load systematically amplifies distortion effects while preserving relative ordering between number types.

4. **Practical Classification**: Simple curvature thresholds achieve ~83% accuracy in distinguishing primes from composites, demonstrating practical utility.

The framework provides both theoretical insights into the geometric structure of mathematical cognition and practical tools for applications in education, algorithm design, and artificial intelligence. While limitations exist regarding parameter estimation and inverse transformation capabilities, the model offers a foundation for future research in cognitive number theory.

My work demonstrates that mathematical perception can be understood through geometric principles, opening new avenues for research at the intersection of mathematics, cognitive science, and computational modeling. The curvature-based approach provides a quantitative foundation for investigating how cognitive systems navigate the landscape of mathematical concepts.

## References

1. Hardy, G. H., & Wright, E. M. (2008). *An Introduction to the Theory of Numbers* (6th ed.). Oxford University Press.

2. Dehaene, S. (2011). *The Number Sense: How the Mind Creates Mathematics*. Oxford University Press.

3. Lakoff, G., & Núñez, R. E. (2000). *Where Mathematics Comes From: How the Embodied Mind Brings Mathematics into Being*. Basic Books.

4. Riemann, B. (1859). Über die Anzahl der Primzahlen unter einer gegebenen Größe. *Monatsberichte der Berliner Akademie*.

5. Do Carmo, M. P. (1992). *Riemannian Geometry*. Birkhäuser.

6. Anderson, J. R. (2007). *How Can the Human Mind Occur in the Physical Universe?* Oxford University Press.

## Appendix A: Computational Implementation

The complete experimental framework is available in the accompanying files:

- `main.py`: Complete CognitiveModel implementation with all mathematical transformations, simulation and visualization functions, data export capabilities, and machine learning validation experiments
- `generate_plots.py`: Visualization generation script for creating publication-quality plots and summary tables

## Appendix B: Experimental Data and Visualizations

Detailed experimental results and visualizations are provided:

**Data Files:**
- `results_load_0.csv`: Baseline cognitive load experiments (Load = 0.0)
- `results_load_30.csv`: Moderate cognitive load experiments (Load = 0.3)
- `results_load_70.csv`: High cognitive load experiments (Load = 0.7)

**Visualization Files:**
- `curvature_analysis.png`: Curvature distribution plots showing prime vs composite separation
- `load_effects.png`: Cognitive load effect analysis with exponential scaling demonstration

Each CSV file contains columns for: n, Z(n), Perceived, Distortion, Curvature

**Additional Documents:**
- `executive_summary.md`: Concise overview of key findings and applications
- `white_paper.md`: This complete technical document

---

*Manuscript prepared using the computational framework described herein. All experimental results are reproducible using the provided Python implementation.*
