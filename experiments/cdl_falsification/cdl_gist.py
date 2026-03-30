#!/usr/bin/env python3
"""
CDL Prime Diagnostic Gist
From problem statement - testing hypothesis on RSA-129 factor range
"""

import math
import numpy as np
from sympy import divisors, isprime

def divisor_count(n: int) -> int:
    return len(divisors(n))

def kappa(n: int) -> float:
    """κ(n) = d(n) · ln(n) / e²."""
    if n <= 1:
        return 0.0
    d_n = divisor_count(n)
    return d_n * math.log(n) / math.exp(2)

def classify(n: int, threshold: float = 1.5) -> str:
    """Classify as 'prime' if κ(n) ≤ threshold, else 'composite'."""
    k = kappa(n)
    return 'prime' if k <= threshold else 'composite'

def z_normalize(n: int, v: float = 1.0) -> float:
    """Z(n) = n / exp(v · κ(n))."""
    return n / math.exp(v * kappa(n))

def prime_diagnostic_prefilter(candidates: np.ndarray, threshold: float = 1.5) -> tuple:
    """Prefilter: likely_primes (κ ≤ threshold), likely_composites (κ > threshold)."""
    likely_primes = [c for c in candidates if kappa(c) <= threshold]
    likely_composites = [c for c in candidates if kappa(c) > threshold]
    return np.array(likely_primes), np.array(likely_composites)

def bootstrap_accuracy(preds: np.ndarray, truths: np.ndarray, n_boot: int = 1000) -> tuple:
    """95% CI for accuracy %."""
    np.random.seed(42)  # For reproducibility
    accs = []
    for _ in range(n_boot):
        idx = np.random.choice(len(preds), len(preds), replace=True)
        acc = np.mean(preds[idx] == truths[idx]) * 100
        accs.append(acc)
    mean_acc = np.mean(accs)
    ci = np.percentile(accs, [2.5, 97.5])
    return mean_acc, ci

# Example: Classify and prefilter RSA-100 factor range sim
if __name__ == "__main__":
    candidates = np.arange(2, 1001)
    likely_primes, likely_composites = prime_diagnostic_prefilter(candidates)
    preds = np.array([classify(c) for c in candidates])
    truths = np.array(['prime' if isprime(c) else 'composite' for c in candidates])
    acc, ci = bootstrap_accuracy(preds, truths)
    print(f"Accuracy: {acc:.2f}% [95% CI {ci}]")
    np.savetxt('primes.csv', likely_primes, delimiter=',')
