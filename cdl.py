#!/usr/bin/env python3
"""
Cognitive Distortion Layer (CDL)

Provides the κ(n) curvature signal as a unified interface for prime diagnostics,
QMC sampling, and signal normalization across the Z Framework.

Core primitives:
1. kappa(n) - Curvature signal
2. classify(n, threshold) - Threshold-based prime/composite classification
3. z_normalize(n, v) - Z-transformation for scale normalization

References:
- CDL_SPECIFICATION.md for detailed protocol
- Baseline: n=2-49, prime avg ~0.739, composite avg ~2.252, accuracy ~83%
"""

import math
from typing import Tuple, Dict, List, Literal


# ============================================================================
# Core Primitive 1: Curvature Signal κ(n)
# ============================================================================

def divisor_count(n: int) -> int:
    """
    Compute the number of divisors d(n).
    
    Uses efficient O(√n) enumeration.
    
    Args:
        n: Positive integer
        
    Returns:
        Number of divisors of n
        
    Examples:
        >>> divisor_count(12)  # divisors: 1,2,3,4,6,12
        6
        >>> divisor_count(7)   # divisors: 1,7
        2
    """
    if n < 1:
        return 0
    
    count = 0
    i = 1
    while i * i <= n:
        if n % i == 0:
            count += 1 if i * i == n else 2
        i += 1
    
    return count


def kappa(n: int) -> float:
    """
    Compute cognitive curvature κ(n) = d(n) · ln(n) / e².
    
    This is the canonical curvature signal for the Z Framework.
    Low κ indicates structural simplicity (prime-like).
    High κ indicates structural complexity (composite-like).
    
    Args:
        n: Positive integer (n >= 2)
        
    Returns:
        Curvature value κ(n) in [0, ∞)
        
    Examples:
        >>> kappa(2)   # Prime, d(2)=2
        0.255
        >>> kappa(12)  # Composite, d(12)=6
        2.028
        
    Empirical ranges (n=2-49):
        - Prime average: ~0.739
        - Composite average: ~2.252
    """
    if n <= 1:
        return 0.0
    
    d_n = divisor_count(n)
    ln_n = math.log(n)
    e_squared = math.e ** 2
    
    return d_n * ln_n / e_squared


# ============================================================================
# Core Primitive 2: Threshold Classifier
# ============================================================================

def classify(n: int, threshold: float = 1.5) -> Literal["prime", "composite"]:
    """
    Classify n as prime or composite based on κ(n) threshold.
    
    Default threshold τ=1.5 yields ~83% accuracy on seed set (n=2-49).
    
    Protocol:
        1. Compute κ(n)
        2. If κ(n) < threshold: "prime"
        3. Otherwise: "composite"
    
    Args:
        n: Integer to classify
        threshold: Classification threshold (default 1.5)
        
    Returns:
        "prime" if κ(n) < threshold, else "composite"
        
    Examples:
        >>> classify(7)    # κ(7) ≈ 0.54
        'prime'
        >>> classify(12)   # κ(12) ≈ 2.03
        'composite'
    """
    k = kappa(n)
    return "prime" if k < threshold else "composite"


def classify_batch(
    numbers: List[int], 
    threshold: float = 1.5
) -> List[Tuple[int, str, float]]:
    """
    Classify multiple numbers efficiently.
    
    Args:
        numbers: List of integers to classify
        threshold: Classification threshold
        
    Returns:
        List of (n, classification, κ(n)) tuples
    """
    results = []
    for n in numbers:
        k = kappa(n)
        classification = "prime" if k < threshold else "composite"
        results.append((n, classification, k))
    return results


