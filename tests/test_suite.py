#!/usr/bin/env python3
"""
Test suite for Cognitive Distortion Layer (CDL)

Tests core primitives:
1. κ(n) curvature computation
2. Threshold-based classification
3. Z-normalization

Run with: python3 tests/test_suite.py
"""

import math
import numpy as np
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import cdl
from cognitive_pilot import CognitivePilot
from cdl_continuous import ContinuousVRecovery, generate_continuous_z_sequence, hybrid_classify, kappa_smooth, z_normalize_continuous
from v_recovery import VRecovery, generate_z_sequence


class TestResults:
    """Simple test results tracker."""
    __test__ = False

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_result(self, name, passed, message=""):
        self.tests.append((name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"TEST RESULTS: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for name, passed, msg in self.tests:
                if not passed:
                    print(f"  ✗ {name}: {msg}")
        print(f"{'='*70}\n")
        return self.failed == 0


def assert_close(actual, expected, tolerance=0.001, name=""):
    """Check if values are close within tolerance."""
    diff = abs(actual - expected)
    passed = diff <= tolerance
    msg = f"Expected {expected}, got {actual}, diff={diff}"
    return passed, msg


def _maybe_return_for_cli(passed):
    if __name__ == "__main__":
        return passed
    return None


def _coerce_result(result):
    if result is None:
        return True
    return bool(result)


def test_divisor_count():
    """Test divisor counting function."""
    print("\n" + "=" * 70)
    print("TEST: divisor_count()")
    print("=" * 70)
    
    results = TestResults()
    
    test_cases = [
        (1, 1),     # 1 has 1 divisor
        (2, 2),     # prime: 1, 2
        (3, 2),     # prime: 1, 3
        (4, 3),     # 1, 2, 4
        (6, 4),     # 1, 2, 3, 6
        (12, 6),    # 1, 2, 3, 4, 6, 12
        (28, 6),    # 1, 2, 4, 7, 14, 28
        (100, 9),   # 1, 2, 4, 5, 10, 20, 25, 50, 100
    ]
    
    for n, expected in test_cases:
        actual = cdl.divisor_count(n)
        passed = actual == expected
        results.add_result(
            f"divisor_count({n})",
            passed,
            f"Expected {expected}, got {actual}"
        )
        status = "✓" if passed else "✗"
        print(f"  {status} divisor_count({n:3}) = {actual} (expected {expected})")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_kappa_computation():
    """Test κ(n) computation."""
    print("\n" + "=" * 70)
    print("TEST: kappa(n)")
    print("=" * 70)
    
    results = TestResults()
    
    # Test known values
    test_cases = [
        (2, 2 * math.log(2) / math.e**2),
        (3, 2 * math.log(3) / math.e**2),
        (12, 6 * math.log(12) / math.e**2),
    ]
    
    for n, expected in test_cases:
        actual = cdl.kappa(n)
        passed, msg = assert_close(actual, expected, tolerance=0.001)
        results.add_result(f"kappa({n})", passed, msg)
        status = "✓" if passed else "✗"
        print(f"  {status} kappa({n:2}) = {actual:.4f} (expected {expected:.4f})")
    
    # Test properties
    print("\n  Property tests:")
    
    # 1. κ(n) > 0 for n >= 2
    passed = all(cdl.kappa(n) > 0 for n in range(2, 100))
    results.add_result("kappa(n) > 0 for n >= 2", passed)
    print(f"  {'✓' if passed else '✗'} kappa(n) > 0 for all n >= 2")
    
    # 2. Primes have lower average κ than composites
    primes = [n for n in range(2, 100) if cdl.is_prime(n)]
    composites = [n for n in range(2, 100) if not cdl.is_prime(n)]
    
    prime_avg = sum(cdl.kappa(p) for p in primes) / len(primes)
    comp_avg = sum(cdl.kappa(c) for c in composites) / len(composites)
    
    passed = comp_avg > prime_avg
    results.add_result("composites have higher avg kappa", passed)
    print(f"  {'✓' if passed else '✗'} composite avg κ ({comp_avg:.3f}) > prime avg κ ({prime_avg:.3f})")
    
    # 3. Monotonic growth within divisor class
    d_4_numbers = [n for n in range(2, 100) if cdl.divisor_count(n) == 4][:10]
    kappas = [cdl.kappa(n) for n in d_4_numbers]
    passed = all(kappas[i] < kappas[i+1] for i in range(len(kappas)-1))
    results.add_result("monotonic growth within d(n) class", passed)
    print(f"  {'✓' if passed else '✗'} κ(n) monotonically increases for fixed d(n)")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_classification():
    """Test threshold-based classification."""
    print("\n" + "=" * 70)
    print("TEST: classify()")
    print("=" * 70)
    
    results = TestResults()
    
    # Test seed set accuracy
    seed_numbers = list(range(2, 50))
    correct = 0
    
    for n in seed_numbers:
        classification = cdl.classify(n, threshold=1.5)
        actual = "prime" if cdl.is_prime(n) else "composite"
        if classification == actual:
            correct += 1
    
    accuracy = correct / len(seed_numbers)
    passed = accuracy >= 0.80  # At least 80% accuracy
    results.add_result(
        "seed set classification accuracy",
        passed,
        f"Accuracy {accuracy:.1%}, expected >= 80%"
    )
    print(f"  {'✓' if passed else '✗'} Seed set accuracy: {accuracy:.1%} (expected >= 80%)")
    
    # Test specific cases
    test_cases = [
        (2, "prime"),
        (3, "prime"),
        (7, "prime"),
        (11, "prime"),
        (12, "composite"),
        (30, "composite"),
    ]
    
    for n, expected in test_cases:
        actual = cdl.classify(n)
        passed = actual == expected
        results.add_result(f"classify({n})", passed)
        status = "✓" if passed else "✗"
        print(f"  {status} classify({n:2}) = {actual:9} (expected {expected})")
    
    # Test batch classification
    numbers = [2, 3, 4, 5, 6]
    batch_results = cdl.classify_batch(numbers)
    passed = len(batch_results) == len(numbers)
    results.add_result("batch classification", passed)
    print(f"  {'✓' if passed else '✗'} Batch classification returns {len(batch_results)} results")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_z_normalization():
    """Test Z-normalization."""
    print("\n" + "=" * 70)
    print("TEST: z_normalize()")
    print("=" * 70)
    
    results = TestResults()
    
    # Test Z(n) <= n
    test_numbers = [2, 7, 12, 30, 100]
    all_less = True
    for n in test_numbers:
        z = cdl.z_normalize(n, v=1.0)
        if z > n:
            all_less = False
        status = "✓" if z <= n else "✗"
        print(f"  {status} Z({n:3}) = {z:.3f} <= {n}")
    
    results.add_result("Z(n) <= n property", all_less)
    
    # Test v parameter effect
    n = 12
    z_light = cdl.z_normalize(n, v=0.5)
    z_standard = cdl.z_normalize(n, v=1.0)
    z_heavy = cdl.z_normalize(n, v=2.0)
    
    passed = z_light > z_standard > z_heavy
    results.add_result("v parameter ordering", passed)
    print(f"\n  {'✓' if passed else '✗'} v parameter effect:")
    print(f"      v=0.5: Z({n}) = {z_light:.3f}")
    print(f"      v=1.0: Z({n}) = {z_standard:.3f}")
    print(f"      v=2.0: Z({n}) = {z_heavy:.3f}")
    
    # Test composites compress more than primes
    prime = 7
    composite = 12
    z_prime = cdl.z_normalize(prime, v=1.0)
    z_comp = cdl.z_normalize(composite, v=1.0)
    
    prime_reduction = (1 - z_prime / prime)
    comp_reduction = (1 - z_comp / composite)
    
    passed = comp_reduction > prime_reduction
    results.add_result("composites compress more", passed)
    print(f"\n  {'✓' if passed else '✗'} Composites compress more:")
    print(f"      Prime {prime}: {prime_reduction:.1%} reduction")
    print(f"      Composite {composite}: {comp_reduction:.1%} reduction")
    
    # Test batch normalization
    numbers = [2, 7, 12, 30]
    batch_results = cdl.z_normalize_batch(numbers, v=1.0)
    passed = len(batch_results) == len(numbers)
    results.add_result("batch normalization", passed)
    print(f"\n  {'✓' if passed else '✗'} Batch normalization returns {len(batch_results)} results")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_integration_helpers():
    """Test integration helper functions."""
    print("\n" + "=" * 70)
    print("TEST: Integration Helpers")
    print("=" * 70)
    
    results = TestResults()
    
    # Test prime diagnostic prefilter
    candidates = list(range(10, 50))
    likely_primes, likely_composites = cdl.prime_diagnostic_prefilter(
        candidates,
        threshold=1.5,
        full_test_threshold=False
    )
    
    total = len(likely_primes) + len(likely_composites)
    passed = total == len(candidates)
    results.add_result("prefilter completeness", passed)
    print(f"  {'✓' if passed else '✗'} Prefilter: {len(likely_primes)} likely primes, "
          f"{len(likely_composites)} likely composites")
    
    # Test QMC sampling bias
    candidates = list(range(100, 120))
    biased = cdl.qmc_sampling_bias(candidates, bias_strength=1.0)
    
    # Check that first candidates have lower κ
    first_5_kappas = [cdl.kappa(n) for n in biased[:5]]
    last_5_kappas = [cdl.kappa(n) for n in biased[-5:]]
    
    avg_first = sum(first_5_kappas) / len(first_5_kappas)
    avg_last = sum(last_5_kappas) / len(last_5_kappas)
    
    passed = avg_first < avg_last
    results.add_result("QMC bias ordering", passed)
    print(f"  {'✓' if passed else '✗'} QMC bias: first 5 avg κ = {avg_first:.3f}, "
          f"last 5 avg κ = {avg_last:.3f}")
    
    # Test signal normalization
    signals = {10: 100.0, 20: 400.0, 30: 900.0}
    normalized = cdl.signal_normalize_pipeline(signals, v=1.0)
    
    passed = len(normalized) == len(signals)
    results.add_result("signal normalization", passed)
    print(f"  {'✓' if passed else '✗'} Signal normalization processes {len(normalized)} signals")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_baseline_reproduction():
    """Test that baseline results are reproduced."""
    print("\n" + "=" * 70)
    print("TEST: Baseline Reproduction (n=2-49)")
    print("=" * 70)
    
    results = TestResults()
    
    seed_numbers = list(range(2, 50))
    primes = [n for n in seed_numbers if cdl.is_prime(n)]
    composites = [n for n in seed_numbers if not cdl.is_prime(n)]
    
    prime_kappas = [cdl.kappa(p) for p in primes]
    composite_kappas = [cdl.kappa(c) for c in composites]
    
    prime_avg = sum(prime_kappas) / len(prime_kappas)
    composite_avg = sum(composite_kappas) / len(composite_kappas)
    
    # Check prime average (expected ~0.739)
    passed, msg = assert_close(prime_avg, 0.739, tolerance=0.01)
    results.add_result("prime avg κ ≈ 0.739", passed, msg)
    print(f"  {'✓' if passed else '✗'} Prime avg κ = {prime_avg:.3f} (expected ~0.739)")
    
    # Check composite average (expected ~2.252)
    passed, msg = assert_close(composite_avg, 2.252, tolerance=0.05)
    results.add_result("composite avg κ ≈ 2.252", passed, msg)
    print(f"  {'✓' if passed else '✗'} Composite avg κ = {composite_avg:.3f} (expected ~2.252)")
    
    # Check separation ratio (expected ~3.05)
    ratio = composite_avg / prime_avg
    passed = 2.8 <= ratio <= 3.3
    results.add_result("separation ratio ≈ 3.05", passed)
    print(f"  {'✓' if passed else '✗'} Separation ratio = {ratio:.2f}× (expected ~3.05×)")
    
    # Check classification accuracy (expected ~83%)
    correct = 0
    for n in seed_numbers:
        classification = cdl.classify(n, threshold=1.5)
        actual = "prime" if cdl.is_prime(n) else "composite"
        if classification == actual:
            correct += 1
    
    accuracy = correct / len(seed_numbers)
    passed = 0.75 <= accuracy <= 0.95
    results.add_result("classification accuracy ≈ 83%", passed)
    print(f"  {'✓' if passed else '✗'} Classification accuracy = {accuracy:.1%} (expected ~83%)")
    
    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_v_recovery():
    """Test traversal-rate recovery from synthetic Z sequences."""
    print("\n" + "=" * 70)
    print("TEST: v Recovery")
    print("=" * 70)

    results = TestResults()
    rng = np.random.default_rng(321)
    recovery = VRecovery(
        calibration_n_max=3000,
        sample_size=500,
        sequence_type="random",
        reference_trials=10,
        random_seed=321,
    )
    v_true = 1.5
    z_sequence, _ = generate_z_sequence(
        numbers=recovery.numbers,
        kappas=recovery.kappas,
        rng=rng,
        v=v_true,
        sample_size=500,
        sequence_type="random",
        noise_level=0.01,
        prime_mask=recovery.prime_mask,
    )

    mle_result = recovery.infer_v(z_sequence, method="mle")
    fingerprint_result = recovery.infer_v(z_sequence, method="fingerprint")
    moment_result = recovery.infer_v(z_sequence, method="moment_match")

    mle_passed = abs(mle_result.v_estimate - v_true) <= 0.05
    results.add_result(
        "MLE recovers v within 0.05",
        mle_passed,
        f"Expected {v_true}, got {mle_result.v_estimate:.4f}",
    )
    print(
        f"  {'✓' if mle_passed else '✗'} MLE estimate = {mle_result.v_estimate:.4f} "
        f"(target {v_true:.2f})"
    )

    fingerprint_passed = abs(fingerprint_result.v_estimate - v_true) <= 0.10
    results.add_result(
        "fingerprint recovers v within 0.10",
        fingerprint_passed,
        f"Expected {v_true}, got {fingerprint_result.v_estimate:.4f}",
    )
    print(
        f"  {'✓' if fingerprint_passed else '✗'} Fingerprint estimate = "
        f"{fingerprint_result.v_estimate:.4f} (target {v_true:.2f})"
    )

    moment_passed = abs(moment_result.v_estimate - v_true) <= 0.10
    results.add_result(
        "moment matching recovers v within 0.10",
        moment_passed,
        f"Expected {v_true}, got {moment_result.v_estimate:.4f}",
    )
    print(
        f"  {'✓' if moment_passed else '✗'} Moment-match estimate = "
        f"{moment_result.v_estimate:.4f} (target {v_true:.2f})"
    )

    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_adaptive_threshold_protocol():
    """Test the Sprint 1 adaptive threshold map and partial QMC bias."""
    print("\n" + "=" * 70)
    print("TEST: Adaptive Threshold Protocol")
    print("=" * 70)

    results = TestResults()

    threshold = cdl.find_adaptive_threshold(1000, 9999)
    threshold_passed = abs(threshold - 2.4921548014819255) <= 0.05
    results.add_result(
        "adaptive threshold on 1K–9.99K window",
        threshold_passed,
        f"Expected ≈2.49, got {threshold:.4f}",
    )
    print(
        f"  {'✓' if threshold_passed else '✗'} Adaptive τ(1000–9999) = {threshold:.4f}"
    )

    adaptive_label = cdl.classify(1009, adaptive=True)
    label_passed = adaptive_label == "prime"
    results.add_result("adaptive classify prime", label_passed, adaptive_label)
    print(f"  {'✓' if label_passed else '✗'} classify(1009, adaptive=True) = {adaptive_label}")

    candidates = list(range(100, 120))
    original = cdl.qmc_sampling_bias(candidates, bias_strength=0.0)
    partial = cdl.qmc_sampling_bias(candidates, bias_strength=0.5)
    full = cdl.qmc_sampling_bias(candidates, bias_strength=1.0)
    qmc_passed = original == candidates and partial != full and partial != original
    results.add_result("partial QMC bias is distinct", qmc_passed)
    print(f"  {'✓' if qmc_passed else '✗'} Partial QMC bias produces a distinct ordering")

    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_continuous_extension():
    """Test the Sprint 5 continuous extension and v recovery transfer."""
    print("\n" + "=" * 70)
    print("TEST: Continuous Extension")
    print("=" * 70)

    results = TestResults()

    smooth_value = kappa_smooth(500000.0)
    smooth_passed, msg = assert_close(smooth_value, 23.5785088518, tolerance=0.05)
    results.add_result("kappa_smooth(500000) matches asymptotic target", smooth_passed, msg)
    print(
        f"  {'✓' if smooth_passed else '✗'} kappa_smooth(500000) = {smooth_value:.4f}"
    )

    z_value = z_normalize_continuous(10000.5, v=0.115)
    z_passed = z_value <= 10000.5
    results.add_result("continuous Z reduces magnitude", z_passed)
    print(f"  {'✓' if z_passed else '✗'} Z_continuous(10000.5) = {z_value:.4f}")

    hybrid_passed = hybrid_classify(101.0) == cdl.classify(101)
    results.add_result("hybrid classify falls back on integers", hybrid_passed)
    print(f"  {'✓' if hybrid_passed else '✗'} hybrid_classify(101.0) matches exact classify")

    rng = np.random.default_rng(123)
    recovery = ContinuousVRecovery(
        x_min=1000.0,
        x_max=1_000_000.0,
        support_points=8000,
        sample_size=2000,
        reference_trials=8,
        random_seed=123,
    )
    z_sequence, _ = generate_continuous_z_sequence(
        rng=rng,
        v=1.5,
        sample_size=2000,
        x_min=1000.0,
        x_max=1_000_000.0,
        noise_level=0.03,
    )
    inference = recovery.infer_v(z_sequence, method="fingerprint")
    recovery_passed = abs(inference.v_estimate - 1.5) <= 0.05
    results.add_result(
        "continuous fingerprint recovery",
        recovery_passed,
        f"Expected 1.5, got {inference.v_estimate:.4f}",
    )
    print(
        f"  {'✓' if recovery_passed else '✗'} Continuous fingerprint estimate = "
        f"{inference.v_estimate:.4f}"
    )

    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def test_cognitive_pilot():
    """Test the Sprint 6 cognitive pilot on a deterministic participant."""
    print("\n" + "=" * 70)
    print("TEST: Cognitive Pilot")
    print("=" * 70)

    results = TestResults()
    pilot = CognitivePilot(
        n_max=10_000,
        participant_trials=120,
        support_size=20_000,
        reference_trials=16,
        random_seed=20260330,
    )
    rng = np.random.default_rng(77)
    payload = pilot.simulate_participant(
        participant_id="P01",
        v_true=1.7,
        rng=rng,
        n_trials=120,
        noise_sigma=0.06,
    )
    participant = pilot.run_participant(
        payload["presented_n"],
        payload["perceived_z"],
        participant_id=payload["participant_id"],
    )
    comparison = pilot.compare_hybrid_vs_continuous(payload["perceived_z"], v_true=1.7)

    recovery_passed = abs(participant.v_recovered - 1.7) <= 0.15
    results.add_result(
        "pilot recovers participant v within 0.15",
        recovery_passed,
        f"Expected 1.7, got {participant.v_recovered:.4f}",
    )
    print(
        f"  {'✓' if recovery_passed else '✗'} Pilot estimate = "
        f"{participant.v_recovered:.4f} (target 1.70)"
    )

    style_passed = participant.cognitive_style == "compressed distortion"
    results.add_result("pilot style classification", style_passed, participant.cognitive_style)
    print(
        f"  {'✓' if style_passed else '✗'} Cognitive style = "
        f"{participant.cognitive_style}"
    )

    improvement_passed = comparison["hybrid_error"] < comparison["continuous_error"]
    results.add_result(
        "hybrid pilot beats pure continuous recovery",
        improvement_passed,
        f"hybrid={comparison['hybrid_error']:.4f}, continuous={comparison['continuous_error']:.4f}",
    )
    print(
        f"  {'✓' if improvement_passed else '✗'} Hybrid error = "
        f"{comparison['hybrid_error']:.4f}, continuous error = {comparison['continuous_error']:.4f}"
    )

    passed = results.summary()
    assert passed
    return _maybe_return_for_cli(passed)


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "=" * 70)
    print("CDL TEST SUITE")
    print("=" * 70)
    
    all_passed = True
    
    # Run all test modules
    all_passed &= _coerce_result(test_divisor_count())
    all_passed &= _coerce_result(test_kappa_computation())
    all_passed &= _coerce_result(test_classification())
    all_passed &= _coerce_result(test_z_normalization())
    all_passed &= _coerce_result(test_integration_helpers())
    all_passed &= _coerce_result(test_baseline_reproduction())
    all_passed &= _coerce_result(test_adaptive_threshold_protocol())
    all_passed &= _coerce_result(test_v_recovery())
    all_passed &= _coerce_result(test_continuous_extension())
    all_passed &= _coerce_result(test_cognitive_pilot())
    
    # Final summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
