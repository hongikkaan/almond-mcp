"""Expose the flat checkout as almond_mcp; wheels contain the actual package.

The editable install adds this directory to sys.path. Loading its __init__.py
as a package keeps imports, resources and python -m almond_mcp identical to
the wheel without restoring a nested source directory.
"""
from importlib.util import spec_from_file_location
from pathlib import Path
import sys

if __name__ == "__main__":
    from almond_mcp.cli import main
    main()
else:
    _root = Path(__file__).resolve().parent
    _spec = spec_from_file_location(__name__, _root / "__init__.py",
                                    submodule_search_locations=[str(_root)])
    _module = sys.modules[__name__]
    _module.__file__ = str(_root / "__init__.py")
    _module.__path__ = [str(_root)]
    _module.__package__ = __name__
    _module.__spec__ = _spec
    _module.__loader__ = _spec.loader
    _spec.loader.exec_module(_module)
