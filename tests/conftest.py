"""Required offline fixtures must not silently disappear from integration runs."""
import os
from pathlib import Path

import pytest


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    if not any(item.get_closest_marker("archive_host") for item in items):
        return
    host = os.environ.get("ALMOND_ARCHIVE_TEST_HOST", "")
    if not host or not Path(host).is_absolute() or not Path(host).is_file():
        raise pytest.UsageError(
            "ArchiveHost is required for the selected integration tests. "
            "Run ./tests/run_tests.ps1 -Development to build and configure it; "
            "use -DotNet <SDK/dotnet.exe> if needed. "
            "ALMOND_ARCHIVE_TEST_HOST must name an existing absolute executable path."
        )
