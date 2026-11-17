"""Exercise the registered egress calculation with explicit domain inputs."""
import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from almond_mcp.features.egress.tools import register


RULES = {
    "occupant_load_m2_per_person": {"business": 10},
    "exits_required_by_occupant_load": [{"max_occupants": None, "exits": 2}],
    "exit_separation_fraction_of_diagonal": {"sprinklered": 1/3, "unsprinklered": .5},
    "egress_width_mm_per_occupant": {"stairs": 7.6, "doors_corridors": 5.1},
    "min_widths_mm": {"exit_stair": 1100, "stair_serving_under_50": 900, "door_clear": 800},
    "max_travel_distance_m": {"business_sprinklered": 60, "business_unsprinklered": 45},
    "max_dead_end_corridor_m": {"sprinklered_business": 15, "default": 6},
}


def check(**changes):
    api = register(FastMCP('egress-test'), SimpleNamespace(
        construction_library=SimpleNamespace(reference={"egress_rules": RULES})))
    inputs = dict(plate_bounds_mm=[0, 0, 10000, 20000], exits=[
        dict(name='A', x_mm=0, y_mm=0, width_mm=1000),
        dict(name='B', x_mm=10000, y_mm=20000, width_mm=1000)])
    inputs.update(changes)
    return json.loads(api['check_egress'](**inputs))


@pytest.mark.parametrize('changes', [
    dict(exits=[dict(x_mm=0,y_mm=0,width_mm=1000)] * 2),
    dict(exits=[dict(x_mm=0,y_mm=0,width_mm=1000), dict(x_mm=0,y_mm=0,width_mm=2000)]),
    dict(exits=[dict(y_mm=0,width_mm=1000)]),
    dict(exits=[dict(x_mm=0,y_mm=0)]),
    dict(exits=[dict(x_mm=0,y_mm=0,width_mm=-1)]),
    dict(exits=[dict(x_mm=float('nan'),y_mm=0,width_mm=1000)]),
    dict(plate_bounds_mm=[0,0,float('inf'),1]),
    dict(plate_bounds_mm=[0,0,0,1]),
    dict(net_area_m2=-1), dict(net_area_m2=float('nan')),
    dict(dead_end_m=-1), dict(dead_end_m=float('inf')),
    dict(travel_distances_m=[-1]), dict(travel_distances_m=[float('nan')]),
    dict(stories=0), dict(stories=1.5),
    dict(plate_bounds_mm=[-1e308,-1e308,1e308,1e308]),
    dict(exits=[dict(x_mm=0,y_mm=0,width_mm=1e308), dict(x_mm=1,y_mm=0,width_mm=1e308)]),
])
def test_invalid_input_returns_consistent_error(changes):
    result = check(**changes)
    assert result['status'] == 'error'
    assert 'checks' not in result


def test_valid_boundaries_preserve_existing_calculation():
    result = check(travel_distances_m=[0,60], dead_end_m=15)
    assert result['passed'] is True
    assert result['occupant_load'] == 20
    assert result['area_m2'] == result['gross_area_m2'] == 200
    checks = {c['check']: c for c in result['checks']}
    assert checks['total_egress_width_mm']['provided'] == 2000
    assert checks['exit_separation_m']['provided'] == 22.36
    assert checks['max_travel_distance_m']['provided'] == 60
    assert check(travel_distances_m=[60.001])['passed'] is False
    assert check(dead_end_m=15.001)['passed'] is False
