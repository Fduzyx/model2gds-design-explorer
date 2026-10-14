#!/usr/bin/env python3
"""Portable offline explorer: current Python computation and historical evidence."""
from pathlib import Path
from functools import lru_cache
from html import escape
import argparse
import hashlib
import json
import math
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from model.golden import gemm
from model.systolic_generic import simulate
from decisions import select as select_decision


def winner_set(values, rel_tol=1e-9, abs_tol=0.0):
    """Frozen positive-quantity tie rule, including the empty feasible set."""
    if not values:
        return []
    smallest = min(values.values())
    return sorted(size for size, value in values.items()
                  if math.isclose(value, smallest, rel_tol=rel_tol, abs_tol=abs_tol))


class Evidence:
    """Adapter for the shared compact bundle; no access to a parent repository."""
    def __init__(self, directory=None):
        self.directory = Path(directory or ROOT / 'evidence').resolve()
        checked = subprocess.run([sys.executable, str(self.directory / 'verify.py')],
                                 cwd=self.directory, capture_output=True, text=True, timeout=60)
        if checked.returncode:
            raise ValueError('Bundled evidence verification failed: ' + checked.stdout + checked.stderr)
        self.integrity_result = checked.stdout.strip()
        self.analysis = self.read('exploratory.json')
        functional = self.read('functional_cases.json')
        self.historical_summary = functional['historical_summary']
        self.vectors = {row['workload_id']: row for row in functional['cases']}
        self.rtl = {size: {key: row['historical_rtl'][str(size)] for key, row in self.vectors.items()}
                    for size in (2, 4)}
        physical = self.read('physical.json')
        members = physical['configurations']
        if (physical['original_family_status'] != 'FAIL' or physical['family'] != 'FINAL_002'
            or sorted(row['array_size'] for row in members) != [2, 4]
            or any(row['qualification'] != 'QUALIFIED_FINAL' or row['pass'] is not True for row in members)
            or physical['excluded']['physical_metrics'] is not None):
            raise ValueError('Unqualified or mixed physical evidence cannot enter selection')
        self.configs = {row['array_size']: row for row in
                        self.analysis['timing_analysis']['configurations']}
        if self.analysis['analysis_mode'] != 'TWO_CONFIGURATION_EXPLORATORY' or set(self.configs) != {2, 4}:
            raise ValueError('Only the qualified historical two-configuration exploration is supported')
        if sorted(self.vectors) != [f'W{i}' for i in range(1, 7)]:
            raise ValueError('The portable bundle must retain all six declared workloads')
        self.workloads = {row['workload_id']: row for row in
                          self.analysis['timing_analysis']['workloads']}
        for member in members:
            cfg = self.configs[member['array_size']]
            if (member['run_path'] != cfg['run_path'] or member['recipe_sha256'] != cfg['recipe_sha256']
                or member['timing']['sta_period']['value'] != cfg['sta_period_ns']
                or member['area']['design__core__area']['value'] != cfg['core_area_um2']
                or member['area']['design__instance__area']['value'] != cfg['cell_area_um2']):
                raise ValueError('Exploratory metrics differ from qualified historical sources')
        self.research = {}
        self.research_directory = ROOT / 'research'
        manifest_path = self.research_directory / 'manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            for entry in manifest['files']:
                path = (self.research_directory / entry['path']).resolve()
                if not path.is_relative_to(self.research_directory.resolve()):
                    raise ValueError('Research evidence path escapes bundle')
                if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                    raise ValueError('Changed round-6 research evidence: ' + entry['path'])
            self.research = json.loads((self.research_directory / 'mapping.json').read_text(encoding='utf-8'))

    def read(self, name):
        return json.loads((self.directory / name).read_text(encoding='utf-8'))

    @lru_cache(maxsize=2)
    def replay(self, workload_id, size):
        if workload_id not in self.vectors or size not in (2, 4):
            raise ValueError('Select one of six workloads and qualified 2x2/4x4')
        case = self.vectors[workload_id]
        calculated = simulate(case['A'], case['B'], size, trace=True)
        golden = gemm(case['A'], case['B'])
        recorded = self.rtl[size][workload_id]
        numerical = calculated['C'] == golden == recorded['C']
        cycle_match = calculated['cycles'] == recorded['cycles']
        tiles_match = calculated['tiles'] == recorded['tiles']
        if not (numerical and cycle_match and tiles_match):
            raise ValueError('Current model differs from historical RTL evidence')
        return {'current': calculated, 'golden': golden, 'recorded_rtl': recorded,
                'numerical_match': numerical, 'cycle_match': cycle_match,
                'tiles_match': tiles_match, 'fresh_rtl_run': False}

    def select(self, workload_id, budget, *, objective='latency', area_metric='core', alpha=0.0):
        return select_decision(self.configs, self.workloads[workload_id], budget,
                               objective=objective, area_metric=area_metric, alpha=alpha,
                               tie_policy=self.analysis['tie_policy'])


