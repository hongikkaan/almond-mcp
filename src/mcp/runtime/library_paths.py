"""Keep personal assets in AppData when Almond is installed from this checkout."""
import os

from almond_mcp import __version__, paths


def configure_library_paths():
    for variable, name in paths.LIBRARY_DIRS.items():
        if os.environ.get(variable):
            continue
        target = paths.user_data_dir() / name
        if name in {"GeneratedAssetfiles", "Draftingfiles"}:
            target = target / "releases" / __version__
        os.environ[variable] = str(target)
