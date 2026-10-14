# Evidence and version boundaries

## Version identity

All copied source/evidence in this candidate came from the single existing
`Model2GDS_Design_Explorer_Round6.zip` archive, SHA-256:

`f12333db272702ba1de88e3a5b26043d47718eebec480aa423e100ed105e5e66`

Its 2,218,668-byte identity matched the adjacent pre-existing package manifest.
The archive's 52 member paths, CRCs and SHA-256 values were checked while reading;
20 evidence-manifest entries and 10 research-manifest entries matched before
staging. Original file identity was checked again after staging validation.
This establishes a fixed input archive, not a freeze or a commit of the active
source working tree. The adjacent package manifest is a checksum record, not
a cryptographic signature or proof of authorship.

## Research stages

1. Historical arithmetic/model versus RTL functional qualification covered
   441 case/configuration executions at sizes 2, 4, 8. The compact Explorer
   preserves twelve selected observations and their inputs, not that full runner.
2. FINAL_002 physical evidence binds the historical freeze commit
   `5239290e91f789d68fd8e4b282b54fdb086f6285` and recipe/source hashes. The independently
   qualified 2x2 and 4x4 members form an exploratory subset. The original full
   three-configuration family is still FAIL; 8x8 is not physically selectable.
3. The Round5 portable Explorer preserved model replay and selected historical
   RTL/physical evidence. The distinct official ISSCC submission is an earlier
   submission snapshot and has separate Git history. This candidate does not
   update the submission, its existing PR, or any remote repository.
4. Round6 adds objective/budget/area-basis decisions, analytic alpha thresholds,
   derived figures and read-only register-to-DEF/GDS mapping. It reuses old
   qualified implementation records; no fresh physical experiment is implied.

The local development report was consulted only to interpret historical claims;
it was not copied as authoritative executable source. It reports 19 targeted
Round6 Demo tests and completed browser operations after recorded failures. Those
are historical reports, not tests reproduced by this staging task. The complete
original archive remains necessary for a full signoff or license provenance audit.

## Separate present checks from past experiments

`VALIDATION.json` lists this round's actual staging checks: Python syntax,
Notebook structure, compact evidence integrity, twelve current model replays,
selection/budget/tie invariants, and preserved mapping consistency. These tests
only use the independent copied candidate. Full RTL regression, EDA signoff,
GDS re-extraction, dependency installation and browser UI are NOT_RUN.

## Publication scope

This candidate is REPRO for its compact Python replay and evidence-derived
selection calculations, plus an offline interactive interface when dependencies
are available. It is not a complete ASIC reproduction package. Decide whether
to use the existing project repository/branch before any future publication;
no new Git repository, push, release or PR action was performed here.
