"""The external adapter must reject stale worker schemas and source snapshots."""
import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/cos"))
from runtime import check_contract, schema_identity, validate_worker_tools


def test_worker_schema_and_name_mismatch_are_rejected():
    tool = {"name": "sample", "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
            "outputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}}
    catalog = {"tools": [tool]}
    validate_worker_tools(catalog, [copy.deepcopy(tool)])
    for field in ("name", "inputSchema", "outputSchema", "annotations"):
        altered = copy.deepcopy(tool)
        altered[field] = "other" if field == "name" else {}
        with pytest.raises(RuntimeError, match="schemas changed"):
            validate_worker_tools(catalog, [altered])
    assert schema_identity({**tool, "description": "new wording"}) == schema_identity(tool)


def test_stale_fingerprint_and_package_version_are_rejected(monkeypatch, tmp_path):
    import runtime
    source = tmp_path / "source.py"
    source.write_text("one", encoding="utf-8")
    monkeypatch.setattr(runtime, "source_paths", lambda engine: {"source": source})
    monkeypatch.setattr(runtime, "version", lambda package: "1")
    catalog = {"packages": {"sdk": "1"}, "sources": {"source": runtime.digest(source)}}
    check_contract(catalog)
    source.write_text("two", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed"):
        check_contract(catalog)
    catalog["sources"]["source"] = runtime.digest(source)
    catalog["packages"]["sdk"] = "2"
    with pytest.raises(RuntimeError, match="expects"):
        check_contract(catalog)
