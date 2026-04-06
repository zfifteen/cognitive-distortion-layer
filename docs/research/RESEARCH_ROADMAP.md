# CDL / Z Framework Research Roadmap

**Environment:** MacBook Pro M1 Max, 32GB, Python 3 + Xcode 26 + LLM stack (Perplexity Max, ChatGPT Pro, xAI Premium)
**Sprint cadence:** 1–3 day focused sprints (12–18h), 1–2 day breaks between

---

## Sprint 0: Restoration (1 day)
**Goal:** Unarchive the project and establish a clean working baseline.

- [ ] Move cognitive-number-theory-main out of archive into a dedicated active repo
- [ ] Commit the revised AGENTS.md (with threshold-invariance and scaffolding-boundary additions)
- [ ] Commit the Codex-generated executive_summary.md (with the three recommended edits applied)
- [ ] Run full test suite: `python tests/test_suite.py` and `python scripts/reports/baseline_report.py` — confirm all metrics reproduce
- [ ] Create a ROADMAP.md in the repo root pointing to this document
- [ ] Set up a dedicated Perplexity Space (done) and pin docs/specification/CDL_SPECIFICATION.md + artifacts/reports/baseline_report.json as sources

**Exit criterion:** Green test suite, revised docs committed, repo publicly visible.

---

## Sprint 1: Threshold Invariance Resolution (2–3 days)
**Goal:** Replace the single fixed τ = 1.5 claim with a documented, range-adaptive threshold protocol.

**Context:** The falsification experiment confirms τ = 1.5 yields 3.21% recall on n=50–10K.
Codex found τ ≈ 2.5 gives 100% recall and 98.3% precision on that range.
This is a threshold configuration problem, not a signal problem.

Tasks:
- [ ] Implement `find_adaptive_threshold(n_min, n_max)` in `src/python/cdl.py` — fits τ on a seed window, reports optimal value
- [ ] Generate a threshold map: τ_optimal vs. log(n_range_midpoint) for ranges [2–49], [50–999], [1K–9.99K], [10K–99.9K]
- [ ] Characterize the false positive population — confirm Codex's finding that FPs are semiprimes and prime squares
- [ ] Document the range-adaptive protocol in docs/specification/CDL_SPECIFICATION.md (replaces the current τ = 1.5 universal claim)
- [ ] Update docs/specification/INTEGRATION.md Port 1 to show range-aware prefilter usage
- [ ] Add data/reference/threshold_map.csv to the repository

**LLM role:** Use ChatGPT Pro o3 (code interpreter) for the threshold map generation and FP characterization.
**Exit criterion:** τ = 1.5 universal claim retired; adaptive protocol documented and tested.

---

## Sprint 2: Scaffolding Audit and Repair (1–2 days)
**Goal:** Repair the known issues in helper scripts so the full codebase matches the CDL core's quality level.

Issues identified by Codex:
1. scripts/demos/main.py — ML validation has label/feature misalignment; n included as raw feature
2. `qmc_sampling_bias()` in `src/python/cdl.py` — partial-bias branch collapses to full sort for any nonzero value
3. scripts/reports/baseline_report.py ablation — uses synthetic n² signal; understates the normalization's real-world relevance

Tasks:
- [ ] Fix scripts/demos/main.py ML validation: remove n as raw feature, align label generation with feature construction
- [ ] Fix qmc_sampling_bias(): implement true partial bias (weighted blend of sorted and random order)
- [ ] Redesign the ablation in scripts/reports/baseline_report.py: replace n² synthetic signal with a real-world-like signal (e.g., sampled from data/simulated/results_load_*.csv data)
- [ ] Re-run scripts/reports/baseline_report.py and confirm metrics hold or improve
- [ ] Add regression tests for qmc_sampling_bias() behavior at bias_strength = 0, 0.5, 1.0

**Exit criterion:** All three issues resolved, test suite still green, no regression in validated metrics.

---

## Sprint 3: The v-Learning Problem — Prior Robustness and Identifiability (3 days)
**Goal:** Extend the implemented inverse path into a prior-robust recovery protocol.

The first-pass inverse now exists in code. `src/python/v_recovery.py` implements moment matching, MLE, and a 20-dimensional distributional fingerprint. `tests/test_suite.py` verifies integer-space recovery, continuous-domain recovery, and participant-level recovery in the cognitive pilot. The open frontier is no longer whether `v` can be recovered at all. The open frontier is how reliably it can be recovered when the support law is only partially known.

Tasks:
- [ ] Write a compact theory note that distinguishes pointwise inversion of unknown `n` from distributional recovery of `v` under calibrated prior
- [ ] Quantify prior mismatch: generate sequences under `random`, `prime_biased`, and `composite_heavy` supports and measure `v` drift under wrong priors
- [ ] Characterize identifiability as a function of sample size, noise level, and support window
- [ ] Test joint inference of sequence regime and `v`
- [ ] Document a process-fingerprinting protocol for sampler auditing and participant inference
- [ ] Write `EXPERIMENT_REPORT.md` with matched-prior and mismatched-prior recovery tables

**M1 Max relevance:** scipy + numpy on M1 Max handles the calibration grids and sample sweeps without issue. No GPU needed at this stage.
**LLM role:** Use Perplexity Space for literature on inverse problems from transformed distributions. Use xAI Grok for exploratory reasoning on identifiability and prior mismatch.
**Exit criterion:** Prior-robust recovery protocol documented with explicit failure modes and sample-size limits.

