"""Canonical guidance is complete, directly readable and pinned to source identity."""
import asyncio
import json
from pathlib import Path
import re
import runpy
import pytest
from almond_mcp.modeling_guidance import BUNDLE, PACKAGE, read_guide, source_files


def test_all_substantive_guide_sections_are_mapped():
    mapping = json.loads((BUNDLE / 'mcp-guide-map.json').read_text(encoding='utf-8'))
    references = [ref for topic in mapping['topics'] for ref in topic['sections']]
    for path in {ref['path'] for ref in references}:
        source = BUNDLE / path
        if path == 'BASIC-INSTRUCTIONS.md':
            source = PACKAGE / path
            assert read_guide('basic')[0]['text'] == source.read_text(encoding='utf-8').strip()
        active = []
        for line in source.read_text(encoding='utf-8').splitlines():
            if line == '---':
                continue
            match = re.match(r'^(#{1,6}) ', line)
            if match:
                level = len(match[1])
                active = [(depth, heading) for depth, heading in active if depth < level]
                active.append((level, re.sub(r'%%.*?%%', '', line).rstrip()))
                continue
            # Front matter and the introduction are delivered in full by basic.
            if path == 'BASIC-INSTRUCTIONS.md' and not any(depth >= 2 for depth, _ in active):
                continue
            if not line.strip() or any(heading == '## 목차' for _, heading in active):
                continue
            assert any(ref['path'] == path and any(
                heading == ref['heading'] and (ref.get('children', True) or heading == active[-1][1])
                for _, heading in active) for ref in references), (path, line)
    for item in read_guide()[0]['topics']:
        assert read_guide(item['id'])[0]['text']


def test_topics_match_current_tools_without_injected_hints():
    from build_catalog import generate
    from external_host import exposed_tools
    from almond_mcp.modeling_guidance import tool_guidance
    catalog = asyncio.run(generate())
    tools = {tool['name']: tool for tool in catalog['tools']}
    for item in read_guide()[0]['topics']:
        topic, _ = read_guide(item['id'])
        assert set(topic['related_tools']) <= tools.keys()
    for tool in tools.values():
        hint = tool_guidance(tool['name'])
        if hint:
            assert hint not in tool['description']
    public = {tool.name: tool for tool in exposed_tools(catalog)[0]}
    assert public['project_info'].description == tools['project_info']['description']
    assert 'connection_id' in public['get_modeling_guide'].input_schema['required']
    retired = {'upsert_design_room','remove_design_room','register_scene_instance','remove_scene_instance','validate_scene_layout'}
    assert not retired & tools.keys()
    assert not any('design_component' in name for name in tools)
    assert {verb+'_ontological_component' for verb in ('upsert','get','sync','remove')} <= tools.keys()


def test_guidance_and_profiles_participate_in_external_source_identity():
    import runtime
    paths = set(runtime.source_paths(runtime.ENGINE).values())
    assert set(source_files()) <= paths
    assert set((PACKAGE / 'profiles').rglob('*.json')) <= paths


@pytest.mark.parametrize('relative', ['features/guidance/guides/mcp-guide-map.json',
                                     'features/guidance/guides/references/assets/roof-drainage.png',
                                     'BASIC-INSTRUCTIONS.md'])
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
