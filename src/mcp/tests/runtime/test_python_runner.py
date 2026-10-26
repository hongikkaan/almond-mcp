"""Exercise real, bounded child processes; never start Rhino or a server."""
import pytest
from python_runner import run_python
from project import process_start_ticks


def test_python_uses_selected_folder_and_bounded_output(tmp_path):
    result = run_python("from pathlib import Path; Path('result.txt').write_text('keep'); print('x'*1000000)", tmp_path, 10, 512)
    assert result["status"] == "success" and result["exit_code"] == 0
    assert len(result["stdout"].encode()) == 512 and result["output_truncated"]
    assert (tmp_path / "result.txt").read_text() == "keep"
    assert list(tmp_path.iterdir()) == [tmp_path / "result.txt"]


def test_python_stops_owned_descendants_and_retains_artifacts_on_timeout(tmp_path):
    child = "import time; time.sleep(30)"
    code = ("import subprocess,sys,time; from pathlib import Path; "
            f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
            "Path('child-pid.txt').write_text(str(p.pid)); time.sleep(30)")
    result = run_python(code, tmp_path, 1)
    assert result["status"] == "error" and result["timed_out"]
    pid = int((tmp_path / "child-pid.txt").read_text())
    with pytest.raises(RuntimeError, match="no longer available|has exited"):
        process_start_ticks(pid)


def test_python_cleans_background_children_even_after_normal_completion(tmp_path):
    code = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(p.pid)"
    result = run_python(code, tmp_path, 10)
    assert result["status"] == "success"
    with pytest.raises(RuntimeError, match="no longer available|has exited"):
        process_start_ticks(int(result["stdout"]))
