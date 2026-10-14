# Explorer snapshot and reproduction scope

This compact candidate uses the existing fixed Round6 portable package selected
in earlier preparation. The archive identity is SHA-256
`f12333db272702ba1de88e3a5b26043d47718eebec480aa423e100ed105e5e66`.
Its Python models, selected evidence and original Apache-2.0 LICENSE/NOTICE
remain intact. Preparation changes the landing-page explanation and integrity
index, rather than selecting changing files from an active research checkout.

## Existing research and this demonstration

The existing Model2GDS research entry is the pinned ISSCC contribution linked
in the README. This independent Explorer has a different small demonstration
scope: reading records, recomputing model traces and evaluating exact choices
between two preserved implementations. It neither changes the submission nor
claims an additional accepted publication.

The original ISSCC sprint FINAL_002 reports 2x2 qualified, 4x4 antenna failure
and 8x8 not run. The later, separately indexed DAC round2 FINAL_002 reports a
qualified 2x2/4x4 subset. Equal labels are not equal runs. The full three-size
physical family remains FAIL. Physical areas and timing estimates are tool
reports, never measured silicon.

## Small preparation check executed 2026-10-11

`python -B checks/verify_candidate.py` passed on this copied snapshot:

- ten Python AST checks and 2 Notebook code-cell syntax checks;
- twenty evidence and ten research manifest entries;
- twelve current Python versus preserved RTL observations;
- thirty-six decision calculations plus budget/tie boundaries;
- 640 preserved accumulator-register associations.

No fresh RTL simulation, full 441-case regression, synthesis, routing, signoff,
power measurement, new layout extraction or Notebook/browser interaction ran.
Dependencies were not installed. Original `VALIDATION.json` remains historical.

## Rights and publication boundary

The existing Apache-2.0 project license is retained; no MIT license is assigned.
NOTICE and the two upstream license copies stay with the selected rendered
geometry. No full PDK, GDS/SPEF, EDA toolchain or dependency environment is
redistributed. Permission to activate publication and use a distinct Explorer
repository is a separate owner decision recorded privately, not in this tree.
