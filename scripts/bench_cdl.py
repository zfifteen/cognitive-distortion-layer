#!/usr/bin/env python3
"""
CDL Benchmark Script
Tests CDL hypothesis on specified range with bootstrap CI
Usage: python scripts/bench_cdl.py --range 50 10000 --threshold 1.5 --boot 1000
"""

import argparse
import json
import math
import sys
import os
from pathlib import Path
import numpy as np
from sympy import divisors, isprime

# Add parent directory to path to import cdl
sys.path.insert(0, str(Path(__file__).parent.parent))


def divisor_count(n: int) -> int:
    """Count divisors using sympy."""
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


def bootstrap_accuracy(preds: np.ndarray, truths: np.ndarray, n_boot: int = 1000) -> tuple:
    """95% CI for accuracy %."""
    if len(preds) == 0:
        return 0.0, np.array([0.0, 0.0])
    
    accs = []
    np.random.seed(42)  # For reproducibility
    for _ in range(n_boot):
        idx = np.random.choice(len(preds), len(preds), replace=True)
        acc = np.mean(preds[idx] == truths[idx]) * 100
        accs.append(acc)
    mean_acc = np.mean(accs)
    ci = np.percentile(accs, [2.5, 97.5])
    return mean_acc, ci


def compute_metrics(preds: np.ndarray, truths: np.ndarray) -> dict:
    """Compute classification metrics."""
    # Confusion matrix
    tp = np.sum((preds == 'prime') & (truths == 'prime'))
    fp = np.sum((preds == 'prime') & (truths == 'composite'))
    tn = np.sum((preds == 'composite') & (truths == 'composite'))
    fn = np.sum((preds == 'composite') & (truths == 'prime'))
    
    # Metrics
    accuracy = (tp + tn) / len(preds) * 100 if len(preds) > 0 else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': {
            'true_positives': int(tp),
            'false_positives': int(fp),
            'true_negatives': int(tn),
            'false_negatives': int(fn)
        }
    }


