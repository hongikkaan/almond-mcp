"""Project-relative paths for managed tool calls; no Rhino-wide cwd changes."""
import os
from pathlib import Path


def bound_model_path(value: str = "") -> str:
    bound = os.environ.get("ALMOND_MODEL_PATH", "")
    if not value:
        if not bound:
            raise ValueError("No bound model path is available for this connection.")
        return bound
    if bound and not Path(value).is_absolute():
        value = str(project_path(value))
    return value


def project_path(relative: str, *, base: Path | None = None) -> Path:
    root = Path(os.environ["ALMOND_PROJECT_ROOT"]).resolve() if base is None else base.resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive or any(part == ".." for part in candidate.parts):
        raise ValueError("Use a relative path inside the managed project/artifact folder.")
    target = root / candidate
    for part in (target, *target.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Managed paths cannot traverse filesystem links.")
        if part == root:
            break
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("The path escapes its managed folder.")
    return resolved


def relative_path(value: str, root: str | None = None) -> str:
    root = root or os.environ.get("ALMOND_PROJECT_ROOT")
    if not root or not value or not os.path.isabs(value):
        return value
    try:
        return Path(os.path.relpath(value, root)).as_posix()
    except ValueError:
        return "[unavailable: a relative path between different drives does not exist]"


def relative_output(value):
    """Only absolute filesystem strings are changed, not URI/code/text payloads."""
    if isinstance(value, list):
        return [relative_output(item) for item in value]
    if isinstance(value, dict):
        return {key: relative_output(item) for key, item in value.items()}
    if isinstance(value, str) and "\n" not in value and os.path.isabs(value):
        return relative_path(value)
    return value