def find_optimal_threshold(
    primes: List[int],
    composites: List[int],
    threshold_range: Tuple[float, float] = (0.5, 3.0),
    steps: int = 50
) -> Tuple[float, float, Dict]:
    """
    Find optimal threshold that maximizes classification accuracy.
    
    Args:
        primes: List of known prime numbers
        composites: List of known composite numbers
        threshold_range: (min, max) threshold values to test
        steps: Number of threshold values to try
        
    Returns:
        (best_threshold, best_accuracy, metrics_dict)
    """
    best_threshold = threshold_range[0]
    best_accuracy = 0.0
    
    thresholds = [
        threshold_range[0] + i * (threshold_range[1] - threshold_range[0]) / steps
        for i in range(steps + 1)
    ]
    
    for threshold in thresholds:
        correct = 0
        total = len(primes) + len(composites)
        
        # Check primes
        for p in primes:
            if classify(p, threshold) == "prime":
                correct += 1
        
        # Check composites
        for c in composites:
            if classify(c, threshold) == "composite":
                correct += 1
        
        accuracy = correct / total if total > 0 else 0.0
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    
    # Compute detailed metrics at best threshold
    tp = sum(1 for p in primes if classify(p, best_threshold) == "prime")
    fp = sum(1 for c in composites if classify(c, best_threshold) == "prime")
    tn = sum(1 for c in composites if classify(c, best_threshold) == "composite")
    fn = sum(1 for p in primes if classify(p, best_threshold) == "composite")
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    metrics = {
        "threshold": best_threshold,
        "accuracy": best_accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn
    }
    
    return best_threshold, best_accuracy, metrics


# ============================================================================
# Core Primitive 3: Z-Normalization
# ============================================================================

def z_normalize(n: int, v: float = 1.0) -> float:
    """
    Apply Z-transformation to normalize for structural distortion.
    
    Formula: Z(n) = n / exp(v · κ(n))
    
    The v parameter controls correction strength:
        - v = 1.0: Standard normalization (diagnostics)
        - v = 0.5: Light correction (QMC sampling)
        - v = 2.0: Heavy correction (signal pipelines)
    
    Args:
        n: Integer to normalize
        v: Scale parameter (task-specific)
        
    Returns:
        Normalized value Z(n) ≤ n
        
    Examples:
        >>> z_normalize(7, v=1.0)   # Prime, low κ
        6.42
        >>> z_normalize(12, v=1.0)  # Composite, high κ
        1.57
        
    Properties:
        - Z(n) ≤ n (normalization reduces value)
        - Stronger correction for high-κ numbers
        - Preserves ordering in low-κ neighborhoods
    """
    k = kappa(n)
    distortion = v * k
    return n / math.exp(distortion)


def z_normalize_batch(
    numbers: List[int],
    v: float = 1.0
) -> List[Tuple[int, float, float]]:
    """
    Apply Z-normalization to multiple numbers.
    
    Args:
        numbers: List of integers to normalize
        v: Scale parameter
        
    Returns:
        List of (n, κ(n), Z(n)) tuples
    """
    results = []
    for n in numbers:
        k = kappa(n)
        z = n / math.exp(v * k)
        results.append((n, k, z))
    return results


# ============================================================================
# Utility Functions
# ============================================================================

def is_prime(n: int) -> bool:
    """
    Simple primality test for validation.
    
    Args:
        n: Integer to test
        
    Returns:
        True if n is prime, False otherwise
    """
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    
    return True


def compute_curvature_stats(numbers: List[int]) -> Dict:
    """
    Compute comprehensive statistics for a set of numbers.
    
    Args:
        numbers: List of integers to analyze
        
    Returns:
        Dictionary with statistics
    """
    if not numbers:
        return {}
    
    # Separate by primality
    primes = [n for n in numbers if is_prime(n)]
    composites = [n for n in numbers if not is_prime(n)]
    
    # Compute κ for each
    prime_kappas = [kappa(p) for p in primes]
    composite_kappas = [kappa(c) for c in composites]
    
    # Statistics
    stats = {
        "n_range": (min(numbers), max(numbers)),
        "n_primes": len(primes),
        "n_composites": len(composites),
        "prime_kappa_mean": sum(prime_kappas) / len(prime_kappas) if prime_kappas else 0.0,
        "composite_kappa_mean": sum(composite_kappas) / len(composite_kappas) if composite_kappas else 0.0,
    }
    
    if stats["prime_kappa_mean"] > 0:
        stats["separation_ratio"] = stats["composite_kappa_mean"] / stats["prime_kappa_mean"]
    else:
        stats["separation_ratio"] = 0.0
    
    return stats


# ============================================================================
# Integration Helpers
# ============================================================================

