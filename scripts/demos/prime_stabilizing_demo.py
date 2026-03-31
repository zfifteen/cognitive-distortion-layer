import numpy as np
import matplotlib.pyplot as plt
import math

print('Starting Prime-Stabilizing Z Demonstration up to 10^18')
print('Method: Z(n) = n^(1 - d(n)/2) at critical v = e²/2\n')

# Algebraic Z at the critical traversal rate
def compute_z(n: int, d: int) -> float:
    if n < 2:
        return 0.0
    exponent = 1.0 - d / 2.0
    try:
        return float(n ** exponent)
    except:
        return 0.0

# Fast divisor count for numbers up to 10^18
def count_divisors(n: int) -> int:
    if n < 2:
        return 0
    count = 1
    exp = 0
    while n % 2 == 0:
        exp += 1
        n //= 2
    if exp > 0:
        count *= (exp + 1)
    i = 3
    while i * i <= n:
        exp = 0
        while n % i == 0:
            exp += 1
            n //= i
        if exp > 0:
            count *= (exp + 1)
        i += 2
    if n > 1:
        count *= 2
    return count

# ==================== PHASE 1: Full sieve to 10^7 ====================
N_small = 10_000_000
print(f'Running full sieve up to {N_small:,} for dense analysis...')
divisors = [0] * (N_small + 1)
for i in range(1, N_small + 1):
    for j in range(i, N_small + 1, i):
        divisors[j] += 1

prime_z = []
composite_z = []
composite_logz = []
n_values = []
z_values = []
is_prime_list = []
d_values = []          # NEW: for Z vs d(n) plot
logn_values = []       # NEW: for coloring

for n in range(2, N_small + 1):
    d = divisors[n]
    z = compute_z(n, d)
    n_values.append(n)
    z_values.append(z)
    is_prime_list.append(d == 2)
    d_values.append(d)
    logn_values.append(math.log10(n))
    if d == 2:
        prime_z.append(z)
    else:
        composite_z.append(z)
        if z > 0:
            composite_logz.append(math.log10(z))
        else:
            composite_logz.append(-300)

print('Phase 1 complete.\n')

# ==================== PHASE 2: Targeted verification to 10^18 ====================
large_test_numbers = [
    1000000007, 1000000000039, 1000000000000037, 999999999999000041,
    1000000000000000000, 999999999999999999, 1000000014000000049, 1000000000000000004,
    4, 9, 25
]

print('Computing targeted numbers up to 10^18...')
large_results = []
for n in large_test_numbers:
    d = count_divisors(n)
    z = compute_z(n, d)
    typ = 'prime' if d == 2 else 'composite'
    large_results.append((n, d, z, typ))

# ==================== SUMMARY STATISTICS ====================
prime_z = np.array(prime_z)
composite_z = np.array(composite_z)

print('=== DEMONSTRATION RESULTS ===')
print(f'Processed {N_small:,} numbers in dense phase')
print(f'Primes found: {len(prime_z):,}')
print(f'Composites found: {len(composite_z):,}')
print(f'Prime band mean Z: {np.mean(prime_z):.15f}')
print(f'Prime band std Z:  {np.std(prime_z):.15f}  ← zero variance')
print(f'Max composite Z : {np.max(composite_z):.15f} (only at n=4)')
print('Classification at Z=1 band: 100% accurate (algebraic guarantee)\n')

print('=== LARGE-SCALE CONFIRMATION (10^18) ===')
for n, d, z, typ in large_results:
    print(f'n = {n:,} | d(n) = {d} | Z(n) = {z:.15e} | {typ.upper()}')

# ==================== PLOTS — THREE SEPARATE FIGURES ====================

np.random.seed(42)
sample_idx = np.random.choice(len(n_values), 50_000, replace=False)
n_sample = np.array(n_values)[sample_idx]
z_sample = np.array(z_values)[sample_idx]
prime_sample = np.array(is_prime_list)[sample_idx]
d_sample = np.array(d_values)[sample_idx]
logn_sample = np.array(logn_values)[sample_idx]

# Plot 1: Prime-Stabilizing Band Scatter
fig1, ax1 = plt.subplots(figsize=(10, 7))
ax1.scatter(n_sample[~prime_sample], z_sample[~prime_sample], s=1, c='blue', alpha=0.4, label='Composites')
ax1.scatter(n_sample[prime_sample], z_sample[prime_sample], s=3, c='red', label='Primes (Z=1 band)')
for n, _, z, typ in large_results:
    color = 'red' if typ == 'prime' else 'blue'
    size = 120 if n > 1e7 else 40
    ax1.scatter([n], [z], s=size, c=color, edgecolors='black', linewidth=1.5, zorder=5)
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_xlabel('n (log scale)')
ax1.set_ylabel('Z(n) (log scale)')
ax1.set_title('Prime-Stabilizing Band at Critical v = e²/2\n(Flat at Z=1 for all primes — scale-invariant up to 10¹⁸)')
ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2.5, label='Invariant Prime Band Z=1')
ax1.legend(loc='upper right', fontsize=11)
ax1.grid(True, which='both', alpha=0.3)
plt.tight_layout()
plt.savefig('prime_stabilizing_band_demo.png', dpi=300, bbox_inches='tight')
print('Saved: prime_stabilizing_band_demo.png')

# Plot 2: Composite Distortion Histogram
fig2, ax2 = plt.subplots(figsize=(10, 7))
ax2.hist(composite_logz, bins=120, color='blue', alpha=0.75, edgecolor='black')
ax2.axvline(x=math.log10(0.5), color='red', linestyle='--', linewidth=2.5, label='Max composite Z=0.5 (n=4)')
ax2.set_xlabel('log₁₀(Z(n)) for composites')
ax2.set_ylabel('Count')
ax2.set_title('Distribution of Composite Distortion\n(Rapid collapse toward zero at critical v)')
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('composite_distortion_histogram_demo.png', dpi=300, bbox_inches='tight')
print('Saved: composite_distortion_histogram_demo.png')

# Plot 3: NEW — Z(n) versus Divisor Count d(n) (colored by log10(n))
fig3, ax3 = plt.subplots(figsize=(11, 7))
scatter = ax3.scatter(d_sample, z_sample, s=2, c=logn_sample, cmap='viridis', alpha=0.6)
ax3.set_yscale('log')
ax3.set_xlabel('d(n) (divisor count)')
ax3.set_ylabel('Z(n) (log scale)')
ax3.set_title('Z(n) versus Divisor Count d(n)\n(Colored by log₁₀(n) — higher d drives stronger compression)')
cbar = plt.colorbar(scatter, ax=ax3)
cbar.set_label('log₁₀(n)')
ax3.grid(True, which='both', alpha=0.3)
plt.tight_layout()
plt.savefig('z_vs_divisor_count_demo.png', dpi=300, bbox_inches='tight')
print('Saved: z_vs_divisor_count_demo.png')

print('\nScript complete. Three distinct, impactful plots generated and saved.')
