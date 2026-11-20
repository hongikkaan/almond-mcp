"""Keep documented Plan template sequences aligned with the stored Steps."""
from pathlib import Path
import re

import pytest

from almond_mcp.features.planning.schema import TASK_SCOPES
from almond_mcp.retrieval_store import AlmondStore


PACKAGE = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scope", TASK_SCOPES)
def test_documented_step_order_matches_created_plan(tmp_path, scope):
    store = AlmondStore(tmp_path / "policy-walkthrough.sqlite3")
    steps = store.create_plan("Review policy workflow", scope=scope)["steps"]
    expected = [step["step_type"] for step in steps]

    # The public template table previously omitted real Steps in two workflows.
    readme = (PACKAGE / "features/planning/README.md").read_text(encoding="utf-8")
    row = re.search(rf"(?m)^\| `{scope}` \|[^|]+\| ([^|]+)\|$", readme)
    assert row, scope
    assert [name.strip() for name in row[1].split("→")] == expected
