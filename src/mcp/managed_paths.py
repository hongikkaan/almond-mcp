"""Project-relative paths for managed tool calls; no Rhino-wide cwd changes."""
import os
from pathlib import Path


# Caller data, source records and field values can contain arbitrary strings
# and keys that look like managed paths, IDs or audit timestamps.
VERBATIM_FIELDS = {
    "execute_project_python": {"result"},
    "execute_rhino_script": {"result"},
    "get_objects": {"user_text", "user_dictionary"},
    "get_rhino_context": {"name", "layer_tree"},
    "resolve_object_intersection": {"user_strings", "user_dictionary"},
    "get_logic_by_id": {"metadata"},
    "run_gh_definition": {"outputs"},
    "get_diagram_asset": {"source"},
    "generate_asset_drawing_views": {"manifest"},
    "get_asset_drawing": {"manifest"},
    "get_drawing_asset": {"spatial"},
    "list_drawing_assets": {"spatial"},
    "search_drawing_assets": {"spatial"},
    "prepare_drawing_asset": {"provenance"},
    "get_drawing_recipe": {"recipe"},
    "list_drawing_recipes": {"recipes"},
    "list_materials": {"textures", "physical", "structural_material", "source", "provenance"},
}


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


def relative_path(value: str, root: str | None = None, *, preserve_cross_drive: bool = False) -> str:
    root = root or os.environ.get("ALMOND_PROJECT_ROOT")
    if not root or not value or not os.path.isabs(value):
        return value
    try:
        return Path(os.path.relpath(value, root)).as_posix()
    except ValueError:
        if preserve_cross_drive:
            return value
        return "[unavailable: a relative path between different drives does not exist]"


def drawing_package_path(value: str, *, library_roots: list[Path]) -> Path:
    """Read a project package or an existing package in a configured library.

    Generation returns project-relative paths even for AppData, or absolute
    paths across Windows drives. Only audit's package directory has this
    exception; source/output paths stay managed.
    """
    root_value = os.environ.get("ALMOND_PROJECT_ROOT")
    candidate = Path(value)
    if not root_value:
        if not candidate.is_absolute():
            raise ValueError("Supply an absolute package directory")
        return candidate
    root = Path(root_value).resolve()
    try:
        package = project_path(value, base=root)
    except ValueError:
        package = None
    if package is not None:
        if (package / "drawing.json").is_symlink():
            raise ValueError("Drawing manifests cannot be filesystem links.")
        return package
    # Normalize '..' from the public relative path, then enforce a specific
    # library root and reject links before reading any package contents.
    candidate = Path(os.path.abspath(candidate if candidate.is_absolute() else root / candidate))
    for library in library_roots:
        library = Path(os.path.abspath(library))
        if candidate == library or not candidate.is_relative_to(library):
            continue
        for part in (candidate, *candidate.parents):
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise ValueError("Drawing package paths cannot traverse filesystem links.")
        if candidate.is_dir() and (candidate / "drawing.json").is_file():
            # drawing.json must not redirect the initial manifest read either.
            manifest = candidate / "drawing.json"
            if manifest.is_symlink():
                raise ValueError("Drawing manifests cannot be filesystem links.")
            return candidate
    raise ValueError("Use a project drawing package or a package returned by the configured drawing library.")


def relative_output(value, *, preserve_cross_drive_fields=(), verbatim_fields=()):
    """Only absolute filesystem strings change, not URI/code/text payloads.

    Named package paths keep their spelling across Windows drives. Opaque
    fields are copied as a whole, including nested caller-owned keys.
    """
    if isinstance(value, list):
        return [relative_output(item, preserve_cross_drive_fields=preserve_cross_drive_fields,
                                verbatim_fields=verbatim_fields) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in verbatim_fields:
                result[key] = item
            elif key in preserve_cross_drive_fields and isinstance(item, str) and "\n" not in item:
                result[key] = relative_path(item, preserve_cross_drive=True)
            else:
                result[key] = relative_output(item, preserve_cross_drive_fields=preserve_cross_drive_fields,
                                              verbatim_fields=verbatim_fields)
        return result
    if isinstance(value, str) and "\n" not in value and os.path.isabs(value):
        return relative_path(value)
    return value
