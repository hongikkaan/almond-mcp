"""Shipped guidance stays reproducible, discoverable, and pinned to host identity."""
import asyncio
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_bundle_is_current_and_all_substantive_guide_sections_are_mapped():
    subprocess.run([sys.executable, '-B', str(ROOT / 'src/mcp/tools/build_modeling_guides.py'), '--check'],
                   check=True, capture_output=True, text=True, encoding='utf-8')
    sources = ROOT / 'docs/modeling/guidance'
    mapping = json.loads((sources / 'mcp-guide-map.json').read_text(encoding='utf-8'))
    references = [ref for topic in mapping['topics'] for ref in topic['sections']]
    for path in {ref['path'] for ref in references}:
        # Every body paragraph must be inside a mapped section; navigation and empty
        # grouping headings are the only omissions allowed in the canonical guide.
        lines = (sources / path).read_text(encoding='utf-8').splitlines()
        active = []
        for line in lines:
            if line == '---':
                continue
            match = re.match(r'^(#{1,6}) ', line)
            if match:
                level = len(match[1])
                active = [(depth, heading) for depth, heading in active if depth < level]
                active.append((level, line))
                continue
            if not line.strip() or any(heading == '## 목차' for _, heading in active):
                continue
            assert any(ref['path'] == path and any(
                heading == ref['heading'] and (ref.get('children', True) or heading == active[-1][1])
                for _, heading in active) for ref in references), (path, line)


def test_topic_references_and_conditional_hints_match_current_exposed_tools():
    from build_catalog import generate
    from external_host import exposed_tools
    from almond_mcp.modeling_guidance import read_guide, tool_guidance
    catalog = asyncio.run(generate())
    tools = {tool['name']: tool for tool in catalog['tools']}
    manifest = json.loads((ROOT / 'src/mcp/almond_mcp/modeling_guides/manifest.json').read_text(encoding='utf-8'))
    assert set(manifest['tool_hints']) <= tools.keys()
    index, _ = read_guide()
    topic_ids = {item['id'] for item in index['topics']}
    for id in topic_ids:
        topic, _ = read_guide(id)
        assert set(topic['related_tools']) <= tools.keys()
        assert not re.search(r'\]\((?:\.\./|references/|assets/)', topic['text'])
    for tool in tools.values():
        assert tool_guidance(tool['name']) in tool['description']
        for target in re.findall(r'get_modeling_guide\(topic="([\w-]+)"', tool['description']):
            assert target == 'index' or target in topic_ids
    public = {tool.name: tool for tool in exposed_tools(catalog)[0]}
    assert public['project_info'].description == tools['project_info']['description']
    assert public['get_modeling_guide'].description == tools['get_modeling_guide']['description']
    assert 'connection_id' in public['get_modeling_guide'].input_schema['required']


@pytest.mark.parametrize('name', ['drafting.md', 'assets/roof-drainage.png', 'manifest.json'])
def test_text_image_and_manifest_changes_invalidate_existing_host(name, tmp_path, monkeypatch):
    import runtime
    from almond_mcp.modeling_guidance import BUNDLE
    paths = runtime.source_paths(runtime.ENGINE)
    assert BUNDLE / name in paths.values()
    source = tmp_path / Path(name).name
    source.write_bytes((BUNDLE / name).read_bytes())
    monkeypatch.setattr(runtime, 'source_paths', lambda _: {'guide': source})
    catalog = {'packages': {}, 'sources': {'guide': runtime.digest(source)}}
    runtime.check_contract(catalog)
    source.write_bytes(source.read_bytes() + b' ')
    with pytest.raises(RuntimeError, match='changed'):
        runtime.check_contract(catalog)


@pytest.mark.parametrize('relative', [
    'docs/modeling/guidance/mcp-guide-map.json',
    'docs/modeling/guidance/modeling-guide.md',
    'docs/modeling/guidance/references/assets/roof-drainage.png',
    'src/mcp/almond_mcp/FUNDAMENTAL-INSTRUCTIONS.md',
    'src/mcp/almond_mcp/MODEL-CONTEXT-INSTRUCTIONS.md',
])
def test_generation_rejects_changed_inputs_before_returning_publishable_files(relative, monkeypatch):
    builder = runpy.run_path(str(ROOT / 'src/mcp/tools/build_modeling_guides.py'))
    original_read = Path.read_bytes
    target = (ROOT / relative).resolve()
    reads = 0

    def changing_read(path):
        nonlocal reads
        raw = original_read(path)
        if path.resolve() == target:
            reads += 1
            if reads > 1:
                return raw + b' '
        return raw

    monkeypatch.setattr(Path, 'read_bytes', changing_read)
    with pytest.raises(RuntimeError, match='source changed during generation'):
        builder['build']()
    assert reads == 2


def test_model_context_content_participates_in_guide_version(monkeypatch):
    builder = runpy.run_path(str(ROOT / 'src/mcp/tools/build_modeling_guides.py'))
    before = json.loads(builder['build']()['manifest.json'])
    original_read = Path.read_bytes
    target = (ROOT / 'src/mcp/almond_mcp/MODEL-CONTEXT-INSTRUCTIONS.md').resolve()

    def changed_read(path):
        raw = original_read(path)
        return raw + b'\nNew project guidance.\n' if path.resolve() == target else raw

    monkeypatch.setattr(Path, 'read_bytes', changed_read)
    after = json.loads(builder['build']()['manifest.json'])
    assert after['model_context_sha256'] != before['model_context_sha256']
    assert after['guide_version'] != before['guide_version']
    assert after['files'] == before['files']
