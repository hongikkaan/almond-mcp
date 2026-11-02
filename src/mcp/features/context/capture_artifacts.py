"""Store validated capture bytes in an owned artifact or connection folder."""

import hashlib
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4

from almond_mcp.managed_paths import project_path, relative_path


def capture_directory() -> tuple[Path, str]:
    """Choose a Plan artifact or the current connection's disposable capture folder."""
    root = Path(os.environ["ALMOND_PROJECT_ROOT"]).resolve()
    artifact = os.environ.get("ALMOND_ARTIFACT_DIR", "")
    if artifact:
        return project_path((Path(artifact) / "captures").as_posix(), base=root), "plan"

    owned = Path(os.environ["ALMOND_CAPTURE_ROOT"])
    if not owned.is_absolute():
        raise ValueError("No bound connection capture directory is available.")
    relative = owned.relative_to(root)
    parts = relative.parts
    if (len(parts) != 5 or parts[:3] != (".almond", "tmp", "python")
            or not re.fullmatch(r"[0-9a-f]{32}", parts[3]) or parts[4] != "captures"):
        raise ValueError("Capture directory is outside this connection's managed scratch layout.")
    return project_path(relative.as_posix(), base=root), "connection"


def write_png(path: Path, raw: bytes) -> None:
    """Commit complete PNG bytes in the destination directory without a partial final file."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".capture-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows os.rename refuses to replace an existing destination.
        os.rename(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_png(raw: bytes, kind: str) -> dict:
    """Saving is best effort; the caller always retains its validated MCP PNG."""
    info = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        blocker = os.environ.get("ALMOND_CAPTURE_SAVE_ERROR")
        if blocker:
            raise OSError("Capture file ownership could not be acquired: " + blocker)
        if kind not in {"viewport", "context", "inspection"}:
            raise ValueError("Unknown capture kind.")
        directory, lifetime = capture_directory()
        directory.mkdir(parents=True, exist_ok=True)
        # Revalidate after creation so a preexisting link never becomes a write target.
        root = Path(os.environ["ALMOND_PROJECT_ROOT"]).resolve()
        relative_directory = directory.relative_to(root)
        project_path(relative_directory.as_posix(), base=root)
        destination = project_path((relative_directory / f"{kind}-{uuid4().hex}.png").as_posix(), base=root)
        write_png(destination, raw)
        return {"status": "saved", "path": relative_path(str(destination), str(root)),
                "lifetime": lifetime, **info}
    except (OSError, ValueError, KeyError) as exc:
        return {"status": "error", "error_code": "capture_file_write_failed",
                "message": str(exc), **info}