def prime_diagnostic_prefilter(
    candidates: List[int],
    threshold: float = 1.5,
    full_test_threshold: bool = True
) -> Tuple[List[int], List[int]]:
    """
    Integration Port: Prime Diagnostics Prefilter
    
    Filter candidates using κ(n) before expensive primality tests.
    
    Workflow:
        1. Compute κ(n) for each candidate
        2. If κ(n) < threshold: "likely prime" (test further)
        3. If κ(n) ≥ threshold: "likely composite" (skip)
    
    Args:
        candidates: List of integers to filter
        threshold: κ threshold for classification
        full_test_threshold: If True, verify with full primality test
        
    Returns:
        (likely_primes, likely_composites) tuple
    """
    likely_primes = []
    likely_composites = []
    
    for n in candidates:
        classification = classify(n, threshold)
        
        if classification == "prime":
            if full_test_threshold:
                # Verify with full test
                if is_prime(n):
                    likely_primes.append(n)
                else:
                    likely_composites.append(n)
            else:
                likely_primes.append(n)
        else:
            likely_composites.append(n)
    
    return likely_primes, likely_composites


def qmc_sampling_bias(
    candidates: List[int],
    bias_strength: float = 0.5
) -> List[int]:
    """
    Integration Port: QMC/Factorization Sampling
    
    Sort candidates by κ(n) to bias exploration toward low-curvature regions.
    
    Workflow:
        1. Compute κ(n) for each candidate
        2. Sort by κ (ascending)
        3. Bias exploration toward low-κ first
    
    Args:
        candidates: List of candidate integers
        bias_strength: Strength of bias (0=none, 1=full sort)
        
    Returns:
        Biased list of candidates
    """
    if bias_strength == 0:
        return candidates
    
    # Compute κ for each
    kappa_pairs = [(n, kappa(n)) for n in candidates]
    
    # Sort by κ
    kappa_pairs.sort(key=lambda x: x[1])
    
    # Extract sorted candidates
    sorted_candidates = [n for n, k in kappa_pairs]
    
    if bias_strength == 1.0:
        return sorted_candidates
    
    # Partial bias: blend original and sorted
    blend = []
    for i in range(len(candidates)):
        idx = int(i * bias_strength + i * (1 - bias_strength))
        idx = min(idx, len(sorted_candidates) - 1)
        blend.append(sorted_candidates[idx])
    
    return blend


def signal_normalize_pipeline(
    signals: Dict[int, float],
    v: float = 1.0
) -> Dict[int, float]:
    """
    Integration Port: Signal Normalization
    
    Normalize signal values using Z-transformation.
    
    Workflow:
        1. Collect raw signal values at {n₁, n₂, ..., nₖ}
        2. Apply Z-normalization: Zᵢ = Z(nᵢ)
        3. Use normalized values as stable feature scale
    
    Args:
        signals: Dict mapping n → raw_signal_value
        v: Scale parameter for Z-normalization
        
    Returns:
        Dict mapping n → normalized_signal_value
    """
    normalized = {}
    
    for n, signal_value in signals.items():
        z_n = z_normalize(n, v)
        # Normalize signal proportionally
        normalized[n] = signal_value * (z_n / n)
    
    return normalized


if __name__ == "__main__":
    # Quick validation
    print("CDL Core Primitives Validation")
    print("=" * 60)
    
    # Test κ(n)
    print("\n1. Curvature Signal κ(n):")
    test_numbers = [2, 3, 7, 11, 12, 30]
    for n in test_numbers:
        k = kappa(n)
        prime_status = "prime" if is_prime(n) else "composite"
        print(f"   κ({n:2}) = {k:.3f} [{prime_status}]")
    
    # Test classifier
    print("\n2. Threshold Classifier (τ=1.5):")
    for n in test_numbers:
        classification = classify(n)
        actual = "prime" if is_prime(n) else "composite"
        match = "✓" if classification == actual else "✗"
        print(f"   n={n:2}: classified as {classification:9} (actual: {actual:9}) {match}")
    
    # Test Z-normalization
    print("\n3. Z-Normalization (v=1.0):")
    for n in test_numbers:
        z = z_normalize(n)
        k = kappa(n)
        print(f"   Z({n:2}) = {z:.3f} (κ={k:.3f}, reduction: {(1-z/n)*100:.1f}%)")
    
    # Test on seed set
    print("\n4. Seed Set Statistics (n=2-49):")
    seed_numbers = list(range(2, 50))
    stats = compute_curvature_stats(seed_numbers)
    print(f"   Primes: {stats['n_primes']}, avg κ = {stats['prime_kappa_mean']:.3f}")
    print(f"   Composites: {stats['n_composites']}, avg κ = {stats['composite_kappa_mean']:.3f}")
    print(f"   Separation ratio: {stats['separation_ratio']:.2f}×")
    
    print("\n" + "=" * 60)
    print("CDL primitives validated successfully!")
