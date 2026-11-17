"""Keep personal assets in AppData when Almond is installed from this checkout."""
import os

from almond_mcp import __version__, paths


def bound_library_dirs() -> dict[str, str]:
    """Resolve the document worker's paths without changing its environment."""
    result = {}
    for variable, name in paths.LIBRARY_DIRS.items():
        if explicit := os.environ.get(variable):
            result[variable] = explicit
            continue
        target = paths.user_data_dir() / name
        if name in {"GeneratedAssetfiles", "Draftingfiles"}:
            target = target / "releases" / __version__
        result[variable] = str(target)
    return result


def configure_library_paths():
    os.environ.update(bound_library_dirs())
