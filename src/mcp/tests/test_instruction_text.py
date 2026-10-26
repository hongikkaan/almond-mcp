"""Guard every MCP description and adjacent instruction reference, without Rhino."""
import ast
from pathlib import Path
import re

import pytest

from almond_mcp.instruction_text import read_instruction, tool_instruction

ROOT = Path(__file__).resolve().parents[1]


def test_all_public_descriptions_and_responses_use_adjacent_markdown():
    referenced = {}
    public_count = 0
    for path in ROOT.rglob('*.py'):
        if 'tests' in path.relative_to(ROOT).parts or path.name == 'instruction_text.py':
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        sections = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                public = any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                             and isinstance(d.func.value, ast.Name) and d.func.value.id == 'mcp'
                             and d.func.attr in {'tool', 'resource', 'prompt'} for d in node.decorator_list)
                if public:
                    assert ast.get_docstring(node) is None, (path, node.name)
                    docs = [d for d in node.decorator_list if isinstance(d, ast.Call)
                            and isinstance(d.func, ast.Name) and d.func.id == 'tool_instruction']
                    # Resources without a description need no new instruction text.
                    if docs:
                        assert len(docs) == 1
                        assert docs[0].args[1].value == node.name
                        assert read_instruction(str(path), node.name).strip()
                        sections.add(node.name)
                        public_count += 1
                    elif any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                             and d.func.attr == 'tool' for d in node.decorator_list):
                        pytest.fail(f'Missing tool instruction: {path}:{node.name}')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'read_instruction':
                assert isinstance(node.args[0], ast.Name) and node.args[0].id == '__file__'
                section = ast.literal_eval(node.args[1])
                assert read_instruction(str(path), section).strip()
                sections.add(section)
        if sections:
            referenced[path.with_name(path.stem + '-explain.md')] = sections
    assert public_count >= 80
    markdown = set(ROOT.rglob('*-explain.md'))
    assert set(referenced) == markdown
    for path, sections in referenced.items():
        listed = re.findall(r'^<!-- instruction:([^\n]+) -->$', path.read_text(encoding='utf-8'), re.M)
        assert len(listed) == len(set(listed))
        assert sections == set(listed), path


def test_missing_or_duplicate_instruction_fails_closed(tmp_path):
    source = tmp_path / 'sample.py'
    with pytest.raises(FileNotFoundError):
        read_instruction(str(source), 'sample')
    markdown = source.with_name('sample-explain.md')
    markdown.write_text('<!-- instruction:sample -->\nOriginal {0!r}\n<!-- /instruction:sample -->', encoding='utf-8')
    @tool_instruction(str(source), 'sample')
    def sample():
        return 42
    assert sample.__doc__ == "Original {0!r}"
    assert sample() == 42
    assert read_instruction(str(source), 'sample').format('value') == "Original 'value'"
    with pytest.raises(ValueError):
        read_instruction(str(source), 'missing')
    markdown.write_text(markdown.read_text(encoding='utf-8') * 2, encoding='utf-8')
    with pytest.raises(ValueError):
        read_instruction(str(source), 'sample')
