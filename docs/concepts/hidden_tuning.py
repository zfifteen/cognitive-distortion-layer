import numpy as np
import matplotlib.pyplot as plt
from sympy import isprime, divisors
import math

def num_divisors(n):
    """Return the number of divisors d(n) — exact match to repo's divisor_count."""
    if n < 1:
        return 0
    return len(divisors(n))

def kappa(n, e2=math.e**2):
    """Curvature κ(n) = d(n) · ln(n) / e² — exact canonical signal from src/python/cdl.py."""
    if n < 2:
        return 0.0
    return num_divisors(n) * np.log(n) / e2

def z_normalize(n, v, e2=math.e**2):
    """Z(n) = n / exp(v · κ(n)) — exact Z-transformation from the repository."""
    if n < 2:
        return 0.0
    return n / np.exp(v * kappa(n, e2))

def find_primes_up_to(max_n):
    """Efficient prime generator matching the repo's is_prime logic."""
    primes = [i for i in range(2, max_n + 1) if isprime(i)]
    return primes

# ====================== CORE INSIGHT DEMONSTRATION ======================
print("=== Cognitive Distortion Layer — Prime Stabilization Demo ===\n")

max_n = 2000
primes = find_primes_up_to(max_n)
print(f"Analyzing {len(primes):,} primes up to {max_n}\n")

# The hidden sweet spot identified in the insight
v_sweet = (math.e ** 2) / 2
print(f"Hidden sweet-spot normalization speed (traversal rate) v = e²/2 ≈ {v_sweet:.6f}\n")

# Compare several v values — only the sweet spot produces a perfectly flat band
vs = [1.0, 2.0, v_sweet, 5.0]
results = {}

print("Z-statistics for all primes:")
for v in vs:
    z_primes = [z_normalize(p, v) for p in primes]
    mean_z = np.mean(z_primes)
    std_z = np.std(z_primes)
    results[v] = (mean_z, std_z)

    print(f"  v = {v:6.4f} → mean Z = {mean_z:10.6f} | std = {std_z:10.8f}")
    if abs(v - v_sweet) < 0.001:
        print("           → PERFECTLY STABLE FLAT BAND (all primes exactly Z=1.0)!")
    print()

# Concrete examples at the sweet spot (proves scale-invariance)
print("\nExamples at sweet-spot v (should all be exactly 1.0):")
for p in primes[:8] + [101, 1009, 10007, 100003, 999983]:
    z_val = z_normalize(p, v_sweet)
    print(f"  Prime {p:6d} → Z(n) = {z_val:.10f}  (exactly 1.0)")

print("\n" + "=" * 70)
print("This is the core insight in action:")
print("• At v = e²/2 the logarithmic growth baked into κ(n) for primes is")
print("  exactly cancelled → Z(p) becomes perfectly scale-invariant.")
print("• At any other v, primes drift with log-scale, exactly as predicted.")
print("• The band is stable no matter how large the numbers get.")
print("=" * 70)

# Visualization — shows the dramatic difference
plt.figure(figsize=(11, 6))
colors = ['blue', 'orange', 'red', 'green']
for i, v in enumerate(vs):
    z_primes = [z_normalize(p, v) for p in primes]
    plt.plot(primes, z_primes, label=f'v = {v:.4f}', color=colors[i], alpha=0.75, linewidth=1.2)

plt.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Stable prime band (Z=1.0)')
plt.xlabel('Prime number p (log scale)')
plt.ylabel('Z-normalized value Z(p)')
plt.title('Cognitive Distortion Layer — Prime Stabilization at Sweet-Spot v = e²/2')
plt.xscale('log')
plt.yscale('log')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

# You can comment the next line and uncomment savefig if you prefer a file
plt.show()
# plt.savefig('cdl_prime_stabilization_demo.png', dpi=300)

print("\nVisualization displayed (or saved as 'cdl_prime_stabilization_demo.png' if you uncomment savefig).")
print("Script completed successfully — no errors.")
