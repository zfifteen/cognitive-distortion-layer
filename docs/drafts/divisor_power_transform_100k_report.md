# Exact Prime Fixed Points and Composite Contraction in the Divisor-Weighted Power Transform

## 1. Overview

This report documents a complete numerical experiment on every integer in the interval `2 <= n <= 100,000` using the divisor-weighted normalization

\[
Z(n) = \frac{n}{\exp\!\left(v \, d(n)\ln(n) / e^2\right)},
\qquad
v = \frac{e^2}{2}.
\]

Under this parameter choice, the transform simplifies exactly to

\[
Z(n) = n^{1 - d(n)/2},
\]

where `d(n)` is the number of positive divisors of `n`.

The headline result from the `10^5` run is exact separation on the tested interval:

- every prime in `2..100,000` maps to `Z(n) = 1.0`,
- every composite in `2..100,000` maps to `Z(n) < 1.0`.

Within this range, the transform produces a delta spike at `1.0` for primes and a sharply contracting composite distribution extending down to `2.98329148e-315`.

## 2. Definitions and Derivation

Let:

- `d(n)` be the number of positive divisors of `n`,
- `e = 2.718281828459045`,
- `v = e^2 / 2`.

Start from the exponential form:

\[
Z(n) = \frac{n}{\exp\!\left(v \, d(n)\ln(n) / e^2\right)}.
\]

Substituting `v = e^2 / 2` gives

\[
Z(n) = \frac{n}{\exp\!\left(\frac{d(n)}{2}\ln(n)\right)}.
\]

Using `exp(a ln n) = n^a`, this becomes

\[
Z(n) = \frac{n}{n^{d(n)/2}} = n^{1 - d(n)/2}.
\]

This closed form is algebraically identical to the original expression and is the numerically stable form used for the full experiment.

## 3. Immediate Structural Consequences

If `n` is prime, then `d(n) = 2`, so

\[
Z(n) = n^{1 - 2/2} = n^0 = 1.
\]

This is exact.

If `n` is composite, then `d(n) >= 3`, so

\[
1 - \frac{d(n)}{2} <= -\frac{1}{2},
\]

and therefore

\[
Z(n) < 1.
\]

The contraction steepens with divisor multiplicity:

| `d(n)` | Exponent `1 - d(n)/2` | Form of `Z(n)` |
|---|---:|---|
| `2` | `0` | `1` |
| `3` | `-1/2` | `1 / sqrt(n)` |
| `4` | `-1` | `1 / n` |
| `6` | `-2` | `1 / n^2` |
| `12` | `-5` | `1 / n^5` |

Prime squares therefore form the upper composite envelope, while numbers with many divisors collapse rapidly toward zero.

## 4. Experimental Protocol

The experiment computes `d(n)` for every integer from `1` to `100,000` with a divisor sieve:

```python
N = 100_000
divisors = [0] * (N + 1)
for i in range(1, N + 1):
    for j in range(i, N + 1, i):
        divisors[j] += 1
```

After the sieve, the transform is evaluated as

```python
z = n ** (1 - divisors[n] / 2.0)
```

This procedure has:

- sieve cost `O(N log N)`,
- transform cost `O(N)`,
- total memory `O(N)`.

The run reported here was executed directly in Python in this repository working directory with no dependency on existing CDL implementation files.

## 5. Numerical Results for `2 <= n <= 100,000`

### 5.1 Class counts and exact separation

| Quantity | Value |
|---|---:|
| Primes | `9,592` |
| Composites | `90,407` |
| Prime values equal to `1.0` exactly | `9,592 / 9,592` |
| Composite values below `1.0` | `90,407 / 90,407` |

On this interval, the classification rule

\[
Z(n) = 1.0 \iff n \text{ is prime}
\]

holds exactly.

### 5.2 Prime summary

| Statistic | Value |
|---|---:|
| Mean `Z` over primes | `1.0` |
| Min `Z` over primes | `1.0` |
| Max `Z` over primes | `1.0` |

The prime distribution is a single exact mass at `1.0`.

### 5.3 Composite summary

| Statistic | Value |
|---|---:|
| Mean `Z` over composites | `5.499753752709761e-05` |
| First quartile | `1.5430852658084735e-33` |
| Median | `2.6273940740306094e-15` |
| Third quartile | `1.0382437076448156e-05` |
| Maximum | `0.5` |
| Minimum | `2.98329148e-315` |

