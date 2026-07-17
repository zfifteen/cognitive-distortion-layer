# Path B — Strongest Survivor Insight

## Part 1: Core Insight

```insight
Dual Channel: Frozen-Speed Mixture Recovery from Distortion Residuals

When the traversal speed is locked to the prime fixed-point value, the mixture
weights of simple versus complex integer families become directly readable from
the distribution of normalized residuals alone, with far fewer samples than the
same recovery needs from raw magnitudes.

What changes is the inverse problem we pose. Instead of asking which speed
produced a distortion stream under a known support law, we ask which support
mixture produced the stream under a known speed.

The non-obvious part is that the fixed-point speed turns prime mass into a
near-binary parking event at residual value one, so prime fraction estimation
collapses to a coin-flip frequency with Fisher information near 1 over pi times
one minus pi, while raw magnitudes of primes and composites remain heavily
overlapped on the same range.

This implies we should expect order-of-magnitude lower sample complexity for
estimating generator mass from residual streams than from unlabeled size
streams of equal length, without needing to recover speed jointly.

Concretely, synthetic probes on support up to twenty thousand show roughly ten
times lower absolute error for mixture-weight MLE from residuals than from log
size features at matched sample sizes, and roughly one hundred times higher
per-observation Fisher information for the residual channel at the fixed-point
speed.
```

## Verdict

**SURVIVOR** (strong for binary prime mass; qualified for full multi-family simplex)

## Mechanism (compact)

Canonical map at fixed \(v\):

\[
Z(n)=n\big/\exp(v\cdot\kappa(n))=n^{1-v\,d(n)/e^{2}}
\]

At \(v^{\star}=e^{2}/2\):

\[
Z(n)=n^{1-d(n)/2}
\]

so \(d=2\Rightarrow Z=1\) exactly, and \(d>2\Rightarrow Z<1\) for all \(n\ge 2\).
Thus \(\hat\pi_{\mathrm{park}}=\frac1M\sum_i\mathbf1\{Z_i=1\}\) is the MLE for prime mass under exact arithmetic, with Bernoulli Fisher \(I(\pi)=1/(\pi(1-\pi))\).

## What is dual to v-recovery

| | v-recovery (existing) | Path B (this probe) |
|---|---|---|
| Known | support / sequence prior | traversal rate \(v\) (esp. \(v^{\star}\)) |
| Unknown | \(v\) | mixture weights \(\pi\) over families |
| Observation | \(Z\) sequence | \(Z\) sequence |
| Special structure | moments/fingerprint vs \(v\)-grid | parking / separated family laws in \(Z\) |

Distinct from zpf joint \((\mathrm{regime},v)\): Path B freezes \(v\) and targets \(\pi\).

## Quantitative results (N=20 000, 40 trials)

Binary \(\pi_{\mathrm{prime}}\) recovery at \(v^{\star}\), MAE averaged over \(\pi\in\{0.1,0.25,0.4,0.55\}\):

| M | z_park | z_mle | n_mle | n_mle / z_mle |
|---:|---:|---:|---:|---:|
| 50 | 0.053 | 0.049 | 0.340 | 7.0 |
| 100 | 0.035 | 0.035 | 0.326 | 9.2 |
| 500 | 0.014 | 0.016 | 0.172 | 10.9 |
| 2000 | 0.008 | 0.008 | 0.091 | 11.1 |

Approx. per-observation Fisher at \(\pi=0.25\): \(I_Z\approx 4\text{–}6.5\) (matches \(1/(\pi(1-\pi))=5.33\)), \(I_n\approx 0.03\text{–}0.05\), ratio \(\sim 90\text{–}240\times\).

## Adversarial attacks and status

1. **“Z just encodes primality labels.”**  
   At exact \(v^{\star}\) with exact \(Z\), yes: parking is equivalent to a prime indicator. That is the mechanism, not a bug. The dual claim is that this indicator is a *distributional* observable of a fixed-\(v\) process channel, dual to recovering \(v\). Off \(v^{\star}\), park fails but calibrated log-\(Z\) MLE still separates families (v-sweep).

2. **“Computing Z needs d(n), so this cannot help primality.”**  
   Path B is not a primality algorithm. It is sample-complexity of \(\pi\) given already-observed \(Z\) vs already-observed \(n\) magnitudes (process audit / mixture ID).

3. **“Advantage is knife-edge at v*.”**  
   Park estimator is knife-edge (only \(v^{\star}\) gives exact mass at 1). log-\(Z\) MLE remains strong for a wide band of large \(v\) because mean log-\(Z\) separation grows with \(v\). Best MLE in the sweep was near \(v=2.5\), not uniquely \(v^{\star}\); \(v^{\star}\) is special for *model-free* parking, not for all MLE.

4. **“Raw n with modular features suffices.”**  
   n_fingerprint includes even / mod 3 / mod 5 fractions and still underperforms z_mle by large factors.

5. **Multi-family qualification.**  
   Mean L1 ratio n/z ≈ 3.6 favors Z, but some high-prime-mass cells at large M show ratio near 1. Tiny d=3 family (34 integers ≤20k) limits full simplex recovery. Strong claim is safest for **binary low-d mass** (prime fraction).

## Prior art delta

- **v_recovery**: opposite unknown (v vs π).
- **zpf**: joint (regime, v); Path B freezes v.
- **dfr / hidden_tuning**: family fixed points \(v_d=e^{2}/d\); Path B uses parking as a *statistical* sufficient structure for mixture weights, not as a band-flatness catalog.
- **Classical mixture MLE / Fisher**: standard tools; novelty is the CDL channel geometry that induces near-orthogonal family components in Z at frozen v.
- **PNT density 1/ln N**: fixed natural baseline; fails for arbitrary generator π (MAE ~0.22 constant).

## Falsifier (executable)

Reject strong survivor if, on support [2, N] with N≥10^4, for M≥250 and π_true in {0.1,0.25,0.4,0.55}, the mean MAE of the best Z estimator is not ≤ half the mean MAE of the best unlabeled raw-n estimator, or if multi-family mean L1 ratio n/z < 1.5.

**Status on this run:** falsifier not triggered (MAE ratio ≈10.7; multi L1 ratio ≈3.6).

## Reproduction

```bash
cd /Users/velocityworks/IdeaProjects/cognitive-distortion-layer
export PYTHONPATH=src/python
python3 artifacts/nie_probe_path_b/path_b_mixture_recovery.py
```

Artifacts:

- `path_b_results.json` — full cells, Fisher, v-sensitivity, multi-family
- `PATH_B_REPORT.md` — tables
- `path_b_mixture_recovery.py` — probe code
- `INSIGHT.md` — this file
