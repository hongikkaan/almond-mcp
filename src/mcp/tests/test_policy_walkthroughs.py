"""Keep the policy review's workflow coverage aligned with real Plan templates.

These checks validate the documented traces, not the quality of agent decisions.
The Given/When/Then decisions are reviewed in the linked walkthrough documents.
"""
from pathlib import Path
import re

import pytest

from almond_mcp.features.planning.schema import SCOPES
from almond_mcp.retrieval_store import AlmondStore


PACKAGE = Path(__file__).resolve().parents[1]
WALKTHROUGHS = PACKAGE / "features/guidance/policy-validation"


def documented_flows():
    flows = {}
    for path in sorted(WALKTHROUGHS.glob("*-flows.md")):
        sections = re.split(r"(?m)^## ([a-z_]+):[^\n]*\n", path.read_text(encoding="utf-8"))
        for scope, body in zip(sections[1::2], sections[2::2]):
            assert scope not in flows, f"Duplicate walkthrough for {scope}: {path}"
            flows[scope] = re.findall(
                r"(?m)^\|\s*\d+\.\s*`([^`]+)`\s*\(([^)]+)\)\s*\|", body)
    return flows


def test_every_builtin_template_has_one_walkthrough():
    assert set(documented_flows()) == set(SCOPES)


@pytest.mark.parametrize("scope", SCOPES)
def test_walkthrough_step_order_and_kind_match_created_plan(tmp_path, scope):
    store = AlmondStore(tmp_path / "policy-walkthrough.sqlite3")
    steps = store.create_plan("Review policy workflow", scope=scope)["steps"]
    expected = [(step["step_type"], step["kind"]) for step in steps]
    assert documented_flows()[scope] == expected

    # The public template table previously omitted real Steps in two workflows.
    readme = (PACKAGE / "features/planning/README.md").read_text(encoding="utf-8")
    row = re.search(rf"(?m)^\| `{scope}` \|[^|]+\| ([^|]+)\|$", readme)
    if row:
        assert [name.strip() for name in row[1].split("→")] == [name for name, _ in expected]