---

## Sprint 4: Analytic Number Theory Connections (2–3 days)
**Goal:** Ground κ(n) in the known analytic number theory literature on d(n) distribution.

**Context:** κ(n) = d(n) · ln(n) / e². The distribution of d(n) is deeply studied.
Known results: average order of d(n) is ln(n); Dirichlet's theorem gives Σ d(k) ~ n ln(n).
The connection to the Riemann Hypothesis runs through the Divisor Problem (how tightly can you bound the error in Dirichlet's theorem?).

Tasks:
- [ ] Write a literature map: identify 5–8 results from analytic number theory that directly relate to d(n) · ln(n)
- [ ] Show formally that the prime average κ ≈ 0.739 is derivable (or at least bounded) from known prime divisor count results (d(p) = 2 always, so κ(p) = 2 · ln(p) / e²; the average over primes in [2,49] follows directly)
- [ ] Examine whether the 3.05× separation ratio has a theoretical floor derivable from prime number theorem density arguments
- [ ] Write connections/ANALYTIC_CONNECTIONS.md documenting these links
- [ ] Identify where the connections break down and what new results would be needed

**LLM role:** Perplexity Space + Perplexity Deep Research for literature retrieval.
**Exit criterion:** Analytic connections document written; at least one separation-ratio bound derived or shown to require new work.

---

## Sprint 5: Continuous Domain Extension — Feasibility Study (2 days)
**Goal:** Determine whether κ(n) can be extended to non-integer or continuous domains in a principled way.

The integer constraint in d(n) is the main obstacle. Two candidate approaches:
1. Analytic continuation via the Riemann zeta function (d(n) has generating function ζ(s)²)
2. Smooth interpolation: replace d(n) with a continuous approximation (e.g., using the average order ln(n) + correction terms)

Tasks:
- [ ] Implement a smooth κ approximation: κ_smooth(x) = (ln(x) + 2γ - 1) · ln(x) / e² where γ is the Euler–Mascheroni constant (this uses the average order of d(n))
- [ ] Compare κ_smooth(n) vs κ(n) for integers n ∈ [2, 1000] — characterize where they agree and diverge
- [ ] Test whether the prime/composite separation holds under κ_smooth (it will degrade; quantify by how much)
- [ ] Document the tradeoff: integer κ is exact and separating; continuous κ_smooth is smooth but loses classification power
- [ ] Write experiments/continuous_extension/FEASIBILITY.md

**Exit criterion:** κ_smooth implemented and compared; feasibility document written with clear go/no-go recommendation for deeper work.

---

## Sprint 6: Public Research Artifact (1–2 days)
**Goal:** Ship the project as a citable, accessible public artifact.

Tasks:
- [ ] Replace README.md lede with the result-first framing (model: Codex revised executive summary)
- [ ] Replace executive_summary.md with the revised Codex version (with the three edits applied)
- [ ] Add ROADMAP.md linking to open frontiers
- [ ] Tag v2.0.0 on the repository — the first version released under the Z Framework framing rather than the cognitive science framing
- [ ] Post a brief thread on X (@alltheputs) summarizing the 88.2% hold-out result and the three open frontiers — link to the repo
- [ ] Submit to relevant math/CS communities (r/math, r/MachineLearning as a crosspost, HN Show HN)

**Exit criterion:** v2.0.0 tagged; public post live; repo publicly accessible.

---

## Ongoing: LLM Stack Allocation

| Task type | Tool | Reason |
|---|---|---|
| Code generation and repair | Codex (with AGENTS.md) | Project-aware, in-repo context |
| Mathematical reasoning | xAI Grok | Strong on exploratory math |
| Literature retrieval | Perplexity Space | CDL-framed, cites sources |
| Long-form analysis | ChatGPT Pro o3 | Deep code interpreter for data work |
| Sanity checks | Perplexity Space | Ground truth for confirmed results |

---

## Hardware Notes

The M1 Max is well-matched to every sprint in this roadmap:
- All Python computation (scipy, numpy, sympy) runs natively on ARM — no emulation overhead
- n up to ~10M fits comfortably in 32GB for κ precomputation with caching
- The bottleneck will be divisor counting at large n (O(√n) per number) — precompute and cache aggressively for n > 100K
- No GPU is needed for any sprint above; if v-learning moves to neural inference, CoreML/MPS is available on M1 Max without cloud cost

---

## Sprint Sequencing Summary

| Sprint | Duration | Priority | Dependency |
|---|---|---|---|
| 0 — Restoration | 1 day | Blocker | None |
| 1 — Threshold Invariance | 2–3 days | Critical | Sprint 0 |
| 2 — Scaffolding Repair | 1–2 days | High | Sprint 0 |
| 3 — Prior-Robust v Recovery | 3 days | Highest research value | Sprint 1 |
| 4 — Analytic Connections | 2–3 days | High theoretical value | Sprint 1 |
| 5 — Continuous Extension | 2 days | Medium | Sprint 4 |
| 6 — Public Artifact | 1–2 days | High visibility value | Sprints 1–2 |

Sprints 3 and 4 can run in parallel across separate working sessions.
Sprint 6 can be pulled forward once Sprints 1 and 2 are complete if momentum warrants early publication.
