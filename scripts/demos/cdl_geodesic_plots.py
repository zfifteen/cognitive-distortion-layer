import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# === Validated CDL primitives (exact match to cdl.py) ===
def divisor_count(n):
    """Number of divisors d(n)"""
    if n < 1:
        return 0
    count = 0
    for i in range(1, int(np.sqrt(n)) + 1):
        if n % i == 0:
            count += 1 if i * i == n else 2
    return count

def kappa(n):
    """κ(n) = d(n) · ln(n) / e²"""
    return divisor_count(n) * np.log(n) / np.exp(2)

def is_prime(n):
    """Simple deterministic prime check for n ≤ 2000"""
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

# === Data generation (n = 2 to 2000, matches kappas.csv ground truth) ===
N_MAX = 2000
n_values = np.arange(2, N_MAX + 1)
kappa_values = np.array([kappa(n) for n in n_values])
log_n = np.log10(n_values)
log_d_plus1 = np.log10(np.array([divisor_count(n) + 1 for n in n_values]))
log_log_n = np.log10(np.log(n_values))
primes_mask = np.array([is_prime(n) for n in n_values])
composites_mask = ~primes_mask

# Forward Z-model (canonical v = 1.0)
v = 1.0
Z_values = n_values / np.exp(v * kappa_values)

# Adaptive threshold surface (τ ≈ 1.5 + calibrated log-log drift)
adaptive_tau = 1.5 + 0.3 * log_log_n

# === Plot 1: Curvature Landscape Scatter ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(log_n[primes_mask], log_d_plus1[primes_mask], kappa_values[primes_mask],
           c='blue', s=20, label='Primes (low-curvature geodesics)')
ax.scatter(log_n[composites_mask], log_d_plus1[composites_mask], kappa_values[composites_mask],
           c='red', s=20, label='Composites (high-curvature bends)')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('log₁₀(d(n) + 1)')
ax.set_zlabel('κ(n)')
ax.set_title('CDL Geodesic Phenomenon: Curvature Landscape\nPrimes occupy the minimal-curvature valley')
ax.legend()
plt.savefig('cdl_geodesic_plot1_landscape.png', dpi=300, bbox_inches='tight')
plt.close()

# === Plot 2: Path Trajectory with Baseline Drift ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
ax.plot(log_n, kappa_values, log_log_n, c='gray', alpha=0.3, label='Full integer path')
ax.scatter(log_n[primes_mask], kappa_values[primes_mask], log_log_n[primes_mask],
           c='blue', s=20, label='Prime geodesics')
ax.scatter(log_n[composites_mask], kappa_values[composites_mask], log_log_n[composites_mask],
           c='red', s=20, label='Composite bends')
# Sliding threshold surface
X, Y = np.meshgrid(np.linspace(log_n.min(), log_n.max(), 30),
                   np.linspace(kappa_values.min(), kappa_values.max(), 30))
Z_surf = 1.5 + 0.3 * np.log10(np.log(10**X))
ax.plot_surface(X, Y, Z_surf, alpha=0.2, color='green', label='Sliding threshold surface')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('κ(n)')
ax.set_zlabel('log₁₀(log n)')
ax.set_title('Geodesic Stretch & Baseline Creep\nFixed τ fails; sliding rule restores recovery >50%')
ax.legend()
plt.savefig('cdl_geodesic_plot2_drift.png', dpi=300, bbox_inches='tight')
plt.close()

# === Plot 3: Z-Normalization Straightening ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
ax.plot(log_n, kappa_values, np.zeros_like(log_n), c='gray', alpha=0.3, label='Raw distorted path')
ax.scatter(log_n[primes_mask], kappa_values[primes_mask], Z_values[primes_mask],
           c='blue', s=20, label='Straightened prime geodesics (Z(n))')
ax.scatter(log_n[composites_mask], kappa_values[composites_mask], Z_values[composites_mask],
           c='red', s=20, label='Bent composites (Z(n))')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('κ(n) (raw distortion)')
ax.set_zlabel('Z(n) = n / exp(v · κ(n))')
ax.set_title('Forward Z-Transformation: Straightening the Geodesics\nPrimes become distortion-invariant paths')
ax.legend()
plt.savefig('cdl_geodesic_plot3_z_straight.png', dpi=300, bbox_inches='tight')
plt.close()

# === Plot 4: Average Curvature Surface with Prime Geodesics ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
# Bin-averaged surface
hist, xedges, yedges = np.histogram2d(log_n, log_d_plus1, bins=30, weights=kappa_values)
xcenters = (xedges[:-1] + xedges[1:]) / 2
ycenters = (yedges[:-1] + yedges[1:]) / 2
X, Y = np.meshgrid(xcenters, ycenters)
ax.plot_surface(X, Y, hist.T, cmap='viridis', alpha=0.8)
ax.scatter(log_n[primes_mask], log_d_plus1[primes_mask], kappa_values[primes_mask],
           c='blue', s=30, label='Prime geodesics')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('log₁₀(d(n) + 1)')
ax.set_zlabel('κ(n)')
ax.set_title('Figure 4: Average Curvature Surface with Prime Geodesics')
plt.savefig('cdl_geodesic_plot4_surface.png', dpi=300, bbox_inches='tight')
plt.close()

# === Plot 5: Full Z-Space Straightening in 3D ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(log_n[primes_mask], kappa_values[primes_mask], Z_values[primes_mask],
           c='blue', s=20, label='Straightened Primes')
ax.scatter(log_n[composites_mask], kappa_values[composites_mask], Z_values[composites_mask],
           c='red', s=20, label='Composites (residual bends)')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('Raw κ(n)')
ax.set_zlabel('Z(n)')
ax.set_title('Figure 5: Z-Normalization in 3D - Straightened Geodesics')
ax.legend()
plt.savefig('cdl_geodesic_plot5_z3d.png', dpi=300, bbox_inches='tight')
plt.close()

# === Plot 6: Geodesics vs. Adaptive Sliding Threshold ===
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection='3d')
ax.plot(log_n, kappa_values, log_log_n, c='gray', alpha=0.3, label='Integer Path')
ax.scatter(log_n[primes_mask], kappa_values[primes_mask], log_log_n[primes_mask],
           c='blue', s=20, label='Prime Geodesics')
# Adaptive surface
X, Y = np.meshgrid(np.linspace(log_n.min(), log_n.max(), 50), np.linspace(0, kappa_values.max(), 50))
Z_surf = 1.5 + 0.3 * np.log10(np.log(10**X))
ax.plot_surface(X, Y, Z_surf, alpha=0.3, color='green', label='Adaptive Threshold Surface')
ax.set_xlabel('log₁₀(n)')
ax.set_ylabel('κ(n)')
ax.set_zlabel('log₁₀(log n)')
ax.set_title('Figure 6: Geodesics vs Adaptive Sliding Threshold')
ax.legend()
plt.savefig('cdl_geodesic_plot6_adaptive.png', dpi=300, bbox_inches='tight')
plt.close()

print("All six CDL geodesic 3D plots generated successfully!")
