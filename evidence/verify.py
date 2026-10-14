"""Portable, standard-library verification of the small round-5 evidence bundle.

This checks included records; it does not rerun RTL, signoff, or replace the full
repository collector. The manifest is an integrity index, not a signature.
"""
from pathlib import Path
import hashlib
import json
import math
import re


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def verify(root=None):
    root = Path(root or Path(__file__).parent).resolve()
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    manifest = read('manifest.json')
    for entry in manifest['files']:
        path = (root / entry['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Bundle path escapes root')
        data = path.read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Changed bundle file: ' + entry['path'])
    f, p, e = (read(name) for name in ('functional_cases.json', 'physical.json', 'exploratory.json'))
    assert p['original_family_status'] == 'FAIL' and p['excluded']['physical_metrics'] is None
    assert [r['array_size'] for r in p['configurations']] == [2, 4]
    assert e['analysis_mode'] == 'TWO_CONFIGURATION_EXPLORATORY'
    periods = {}
    for row in p['configurations']:
        size = row['array_size']
        assert row['pass'] and row['qualification'] == 'QUALIFIED_FINAL'
        assert row['run_id'] == p['family'] == 'FINAL_002'
        state = read(f'raw/cfg_{size}x{size}/final_state.json')['metrics']
        for metric in row['signoff'].values():
            assert metric['value'] == state[metric['source_key']] == 0
        for metric in row['area'].values():
            assert metric['value'] == state[metric['source_key']]
        hold = read(f'raw/cfg_{size}x{size}/post_route_state.json')['metrics']
        for key, metric in row['post_route_hold'].items():
            assert metric['value'] == hold[key]
            if 'vio__count' in key:
                assert metric['value'] == 0
        report = (root / f'raw/cfg_{size}x{size}/r2r.stdout.log').read_text()
        values = re.findall(r'^PHASE2_R2R_SETUP_WS_NS\s+([-+.\deE]+)$', report, re.M)
        assert len(values) == 1 and 'PHASE2_R2R_STA_PASS' in report
        period = row['timing']['constraint_period']['value'] - float(values[0])
        assert period == row['timing']['sta_period']['value'] > 0
        periods[size] = period
    assert [c['workload_id'] for c in f['cases']] == [f'W{i}' for i in range(1, 7)]
    assert sum(c['summary']['passed'] for c in f['historical_summary']['configurations']) == f['historical_summary']['total_cases']
    rtl = {str(s): {r['case_id']: r for r in
           (json.loads(line) for line in (root / f'raw/rtl_S{s}_selected.jsonl').read_text().splitlines())}
           for s in (2, 4)}
    for case, workload in zip(f['cases'], e['timing_analysis']['workloads']):
        assert case['workload_id'] == workload['workload_id']
        assert hashlib.sha256(canonical({'A': case['A'], 'B': case['B']})).hexdigest() == case['input_sha256']
        for cfg in workload['configurations']:
            s = str(cfg['array_size'])
            record = case['historical_rtl'][s]
            assert record == rtl[s][case['workload_id']]
            qualification = case['qualification'][s]
            assert qualification['pass'] and qualification['input_sha256'] == case['input_sha256']
            assert hashlib.sha256(canonical(record['C'])).hexdigest() == qualification['rtl_result_sha256']
            assert record['cycles'] == qualification['rtl_cycles'] == cfg['model_cycles'] == cfg['rtl_cycles']
            assert math.isclose(record['cycles'] * periods[int(s)], cfg['implementation_latency_ns'], rel_tol=1e-14)
    return {'status': 'PASS', 'files': len(manifest['files']), 'historical_rtl_records': 12,
            'qualified_physical_members': [2, 4], 'original_family_status': 'FAIL',
            'scope': 'Included-record integrity and derivation checks; no new RTL or EDA execution'}


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
