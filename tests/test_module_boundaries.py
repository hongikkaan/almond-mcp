"""Guard dependency direction and moved build inputs at the integration boundary."""
import ast
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_implementation_and_tests_do_not_import_cos():
    cos_modules = {p.stem for p in (ROOT / 'src/cos').glob('*.py')}
    violations = []
    for path in (ROOT / 'src/mcp').rglob('*.py'):
        if any(part in {'data', '__pycache__', '.venv'} for part in path.relative_to(ROOT).parts):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            imports = ([a.name for a in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            for name in imports:
                if name.split('.')[0] in cos_modules or name.startswith(('src.cos', 'cos.')):
                    violations.append(f'{path.relative_to(ROOT)}:{node.lineno}: {name}')
    assert violations == []


def test_native_project_references_exist_and_have_no_cycles():
    projects = [p for p in (ROOT / 'src').rglob('*.csproj')
                if not any(part in {'data', 'bin', 'obj', 'plugin-runtime'} for part in p.relative_to(ROOT).parts)]
    edges = {}
    for project in projects:
        references = []
        for node in ET.parse(project).getroot().iter():
            relative = node.get('Include', '').replace('\\', '/')
            if node.tag not in {'Compile', 'EmbeddedResource', 'ProjectReference'} or not relative.startswith('../'):
                continue
            matches = list(project.parent.glob(relative))
            assert matches, f'{project.relative_to(ROOT)}: missing {relative}'
            assert all(p.resolve().is_relative_to(ROOT) for p in matches), 'Linked source escaped the checkout.'
            if node.tag == 'ProjectReference':
                references.extend(p.resolve() for p in matches)
        edges[project.resolve()] = references
    def visit(project, ancestors):
        assert project not in ancestors, f'Circular native project reference: {project}'
        for dependency in edges.get(project, []):
            visit(dependency, ancestors | {project})
    for project in edges:
        visit(project, set())
    engine = (ROOT / 'src/rhp/Engine/Almond.Engine.csproj').resolve()
    assert edges[engine] == [], 'The shared Engine must not depend on its hosts.'


def test_old_engine_directory_contains_only_compatibility_entry_points():
    allowed = {'README.md', 'Almond 시작.cmd', 'Almond 정리.cmd',
               'rebuild_environment.ps1', 'use_offline_environment.ps1'}
    files = {p.name for p in (ROOT / 'src/engine').iterdir() if p.is_file()}
    assert files == allowed
