"""Fail explicitly when a selected native archive fixture is unavailable."""
import os
from pathlib import Path
import pytest


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    if any(item.get_closest_marker("archive_host") for item in items):
        host = Path(os.environ.get("ALMOND_ARCHIVE_TEST_HOST", ""))
        if not host.is_absolute() or not host.is_file():
            raise pytest.UsageError("ArchiveHost is required. Run tests/run_tests.ps1 -Development; supply -DotNet if necessary.")
