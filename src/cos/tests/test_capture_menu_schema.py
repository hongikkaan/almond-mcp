"""A new Codex host publishes only common live menu GUIDs before attachment."""
import json
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator
import pytest

from capture_menu import MODE_FIELDS, common_mode_ids, menu_input_error
from external_host import exposed_tools


def test_host_menu_requires_positive_evidence_from_every_live_host():
    shared, first, second = (str(uuid4()) for _ in range(3))
    hosts = [{"display_mode_ids": [first, shared]}, {"display_mode_ids": [shared, second]}]
    assert common_mode_ids(hosts) == (shared,)
    assert common_mode_ids(hosts[:1]) == tuple(sorted([first, shared]))
    assert common_mode_ids([]) == ()
    for unknown in ({}, {"display_mode_ids": []}, {"display_mode_ids": ["corrupt"]}):
        assert common_mode_ids([*hosts, unknown]) == ()


@pytest.mark.parametrize("name", MODE_FIELDS)
def test_routed_schema_and_direct_calls_agree_without_changing_worker_schema(name):
    path = Path(__file__).resolve().parents[3] / "tests/integration/tool_schemas.json"
    original = json.loads(path.read_text(encoding="utf8"))[name]
    before = json.dumps(original)
    allowed, hidden = str(uuid4()), str(uuid4())
    catalog = {"tools": [original]}

    def schema(modes):
        public = exposed_tools(catalog, explicit_connections=True, mode_ids=modes)[0].input_schema
        Draft202012Validator.check_schema(public)
        props = public["properties"]
        return props["views"]["items"].get("properties", {}) if name == "capture_02-inspection" else props

    snapshot, unavailable = schema((allowed,)), schema(())
    for field in MODE_FIELDS[name]:
        assert snapshot[field]["enum"] == [allowed] and field not in unavailable
        def args(value):
            return {"views": [{field: value}]} if name == "capture_02-inspection" else {field: value}
        assert menu_input_error(name, args(allowed), (allowed,)) is None
        assert menu_input_error(name, {}, ()) is None
        assert "View Display Mode Menu" in menu_input_error(name, args(hidden), (allowed,))
        assert menu_input_error(name, args(allowed), ())
    assert json.dumps(original) == before
