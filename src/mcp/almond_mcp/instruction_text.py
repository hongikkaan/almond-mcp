"""Read adjacent Markdown instructions without importing a model runtime."""
from pathlib import Path


def read_instruction(source_file: str, section: str) -> str:
    path = Path(source_file).with_name(Path(source_file).stem + "-explain.md")
    text = path.read_text(encoding="utf-8")
    start = f"<!-- instruction:{section} -->\n"
    end = f"<!-- /instruction:{section} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate instruction section {section!r} in {path}")
    return text.split(start, 1)[1].split(end, 1)[0].removesuffix("\n")


def tool_instruction(source_file: str, section: str):
    def apply(function):
        function.__doc__ = read_instruction(source_file, section)
        return function
    return apply
