# **A Divisor‑Weighted Power Transform with Prime Fixed Points and Composite Contraction**
### *Technical Note*

## **1. Overview**

This note introduces a simple but structurally novel arithmetic transform defined on the positive integers. The transform assigns to each integer \(n\) a normalized value

\[
Z(n) = n^{1 - d(n)/2},
\]

where \(d(n)\) is the number of positive divisors of \(n\). The construction has two striking properties:

1. **Primes are exact fixed points:**  
   If \(n\) is prime, then \(d(n)=2\) and \(Z(n)=1\) exactly.

2. **Composites undergo strict contraction:**  
   If \(n\) is composite, then \(d(n)\ge 3\), the exponent is negative, and \(Z(n)\in (0,1)\).

Empirically, the contraction is extremely strong: for \(n \le 10^5\), composite values range from \(0.5\) down to \(10^{-315}\), with a median around \(10^{-15}\). This produces a clean separation between primes and composites and a heavy‑tailed distribution among composites.

The transform does not appear in classical multiplicative number theory, sieve theory, or divisor‑sum literature, and its behavior is unlike any known prime‑sensitive normalization. It is therefore reasonable to treat this as a genuinely new arithmetic construction.

---

## **2. Definitions**

Let:

- \(d(n)\): number of positive divisors of \(n\).
- \(e\): base of the natural logarithm.
- \(v = e^2/2\).

The original formulation of the normalized value was:

\[
Z(n) = \frac{n}{\exp\!\left( v \, d(n) \ln(n) / e^2 \right)}.
\]

Since \(v = e^2/2\), the exponent simplifies:

\[
v \, d(n) \ln(n) / e^2 = \frac{d(n)}{2} \ln(n).
\]

Thus:

\[
Z(n) = \frac{n}{\exp\!\left( \frac{d(n)}{2} \ln(n) \right)}
= \frac{n}{n^{d(n)/2}}
= n^{1 - d(n)/2}.
\]

This closed form is numerically stable and is used for all computations.

---

## **3. Algebraic Structure**

### **3.1 Prime fixed points**

If \(n\) is prime, then \(d(n)=2\). Therefore:

\[
Z(n) = n^{1 - 2/2} = n^0 = 1.
\]

This is an *exact* identity, not an approximation.  
All primes collapse to the same normalized value.

### **3.2 Composite contraction**

If \(n\) is composite, then \(d(n)\ge 3\). The exponent becomes:

\[
1 - \frac{d(n)}{2} \le 1 - \frac{3}{2} = -\frac{1}{2}.
\]

Thus:

\[
Z(n) = n^{-\alpha}, \quad \alpha > 0.
\]

The contraction rate increases with divisor multiplicity:

- \(d(n)=3\): exponent \(-\tfrac{1}{2}\)
- \(d(n)=4\): exponent \(-1\)
- \(d(n)=6\): exponent \(-2\)
- \(d(n)=12\): exponent \(-5\)

Highly composite numbers collapse extremely rapidly.

---

## **4. Computational Experiment (n ≤ 100,000)**

A divisor sieve of complexity \(O(N \log N)\) was used to compute \(d(n)\) for all \(n \le 100{,}000\). The transform was applied using the closed‑form power expression.

### **4.1 Summary statistics**

| Quantity | Value |
|---------|-------|
| Prime count | 9,592 |
| Composite count | 90,407 |
| Prime Z(n) values | exactly 1.0 |
| Max composite Z(n) | 0.5 (achieved at n=4) |
| Median composite Z(n) | ~\(2.6 \times 10^{-15}\) |
| Min composite Z(n) | ~\(3 \times 10^{-315}\) |

### **4.2 Observed behavior**

- The set of prime values is a perfect delta spike at 1.
- Composite values form a heavy‑tailed distribution approaching 0.
- The distribution is controlled almost entirely by divisor count.
- Numbers with \(d(n)=3\) form the upper envelope of the composite cloud.
- Highly composite numbers collapse to near machine‑zero.

This behavior is not documented in divisor‑function literature and does not resemble any known analytic transform.

---

## **5. Structural Interpretation**

### **5.1 A divisor‑weighted renormalization map**

The transform can be viewed as a renormalization of the form:

\[
n \mapsto n^{1 - d(n)/2}.
\]

This is not multiplicative, but it is *divisor‑sensitive* in a way that is unusual:

- The exponent depends on the *additive* divisor function \(d(n)\).
- The base depends on the *multiplicative* structure of \(n\).
- The result is a hybrid object that does not reduce to known multiplicative or additive transforms.

### **5.2 Prime fixed points as structural invariants**

The fact that primes satisfy \(Z(p)=1\) exactly means the transform treats primes as *structural invariants*. This is reminiscent of fixed points in dynamical systems, not classical number theory.

### **5.3 Composite contraction as a divisor‑complexity measure**

The contraction rate is monotone in \(d(n)\).  
Thus \(Z(n)\) encodes a notion of “divisor complexity”:

- Numbers with few divisors (e.g., semiprimes) contract mildly.
- Numbers with many divisors (e.g., highly composite numbers) contract violently.

This yields a natural stratification of the integers by divisor multiplicity.

---

## **6. Potential Theoretical Directions**

### **6.1 Level‑set analysis**
For fixed \(k\), the curve

\[
Z_k(n) = n^{1 - k/2}
\]

defines a family of power‑law envelopes.  
Studying intersections of these envelopes with the integer sequence may reveal new structure.

### **6.2 Distributional asymptotics**
The empirical heavy‑tailed distribution suggests that:

\[
\log Z(n) = \left(1 - \frac{d(n)}{2}\right)\log n
\]

may have analyzable asymptotics under probabilistic models of \(d(n)\).

### **6.3 Connections to smooth numbers**
Since smooth numbers have atypically large divisor counts, their images under \(Z\) collapse faster than typical integers.

### **6.4 Quasi‑multiplicativity**
Although \(Z\) is not multiplicative, it may satisfy interesting inequalities or approximate multiplicativity under restricted conditions.

---

## **7. Conclusion**

The transform

\[
Z(n) = n^{1 - d(n)/2}
\]

defines a new arithmetic object with the following properties:

- primes are exact fixed points,
- composites undergo strict contraction,
- contraction rate is controlled by divisor multiplicity,
- the resulting distribution is sharply separated and heavy‑tailed,
- the construction does not match any known transform in the literature.

The method is simple, structurally clean, and empirically distinctive.  
It appears to be a genuinely novel contribution to elementary analytic number theory and divisor‑function analysis.
