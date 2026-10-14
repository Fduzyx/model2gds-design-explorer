# License and publication review

The fixed Round6 archive already contains a project Apache-2.0 LICENSE and
NOTICE. They are copied byte-for-byte; this task selected no new license.
The archived NOTICE states the project source's existing license scope and
attributes SKY130 standard-cell material/open_pdks at pinned revisions.
The owner's confirmation of authorship/contribution and intended publication
scope remains a publication decision, not something established by a checksum.

Included third-party license copies:

- `third_party/sky130_fd_sc_hd/LICENSE` (preserved Apache-2.0 copy).
- `third_party/open_pdks/LICENSE` (preserved Apache-2.0 copy).
- `third_party/upstream_license_sources.json` records historical queried URLs,
  revisions and hashes. Two personal home-directory prefixes were replaced by
  `<original-user-pdk-root>` only in the staging copy; the original SHA-256 and
  modification are recorded in the separate private release records.

No complete PDK, standard-cell installation, full GDS/SPEF, EDA executable,
Docker image or dependency environment is redistributed. Layouts are existing
rendered selected top-level geometry; the archived NOTICE/layout manifest
specifies omitted cell internals, cuts and labels. Keep those notices and review
whether the chosen presentation/derived-data scope is acceptable before release.

Pinned Notebook requirements do not grant rights to redistribute dependencies.
They are listed, not installed or vendored. The Windows/Jupyter browser workflow
was not retested in this staging round.

The owner-only source manifest was excluded from this review tree. Use
relative-path FILE_MANIFEST.sha256 and this summary publicly. The existing
project LICENSE and upstream notices were compared with the pinned GitHub
submission; this was not a new legal determination or relicensing.
No LICENSE files were added to unrelated new projects by this agent.
