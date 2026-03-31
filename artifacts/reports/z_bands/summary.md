# Z-Bands Summary

## Methodology

- Platform: Apple Silicon only (`Darwin arm64`).
- Arithmetic stack: C99 with GMP and MPFR only.
- Construction path: fully deterministic, with no random generation and no fallback branches.
- Study mode: exact known-factorization families across decimal digit bands `1..256`.
- Samples per band and family: `1`.
- Per band-family pair, the harness emits a canonical deterministic construction replicated across the requested sample rows.
- MPFR precision: `8192` bits.
- Probable-prime repetitions: `64`.

## Mathematical Method

For each constructed integer `n`, the harness studies the divisor-count transform
`Z(n) = n^(1 - d(n)/2)`, where `d(n)` is the number of positive divisors of `n`.

This is the numerically stable closed form of the equivalent exponential expression
`Z(n) = n / exp(v * d(n) * ln(n) / e^2)` with `v = e^2 / 2`.

The key structural property is:

- If `d(n) = 2`, then `n` is prime and `Z(n) = 1` exactly.
- If `d(n) > 2`, then `n` is composite and `Z(n) < 1`.

This harness does not scan every integer in a range. Instead, it constructs representative
integers from exact factorization families. If `n = prod p_i^a_i`, then the divisor count is
`d(n) = prod (a_i + 1)`. Each family therefore fixes the divisor-count regime in advance and
lets the run compare how the same transform behaves across increasing digit bands.

## Family Definitions

| Family | Description | Exponents | d(n) | Minimum supported digits |
|---|---|---|---:|---:|
| `probable_prime` | Single probable prime; the exact fixed-point family with d(n)=2. | `1` | `2` | `1` |
| `semiprime_balanced` | Product of two distinct primes with matched scale; the basic semiprime family. | `1,1` | `4` | `1` |
| `prime_square` | Square of a prime; the simplest prime-power composite family. | `2` | `3` | `1` |
| `prime_cube` | Cube of a prime; a higher-curvature prime-power composite family. | `3` | `4` | `1` |
| `squarefree_3` | Product of three distinct primes; a low-multiplicity squarefree composite family. | `1,1,1` | `8` | `2` |
| `squarefree_6` | Product of six distinct primes; a higher-divisor squarefree composite family. | `1,1,1,1,1,1` | `64` | `5` |
| `smooth_4321` | Composite with exponent pattern 4,3,2,1; a smooth high-divisor family. | `4,3,2,1` | `120` | `5` |

## How to Read the Outputs

- `samples.csv` contains one row per emitted sample. Each row records the band, family, divisor count,
  the sampled integer's size metadata, and the transform outputs `Z(n)` and `-log10(Z)`.
- `bands.csv` aggregates those sample rows by band and family, including support status and contraction statistics.
- `z_sci` is the scientific-notation rendering of `Z(n)`.
- `neg_log10_z` is the contraction depth. Larger values mean smaller `Z(n)` and therefore stronger composite contraction.
- In this experiment, rows labeled `probable_prime` are fixed-point rows (`Z = 1`), while the composite families are contraction rows (`Z < 1`).

## Run Configuration

- Total band rows: `1792`
- Supported band rows: `1783`
- Unsupported band rows: `9`
- Total samples requested: `1792`
- Total samples built: `1783`

## Results

- Probable-prime fixed points: `256 / 256` rows emitted `Z = 1` exactly.
- Composite strict contractions: `1527 / 1527` rows emitted `-log10(Z) > 0`.
- Supported coverage was emitted for every band-family pair with `band_digits >= minimum supported digits`.

## Highlighted Examples

### Composite Closest to the Fixed Point

- Family: `prime_square`
- Band: `1`
- Sample index: `0`
- d(n): `3`
- Factor digit lengths: `1`
- Leading16: `4`
- Trailing16: `4`
- Z(n): `5.000000000000000000000000e-1`
- -log10(Z): `0.301029995663981195213739`

### Deepest Composite Contraction

- Family: `smooth_4321`
- Band: `256`
- Sample index: `0`
- d(n): `120`
- Factor digit lengths: `16,22,32,70`
- Leading16: `1000000000000000`
- Trailing16: `3441225045530647`
- Z(n): `10.000000000000000000000000e-15046`
- -log10(Z): `15045.000000000000000000000000`

