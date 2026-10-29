"""BASIC and tool explanations match current catalogs and source identity."""
import asyncio
from pathlib import Path
import runpy
import pytest
from almond_mcp.modeling_guidance import BASIC_GUIDE, PACKAGE, read_guide, source_files


def test_tool_guides_cover_the_live_catalog_and_preserve_parameter_help():
    from build_catalog import generate
    from external_host import exposed_tools
    from almond_mcp.instruction_text import read_instruction
    catalog = asyncio.run(generate())
    tools = {item['name']: item for item in catalog['tools']}
    basic = read_guide()
    assert basic['text'] == BASIC_GUIDE.read_text(encoding='utf-8').strip()
    assert set(basic['tools']) == tools.keys()
    schema = tools['get_modeling_guide']['inputSchema']['properties']
    assert set(schema) == {'tool'} and schema['tool']['default'] == ''
    assert 'help' not in tools['assign_material']['inputSchema']['properties']
    assert 'public static Run' in tools['execute_rhino_script']['inputSchema']['properties']['script']['description']
    for name in basic['tools']:
        guide = read_guide(tool=name)
        assert guide['guide_version'] == basic['guide_version']
        note = PACKAGE.parent.parent / guide['source_refs'][0]['path']
        source = note.with_name(note.name.replace('-explain.md', '.py'))
        assert guide['text'] == read_instruction(str(source), name)
        assert len(guide['source_refs'][0]['sha256']) == 64
    public = {tool.name: tool for tool in exposed_tools(catalog)[0]}
    assert 'connection_id' in public['get_modeling_guide'].input_schema['required']
    assert public['project_info'].description == tools['project_info']['description']


def test_guidance_and_profiles_participate_in_external_source_identity():
    import runtime
    paths = set(runtime.source_paths(runtime.ENGINE).values())
    assert set(source_files()) <= paths
    assert set((PACKAGE / 'profiles').rglob('*.json')) <= paths


@pytest.mark.parametrize('relative', ['BASIC-INSTRUCTIONS.md', 'features/modeling/tools-explain.md', 'features/modeling/tools.py'])
def test_reader_rejects_sources_changed_during_snapshot(relative, monkeypatch):
    reader = runpy.run_path(str(PACKAGE / 'modeling_guidance.py'))
    original = Path.read_bytes
    target = PACKAGE / relative
    reads = 0

    def changing_read(path):
        nonlocal reads
        raw = original(path)
        if path == target:
            reads += 1
            if reads > 1:
                return raw + b' '
        return raw

    monkeypatch.setattr(Path, 'read_bytes', changing_read)
    with pytest.raises(RuntimeError, match='source changed'):
        reader['read_guide']()


def test_existing_host_rejects_edited_guidance(tmp_path, monkeypatch):
    import runtime
    source = tmp_path / 'guide.md'
    source.write_text('Before', encoding='utf-8')
    monkeypatch.setattr(runtime, 'source_paths', lambda _: {'guide': source})
    catalog = {'packages': {}, 'sources': {'guide': runtime.digest(source)}}
    runtime.check_contract(catalog)
    source.write_text('After', encoding='utf-8')
    with pytest.raises(RuntimeError, match='changed'):
        runtime.check_contract(catalog)