def table(headers, rows):
    head = ''.join(f'<th>{escape(str(h))}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{escape(str(v))}</td>' for v in row) + '</tr>' for row in rows)
    return f'<table class="m2g-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def names(values):
    return ', '.join(f'{n}×{n}' for n in values) if values else 'none'


def details(label, body):
    return f'<details><summary>{escape(label)}</summary>{body}</details>'


STYLE = '''<style>
.m2g{font-family:system-ui,sans-serif;color:#162c3c;max-width:1100px;line-height:1.5}
.m2g .muted{color:#506779}.m2g h2{margin:0 0 6px;font-size:26px}.m2g h3{font-size:17px;margin:8px 0}
.m2g .badge{display:inline-block;font-size:12px;padding:3px 9px;background:#e6f3ef;border-radius:5px;margin:3px 5px 3px 0}
.m2g .note{background:#edf4fa;padding:12px 16px;border-left:4px solid #29738c;margin:8px 0}
.m2g-table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}
.m2g-table td,.m2g-table th{text-align:left;padding:8px 10px;border-bottom:1px solid #d7e2e9}
.m2g-table th{color:#506779;background:#f3f7fa}.m2g pre{white-space:pre-wrap;font-size:12px}
.m2g details{margin:10px 0}.m2g summary{cursor:pointer;color:#29738c}
.m2g .decision-result{font-size:21px;font-weight:650;color:#146253}
</style>'''


def trace_svg(frame, size):
    """Render actual current Python PE registers after a counted rising edge."""
    cell, left, top = 175, 45, 40
    width, height = size * cell + 70, size * 112 + 75
    parts = [f'<svg role="img" aria-label="Current Python systolic PE registers" viewBox="0 0 {width} {height}" style="width:100%;max-width:850px">']
    for pe in frame['pe']:
        row, col = pe['row'], pe['col']
        x, y = left + col * cell, top + row * 112
        active = bool(frame['active_mask'] & (1 << (row * size + col)))
        multiplying = pe['a']['valid'] and pe['b']['valid']
        fill = '#d9f2e6' if pe['result_valid'] else '#ddedf9' if multiplying else '#f1f4f7'
        if not active:
            fill = '#e5e7eb'
        if col < size - 1:
            parts.append(f'<text x="{x+153}" y="{y+43}" fill="#29738c" font-size="20">→</text>')
        if row < size - 1:
            parts.append(f'<text x="{x+67}" y="{y+107}" fill="#29738c" font-size="18">↓</text>')
        parts.append(f'<rect x="{x}" y="{y}" width="148" height="90" rx="8" fill="{fill}" stroke="#94aebb"/>')
        a = str(pe['a']['value']) if pe['a']['valid'] else '—'
        b = str(pe['b']['value']) if pe['b']['valid'] else '—'
        state = 'result valid' if pe['result_valid'] else 'MAC' if multiplying else 'clear / idle'
        if not active:
            state = 'masked output'
        labels = [f'PE ({row},{col}) · {state}', f'A {a}  ×  B {b}', f'acc = {pe["acc"]}',
                  'k = ' + (str(pe['a']['k']) if multiplying else '—')]
        for offset, text in enumerate(labels):
            parts.append(f'<text x="{x+9}" y="{y+18+offset*20}" font-size="12" fill="#162c3c">{escape(text)}</text>')
    parts.append('</svg>')
    return ''.join(parts)


