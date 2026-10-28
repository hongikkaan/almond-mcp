"""Read adjacent Markdown instructions without importing a model runtime."""
from pathlib import Path
import re


def read_instruction(source_file: str, section: str) -> str:
    path = Path(source_file).with_name(Path(source_file).stem + "-explain.md")
    text = path.read_text(encoding="utf-8")
    start = f"<!-- instruction:{section} -->\n"
    end = f"<!-- /instruction:{section} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate instruction section {section!r} in {path}")
    return text.split(start, 1)[1].split(end, 1)[0].removesuffix("\n")


def read_tool_instruction(source_file: str, section: str) -> str:
    description = read_instruction(source_file, section)
    # Keep the full explanation in its adjacent Markdown. FastMCP still needs
    # Args/Returns metadata to preserve parameter and output schemas.
    metadata = re.search(r"^(?:Args|Arguments|Returns|Raises|Yields):\s*$", description, re.M)
    prose = description[:metadata.start()] if metadata else description
    summary = re.split(r"(?<=[.!?])\s+", " ".join(prose.split()), maxsplit=1)[0]
    return summary + ("\n\n" + description[metadata.start():] if metadata else "")


def tool_instruction(source_file: str, section: str):
    def apply(function):
        function.__doc__ = read_tool_instruction(source_file, section)
        return function
    return apply
