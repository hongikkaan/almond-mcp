"""Exercise user-input delivery through real isolated child processes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from almond_mcp import modeling_guidance
from almond_mcp.required_guidance import REQUIRED_DOCUMENTS
import user_guidance


@pytest.fixture
def sources(tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in REQUIRED_DOCUMENTS}
    for name, path in paths.items():
        path.write_text(f"{name}: 첫 줄\n마지막 줄  \n", encoding="utf-8")
    monkeypatch.setattr(modeling_guidance, "REQUIRED_GUIDE_SOURCES", paths)
    description, _ = modeling_guidance.POLICIES["basic"]
    monkeypatch.setattr(modeling_guidance, "POLICIES", {
        **modeling_guidance.POLICIES, "basic": (description, paths["BASIC-INSTRUCTIONS.md"]),
    })
    monkeypatch.delenv("ALMOND_GUIDANCE_FORMAT", raising=False)
    modeling_guidance._snapshot.cache_clear()
    yield paths
    modeling_guidance._snapshot.cache_clear()


@pytest.fixture
def invocation(tmp_path, sources):
    child = tmp_path / "capture.py"
    child.write_text(
        "import json, os, pathlib, sys\n"
        "payload = {'arguments': sys.argv[3:], 'cwd': os.getcwd(), "
        "'stdin': sys.stdin.buffer.read().decode('utf-8') if sys.argv[2] == 'stdin' else None}\n"
        "pathlib.Path(sys.argv[1]).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')\n"
        "print('child stdout')\n"
        "print('child stderr', file=sys.stderr)\n"
        "sys.exit(int(os.environ.get('ALMOND_TEST_CHILD_EXIT', '0')))\n",
        encoding="utf-8",
    )
    # A real new Python process loads disposable documents, without editing the
    # checkout's policies or creating alternate product source-location settings.
    runner = tmp_path / "runner.py"
    runner.write_text(
        "from pathlib import Path\nimport sys\n"
        f"sys.path.insert(0, {str(Path(user_guidance.__file__).parent)!r})\n"
        "from almond_mcp import modeling_guidance as g\n"
        "g.REQUIRED_GUIDE_SOURCES = {name: Path(sys.argv[1]) / name for name in g.REQUIRED_DOCUMENTS}\n"
        "description, _ = g.POLICIES['basic']\n"
        "g.POLICIES['basic'] = (description, g.REQUIRED_GUIDE_SOURCES['BASIC-INSTRUCTIONS.md'])\n"
        "import user_guidance\nraise SystemExit(user_guidance.main(sys.argv[2:]))\n",
        encoding="utf-8",
    )
    output = tmp_path / "captured.json"
    request = {
        "codex": sys.executable,
        "arguments": [str(child), str(output), "argv"],
        "cwd": str(tmp_path), "prompt": None, "stdin_prompt": False,
    }

    def run(*, stdin=None, patch=None):
        values = {**request, **(patch or {})}
        request_path = tmp_path / "request.json"
        request_path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8-sig")
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(runner), str(tmp_path), "--request", str(request_path)],
            input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    return request, output, run


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
@pytest.mark.parametrize("arguments", [[], ["resume", "saved-id"], ["resume", "--last"]])
def test_new_and_resumed_launch_preserves_original_task_and_each_document_once(
    invocation, sources, monkeypatch, delivery, arguments,
):
    request, output, run = invocation
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)
    prompt = '  원래 "인용" \'문장\' ` $() \\끝\\\r\nUser request:\nBEGIN REQUIRED DOCUMENT x\n  '
    request["arguments"].extend(arguments)
    result = run(patch={"prompt": prompt})
    assert result.returncode == 0, result.stderr.decode("utf-8")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["arguments"][:-1] == arguments
    assert payload["arguments"][-1] == user_guidance.compose_user_input(prompt)
    assert payload["cwd"] == request["cwd"]
    assert payload["stdin"] is None
    guide, original = payload["arguments"][-1].split("\n\nUser request:\n", 1)
    assert original == prompt
    for name, path in sources.items():
        body = path.read_text(encoding="utf-8")
        if delivery == "fields":
            assert json.loads(guide)[name] == body
            assert guide.count(json.dumps(body, ensure_ascii=False)) == 1
        else:
            assert guide.count(body) == 1
    assert result.stdout == (b"child stdout\r\n" if os.name == "nt" else b"child stdout\n")
    assert b"child stderr" in result.stderr


@pytest.mark.parametrize("prompt", [None, "", "   \r\n"])
def test_only_absent_task_gets_wait_instruction(invocation, prompt):
    _, output, run = invocation
    assert run(patch={"prompt": prompt}).returncode == 0
    composed = json.loads(output.read_text(encoding="utf-8"))["arguments"][-1]
    assert composed.endswith("\n\nUser request:\n" + (user_guidance.WAIT_FOR_REQUEST if prompt is None else prompt))


def test_explicit_prompt_index_is_used_without_examining_argument_words(invocation):
    request, output, run = invocation
    request["arguments"].extend(["resume", "--unrelated", "resume"])
    index = len(request["arguments"]) - 3
    assert run(patch={"prompt": "task", "prompt_index": index}).returncode == 0
    assert json.loads(output.read_text(encoding="utf-8"))["arguments"] == [
        user_guidance.compose_user_input("task"), "resume", "--unrelated", "resume",
    ]


def test_exec_stdin_preserves_large_utf8_input_and_existing_arguments(invocation):
    request, output, run = invocation
    prompt = '  한글 "인용"\r\n' + "설계 근거😀 " * 10_000 + "\r\n  "
    request["arguments"][2] = "stdin"
    request["arguments"].extend(["exec", "--json", "--ephemeral", "-"])
    result = run(stdin=prompt.encode("utf-8"), patch={"stdin_prompt": True})
    assert result.returncode == 0, result.stderr.decode("utf-8")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["arguments"] == ["exec", "--json", "--ephemeral", "-"]
    assert payload["stdin"] == user_guidance.compose_user_input(prompt)


def test_child_exit_code_is_returned(invocation, monkeypatch):
    _, output, run = invocation
    monkeypatch.setenv("ALMOND_TEST_CHILD_EXIT", "17")
    assert run().returncode == 17
    assert output.exists()


@pytest.mark.parametrize("failure", ["missing", "blank", "invalid_format"])
def test_bad_guidance_never_starts_child(invocation, sources, monkeypatch, failure):
    _, output, run = invocation
    if failure == "missing":
        sources["design_judgment.md"].unlink()
    elif failure == "blank":
        sources["design_judgment.md"].write_text(" \n", encoding="utf-8")
    else:
        monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", "unknown")
    result = run()
    assert result.returncode == 2
    assert not output.exists()
    assert b"Almond user guidance:" in result.stderr


def test_new_process_rereads_changed_document_without_history_or_dedup_state(invocation, sources):
    _, output, run = invocation
    assert run().returncode == 0
    first = json.loads(output.read_text(encoding="utf-8"))["arguments"][-1]
    sources["design_judgment.md"].write_text("갱신 문서: 마지막\n", encoding="utf-8")
    assert run().returncode == 0
    second = json.loads(output.read_text(encoding="utf-8"))["arguments"][-1]
    assert first != second
    assert second.count("갱신 문서: 마지막\n") == 1


@pytest.mark.parametrize("patch", [
    {"arguments": "not-a-list"}, {"arguments": [42]}, {"arguments": ["bad\0argument"]},
    {"prompt": 1}, {"prompt": "secret\0task"}, {"stdin_prompt": 1},
    {"stdin_prompt": True, "prompt": "task"}, {"stdin_prompt": True, "prompt_index": 0},
    {"prompt_index": True}, {"prompt_index": -1}, {"prompt_index": 10_000},
    {"cwd": "relative"}, {"codex": "relative"}, {"unknown": True},
])
def test_invalid_request_does_not_start_child_or_print_task(invocation, patch):
    _, output, run = invocation
    result = run(patch=patch)
    assert result.returncode == 2
    assert not output.exists()
    assert b"secret" not in result.stderr


def test_windows_utf16_quoted_command_limit_includes_terminating_nul():
    user_guidance.check_windows_command_line(["x" * 32766])
    with pytest.raises(ValueError, match="32767"):
        user_guidance.check_windows_command_line(["x" * 32767])
    user_guidance.check_windows_command_line(["😀" * 16383])
    with pytest.raises(ValueError, match="32767"):
        user_guidance.check_windows_command_line(["😀" * 16384])
    with pytest.raises(ValueError, match="32767"):
        user_guidance.check_windows_command_line(['"' * 16384])


def test_oversized_interactive_input_fails_before_child_without_truncation(invocation):
    _, output, run = invocation
    result = run(patch={"prompt": "😀" * 20_000})
    assert result.returncode == 2
    assert not output.exists()
    assert b"32767" in result.stderr


def test_batch_wrapper_is_rejected(invocation, tmp_path):
    _, output, run = invocation
    wrapper = tmp_path / "codex.cmd"
    wrapper.write_text("@echo unsafe", encoding="utf-8")
    result = run(patch={"codex": str(wrapper)})
    assert result.returncode == 2
    assert b"Batch Codex wrappers are unsupported" in result.stderr
    assert not output.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell script argument boundary")
def test_powershell_wrapper_receives_original_composed_argument_as_data(invocation, tmp_path):
    request, output, run = invocation
    wrapper = tmp_path / "capture.ps1"
    wrapper.write_text(
        "$result = @{ arguments = @($args | Select-Object -Skip 1); cwd = (Get-Location).Path }\n"
        "[IO.File]::WriteAllText($args[0], ($result | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))\n"
        "exit 19\n", encoding="utf-8-sig",
    )
    prompt = ' 한글 "인용" \'작업\' ` $()\r\n다음 줄\\  '
    result = run(patch={
        "codex": str(wrapper), "powershell": shutil.which("powershell.exe"),
        "arguments": [str(output), "resume", "saved-id"], "prompt": prompt,
    })
    assert result.returncode == 19, result.stderr.decode("utf-8")
    payload = json.loads(output.read_text(encoding="utf-8-sig"))
    assert payload["arguments"] == ["resume", "saved-id", user_guidance.compose_user_input(prompt)]
    assert payload["cwd"] == request["cwd"]