class Explorer:
    def __init__(self, evidence=None):
        import ipywidgets as w
        self.evidence = evidence or Evidence()
        self.workload = w.Dropdown(options=[(f'{key} · {case["M"]}×{case["N"]}×{case["K"]}', key)
                                            for key, case in self.evidence.vectors.items()], description='GEMM:')
        self.workload.add_class('m2g-workload')
        self.array = w.ToggleButtons(options=[('2×2', 2), ('4×4', 4)], description='Trace array:')
        self.objective = w.Dropdown(options=[('Minimum STA latency', 'latency'), ('Minimum cycles', 'cycles'),
            ('Area × latency (ADP)', 'adp'), ('Latency × area^α', 'weighted')], description='Objective:',
            layout=w.Layout(width='330px'))
        self.objective.add_class('m2g-objective')
        self.area_metric = w.Dropdown(options=[('Core area', 'core'), ('Cell area', 'cell')], description='Area basis:')
        self.area_metric.add_class('m2g-area-metric')
        self.alpha = w.FloatSlider(value=0.95, min=0, max=2, step=.01, description='α:',
                                  readout_format='.3f', continuous_update=False, disabled=True,
                                  layout=w.Layout(width='400px'))
        self.alpha.add_class('m2g-alpha')
        self.at_threshold = w.Button(description='Set α to exact tie', tooltip='Use the unrounded analytic threshold')
        self.budget = w.BoundedFloatText(value=max(c['core_area_um2'] for c in self.evidence.configs.values()),
                                        min=0, max=1e12, step=1, description='Core µm²:', continuous_update=False)
        self.budget.add_class('m2g-budget')
        self.budget_presets = w.Dropdown(options=[('Both fit', 'both'), ('Only smaller fits', 'small'),
                                                ('Nothing fits', 'none'), ('Custom', 'custom')], description='Budget:')
        self.budget_presets.add_class('m2g-presets')
        self.cycle = w.IntSlider(value=1, min=1, max=2, description='Edge:', continuous_update=False,
                                layout=w.Layout(width='75%'))
        self.play = w.Play(value=1, min=1, max=2, interval=350, description='Play')
        self._link = w.jslink((self.play, 'value'), (self.cycle, 'value'))
        self.replay_status, self.decision, self.frame, self.sources, self.layout_caption = (w.HTML() for _ in range(5))
        self.mapping_caption = w.HTML()
        self.mapping_image = w.Image(format='svg+xml', layout=w.Layout(width='100%', max_width='1100px'))
        self.layout_image = w.Image(format='png', layout=w.Layout(width='100%', max_width='1100px'))
        self._updating = False
        self._budget_sync = False
        self.callback_count = 0
        header = w.HTML(STYLE + '<div class="m2g"><h2>Model2GDS · Design Explorer</h2>'
                        '<p class="muted">Evidence-grounded accelerator selection · What are you optimizing, and what evidence decides?</p>'
                        '<span class="badge">Current Python</span><span class="badge">Historical RTL · recorded replay</span>'
                        '<span class="badge">Historical ASIC · STA estimate</span>'
                        '<div class="note">Independent 2×2 / 4×4 exploration. 8×8 has historical functional verification; physical signoff remains incomplete and it is excluded from ranking.</div></div>')
        trace_box = w.VBox([w.HBox([self.play, self.cycle]), self.frame])
        overview_path = self.evidence.research_directory / 'decisions.png'
        overview = w.VBox([w.HTML('<div class="m2g"><h3>All six workloads · derived tradeoffs</h3>'
            '<p>Historical two-configuration subset. These are discrete qualified alternatives, '
            'not a continuous design space or new physical measurements.</p></div>'),
            w.Image(value=overview_path.read_bytes() if overview_path.exists() else b'', format='png',
                    layout=w.Layout(width='100%', max_width='1100px'))])
        tabs = w.Tab(children=[trace_box, w.VBox([self.mapping_caption, self.mapping_image]),
                              w.VBox([self.layout_caption, self.layout_image]), overview, self.sources])
        tabs.set_title(0, 'Cycle-by-cycle PE view')
        tabs.set_title(1, 'Logic → physical evidence')
        tabs.set_title(2, 'Historical routed layout')
        tabs.set_title(3, 'Tradeoff overview')
        tabs.set_title(4, 'Evidence & limits')
        self.tabs = tabs
        self.widget = w.VBox([header, w.HBox([self.workload, self.array]),
            w.HBox([self.objective, self.area_metric]), w.HBox([self.alpha, self.at_threshold]),
            w.HBox([self.budget_presets, self.budget]), self.decision, self.replay_status, tabs])
        self.workload.observe(self._on_model, names='value')
        self.array.observe(self._on_model, names='value')
        self.budget.observe(self._on_budget, names='value')
        self.budget_presets.observe(self._on_preset, names='value')
        self.objective.observe(self._on_objective, names='value')
        self.area_metric.observe(self._on_area_metric, names='value')
        self.alpha.observe(self._on_budget, names='value')
        self.at_threshold.on_click(self._on_threshold)
        self.cycle.observe(self._on_cycle, names='value')
        self._on_model(None)

    def _on_model(self, change):
        self.callback_count += 1
        self._updating = True
        self.replay = self.evidence.replay(self.workload.value, self.array.value)
        result = self.replay['current']
        self.cycle.value = self.play.value = 1
        self.cycle.max = self.play.max = result['cycles']
        case = self.evidence.vectors[self.workload.value]
        previews = table(['A input (first 4×4)', 'B input (first 4×4)', 'C output (first 4×4)'],
                         [[str([row[:4] for row in case['A'][:4]]),
                           str([row[:4] for row in case['B'][:4]]),
                           str([row[:4] for row in result['C'][:4]])]])
        self.replay_status.value = ('<div class="m2g"><h3>Current Python computation: PASS</h3>'
            f'<p>Numerical golden = token model = historical RTL output. Current {result["cycles"]:,} edges = '
            f'historical RTL {self.replay["recorded_rtl"]["cycles"]:,} edges; {len(result["tiles"])} sequential tiles. '
            'Each tile includes one clear edge. No new RTL simulator ran.</p>' +
            details('Inspect the current matrices', previews) + '</div>')
        self._updating = False
        image_path = ROOT / 'assets' / f'cfg_{self.array.value}x{self.array.value}_layout.png'
        manifest = json.loads((ROOT / 'assets/layout_manifest.json').read_text(encoding='utf-8'))
        layout_record = next(row for row in manifest['images'] if row['array_size'] == self.array.value)
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != layout_record['sha256']:
            raise ValueError('Historical layout image hash differs')
        self.layout_image.value = image_path.read_bytes()
        self.layout_caption.value = ('<div class="m2g"><h3>Historical qualified FINAL_002 layout · '
            f'{self.array.value}×{self.array.value}</h3><p>Same rendering rule for both arrays: selected top-cell metals; '
            'library-internal geometry, cuts and labels omitted. This is an image of a preserved GDS, '
            'not new physical execution or complete signoff inspection.</p>' +
            details('GDS source identity', '<pre>' + escape(json.dumps(layout_record['source_gds'], indent=2)) + '</pre>') + '</div>')
        self._update_mapping()
        self._on_budget(None)
        self._on_cycle(None)

    def _on_preset(self, change):
        if self._budget_sync or self.budget_presets.value == 'custom':
            return
        areas = sorted(cfg[self.area_metric.value + '_area_um2'] for cfg in self.evidence.configs.values())
        self._budget_sync = True
        self.budget.value = {'both': areas[-1], 'small': areas[0], 'none': 0}[self.budget_presets.value]
        self._budget_sync = False
        self._on_budget(None)

    def _on_objective(self, change):
        self.alpha.disabled = self.objective.value != 'weighted'
        self._on_budget(None)

    def _on_area_metric(self, change):
        self.budget.description = self.area_metric.label.split()[0] + ' µm²:'
        # A numeric budget in one metric is not carried into the other by accident.
        if self.budget_presets.value == 'custom':
            self.budget_presets.value = 'both'
        self._on_preset(None)

    def _on_threshold(self, button):
        self.objective.value = 'weighted'
        self.alpha.value = self.selection['threshold']['alpha_star']

    def _on_budget(self, change):
        if self._updating:
            return
        self.callback_count += 1
        if change and change.get('owner') is self.budget and not self._budget_sync:
            self._budget_sync = True
            self.budget_presets.value = 'custom'
            self._budget_sync = False
        try:
            self.selection = self.evidence.select(self.workload.value, self.budget.value,
                objective=self.objective.value, area_metric=self.area_metric.value, alpha=self.alpha.value)
        except ValueError as exc:
            self.decision.value = '<div class="m2g note">Invalid controls: ' + escape(str(exc)) + '</div>'
            return
        selected = self.selection
        rows = [[f'{r["array_size"]}×{r["array_size"]}', r['cycles'], f'{r["sta_period_ns"]:.6f}',
                 f'{r["latency_ns"]:.3f}', f'{r["area_um2"]:,.1f}', f'{r["score"]:.6g}',
                 'Yes' if r['feasible'] else 'No']
                for r in selected['rows']]
        message = ('No feasible configuration at this area budget.' if not selected['feasible_array_sizes'] else
                   ('Tied under the declared tolerance: ' if len(selected['winner_set']) > 1 else 'Recommended: ') +
                   names(selected['winner_set']))
        margin = next(row for row in self.evidence.analysis['timing_analysis']['pairwise']['decisions']
                      if row['workload_id'] == self.workload.value)
        margin_text = (f'Unconstrained ln(2×2 / 4×4) margin: cycles {margin["M_arch"]:.6f}; '
                       f'STA latency {margin["M_impl"]:.6f}; change {margin["margin_delta"]:+.6f}. '
                       f'Pair order: {margin["decision"]}.')
        threshold = selected['threshold']
        basis = self.area_metric.label
        explanation = (f'4×4 is {threshold["latency_speedup_4_over_2"]:.4f}× faster in STA-derived latency, '
            f'but uses {threshold["area_ratio_4_over_2"]:.4f}× the {basis.lower()}. '
            f'Before budget filtering, objective score ratio 4×4 / 2×2 = {selected["score_ratio_4_over_2"]:.6f}; lower is better.')
        threshold_text = (f'With both feasible, latency × area^α switches at α* = '
            f'{threshold["alpha_star"]:.9f}: below → 4×4; above → 2×2; at the threshold → tie. '
            'The exact-tie button uses the unrounded value. α = 0 means latency; α = 1 means ADP.')
        pareto = f'Pareto set before budget filtering ({basis.lower()}, latency): {names(selected["pareto_array_sizes"])}. Neither dominates: one is smaller, the other faster.'
        units = ('cycles' if self.objective.value == 'cycles' else 'ns' if self.objective.value == 'latency'
                 else 'ns·µm²' if self.objective.value == 'adp' else f'ns·(µm²)^{self.alpha.value:.6g}')
        self.decision.value = ('<div class="m2g"><h3>Decision from qualified historical evidence</h3>'
            '<div class="decision-result">' + escape(message) + '</div><p>' + escape(selected['reason']) + '</p>' +
            table(['Array', 'RTL edges', 'STA period ns', 'Latency ns', basis + ' µm²', 'Score (' + units + ')', 'Fits'], rows) +
            '<p>' + escape(explanation) + '</p><div class="note">' + escape(threshold_text) + '</div>' +
            details('Decision rules, Pareto relation and timing margin', '<p>' + escape(pareto) + '</p><p>' +
                escape(margin_text) + '</p><p>Within budget: cycle choice ' + names(selected['architecture_winner_set']) +
                '; STA-latency choice ' + names(selected['implementation_winner_set']) + '.</p><p>' +
                'α* = ln(T₂/T₄) / ln(A₄/A₂). Positive scores tie at relative tolerance 1e-9. '
                f'The numerical tie band in α is [{threshold["tie_alpha_lower"]:.12f}, '
                f'{threshold["tie_alpha_upper"]:.12f}]; it is not physical uncertainty. '
                'Core area is the floorplan region; cell area is the tool-reported instance area. '
                'The selected basis applies to both score and budget. Switching basis resets the numeric budget '
                'to its preset (Custom resets to Both fit); these quantities are not interchangeable. '
                'Score magnitudes with different α have different units; compare candidates at the same α.</p>') +
            '<p class="muted">Current decision calculation from historical ASIC / RTL evidence. '
            'Latency = RTL edges × fixed-layout R2R STA period; not silicon or system latency. '
            'Changing an objective or excluding an array by area is not a timing-ranking reversal.</p></div>')
        cfg = self.evidence.configs[self.array.value]
        provenance = {'run': cfg['run_path'], 'freeze_commit': cfg['freeze_commit'],
                      'recipe_sha256': cfg['recipe_sha256'], 'raw_provenance': cfg['raw_provenance'],
                      'tie_policy': self.evidence.analysis['tie_policy']}
        self.sources.value = ('<div class="m2g"><h3>Evidence chain</h3><p>Bundled historical raw observations → preserved '
            'processed exploration → current read-only selection calculation. Current token trace is Python simulation, '
            'not a captured RTL waveform.</p><p>Only two fixed layouts, one recipe, six predefined workloads. '
            'This post-result subset does not complete the original three-configuration study. A current model replay '
            'does not renew physical signoff. No EDA tools are invoked.</p><p>Historical functional corpus: ' +
            escape(str(self.evidence.historical_summary['total_cases'])) +
            ' case/configuration executions. This compact Explorer replays only its six displayed workloads on 2×2 / 4×4.</p>' +
            details('Expand raw-source paths, hashes and verification receipt', '<pre>' +
                escape(self.evidence.integrity_result) + '\n' + escape(json.dumps(provenance, indent=2)) + '</pre>') + '</div>')

    def _update_mapping(self):
        # Populated only by source-bound extraction, never by guessing PE regions.
        research = self.evidence.research
        if not research:
            self.mapping_caption.value = '<div class="m2g">Physical mapping evidence is not bundled.</div>'
            return
        from physical_view import mapping_view
        caption, image_path = mapping_view(research, self.array.value, self.evidence.research_directory)
        self.mapping_caption.value = '<div class="m2g">' + caption + '</div>'
        self.mapping_image.value = image_path.read_bytes()

    def _on_cycle(self, change):
        if self._updating:
            return
        self.callback_count += 1
        frame = self.replay['current']['trace'][self.cycle.value - 1]
        self.current_frame = frame
        tile = self.replay['current']['tiles'][frame['tile_index']]
        self.frame.value = ('<div class="m2g"><h3>Current Python trace · counted edge '
            f'{frame["cycle"]:,} / {self.replay["current"]["cycles"]:,}</h3><p>Tile {frame["tile_index"]+1}, '
            f'output origin ({tile["row"]},{tile["col"]}); tile edge {frame["tile_cycle"]}; '
            f'{frame["phase"]}; tile done = {frame["tile_done"]}.</p>' + trace_svg(frame, self.array.value) +
            '<p class="muted">A travels right, B travels down; accumulators stay in place. Blue: MAC; green: result valid. '
            'Values are PE registers after this edge; a clear edge has no multiplication.</p></div>')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--workload', default='W1', choices=[f'W{i}' for i in range(1, 7)])
    cli.add_argument('--array', type=int, default=2, choices=[2, 4])
    cli.add_argument('--budget', type=float, default=None)
    cli.add_argument('--objective', choices=['cycles', 'latency', 'adp', 'weighted'], default='latency')
    cli.add_argument('--area-metric', choices=['core', 'cell'], default='core')
    cli.add_argument('--alpha', type=float, default=0.95)
    cli.add_argument('--evidence', type=Path)
    args = cli.parse_args()
    evidence = Evidence(args.evidence)
    replay = evidence.replay(args.workload, args.array)
    budget = args.budget if args.budget is not None else max(r[args.area_metric + '_area_um2'] for r in evidence.configs.values())
    output = {'workload': args.workload, 'array_size': args.array,
              'current_python_numerical_and_cycle_replay': 'PASS',
              'current_cycles': replay['current']['cycles'], 'fresh_rtl_run': False,
              'fresh_physical_run': False, 'analysis_mode': 'TWO_CONFIGURATION_EXPLORATORY',
              'selection': evidence.select(args.workload, budget, objective=args.objective,
                                           area_metric=args.area_metric, alpha=args.alpha)}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
