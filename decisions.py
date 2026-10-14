"""Pure arithmetic on already-qualified 2x2/4x4 records; never runs EDA.

All objectives are minimized. Budgets use the selected, explicitly named area
metric. Score = T * A**alpha has the same winners under a common change of units.
Relative score ties use the historical positive-quantity comparison policy.
"""
import math

AREA_KEYS = {'core': 'core_area_um2', 'cell': 'cell_area_um2'}
OBJECTIVES = {'cycles': 'Cycle count', 'latency': 'STA latency',
              'adp': 'Area × STA latency', 'weighted': 'STA latency × area^α'}
DEFAULT_TIE_POLICY = {'relative_tolerance': 1e-9, 'absolute_tolerance': 0.0}


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be finite and nonnegative')
    if value < 0 or (positive and value == 0):
        raise ValueError(name + (' must be positive' if positive else ' must be finite and nonnegative'))
    return value


def _policy(tie_policy):
    policy = tie_policy or DEFAULT_TIE_POLICY
    rel, absolute = policy['relative_tolerance'], policy['absolute_tolerance']
    if not 0 <= rel < 1 or absolute != 0:
        raise ValueError('Positive-quantity relative ties with zero absolute tolerance are required')
    return rel, absolute


def winners(values, tie_policy=None):
    if not values:
        return []
    rel, absolute = _policy(tie_policy)
    best = min(values.values())
    return sorted(size for size, value in values.items()
                  if math.isclose(value, best, rel_tol=rel, abs_tol=absolute))


def observations(configs, workload):
    """Join two qualified metric records with matched historical cycle records."""
    if set(configs) != {2, 4}:
        raise ValueError('Exactly the qualified 2x2/4x4 subset is supported')
    observations = workload['configurations']
    if len(observations) != 2 or sorted(row['array_size'] for row in observations) != [2, 4]:
        raise ValueError('Exactly one workload observation per supported configuration is required')
    rows = []
    for row in sorted(observations, key=lambda row: row['array_size']):
        cfg, cycles = configs[row['array_size']], row['rtl_cycles']
        if type(cycles) is not int or cycles <= 0 or row['model_cycles'] != cycles:
            raise ValueError('Positive matched model/RTL cycle counts are required')
        period = _finite(cfg['sta_period_ns'], 'STA period', positive=True)
        latency = cycles * period
        if not math.isfinite(latency):
            raise ValueError('STA latency overflows')
        rows.append({'array_size': row['array_size'], 'cycles': cycles,
                     'sta_period_ns': period, 'latency_ns': latency,
                     **{key: _finite(cfg[key], key, positive=True) for key in AREA_KEYS.values()}})
    return rows


def switching_threshold(rows, area_metric='core', tie_policy=None):
    """Solve ln(S2/S4) = ln(T2/T4) - alpha*ln(A4/A2) = 0.

    The tie interval comes from |ln(S2/S4)| <= -ln(1-rel_tol).
    It is a numerical comparison band, not physical uncertainty.
    """
    key = AREA_KEYS[area_metric]
    small, large = rows
    area_ratio = large[key] / small[key]
    speedup = small['latency_ns'] / large['latency_ns']
    area_log, latency_log = math.log(area_ratio), math.log(speedup)
    rel, _ = _policy(tie_policy)
    common = {'area_ratio_4_over_2': area_ratio,
              'latency_speedup_4_over_2': speedup,
              'equation': 'alpha* = ln(T2/T4) / ln(A4/A2)',
              'tie_band_is_physical_uncertainty': False}
    if area_log == 0:
        return {**common, 'alpha_star': None, 'tie_alpha_lower': None,
                'tie_alpha_upper': None, 'below_winner_set': None,
                'above_winner_set': None, 'at_threshold_winner_set': None,
                'no_switch_reason': 'Equal areas: the latency ordering holds for every alpha.'}
    threshold = latency_log / area_log
    half_width = -math.log1p(-rel) / abs(area_log)
    return {**common, 'alpha_star': threshold,
            'tie_alpha_lower': threshold - half_width,
            'tie_alpha_upper': threshold + half_width,
            'below_winner_set': [4] if area_log > 0 else [2],
            'above_winner_set': [2] if area_log > 0 else [4],
            'at_threshold_winner_set': [2, 4]}


def pareto_set(rows, area_metric='core'):
    """Exact nondominance on historical numerical area/latency estimates."""
    key = AREA_KEYS[area_metric]
    return [row['array_size'] for row in rows if not any(
        other[key] <= row[key] and other['latency_ns'] <= row['latency_ns']
        and (other[key] < row[key] or other['latency_ns'] < row['latency_ns'])
        for other in rows)]


