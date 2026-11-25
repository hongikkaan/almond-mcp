"""Check the on-disk locks used by asset preparation and library refresh."""
from pathlib import Path

import pytest

from almond_mcp.features.assets import drawing_assets, preparation
from almond_mcp.features.assets._file_lock import asset_file_lock


def test_preparation_locks_the_job_for_inspect_and_normalize(tmp_path, monkeypatch):
    def check_during_inspect(job, *_):
        with pytest.raises(OSError):
            with asset_file_lock(job / ".prepare.lock"):
                pass
        with asset_file_lock(job / ".register.lock"):
            pass

    source = tmp_path / "sample.3dm"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(preparation, "_dispatch", check_during_inspect)
    result = preparation.prepare(stage="inspect", source_file=str(source), artifact_dir=tmp_path)
    job = Path(result["job_dir"])
    with asset_file_lock(job / ".prepare.lock"):
        with pytest.raises(OSError):
            preparation.prepare(stage="normalize", job_dir=str(job), artifact_dir=tmp_path)


def test_publication_locks_the_manifest_and_releases_it_on_error(tmp_path):
    source = tmp_path / "prepared.3dm"
    source.write_bytes(b"fixture")
    (tmp_path / "manifest.json").write_text('{"assets": []}', encoding="utf-8")
    with asset_file_lock(tmp_path / ".register.lock"):
        with pytest.raises(OSError):
            drawing_assets.register_prepared_3dm(
                tmp_path, source_3dm=str(source), asset_id="new", name="New", category="fixture",
                tags=[], description="", source_url="", replace_existing=False, extract=None,
            )
        with pytest.raises(OSError):
            drawing_assets.refresh_registered_asset(tmp_path, "missing", extract=None)
    # A failed refresh must release its lock for the next publisher.
    with pytest.raises(ValueError, match="Refresh requires one registered"):
        drawing_assets.refresh_registered_asset(tmp_path, "missing", extract=None)
    with asset_file_lock(tmp_path / ".register.lock"):
        pass
