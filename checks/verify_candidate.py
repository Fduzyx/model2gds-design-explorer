#!/usr/bin/env python3
"""Check only this compact staging candidate; no RTL/EDA/network execution."""
from pathlib import Path
import ast
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from app import Evidence
from physical_view import mapping_view


def main():
    parsed = []
    for path in sorted(ROOT.rglob('*.py')):
        ast.parse(path.read_text(encoding='utf-8'), filename=path.name)
        parsed.append(path.relative_to(ROOT).as_posix())
    notebook = json.loads((ROOT / 'Explorer.ipynb').read_text(encoding='utf-8'))
    assert notebook['nbformat'] == 4
    code_cells = [c for c in notebook['cells'] if c['cell_type'] == 'code']
    for cell in code_cells:
        ast.parse(''.join(cell['source']))
        assert cell.get('execution_count') is None and not cell.get('outputs')

    manifest_counts = {}
    for directory in ('evidence', 'research'):
        base = ROOT / directory
        entries = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))['files']
        for entry in entries:
            path = (base / entry['path']).resolve()
            assert path.is_relative_to(base.resolve())
            data = path.read_bytes()
            assert len(data) == entry['bytes']
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
        manifest_counts[directory] = len(entries)

    evidence = Evidence()
    replay = []
    decisions = []
    for wid in sorted(evidence.vectors):
        for size in (2, 4):
            result = evidence.replay(wid, size)
            assert result['numerical_match'] and result['cycle_match'] and result['tiles_match']
            assert result['fresh_rtl_run'] is False
            replay.append({'workload': wid, 'array_size': size,
                           'current_cycles': result['current']['cycles'],
                           'comparison': 'Current Python vs preserved RTL observation',
                           'status': 'PASS'})
        for metric in ('core', 'cell'):
            for objective, expected in [('cycles', [4]), ('latency', [4]), ('adp', [2])]:
                selected = evidence.select(wid, None, objective=objective, area_metric=metric)
                assert selected['winner_set'] == expected
                decisions.append({'workload': wid, 'metric': metric,
                                  'objective': objective, 'winner_set': expected})
            empty = evidence.select(wid, 0, area_metric=metric)
            assert empty['winner_set'] == [] and empty['decision_status'] == 'NO_FEASIBLE_CONFIGURATION'
            exact_small = evidence.configs[2][metric + '_area_um2']
            bounded = evidence.select(wid, exact_small, objective='latency', area_metric=metric)
            assert bounded['feasible_array_sizes'] == [2] and bounded['winner_set'] == [2]
            threshold = evidence.select(wid, None, objective='adp', area_metric=metric)['threshold']['alpha_star']
            tied = evidence.select(wid, None, objective='weighted', area_metric=metric, alpha=threshold)
            assert tied['winner_set'] == [2, 4]
    for wid in ('W4', 'W5'):
        assert evidence.select(wid, None, objective='weighted', area_metric='core', alpha=0.95)['winner_set'] == [4]
        assert evidence.select(wid, None, objective='weighted', area_metric='cell', alpha=0.95)['winner_set'] == [2]
    assert evidence.historical_summary['total_cases'] == 441
    mapped = []
    for size in (2, 4):
        caption, image = mapping_view(evidence.research, size, ROOT / 'research')
        assert image.is_file() and ET.fromstring(image.read_text(encoding='utf-8')).tag.endswith('svg')
        cfg = next(x for x in evidence.research['configurations'] if x['array_size'] == size)
        mapped.append({'array_size': size, 'preserved_accumulator_registers': len(cfg['accumulator_registers']),
                       'new_geometry_extraction': False, 'status': 'PASS'})
    assert sum(row['preserved_accumulator_registers'] for row in mapped) == 640
    result = {'schema_version': 1, 'status': 'PASS', 'scope': 'Independent copied candidate only',
              'python_version': sys.version.split()[0],
              'validation_attempts': [{'attempt': 1, 'status': 'FAIL', 'reason': 'New staging harness incorrectly required an optional SVG XML prolog; source SVG unchanged'}, {'attempt': 2, 'status': 'PASS', 'correction': 'Parse XML and check SVG root instead'}], 'python_AST_files': parsed,
              'notebook_code_cells_syntax_checked': len(code_cells),
              'preserved_manifest_entries_checked': manifest_counts,
              'existing_evidence_verifier': json.loads(evidence.integrity_result),
              'current_model_replays': replay, 'selection_calculations_checked': len(decisions),
              'selection_boundary_checks': 'Six workloads, Core/Cell: empty budget, inclusive smaller-only boundary, exact alpha tie; W4/W5 basis switch',
              'preserved_mapping_checks': mapped,
              'historical_441_case_regression': 'NOT_RUN (historical evidence only)',
              'fresh_RTL_EDA_signoff_GDS_extraction': 'NOT_RUN',
              'notebook_runtime_browser_UI': 'NOT_RUN',
              'dependency_installation': 'NOT_RUN', 'network_and_remote_publication': 'NOT_RUN'}
    if '--write-record' in sys.argv:
        (ROOT / 'VALIDATION.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'status': result['status'], 'python_AST_files': len(parsed),
                      'notebook_code_cells': len(code_cells), 'manifests': manifest_counts,
                      'current_model_replays': len(replay), 'decision_calculations': len(decisions),
                      'preserved_mapped_FFs': 640, 'fresh_RTL_or_EDA': False}, indent=2))


if __name__ == '__main__':
    main()
