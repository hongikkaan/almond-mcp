"""A missing fixture stops the selected suite before test code can run."""
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def guarded_suite(pytester):
    pytester.makeconftest(Path(__file__).with_name("conftest.py").read_text(encoding="utf-8"))
    pytester.makeini("[pytest]\nmarkers = archive_host: requires the standalone archive fixture\n")
    pytester.makepyfile(test_cases='''
from pathlib import Path
import pytest

@pytest.mark.archive_host
def test_archive():
    Path("executed").touch()

def test_independent():
    pass
''')
    return pytester


@pytest.mark.parametrize("host", [None, "missing.exe"])
def test_missing_archive_host_fails_before_execution(guarded_suite, monkeypatch, host):
    if host is None:
        monkeypatch.delenv("ALMOND_ARCHIVE_TEST_HOST", raising=False)
    else:
        monkeypatch.setenv("ALMOND_ARCHIVE_TEST_HOST", str(guarded_suite.path / host))
    result = guarded_suite.runpytest_subprocess("-q")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*ArchiveHost is required*tests/run_tests.ps1 -Development*"])
    assert not (guarded_suite.path / "executed").exists()


def test_independent_selection_does_not_require_archive_host(guarded_suite, monkeypatch):
    monkeypatch.delenv("ALMOND_ARCHIVE_TEST_HOST", raising=False)
    result = guarded_suite.runpytest_subprocess("-q", "-k", "independent")
    result.assert_outcomes(passed=1, deselected=1)
