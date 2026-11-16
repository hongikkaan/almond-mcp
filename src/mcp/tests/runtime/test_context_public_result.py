"""Only normalized successful context catalogues bypass the generic path pass."""
import json
import ntpath

import pytest

from shared_store import public_result


@pytest.mark.parametrize("name,status,preserve", [
    ("get_rhino_context", "success", True),
    ("get_rhino_context", "error", False),
    ("execute_rhino_script", "success", False),
])
def test_worksession_preservation_is_limited_to_successful_context(tmp_path, monkeypatch, name, status, preserve):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    drive = "Z:" if ntpath.splitdrive(str(tmp_path))[0].casefold() != "z:" else "Y:"
    reference = drive + "\\survey\\reference.3dm"
    payload = {"status": status, "worksession": {"attachments": [{"filename": "reference.3dm", "path": reference}]},
               "artifact": {"path": str(tmp_path / "report.json")}}
    result = json.loads(public_result(json.dumps(payload), name))
    path = result["worksession"]["attachments"][0]["path"]
    if preserve:
        assert path == reference
    else:
        assert path.startswith("[unavailable:")
    assert result["artifact"]["path"] == "report.json"
    assert payload["worksession"]["attachments"][0]["path"] == reference
