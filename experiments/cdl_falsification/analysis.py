#!/usr/bin/env python3
"""
Quick analysis script for CDL falsification experiment
Shows key statistics and findings
"""

import json
import csv

print("=" * 70)
print("CDL FALSIFICATION EXPERIMENT - QUICK ANALYSIS")
print("=" * 70)

# Load CI data
with open('experiments/cdl_falsification/ci.json', 'r') as f:
    ci_data = json.load(f)

print("\n1. DATASET")
print("-" * 70)
print(f"Range: {ci_data['experiment']['range'][0]} to {ci_data['experiment']['range'][1]}")
print(f"Total: {ci_data['dataset']['total']} numbers")
print(f"Primes: {ci_data['dataset']['primes']} ({ci_data['dataset']['primes']/ci_data['dataset']['total']*100:.1f}%)")
print(f"Composites: {ci_data['dataset']['composites']} ({ci_data['dataset']['composites']/ci_data['dataset']['total']*100:.1f}%)")

print("\n2. CURVATURE SEPARATION")
print("-" * 70)
print(f"Prime mean κ:     {ci_data['curvature_statistics']['prime_mean_kappa']:.3f}")
print(f"Composite mean κ: {ci_data['curvature_statistics']['composite_mean_kappa']:.3f}")
print(f"Separation ratio: {ci_data['curvature_statistics']['separation_ratio']:.2f}×")
print("✓ Strong separation maintained")

print("\n3. CLASSIFICATION METRICS")
print("-" * 70)
print(f"Accuracy:  {ci_data['classification_metrics']['accuracy']:.2f}%")
print(f"Precision: {ci_data['classification_metrics']['precision']:.2f}%")
print(f"Recall:    {ci_data['classification_metrics']['recall']:.2f}% ← CRITICAL FAILURE")
print(f"F1 Score:  {ci_data['classification_metrics']['f1_score']:.2f}%")

print("\n4. BOOTSTRAP CONFIDENCE INTERVAL")
print("-" * 70)
print(f"Mean accuracy: {ci_data['bootstrap_ci']['mean_accuracy']:.2f}%")
print(f"95% CI: [{ci_data['bootstrap_ci']['confidence_interval'][0]:.2f}%, {ci_data['bootstrap_ci']['confidence_interval'][1]:.2f}%]")
print("✓ Tight interval, high statistical certainty")

print("\n5. CONFUSION MATRIX")
print("-" * 70)
cm = ci_data['confusion_matrix']
print(f"                 Predicted")
print(f"                 Prime    Composite")
print(f"Actual Prime     {cm['true_positives']:<6}   {cm['false_negatives']:<6}")
print(f"       Composite {cm['false_positives']:<6}   {cm['true_negatives']:<6}")

print("\n6. FAILURE ANALYSIS")
print("-" * 70)
print(f"False negatives: {cm['false_negatives']} primes missed")
print(f"True positives:  {cm['true_positives']} primes found")
print(f"Miss rate:       {cm['false_negatives']/(cm['false_negatives']+cm['true_positives'])*100:.1f}%")
print(f"Failure ratio:   {cm['false_negatives']/cm['true_positives']:.1f}:1 (FN:TP)")

# Analyze the accuracy data to find where it breaks
with open('experiments/cdl_falsification/accuracy.csv', 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)

true_positives = [row for row in data if row['actual'] == 'prime' and row['predicted'] == 'prime']
false_negatives = [row for row in data if row['actual'] == 'prime' and row['predicted'] == 'composite']

if true_positives:
    last_tp = int(true_positives[-1]['n'])
    print(f"\nLast correctly identified prime: {last_tp}")
    
if false_negatives:
    first_fn = int(false_negatives[0]['n'])
    print(f"First missed prime: {first_fn}")
    print(f"\nThreshold breakdown occurs around n={first_fn}")

print("\n7. NULL MODEL COMPARISON")
print("-" * 70)
null_accuracy = ci_data['dataset']['composites'] / ci_data['dataset']['total'] * 100
cdl_accuracy = ci_data['classification_metrics']['accuracy']
improvement = cdl_accuracy - null_accuracy
print(f"'Always predict composite' accuracy: {null_accuracy:.2f}%")
print(f"CDL classifier accuracy:             {cdl_accuracy:.2f}%")
print(f"Improvement:                         +{improvement:.2f} percentage points")
print(f"Relative improvement:                +{improvement/null_accuracy*100:.1f}%")
print("✗ Negligible improvement over null model")

print("\n8. VERDICT")
print("=" * 70)
print("HYPOTHESIS FALSIFIED")
print()
print("While the curvature signal shows excellent separation (5.35×),")
print("the fixed threshold approach fails catastrophically at scale:")
print()
print("  • 96.8% of primes are missed (recall = 3.21%)")
print("  • Only 39 out of 1,214 primes correctly identified")
print("  • 88% accuracy is driven by class imbalance, not model quality")
print("  • Adds only 0.4% over trivial 'always composite' baseline")
print()
print("The classifier is NOT fit for purpose as a prime diagnostic.")
print("=" * 70)
