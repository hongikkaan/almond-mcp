"""Profile relocation preserves shipped data and explicit user library routing."""
import json
from pathlib import Path

from almond_mcp import paths
from almond_mcp.features.guidance.library import ConstructionLibrary
from almond_mcp.features.modeling.library import MaterialLibrary
from almond_mcp.features.structure import design_codes


def test_shipped_profiles_load_without_cross_reading_other_profile_types(monkeypatch, tmp_path):
    package = Path(paths.__file__).parent
    monkeypatch.setenv('ALMOND_DESIGN_CODE_DIR', str(tmp_path / 'codes'))
    for variable, folder, loader, collection in (
        ('RHINO_MCP_MATERIAL_DIR', 'material', MaterialLibrary, 'materials'),
        ('RHINO_MCP_CONSTRUCTION_DIR', 'construction_system', ConstructionLibrary, 'systems'),
    ):
        monkeypatch.delenv(variable, raising=False)
        expected = package / 'profiles' / folder
        assert Path(paths.resolve_dir(variable)) == expected
        manifest = json.loads((expected / 'manifest.json').read_text(encoding='utf-8'))
        loaded = loader(paths.resolve_dir(variable))
        assert len(getattr(loaded, collection)) == len(manifest[collection]) > 0
        override = tmp_path / folder
        monkeypatch.setenv(variable, str(override))
        assert Path(paths.resolve_dir(variable)) == override
    codes, problems = design_codes.discover()
    assert set(codes) == {'eurocode'}
    assert problems == []


def test_packaged_profiles_scaffold_legacy_user_folders_without_overwriting(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, '_repo_dir', lambda _: None)
    monkeypatch.setattr(paths, 'user_data_dir', lambda: tmp_path)
    for variable, legacy in (('RHINO_MCP_MATERIAL_DIR', 'Materialfiles'),
                             ('RHINO_MCP_CONSTRUCTION_DIR', 'Constructionfiles')):
        monkeypatch.delenv(variable, raising=False)
        resolved = Path(paths.resolve_dir(variable))
        assert resolved == tmp_path / legacy
        manifest = resolved / 'manifest.json'
        assert manifest.read_bytes() == paths._bundled_data(legacy).joinpath('manifest.json').read_bytes()
        original_user_content = b'{"custom_user_library": true}'
        manifest.write_bytes(original_user_content)
        assert Path(paths.resolve_dir(variable)) == resolved
        assert manifest.read_bytes() == original_user_content
