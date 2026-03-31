#!/usr/bin/env python3
"""Deterministic CDL geodesic prefilter for cryptographic prime generation."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence


SWEET_SPOT_V = math.e ** 2 / 2.0
FIXED_POINT_TOLERANCE = 1e-12

DEFAULT_NAMESPACE = "cdl-prime-geodesic"
DEFAULT_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19)

DEFAULT_PRIMARY_PRIME_LIMIT = 200003
DEFAULT_PRIMARY_CHUNK_SIZE = 256
DEFAULT_TAIL_PRIME_LIMIT = 300007
DEFAULT_TAIL_CHUNK_SIZE = 256
DEFAULT_DEEP_TAIL_PRIME_LIMIT = 1000003
DEFAULT_DEEP_TAIL_CHUNK_SIZE = 256
DEFAULT_DEEP_TAIL_MIN_BITS = 4096


def deterministic_odd_candidate(
    bit_length: int,
    index: int,
    namespace: str = DEFAULT_NAMESPACE,
) -> int:
    """Build one deterministic odd candidate with the requested bit length."""
    if bit_length < 2:
        raise ValueError("bit_length must be at least 2")
    if index < 0:
        raise ValueError("index must be non-negative")

    byte_length = (bit_length + 7) // 8
    digest = bytearray()
    counter = 0
    while len(digest) < byte_length:
        payload = f"{namespace}:{bit_length}:{index}:{counter}".encode("utf-8")
        digest.extend(hashlib.sha256(payload).digest())
        counter += 1

    value = int.from_bytes(digest[:byte_length], "big")
    value &= (1 << bit_length) - 1
    value |= 1 << (bit_length - 1)
    value |= 1
    return value


def miller_rabin_fixed_bases(
    n: int,
    bases: Sequence[int] = DEFAULT_MR_BASES,
) -> bool:
    """Run the fixed-base Miller-Rabin path used in the crypto benchmarks."""
    if n < 2:
        return False

    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if n in small_primes:
        return True
    for prime in small_primes:
        if n % prime == 0:
            return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for base in bases:
        a = base % n
        if a in (0, 1, n - 1):
            continue

        x = pow(a, d, n)
        if x in (1, n - 1):
            continue

        witness_failed = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                witness_failed = False
                break

        if witness_failed:
            return False

    return True


def sieve_primes(limit: int) -> list[int]:
    """Generate primes up to limit with a deterministic sieve."""
    if limit < 2:
        return []

    flags = bytearray(b"\x01") * (limit + 1)
    flags[:2] = b"\x00\x00"
    primes: list[int] = []
    for value in range(2, limit + 1):
        if not flags[value]:
            continue
        primes.append(value)
        start = value * value
        if start <= limit:
            flags[start : limit + 1 : value] = b"\x00" * (((limit - start) // value) + 1)
    return primes


class WheelPrimeTable:
    """Deterministic prime table with chunked GCD batches for fast factor discovery."""

    def __init__(self, limit: int, chunk_size: int, start_exclusive: int = 2) -> None:
        if limit < 3:
            raise ValueError("prime table limit must be at least 3")
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
        if start_exclusive >= limit:
            raise ValueError("start_exclusive must be smaller than limit")

        self.limit = limit
        self.chunk_size = chunk_size
        self.start_exclusive = start_exclusive
        self.primes = [
            prime
            for prime in sieve_primes(limit)
            if prime != 2 and prime > start_exclusive
        ]
        self.chunks: list[list[int]] = []
        self.chunk_products: list[int] = []

        for start in range(0, len(self.primes), chunk_size):
            chunk = self.primes[start : start + chunk_size]
            product = 1
            for prime in chunk:
                product *= prime
            self.chunks.append(chunk)
            self.chunk_products.append(product)

    def find_small_factor(self, n: int) -> int | None:
        """Return one prime factor from this interval if it is present."""
        for chunk, product in zip(self.chunks, self.chunk_products):
            if math.gcd(n, product) == 1:
                continue
            for prime in chunk:
                if n % prime == 0:
                    return prime
        return None

    def divisor_lower_bound(self, n: int) -> tuple[float, int | None]:
        """Return the divisor lower bound induced by the first factor found."""
        factor = self.find_small_factor(n)
        if factor is None:
            return 2.0, None

        residual = n
        exponent = 0
        while residual % factor == 0:
            residual //= factor
            exponent += 1

        d_lower = float(exponent + 1)
        if residual > 1:
            d_lower *= 2.0
        return d_lower, factor


class CDLPrimeGeodesicPrefilter:
    """Deterministic CDL accelerator locked to the sweet-spot prime band."""

    def __init__(
        self,
        bit_length: int = 1024,
        namespace: str = DEFAULT_NAMESPACE,
        mr_bases: Sequence[int] = DEFAULT_MR_BASES,
    ) -> None:
        if bit_length < 2:
            raise ValueError("bit_length must be at least 2")

        self.bit_length = bit_length
        self.namespace = namespace
        self.mr_bases = tuple(mr_bases)
        self.v = SWEET_SPOT_V
        self._candidate_index = 0
        self._seen_candidates: set[int] = set()

        self.primary_table = WheelPrimeTable(
            DEFAULT_PRIMARY_PRIME_LIMIT,
            DEFAULT_PRIMARY_CHUNK_SIZE,
        )
        self.tail_table = WheelPrimeTable(
            DEFAULT_TAIL_PRIME_LIMIT,
            DEFAULT_TAIL_CHUNK_SIZE,
            start_exclusive=DEFAULT_PRIMARY_PRIME_LIMIT,
        )
        self.deep_tail_table = None
        if bit_length >= DEFAULT_DEEP_TAIL_MIN_BITS:
            self.deep_tail_table = WheelPrimeTable(
                DEFAULT_DEEP_TAIL_PRIME_LIMIT,
                DEFAULT_DEEP_TAIL_CHUNK_SIZE,
                start_exclusive=DEFAULT_TAIL_PRIME_LIMIT,
            )

    def _proxy(self, n: int) -> dict[str, float | int | bool | str | None]:
        """Evaluate the deterministic geodesic proxy for one candidate."""
        if n < 2:
            return {
                "z_hat": 0.0,
                "d_est": 0.0,
                "rejected": True,
                "smallest_factor": None,
                "factor_source": "invalid",
            }

        d_est, smallest_factor = self.primary_table.divisor_lower_bound(n)
        factor_source = "primary"

        if smallest_factor is None:
            d_est, smallest_factor = self.tail_table.divisor_lower_bound(n)
            factor_source = "tail"

        if (
            smallest_factor is None
            and self.deep_tail_table is not None
            and n.bit_length() >= DEFAULT_DEEP_TAIL_MIN_BITS
        ):
            d_est, smallest_factor = self.deep_tail_table.divisor_lower_bound(n)
            factor_source = "deep_tail"

        if smallest_factor is not None:
            z_hat = math.exp((1.0 - d_est / 2.0) * math.log(n))
        else:
            z_hat = 1.0
            factor_source = "survivor"

        return {
            "z_hat": z_hat,
            "d_est": d_est,
            "rejected": bool(z_hat < 1.0 - FIXED_POINT_TOLERANCE),
            "smallest_factor": smallest_factor,
            "factor_source": factor_source,
        }

    def proxy_z(self, n: int) -> float:
        """Return the proxy Z-band position for one candidate."""
        return float(self._proxy(n)["z_hat"])

    def is_prime_candidate(self, n: int) -> bool:
        """Return True when the candidate survives the CDL geodesic prefilter."""
        return not bool(self._proxy(n)["rejected"])

    def is_probable_prime(
        self,
        n: int,
        public_exponent: int | None = None,
        excluded_values: set[int] | None = None,
    ) -> bool:
        """Return True when the candidate survives the band test and fixed-base MR."""
        if not self.is_prime_candidate(n):
            return False
        if public_exponent is not None and math.gcd(n - 1, public_exponent) != 1:
            return False
        if excluded_values is not None and n in excluded_values:
            return False
        return miller_rabin_fixed_bases(n, self.mr_bases)

    def _next_odd_candidate(self) -> int:
        """Yield the next deterministic odd candidate for this prefilter instance."""
        while True:
            candidate = deterministic_odd_candidate(
                self.bit_length,
                self._candidate_index,
                namespace=self.namespace,
            )
            self._candidate_index += 1
            if candidate in self._seen_candidates:
                continue
            self._seen_candidates.add(candidate)
            return candidate

    def generate_prime(
        self,
        public_exponent: int | None = None,
        excluded_values: set[int] | None = None,
    ) -> int:
        """Generate a deterministic probable prime with CDL in front of Miller-Rabin."""
        while True:
            candidate = self._next_odd_candidate()
            if self.is_probable_prime(
                candidate,
                public_exponent=public_exponent,
                excluded_values=excluded_values,
            ):
                return candidate


def generate_rsa_prime(
    bit_length: int = 1024,
    namespace: str = DEFAULT_NAMESPACE,
    public_exponent: int = 65537,
) -> int:
    """Generate one deterministic RSA prime with the CDL geodesic prefilter."""
    prefilter = CDLPrimeGeodesicPrefilter(bit_length=bit_length, namespace=namespace)
    return prefilter.generate_prime(public_exponent=public_exponent)


__all__ = [
    "CDLPrimeGeodesicPrefilter",
    "DEFAULT_MR_BASES",
    "DEFAULT_NAMESPACE",
    "FIXED_POINT_TOLERANCE",
    "SWEET_SPOT_V",
    "WheelPrimeTable",
    "deterministic_odd_candidate",
    "generate_rsa_prime",
    "miller_rabin_fixed_bases",
    "sieve_primes",
]
