# Model2GDS · Evidence-Grounded Design Explorer

Offline Jupyter/ipywidgets prototype for DAC. Reuses six fixed GEMM workloads and
independently qualified FINAL_002 2×2/4×4 ASIC implementations. The original
three-size family remains FAIL; 8×8 never enters physical selection.

With Python 3.12+ and dependencies installed once from `requirements.txt`:

```text
python launch.py
```

Wait for kernel **Idle**, then **Run → Run All Cells**. The package works from any
working directory and needs no network, Docker, OpenLane or PDK at show time.
No additional round-6 dependencies were introduced.
After restarting the kernel, reload the browser page before Run All if widgets
stop responding. The validated Jupyter environment can otherwise retain a stale
subshell identifier. A saved output is not proof that the current kernel ran.

Standard-library CLI, also runnable from another directory:

```text
python /path/to/model2gds_explorer/app.py --workload W4 --objective weighted --alpha 0.95 --area-metric core
python /path/to/model2gds_explorer/app.py --workload W4 --objective weighted --alpha 0.95 --area-metric cell
```

## Five-minute demonstration

| Time | Operation | Explain |
|---|---|---|
| 0:00–0:50 | W1, Both fit: cycles → latency → ADP | 4×4 is faster; 2×2 has lower area×latency. Different objective, no timing reversal. |
| 0:50–2:00 | W4, weighted, α=0.95; switch Core / Cell; press exact-tie button | The explicit area definition and analytic threshold explain the choice. Preserve both at a tie. |
| 2:00–2:45 | Both fit → Only smaller fits → Nothing fits; enter an exact area boundary | Filter A ≤ budget before minimizing score. Empty means no feasible option. |
| 2:45–3:30 | Both fit, trace array 4×4, Play or scrub Edge | Current Python matches saved RTL observations; no simulator is running. |
| 3:30–4:30 | Logic → physical evidence, then Historical routed layout | Preserved accumulator signals identify actual FFs in netlist, DEF and named GDS references. Dots are not PE boundaries. |
| 4:30–5:00 | Tradeoff overview, expand evidence | All six workloads retained; two physical layouts; qualified but exploratory subset. |

Core and cell budgets have different meanings. Changing the area basis resets
the numeric budget to the selected preset; Custom resets to Both fit. α is used
only by the weighted objective; ADP uses exactly α=1. The tie button uses the
unrounded threshold. A numerical tie band is not an uncertainty estimate.

## What is being executed

- **Current Python:** unchanged golden/token model recomputes preserved inputs;
  two most recent workload/array traces are cached in the kernel. The animation
  is not a captured RTL waveform or a silicon timing trace.
- **Historical RTL:** recorded matrices, cycles and tiles are checked against
  current Python. The 441-case total is historical coverage, not fresh runs.
- **Historical ASIC:** two independently qualified layouts provide actual
  tool-reported areas, fixed-layout R2R STA estimates and GDS images.
- **Current decisions:** cycles, latency, ADP, weighted score, Pareto candidates
  and exact budgets. Different objectives do not imply timing reversal.
- **Read-only mapping:** 128/512 accumulator FFs are matched by retained signal,
  final instance, DEF coordinate and native GDS property/transform. Example STA
  endpoints identify source/destination state; no per-PE area/delay, arithmetic
  cone boundary or input-dependent critical-path activity is claimed.

`evidence/verify.py` checks the unchanged compact raw RTL/physical records.
`research/manifest.json` binds the new derived data, figures and source excerpts.
Raw archive identifiers are provenance, not local runtime dependencies. The full
original archive remains necessary for a fresh complete signoff audit.

STA latency is recorded RTL cycles × fixed-layout internal R2R STA period. It is
not measured silicon Fmax, complete IO closure or system latency. Both candidates
are Pareto non-dominated, not endpoints of a continuous realizable frontier.
Only one recipe and two physical layouts exist here; six workloads are not six
physical replications. No new physical result or novel optimization algorithm is
claimed. Model/RTL semantics and the separate round-5/ISSCC releases are unchanged.

Apache-2.0; see LICENSE and NOTICE. Repository reproduction and actual validation
records are indexed in `reports/dac27_round6.md` in the development checkout.
