# Z-Bands Summary

## Methodology

- Platform: Apple Silicon only (`Darwin arm64`).
- Arithmetic stack: C99 with GMP and MPFR only.
- Construction path: fully deterministic, with no random generation and no fallback branches.
- Study mode: exact known-factorization families across decimal digit bands `1..32`.
- Samples per band and family: `4`.
- Per band-family pair, the harness emits a canonical deterministic construction replicated across the requested sample rows.
- MPFR precision: `8192` bits.
- Probable-prime repetitions: `64`.

## Family Definitions

| Family | Exponents | d(n) | Minimum supported digits |
|---|---|---:|---:|
| `probable_prime` | `1` | `2` | `1` |
| `semiprime_balanced` | `1,1` | `4` | `1` |
| `prime_square` | `2` | `3` | `1` |
| `prime_cube` | `3` | `4` | `1` |
| `squarefree_3` | `1,1,1` | `8` | `2` |
| `squarefree_6` | `1,1,1,1,1,1` | `64` | `5` |
| `smooth_4321` | `4,3,2,1` | `120` | `5` |

## Run Configuration

- Total band rows: `224`
- Supported band rows: `215`
- Unsupported band rows: `9`
- Total samples requested: `896`
- Total samples built: `860`

## Results

- Probable-prime fixed points: `128 / 128` rows emitted `Z = 1` exactly.
- Composite strict contractions: `732 / 732` rows emitted `-log10(Z) > 0`.
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
- Band: `32`
- Sample index: `0`
- d(n): `120`
- Factor digit lengths: `2,3,4,15`
- Leading16: `1000000000000002`
- Trailing16: `8259322833581929`
- Z(n): `9.999999999998332699952819e-1830`
- -log10(Z): `1829.000000000000072409921017`

