"""Read adjacent Markdown instructions without importing a model runtime."""
from functools import wraps
from inspect import signature
from pathlib import Path


def read_instruction(source_file: str, section: str) -> str:
    path = Path(source_file).with_name(Path(source_file).stem + "-explain.md")
    return parse_instruction(path.read_text(encoding="utf-8"), section, path)


def parse_instruction(text: str, section: str, path: Path) -> str:
    """Extract one instruction from an already captured source snapshot."""
    start = f"<!-- instruction:{section} -->\n"
    end = f"<!-- /instruction:{section} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate instruction section {section!r} in {path}")
    return text.split(start, 1)[1].split(end, 1)[0].removesuffix("\n")


def read_tool_instruction(source_file: str, section: str) -> str:
    """Return the complete description, including its Args/Returns metadata."""
    return read_instruction(source_file, section)


def tool_instruction(source_file: str, section: str):
    def apply(function):
        function.__doc__ = read_tool_instruction(source_file, section)
        parameters = signature(function)
        @wraps(function)
        def invoke(*args, **kwargs):
            from almond_mcp.tool_guidance import guide_result
            arguments = parameters.bind(*args, **kwargs)
            arguments.apply_defaults()
            return guide_result(section, function(*args, **kwargs), arguments.arguments)
        return invoke
    return apply