def select(configs, workload, budget, *, objective='latency', area_metric='core',
           alpha=0.0, tie_policy=None):
    """Return actual scores, feasible winners, analytical threshold and reason.

    None means unconstrained budget, not zero. The portable UI supplies finite
    budgets. Alpha is relevant only to 'weighted'; ADP uses exactly alpha=1.
    """
    if area_metric not in AREA_KEYS or objective not in OBJECTIVES:
        raise ValueError('Unknown area metric or optimization objective')
    if budget is not None:
        _finite(budget, 'Area budget')
    _finite(alpha, 'Alpha')
    _policy(tie_policy)
    exponent = 1.0 if objective == 'adp' else alpha if objective == 'weighted' else 0.0
    rows = observations(configs, workload)
    for row in rows:
        area = row[AREA_KEYS[area_metric]]
        try:
            score = (row['cycles'] if objective == 'cycles' else
                     row['latency_ns'] * area ** exponent)
        except OverflowError as exc:
            raise ValueError('Requested score exceeds floating-point range') from exc
        if not math.isfinite(score):
            raise ValueError('Requested score exceeds floating-point range')
        row.update(area_um2=area, feasible=budget is None or area <= budget,
                   adp_ns_um2=area * row['latency_ns'], score=score)
    feasible = [row for row in rows if row['feasible']]
    def winning(key, candidates):
        return winners({row['array_size']: row[key] for row in candidates}, tie_policy)
    arch, impl = winning('cycles', feasible), winning('latency_ns', feasible)
    chosen = winning('score', feasible)
    unconstrained = winning('score', rows)
    threshold = switching_threshold(rows, area_metric, tie_policy)
    feasible_sizes = [row['array_size'] for row in feasible]
    if not chosen:
        reason = f'Neither qualified configuration fits the {area_metric}-area budget.'
    elif len(feasible) == 1:
        only = feasible[0]
        reason = (f'Only {only["array_size"]}×{only["array_size"]} fits the {area_metric}-area budget '
                  f'({only["area_um2"]:,.6g} µm² ≤ {budget:,.6g} µm²). '
                  'Area exclusion is separate from timing ranking.')
    elif len(chosen) != 1:
        reason = ('Both configurations are tied under the declared relative tolerance; '
                  'no unique recommendation is justified.')
    else:
        best = next(row for row in rows if row['array_size'] == chosen[0])
        other = next(row for row in rows if row['array_size'] != chosen[0])
        reason = (f'{chosen[0]}×{chosen[0]} minimizes {OBJECTIVES[objective]}: '
                  f'{best["score"]:,.6g} versus {other["score"]:,.6g} '
                  f'({other["score"]/best["score"]:.4f}× objective advantage). ')
        if objective in ('adp', 'weighted'):
            reason += (f'4×4 uses {threshold["area_ratio_4_over_2"]:.4f}× {area_metric} area '
                       f'for {threshold["latency_speedup_4_over_2"]:.4f}× STA-latency speedup. '
                       'Changing the objective is not a cycle-to-STA timing reversal.')
    return {'budget_um2': budget, 'area_metric': area_metric,
            'objective': objective, 'objective_label': OBJECTIVES[objective],
            'alpha': exponent, 'rows': rows, 'winner_set': chosen,
            'unconstrained_winner_set': unconstrained,
            'feasible_array_sizes': feasible_sizes,
            'architecture_winner_set': arch, 'implementation_winner_set': impl,
            'unconstrained_architecture_winner_set': winning('cycles', rows),
            'unconstrained_implementation_winner_set': winning('latency_ns', rows),
            'status': ('NO_FEASIBLE_CONFIGURATION' if not feasible else
                       'TIED_OR_INDETERMINATE' if len(arch) != 1 or len(impl) != 1 else
                       'AGREEMENT' if arch == impl else 'DISAGREEMENT'),
            'decision_status': ('NO_FEASIBLE_CONFIGURATION' if not chosen else
                                'TIED_OR_INDETERMINATE' if len(chosen) > 1 else 'UNIQUE_WINNER'),
            'score_ratio_4_over_2': rows[1]['score'] / rows[0]['score'],
            'score_margin_ln_2_over_4': math.log(rows[0]['score'] / rows[1]['score']),
            'threshold': threshold, 'pareto_array_sizes': pareto_set(rows, area_metric),
            'feasible_pareto_array_sizes': pareto_set(feasible, area_metric),
            'reason': reason, 'area_exclusion_is_timing_reversal': False,
            'objective_change_is_timing_reversal': False}


def workload_analysis(configs, workload, tie_policy=None):
    rows = observations(configs, workload)
    areas = {}
    for metric in AREA_KEYS:
        adp = select(configs, workload, None, objective='adp', area_metric=metric, tie_policy=tie_policy)
        areas[metric] = {'threshold': adp['threshold'], 'adp_winner_set': adp['winner_set'],
                         'adp_ratio_4_over_2': adp['score_ratio_4_over_2'],
                         'pareto_array_sizes': adp['pareto_array_sizes'],
                         'adp_ns_um2': {str(row['array_size']): row['score'] for row in adp['rows']}}
    return {'workload_id': workload['workload_id'],
            **{key: workload[key] for key in ('M', 'N', 'K')}, 'configurations': rows,
            'cycle_winner_set': winners({row['array_size']: row['cycles'] for row in rows}, tie_policy),
            'sta_latency_winner_set': winners({row['array_size']: row['latency_ns'] for row in rows}, tie_policy),
            'cycle_speedup_4_over_2': rows[0]['cycles'] / rows[1]['cycles'],
            'sta_latency_speedup_4_over_2': rows[0]['latency_ns'] / rows[1]['latency_ns'],
            'areas': areas}