The composite distribution is strongly compressed toward zero, with the bulk of values many orders of magnitude below `1`.

### 5.4 Largest composite values

These are the composites closest to the prime fixed point:

| `n` | `d(n)` | `Z(n)` |
|---:|---:|---:|
| `4` | `3` | `0.5` |
| `9` | `3` | `0.3333333333333333` |
| `25` | `3` | `0.2` |
| `6` | `4` | `0.16666666666666666` |
| `49` | `3` | `0.14285714285714285` |
| `8` | `4` | `0.125` |
| `10` | `4` | `0.1` |
| `121` | `3` | `0.09090909090909091` |
| `169` | `3` | `0.07692307692307693` |
| `14` | `4` | `0.07142857142857142` |

The upper edge is dominated by prime squares because `d(p^2) = 3` gives the least negative composite exponent.

### 5.5 Smallest composite values

The strongest contractions occur at large integers with very high divisor counts:

| `n` | `d(n)` | `Z(n)` |
|---:|---:|---:|
| `98,280` | `128` | `2.98329148e-315` |
| `83,160` | `128` | `1.11016547847634e-310` |
| `95,760` | `120` | `1.2886527162192837e-294` |
| `92,400` | `120` | `1.0601167537425835e-293` |
| `90,720` | `120` | `3.1298285557221715e-293` |

The maximum divisor count attained in the interval is `128`, reached by `83,160` and `98,280`.

## 6. Divisor Count Stratification

The transform is controlled directly by divisor multiplicity, so families with fixed `d(n)` fall on distinct power-law strata.

Selected strata from the run:

| `d(n)` | Count | Mean `Z(n)` | Max `Z(n)` |
|---:|---:|---:|---:|
| `3` | `65` | `0.031115739380801796` | `0.5` |
| `4` | `23,327` | `0.00012490336672697314` | `0.16666666666666666` |
| `6` | `5,627` | `3.330907171204056e-06` | `0.006944444444444444` |
| `8` | `22,181` | `7.705024414796089e-09` | `7.233796296296296e-05` |
| `12` | `9,954` | `2.543668700533393e-13` | `1.286008230452675e-09` |
| `16` | `10,728` | `2.9782204916183714e-19` | `2.790816472336534e-15` |
| `120` | `7` | `1.859322205889425e-281` | `1.3014573048847912e-280` |
| `128` | `2` | `5.5509765569557e-311` | `1.11016547847634e-310` |

This stratification explains both the exact prime/composite split and the severe compression of highly composite numbers.

## 7. Reproducible Reference Implementation

```python
import statistics

N = 100_000

divisors = [0] * (N + 1)
for i in range(1, N + 1):
    for j in range(i, N + 1, i):
        divisors[j] += 1

prime_z = []
composite_z = []

for n in range(2, N + 1):
    d = divisors[n]
    z = n ** (1 - d / 2.0)
    if d == 2:
        prime_z.append(z)
    else:
        composite_z.append(z)

print("primes:", len(prime_z))
print("composites:", len(composite_z))
print("prime mean/min/max:", statistics.fmean(prime_z), min(prime_z), max(prime_z))
print("composite mean/min/max:", statistics.fmean(composite_z), min(composite_z), max(composite_z))
```

## 8. Interpretation

This normalization behaves as a divisor-sensitive contraction map with two exact regimes on the tested interval:

- primes are fixed points,
- composites are strict contractions.

The result is not merely approximate clustering. It is exact point separation at `Z = 1.0` for every prime in `2..100,000`, with composites pushed below that boundary by an amount determined by divisor multiplicity.

For this method, the decisive empirical fact from the `10^5` run is simple: the closed-form transform `Z(n) = n^{1 - d(n)/2}` converts the divisor count condition `d(n) = 2` into an exact normalized fixed point, while mapping the entire composite class into a strictly subunit band whose lower tail extends to near-underflow scale.

## 9. Conclusion

The `10^5` experiment establishes the following interval-specific result:

\[
\forall n \in \{2, \ldots, 100000\},
\qquad
Z(n) = 1.0 \text{ exactly for primes, and } Z(n) < 1.0 \text{ for composites.}
\]

The method is easy to reproduce, computationally cheap at sieve scale, and structurally transparent:

- the derivation is exact,
- the implementation is short,
- the prime fixed point is exact,
- the composite contraction is strict,
- the composite distribution is sharply stratified by divisor count.

That is the full technical content of the reproduced run.
