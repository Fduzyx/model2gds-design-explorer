"""Present only source-confirmed register locations from preserved implementations."""
from html import escape
import json


def mapping_view(mapping, size, directory):
    if (mapping['status'] != 'PASS' or mapping['family'] != 'FINAL_002'
            or mapping['new_eda_measurement'] is not False):
        raise ValueError('Unexpected physical mapping evidence')
    cfg = next(row for row in mapping['configurations'] if row['array_size'] == size)
    registers = cfg['accumulator_registers']
    if len(registers) != size * size * 32 or not all(r['gds_reference_verified'] for r in registers):
        raise ValueError('Accumulator mapping is incomplete or unverified')
    path = cfg['critical_path']
    def endpoint(label, endpoint):
        return ('<li><b>' + label + ':</b> ' + escape(endpoint['logical_state']['label']) +
            ' → <code>' + escape(endpoint['instance'] + '/' + endpoint['sta_pin']) + '</code>' +
            f' at DEF origin ({endpoint["x_um"]:.3f}, {endpoint["y_um"]:.3f}) µm.</li>')
    caption = (f'<h3>Logical state → actual physical instances · {size}×{size}</h3>'
        f'<p>{len(registers)} accumulator flip-flops, 32 per logical PE: preserved RTL signal → '
        'mapped Q net → final placed instance → instance name and transformed origin in real GDS.</p>'
        '<div class="note">Dots are confirmed register locations, <b>not PE boundaries</b>. '
        'Colors identify logical PE ownership of these accumulator bits. Other PE logic is not assigned '
        'a colored region. L / C identify timing endpoints; no routed path is drawn.</div>'
        '<h3>A real historical STA path</h3><ul>' + endpoint('Launch Q', path['launch']) +
        endpoint('Capture D', path['capture']) + '</ul>'
        '<p>The capture label describes the state stored at this flip-flop’s Q; the path ends at its D input. '
        'This connects PE state in the Python view to actual hardware state, not to a measured waveform. '
        'Static timing does not show that this path is exercised by the currently displayed input.</p>'
        f'<p>Historical corner: <code>{escape(path["corner"])}</code>; '
        f'fixed-layout R2R period estimate: {path["sta_period_ns"]:.6f} ns. '
        'The same period is reused for all six workloads. It is not the animated edge duration.</p>'
        '<details><summary>Inspect path identity, mapping method and original sources</summary><pre>' +
        escape(json.dumps({'critical_path': path, 'sources': cfg['sources'],
                           'compact_evidence': cfg['compact_evidence']}, indent=2, ensure_ascii=False)) +
        '</pre></details>')
    return caption, directory / f'cfg_{size}_mapping.svg'
