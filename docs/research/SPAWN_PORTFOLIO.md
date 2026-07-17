# CDL Spawn Portfolio (local scaffolds)

Parent: this repository.

Local child scaffolds under `~/IdeaProjects/`:

## Tier 1

| Repo | Package | Identity |
| --- | --- | --- |
| `/Users/velocityworks/IdeaProjects/divisor-family-resonance` | `dfr` | `v_d = e^2/d` family fixed points |
| `/Users/velocityworks/IdeaProjects/cdl-structural-threshold` | `cst` | `tau(b) = 2 ln(b)/e^2` + gap condition |
| `/Users/velocityworks/IdeaProjects/z-process-fingerprint` | `zpf` | joint `(regime, v)` process channel |

## Tier 2

| Repo | Package | Identity |
| --- | --- | --- |
| `/Users/velocityworks/IdeaProjects/divisor-power-transform` | `dpt` | `Z = n^(1-d/2)` pure transform |
| `/Users/velocityworks/IdeaProjects/analytic-curvature-series` | `acs` | kappa asymptotics and `K(s)` |
| `/Users/velocityworks/IdeaProjects/cognitive-distortion-field-study` | `cdfs` | external participant protocol |

## Already extracted elsewhere

- `prime-gap-structure`
- `geodesic-prime-prefilter`
- `prime-gap-structure-extensions`

## Scaffold contract

Each child has README, AGENTS, docs/SCOPE, docs/PARENT, MIT LICENSE, pyproject, smoke tests.
Scaffolds are not validated scientific results. Green smoke tests only check stub arithmetic.

## Parent CDL imports

Each child package exposes `src/<pkg>/_parent.py` which:

1. Resolves parent root as sibling `IdeaProjects/cognitive-distortion-layer`, or `CDL_ROOT`
2. Puts `parent/src/python` on `sys.path`
3. Imports `cdl` (and optionally `v_recovery`, `cdl_continuous`, `cognitive_pilot`)

Example:

```python
from dfr import import_cdl, power_z
cdl = import_cdl()
assert power_z(17) == 1.0
assert cdl.kappa(17) > 0
```
