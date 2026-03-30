#!/usr/bin/env python3
"""
Generate CDL Validation Dashboards

Creates visual dashboards showing:
1. κ(n) histograms for primes vs composites
2. Z-normalized traces
3. Classification boundary visualization
4. Scale comparison plots

Requires: matplotlib, numpy
"""

import math
import matplotlib.pyplot as plt
import numpy as np
import cdl


def create_kappa_histograms():
    """Generate κ(n) distribution histograms."""
    print("Generating κ(n) histograms...")
    
    # Generate data for multiple ranges
    ranges = [
        (2, 100, "Small (n=2-100)"),
        (100, 1000, "Medium (n=100-1000)"),
        (1000, 5000, "Large (n=1000-5000)")
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, (start, end, label) in enumerate(ranges):
        ax = axes[idx]
        
        numbers = list(range(start, end))
        primes = [n for n in numbers if cdl.is_prime(n)]
        composites = [n for n in numbers if not cdl.is_prime(n)]
        
        prime_kappas = [cdl.kappa(p) for p in primes]
        composite_kappas = [cdl.kappa(c) for c in composites]
        
        # Create histograms
        # Use first 100 composites or all if fewer, to avoid outliers skewing bins
        comp_sample = composite_kappas[:100] if len(composite_kappas) >= 100 else composite_kappas
        max_kappa = max(max(prime_kappas) if prime_kappas else 0, 
                       max(comp_sample) if comp_sample else 0)
        bins = np.linspace(0, max_kappa, 40)
        
        ax.hist(prime_kappas, bins=bins, alpha=0.7, color='blue', 
                label=f'Primes (n={len(primes)})', density=True)
        ax.hist(composite_kappas, bins=bins, alpha=0.7, color='red', 
                label=f'Composites (n={len(composites)})', density=True)
        
        # Mark threshold
        ax.axvline(x=1.5, color='green', linestyle='--', linewidth=2, 
                   label='Threshold (τ=1.5)')
        
        ax.set_xlabel('Curvature κ(n)', fontsize=11)
        ax.set_ylabel('Density', fontsize=11)
        ax.set_title(label, fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        prime_avg = np.mean(prime_kappas)
        comp_avg = np.mean(composite_kappas)
        
        text = f'Prime: μ={prime_avg:.2f}\nComp: μ={comp_avg:.2f}\nRatio: {comp_avg/prime_avg:.2f}×'
        ax.text(0.65, 0.95, text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', 
                facecolor='wheat', alpha=0.8), fontsize=9)
    
    plt.tight_layout()
    plt.savefig('cdl_kappa_histograms.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: cdl_kappa_histograms.png")
    plt.close()


def create_z_normalized_traces():
    """Generate Z-normalized value traces."""
    print("Generating Z-normalized traces...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Raw vs Z-normalized values
    ax = axes[0, 0]
    numbers = list(range(2, 100))
    z_values_v1 = [cdl.z_normalize(n, v=1.0) for n in numbers]
    
    ax.plot(numbers, numbers, 'k--', alpha=0.3, label='Identity (no normalization)')
    ax.plot(numbers, z_values_v1, 'b-', linewidth=2, label='Z(n) with v=1.0')
    
    # Highlight primes
    primes = [n for n in numbers if cdl.is_prime(n)]
    z_primes = [cdl.z_normalize(p, v=1.0) for p in primes]
    ax.scatter(primes, z_primes, c='red', s=30, zorder=5, label='Primes')
    
    ax.set_xlabel('n', fontsize=11)
    ax.set_ylabel('Value', fontsize=11)
    ax.set_title('Raw vs Z-Normalized Values', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Different v parameters
    ax = axes[0, 1]
    numbers = list(range(2, 100))
    z_v05 = [cdl.z_normalize(n, v=0.5) for n in numbers]
    z_v10 = [cdl.z_normalize(n, v=1.0) for n in numbers]
    z_v20 = [cdl.z_normalize(n, v=2.0) for n in numbers]
    
    ax.plot(numbers, z_v05, 'g-', linewidth=1.5, alpha=0.7, label='v=0.5 (light)')
    ax.plot(numbers, z_v10, 'b-', linewidth=2, label='v=1.0 (standard)')
    ax.plot(numbers, z_v20, 'r-', linewidth=1.5, alpha=0.7, label='v=2.0 (heavy)')
    
    ax.set_xlabel('n', fontsize=11)
    ax.set_ylabel('Z(n)', fontsize=11)
    ax.set_title('Z-Normalization with Different v Parameters', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Reduction percentage by class
    ax = axes[1, 0]
    numbers = list(range(2, 200))
    primes = [n for n in numbers if cdl.is_prime(n)]
    composites = [n for n in numbers if not cdl.is_prime(n)]
    
    prime_reductions = [(1 - cdl.z_normalize(p, v=1.0) / p) * 100 for p in primes]
    comp_reductions = [(1 - cdl.z_normalize(c, v=1.0) / c) * 100 for c in composites]
    
    ax.scatter(primes, prime_reductions, c='blue', s=20, alpha=0.6, label='Primes')
    ax.scatter(composites, comp_reductions, c='red', s=20, alpha=0.6, label='Composites')
    
    ax.set_xlabel('n', fontsize=11)
    ax.set_ylabel('Z-reduction (%)', fontsize=11)
    ax.set_title('Z-Normalization Reduction by Class', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Log-scale comparison
    ax = axes[1, 1]
    numbers = list(range(2, 1000))
    z_values = [cdl.z_normalize(n, v=1.0) for n in numbers]
    
    ax.semilogy(numbers, numbers, 'k--', alpha=0.3, label='Identity')
    ax.semilogy(numbers, z_values, 'b-', linewidth=2, label='Z(n)')
    
    ax.set_xlabel('n', fontsize=11)
    ax.set_ylabel('Value (log scale)', fontsize=11)
    ax.set_title('Z-Normalization Effect (Log Scale)', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('cdl_z_normalized_traces.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: cdl_z_normalized_traces.png")
    plt.close()


def create_classification_boundary():
    """Visualize classification boundary and accuracy."""
    print("Generating classification boundary visualization...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: κ(n) vs n with classification boundary
    ax = axes[0]
    numbers = list(range(2, 200))
    primes = [n for n in numbers if cdl.is_prime(n)]
    composites = [n for n in numbers if not cdl.is_prime(n)]
    
    prime_kappas = [cdl.kappa(p) for p in primes]
    composite_kappas = [cdl.kappa(c) for c in composites]
    
    ax.scatter(primes, prime_kappas, c='blue', s=30, alpha=0.7, 
               label='Primes', marker='o')
    ax.scatter(composites, composite_kappas, c='red', s=30, alpha=0.7, 
               label='Composites', marker='s')
    
    # Draw threshold line
    ax.axhline(y=1.5, color='green', linestyle='--', linewidth=2.5, 
               label='Classification Threshold (τ=1.5)')
    
    # Shade regions
    ax.axhspan(0, 1.5, alpha=0.1, color='blue', label='Prime Region')
    ax.axhspan(1.5, ax.get_ylim()[1], alpha=0.1, color='red', label='Composite Region')
    
    ax.set_xlabel('n', fontsize=11)
    ax.set_ylabel('κ(n)', fontsize=11)
    ax.set_title('Classification Boundary', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 10)
    
    # Plot 2: Accuracy vs threshold
    ax = axes[1]
    
    # Test different thresholds
    thresholds = np.linspace(0.5, 3.0, 50)
    accuracies = []
    precisions = []
    recalls = []
    
    test_numbers = list(range(2, 500))
    test_primes = [n for n in test_numbers if cdl.is_prime(n)]
    test_composites = [n for n in test_numbers if not cdl.is_prime(n)]
    
    for threshold in thresholds:
        correct = 0
        tp = fp = fn = 0
        
        for p in test_primes:
            if cdl.classify(p, threshold) == "prime":
                correct += 1
                tp += 1
            else:
                fn += 1
        
        for c in test_composites:
            if cdl.classify(c, threshold) == "composite":
                correct += 1
            else:
                fp += 1
        
        accuracy = correct / len(test_numbers)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        accuracies.append(accuracy)
        precisions.append(precision)
        recalls.append(recall)
    
    ax.plot(thresholds, accuracies, 'b-', linewidth=2, label='Accuracy')
    ax.plot(thresholds, precisions, 'g-', linewidth=2, label='Precision')
    ax.plot(thresholds, recalls, 'r-', linewidth=2, label='Recall')
    
    # Mark optimal threshold
    best_idx = np.argmax(accuracies)
    best_threshold = thresholds[best_idx]
    ax.axvline(x=best_threshold, color='orange', linestyle='--', linewidth=2,
               label=f'Optimal τ={best_threshold:.2f}')
    
    # Mark default threshold
    ax.axvline(x=1.5, color='purple', linestyle=':', linewidth=2,
               label='Default τ=1.5')
    
    ax.set_xlabel('Threshold τ', fontsize=11)
    ax.set_ylabel('Score', fontsize=11)
    ax.set_title('Classification Metrics vs Threshold', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.1)
    
    plt.tight_layout()
    plt.savefig('cdl_classification_boundary.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: cdl_classification_boundary.png")
    plt.close()


def create_scale_comparison():
    """Compare behavior across different scales."""
    print("Generating scale comparison plots...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Define scale ranges
    scales = [
        (2, 100, "Small Scale"),
        (100, 1000, "Medium Scale"),
        (1000, 5000, "Large Scale"),
        (5000, 10000, "Very Large Scale")
    ]
    
    for idx, (start, end, label) in enumerate(scales):
        ax = axes[idx // 2, idx % 2]
        
        # Sample every Nth number for large ranges
        step = max(1, (end - start) // 200)
        numbers = list(range(start, end, step))
        
        kappas = [cdl.kappa(n) for n in numbers]
        colors = ['blue' if cdl.is_prime(n) else 'red' for n in numbers]
        
        ax.scatter(numbers, kappas, c=colors, s=10, alpha=0.5)
        
        # Add threshold
        ax.axhline(y=1.5, color='green', linestyle='--', linewidth=2, 
                   label='Threshold τ=1.5')
        
        ax.set_xlabel('n', fontsize=11)
        ax.set_ylabel('κ(n)', fontsize=11)
        ax.set_title(f'{label} (n={start}-{end})', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Add statistics box
        primes = [n for n in numbers if cdl.is_prime(n)]
        composites = [n for n in numbers if not cdl.is_prime(n)]
        
        prime_kappas_scale = [cdl.kappa(p) for p in primes]
        comp_kappas_scale = [cdl.kappa(c) for c in composites]
        prime_avg = np.mean(prime_kappas_scale) if prime_kappas_scale else np.nan
        comp_avg = np.mean(comp_kappas_scale) if comp_kappas_scale else np.nan
        
        text = f'Primes: {len(primes)}\nComposites: {len(composites)}\n'
        text += f'Prime μ: {prime_avg:.2f}\nComp μ: {comp_avg:.2f}'
        
        ax.text(0.02, 0.98, text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', 
                facecolor='wheat', alpha=0.8), fontsize=9)
    
    plt.tight_layout()
    plt.savefig('cdl_scale_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: cdl_scale_comparison.png")
    plt.close()


def create_integration_examples():
    """Visualize integration port examples."""
    print("Generating integration examples...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Example 1: Prime diagnostic prefilter
    ax = axes[0, 0]
    candidates = list(range(1000, 1200))
    kappas = [cdl.kappa(n) for n in candidates]
    colors = ['blue' if cdl.is_prime(n) else 'red' for n in candidates]
    
    ax.scatter(candidates, kappas, c=colors, s=20, alpha=0.6)
    ax.axhline(y=1.5, color='green', linestyle='--', linewidth=2, label='Filter Threshold')
    ax.fill_between(candidates, 0, 1.5, alpha=0.1, color='blue', label='Pass to Full Test')
    
    ax.set_xlabel('Candidate n', fontsize=11)
    ax.set_ylabel('κ(n)', fontsize=11)
    ax.set_title('Prime Diagnostic Prefilter', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Example 2: QMC sampling bias
    ax = axes[0, 1]
    candidates = list(range(1000, 1050))
    original_order = list(range(len(candidates)))
    
    # Sort by kappa
    sorted_candidates = sorted(candidates, key=lambda n: cdl.kappa(n))
    new_order = [candidates.index(n) for n in sorted_candidates]
    
    ax.plot(original_order, label='Original Order', linewidth=2)
    ax.plot(new_order, label='κ-Biased Order', linewidth=2)
    
    ax.set_xlabel('Position in Queue', fontsize=11)
    ax.set_ylabel('Original Index', fontsize=11)
    ax.set_title('QMC Sampling Reordering', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Example 3: Signal normalization
    ax = axes[1, 0]
    positions = [10, 50, 100, 500, 1000, 5000]
    raw_signals = [p ** 1.5 for p in positions]  # Simulated raw signal
    normalized_signals = [cdl.signal_normalize_pipeline({p: raw_signals[i]}, v=1.0)[p] 
                         for i, p in enumerate(positions)]
    
    x = np.arange(len(positions))
    width = 0.35
    
    ax.bar(x - width/2, raw_signals, width, label='Raw Signal', alpha=0.7)
    ax.bar(x + width/2, normalized_signals, width, label='Z-Normalized', alpha=0.7)
    
    ax.set_xlabel('Position Index', fontsize=11)
    ax.set_ylabel('Signal Value', fontsize=11)
    ax.set_title('Signal Normalization Effect', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([str(p) for p in positions], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Example 4: Variance reduction
    ax = axes[1, 1]
    
    ranges = [(2, 100), (100, 500), (500, 1000), (1000, 2000)]
    raw_vars = []
    norm_vars = []
    
    for start, end in ranges:
        numbers = list(range(start, end))
        raw_signals = {n: n ** 2 for n in numbers}
        norm_signals = cdl.signal_normalize_pipeline(raw_signals, v=1.0)
        
        raw_vals = list(raw_signals.values())
        norm_vals = list(norm_signals.values())
        
        raw_var = np.var(raw_vals)
        norm_var = np.var(norm_vals)
        
        raw_vars.append(raw_var)
        norm_vars.append(norm_var)
    
    x = np.arange(len(ranges))
    width = 0.35
    
    ax.bar(x - width/2, raw_vars, width, label='Raw Variance', alpha=0.7)
    ax.bar(x + width/2, norm_vars, width, label='Normalized Variance', alpha=0.7)
    
    ax.set_xlabel('Range', fontsize=11)
    ax.set_ylabel('Variance', fontsize=11)
    ax.set_title('Variance Reduction Across Scales', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{s}-{e}' for s, e in ranges], rotation=45)
    ax.legend()
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('cdl_integration_examples.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: cdl_integration_examples.png")
    plt.close()


def main():
    """Generate all CDL dashboards."""
    print("\n" + "=" * 70)
    print("GENERATING CDL VALIDATION DASHBOARDS")
    print("=" * 70 + "\n")
    
    create_kappa_histograms()
    create_z_normalized_traces()
    create_classification_boundary()
    create_scale_comparison()
    create_integration_examples()
    
    print("\n" + "=" * 70)
    print("DASHBOARD GENERATION COMPLETE")
    print("=" * 70)
    print("\nGenerated files:")
    print("  • cdl_kappa_histograms.png")
    print("  • cdl_z_normalized_traces.png")
    print("  • cdl_classification_boundary.png")
    print("  • cdl_scale_comparison.png")
    print("  • cdl_integration_examples.png")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
