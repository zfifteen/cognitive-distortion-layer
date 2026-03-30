#!/usr/bin/env python3
"""
Generate plots and tables for the white paper based on experimental data.
"""

import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def load_experimental_data(filename):
    """Load data from CSV file."""
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'n': int(row['n']),
                'z_n': float(row['Z(n)']),
                'perceived': float(row['Perceived']),
                'distortion': float(row['Distortion']),
                'curvature': float(row['Curvature'])
            })
    return data

def is_prime(n):
    """Simple primality test for our range."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def create_curvature_comparison_plot():
    """Create a comparison plot of curvature for primes vs composites."""
    data = load_experimental_data('results_load_0.csv')
    
    # Separate primes and composites
    primes = [d for d in data if is_prime(d['n'])]
    composites = [d for d in data if not is_prime(d['n'])]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Curvature vs Number
    prime_n = [p['n'] for p in primes]
    prime_curv = [p['curvature'] for p in primes]
    comp_n = [c['n'] for c in composites]
    comp_curv = [c['curvature'] for c in composites]
    
    ax1.scatter(prime_n, prime_curv, c='blue', s=60, alpha=0.7, label='Primes', marker='o')
    ax1.scatter(comp_n, comp_curv, c='red', s=60, alpha=0.7, label='Composites', marker='s')
    ax1.set_xlabel('Number (n)')
    ax1.set_ylabel('Cognitive Curvature κ(n)')
    ax1.set_title('Cognitive Curvature Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Distortion vs Curvature  
    prime_dist = [p['distortion'] for p in primes]
    comp_dist = [c['distortion'] for c in composites]
    
    ax2.scatter(prime_curv, prime_dist, c='blue', s=60, alpha=0.7, label='Primes', marker='o')
    ax2.scatter(comp_curv, comp_dist, c='red', s=60, alpha=0.7, label='Composites', marker='s')
    ax2.set_xlabel('Cognitive Curvature κ(n)')
    ax2.set_ylabel('Perceived Distortion')
    ax2.set_title('Curvature vs Distortion Relationship')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')  # Log scale for better visibility
    
    plt.tight_layout()
    plt.savefig('curvature_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_load_effect_plot():
    """Create a plot showing the effect of cognitive load."""
    load_0 = load_experimental_data('results_load_0.csv')
    load_30 = load_experimental_data('results_load_30.csv')
    load_70 = load_experimental_data('results_load_70.csv')
    
    # Calculate average distortions
    loads = [0.0, 0.3, 0.7]
    avg_distortions = [
        np.mean([d['distortion'] for d in load_0]),
        np.mean([d['distortion'] for d in load_30]),
        np.mean([d['distortion'] for d in load_70])
    ]
    
    # Separate by prime/composite
    prime_avg_dist = []
    comp_avg_dist = []
    
    for data in [load_0, load_30, load_70]:
        primes = [d['distortion'] for d in data if is_prime(d['n'])]
        comps = [d['distortion'] for d in data if not is_prime(d['n'])]
        prime_avg_dist.append(np.mean(primes))
        comp_avg_dist.append(np.mean(comps))
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Overall load effect
    ax1.plot(loads, avg_distortions, 'ko-', linewidth=2, markersize=8, label='Overall Average')
    ax1.set_xlabel('Cognitive Load')
    ax1.set_ylabel('Average Distortion')
    ax1.set_title('Cognitive Load Effect on Distortion')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Prime vs Composite load effects
    ax2.plot(loads, prime_avg_dist, 'bo-', linewidth=2, markersize=8, label='Primes')
    ax2.plot(loads, comp_avg_dist, 'rs-', linewidth=2, markersize=8, label='Composites')
    ax2.set_xlabel('Cognitive Load')
    ax2.set_ylabel('Average Distortion')
    ax2.set_title('Load Effect: Primes vs Composites')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')
    
    plt.tight_layout()
    plt.savefig('load_effects.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_summary_table():
    """Generate a summary table for the white paper."""
    data = load_experimental_data('results_load_0.csv')
    
    # Find extremes
    highest_curv = sorted(data, key=lambda x: x['curvature'], reverse=True)[:5]
    lowest_curv = sorted(data, key=lambda x: x['curvature'])[:5]
    
    print("TABLE 1: Numbers with Highest Cognitive Curvature")
    print("n\tκ(n)\tDistortion\tType\tFactorization")
    print("-" * 60)
    for item in highest_curv:
        n = item['n']
        prime_status = "Prime" if is_prime(n) else "Composite"
        print(f"{n}\t{item['curvature']:.3f}\t{item['distortion']:.1f}\t\t{prime_status}")
    
    print("\nTABLE 2: Numbers with Lowest Cognitive Curvature")  
    print("n\tκ(n)\tDistortion\tType")
    print("-" * 40)
    for item in lowest_curv:
        n = item['n']
        prime_status = "Prime" if is_prime(n) else "Composite"
        print(f"{n}\t{item['curvature']:.3f}\t{item['distortion']:.1f}\t\t{prime_status}")

if __name__ == "__main__":
    print("Generating plots and tables for white paper...")
    
    # Create visualizations
    create_curvature_comparison_plot()
    print("✓ Created curvature_analysis.png")
    
    create_load_effect_plot()
    print("✓ Created load_effects.png")
    
    # Generate tables
    print("\n" + "="*60)
    generate_summary_table()
    print("="*60)
    
    print("\nAll visualizations and tables generated successfully!")