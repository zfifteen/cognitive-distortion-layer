"""Tests for the production CDL geodesic prefilter module."""

from __future__ import annotations

import math
import sys
from pathlib import Path

from sympy import isprime


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import cdl
import cdl_prime_geodesic_prefilter as prefilter


def test_prefilter_rejects_small_factor_composites_and_keeps_prime_band():
    """The production proxy should contract easy composites and keep prime survivors."""
    geodesic = prefilter.CDLPrimeGeodesicPrefilter(bit_length=32, namespace="unit")

    assert geodesic.is_prime_candidate(101) is True
    assert geodesic.proxy_z(101) == 1.0

    composite = 3 * 101
    assert geodesic.is_prime_candidate(composite) is False
    assert geodesic.proxy_z(composite) < 1.0


def test_generate_prime_matches_first_baseline_survivor_on_same_stream():
    """The integrated generator should return the same first prime as MR-only search."""
    namespace = "unit:baseline"
    expected = None
    index = 0
    seen = set()

    while expected is None:
        candidate = prefilter.deterministic_odd_candidate(32, index, namespace=namespace)
        index += 1
        if candidate in seen:
            continue
        seen.add(candidate)
        if math.gcd(candidate - 1, 65537) != 1:
            continue
        if prefilter.miller_rabin_fixed_bases(candidate, prefilter.DEFAULT_MR_BASES):
            expected = candidate

    geodesic = prefilter.CDLPrimeGeodesicPrefilter(bit_length=32, namespace=namespace)
    actual = geodesic.generate_prime(public_exponent=65537)

    assert actual == expected
    assert prefilter.miller_rabin_fixed_bases(actual, prefilter.DEFAULT_MR_BASES) is True


def test_generate_rsa_prime_hits_exact_small_scale_fixed_point():
    """A generated small RSA prime should satisfy the exact sweet-spot fixed point."""
    prime = prefilter.generate_rsa_prime(bit_length=32, namespace="unit:rsa")

    assert isprime(prime) is True
    assert math.isclose(
        cdl.z_normalize(prime, v=prefilter.SWEET_SPOT_V),
        1.0,
        rel_tol=prefilter.FIXED_POINT_TOLERANCE,
        abs_tol=prefilter.FIXED_POINT_TOLERANCE,
    )
