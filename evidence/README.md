# Portable historical evidence

Run `python verify.py` here to verify included records and derivations. This does not rerun RTL, physical signoff or the complete repository collector.

The original FINAL_002 three-size family remains FAIL. Only its independently qualified 2x2 and 4x4 are included in the separate post-result exploration. STA is a fixed-layout internal-path estimate, not silicon measurement.

`manifest.json` maps every portable file to its original repository path and SHA-256. Selected RTL JSONL records retain original line bytes and indices. Full GDS, SPEF, netlists, tools and all raw signoff evidence stay in the original local archive, indexed by `physical.json`; this small bundle is sufficient for presentation and replay, not a replacement EDA archive.