def run_benchmark(start: int, end: int, threshold: float, n_boot: int, output_dir: str):
    """Run CDL benchmark on specified range."""
    print("=" * 70)
    print("CDL BENCHMARK: HYPOTHESIS FALSIFICATION EXPERIMENT")
    print("=" * 70)
    print(f"\nDataset: n = {start} to {end}")
    print(f"Threshold: κ = {threshold}")
    print(f"Bootstrap samples: {n_boot}")
    print(f"Output directory: {output_dir}")
    print("\n" + "-" * 70)
    
    # Generate candidates
    print(f"Generating candidates in range [{start}, {end}]...")
    candidates = np.arange(start, end + 1)
    
    # Classify using CDL
    print(f"Computing κ(n) and classifying {len(candidates)} candidates...")
    preds = []
    truths = []
    kappa_values = []
    
    for i, n in enumerate(candidates):
        if i % 1000 == 0:
            print(f"  Progress: {i}/{len(candidates)} ({i*100/len(candidates):.1f}%)")
        
        pred = classify(n, threshold)
        truth = 'prime' if isprime(n) else 'composite'
        k = kappa(n)
        
        preds.append(pred)
        truths.append(truth)
        kappa_values.append(k)
    
    preds = np.array(preds)
    truths = np.array(truths)
    kappa_values = np.array(kappa_values)
    
    print(f"  Progress: {len(candidates)}/{len(candidates)} (100.0%)")
    
    # Compute metrics
    print("\nComputing metrics...")
    metrics = compute_metrics(preds, truths)
    
    # Bootstrap CI
    print(f"Computing bootstrap confidence intervals ({n_boot} resamples)...")
    mean_acc, ci = bootstrap_accuracy(preds, truths, n_boot)
    
    # Separate by actual primality
    prime_mask = truths == 'prime'
    composite_mask = truths == 'composite'
    
    prime_kappas = kappa_values[prime_mask]
    composite_kappas = kappa_values[composite_mask]
    
    prime_mean = np.mean(prime_kappas) if len(prime_kappas) > 0 else 0
    composite_mean = np.mean(composite_kappas) if len(composite_kappas) > 0 else 0
    separation_ratio = composite_mean / prime_mean if prime_mean > 0 else 0
    
    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nDataset Statistics:")
    print(f"  Total numbers: {len(candidates)}")
    print(f"  Primes: {np.sum(prime_mask)}")
    print(f"  Composites: {np.sum(composite_mask)}")
    
    print(f"\nCurvature Statistics:")
    print(f"  Prime avg κ:     {prime_mean:.3f}")
    print(f"  Composite avg κ: {composite_mean:.3f}")
    print(f"  Separation ratio: {separation_ratio:.2f}×")
    
    print(f"\nClassification Performance:")
    print(f"  Accuracy:  {metrics['accuracy']:.2f}%")
    print(f"  Precision: {metrics['precision']:.2f}%")
    print(f"  Recall:    {metrics['recall']:.2f}%")
    print(f"  F1 Score:  {metrics['f1_score']:.2f}%")
    
    print(f"\nBootstrap 95% CI:")
    print(f"  Mean accuracy: {mean_acc:.2f}%")
    print(f"  CI: [{ci[0]:.2f}%, {ci[1]:.2f}%]")
    
    print(f"\nConfusion Matrix:")
    cm = metrics['confusion_matrix']
    print(f"  True Positives:  {cm['true_positives']}")
    print(f"  False Positives: {cm['false_positives']}")
    print(f"  True Negatives:  {cm['true_negatives']}")
    print(f"  False Negatives: {cm['false_negatives']}")
    
    # Save results
    print(f"\nSaving results to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save accuracy.csv
    accuracy_data = np.column_stack((candidates, kappa_values, preds, truths))
    accuracy_file = os.path.join(output_dir, 'accuracy.csv')
    np.savetxt(
        accuracy_file,
        accuracy_data,
        delimiter=',',
        header='n,kappa,predicted,actual',
        fmt='%s',
        comments=''
    )
    print(f"  ✓ {accuracy_file}")
    
    # Save ci.json
    ci_data = {
        'experiment': {
            'range': [int(start), int(end)],
            'threshold': threshold,
            'bootstrap_samples': n_boot
        },
        'dataset': {
            'total': int(len(candidates)),
            'primes': int(np.sum(prime_mask)),
            'composites': int(np.sum(composite_mask))
        },
        'curvature_statistics': {
            'prime_mean_kappa': float(prime_mean),
            'composite_mean_kappa': float(composite_mean),
            'separation_ratio': float(separation_ratio)
        },
        'classification_metrics': {
            'accuracy': float(metrics['accuracy']),
            'precision': float(metrics['precision']),
            'recall': float(metrics['recall']),
            'f1_score': float(metrics['f1_score'])
        },
        'bootstrap_ci': {
            'mean_accuracy': float(mean_acc),
            'confidence_interval': [float(ci[0]), float(ci[1])]
        },
        'confusion_matrix': metrics['confusion_matrix']
    }
    
    ci_file = os.path.join(output_dir, 'ci.json')
    with open(ci_file, 'w') as f:
        json.dump(ci_data, f, indent=2)
    print(f"  ✓ {ci_file}")
    
    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
    
    return ci_data


def main():
    parser = argparse.ArgumentParser(description='CDL Benchmark Script')
    parser.add_argument('--range', nargs=2, type=int, default=[50, 10000],
                        help='Range of numbers to test (default: 50 10000)')
    parser.add_argument('--threshold', type=float, default=1.5,
                        help='Classification threshold (default: 1.5)')
    parser.add_argument('--boot', type=int, default=1000,
                        help='Bootstrap samples (default: 1000)')
    parser.add_argument('--output-dir', type=str, default='experiments/cdl_falsification',
                        help='Output directory (default: experiments/cdl_falsification)')
    
    args = parser.parse_args()
    
    start, end = args.range
    threshold = args.threshold
    n_boot = args.boot
    output_dir = args.output_dir
    
    run_benchmark(start, end, threshold, n_boot, output_dir)


if __name__ == '__main__':
    main()
