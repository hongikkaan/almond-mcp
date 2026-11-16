"""Send required guidance and the original task as one launch's user input.

The launcher supplies a disposable UTF-8 JSON request, avoiding PowerShell's
native argument rewriting. No conversation history or persisted settings are
read or changed. stdout/stderr and interactive stdin belong to the child.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from almond_mcp.modeling_guidance import startup_instructions


WAIT_FOR_REQUEST = "필수 지침을 확인하고 사용자의 작업 요청을 기다리세요."
WINDOWS_COMMAND_LINE_LIMIT = 32767


def compose_user_input(prompt: str | None) -> str:
    """Read current guidance once and append the task without interpreting it."""
    if prompt is not None and not isinstance(prompt, str):
        raise ValueError("prompt must be a string or null.")
    return startup_instructions() + "\n\nUser request:\n" + (
        WAIT_FOR_REQUEST if prompt is None else prompt
    )


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or "\0" in value:
        raise ValueError(f"{name} must be a string without NUL characters.")
    return value


def _path(value: object, name: str, *, directory: bool = False) -> Path:
    path = Path(_string(value, name))
    if not path.is_absolute() or not (path.is_dir() if directory else path.is_file()):
        kind = "directory" if directory else "file"
        raise ValueError(f"{name} must name an existing absolute {kind}.")
    return path


def check_windows_command_line(arguments: list[str]) -> None:
    """Count the actual Windows quoted command, including its terminating NUL."""
    size = len(subprocess.list2cmdline(arguments).encode("utf-16-le")) // 2 + 1
    if size > WINDOWS_COMMAND_LINE_LIMIT:
        raise ValueError("Codex command exceeds the Windows 32767 UTF-16 unit limit; no process was started.")


def launch(request: object) -> int:
    """Validate a request and return the child exit code without modifying it."""
    if not isinstance(request, dict):
        raise ValueError("The launch request must be a JSON object.")
    required = {"codex", "arguments", "cwd", "prompt", "stdin_prompt"}
    if not required <= request.keys() or request.keys() - required - {"powershell", "prompt_index"}:
        raise ValueError("The launch request has missing or unknown fields.")
    executable = _path(request["codex"], "codex")
    cwd = _path(request["cwd"], "cwd", directory=True)
    values = request["arguments"]
    if not isinstance(values, list):
        raise ValueError("arguments must be a list of strings.")
    arguments = [_string(value, "arguments entry") for value in values]
    prompt = request["prompt"]
    if prompt is not None:
        prompt = _string(prompt, "prompt")
    stdin_prompt = request["stdin_prompt"]
    if not isinstance(stdin_prompt, bool):
        raise ValueError("stdin_prompt must be a boolean.")
    if stdin_prompt and (prompt is not None or "prompt_index" in request):
        raise ValueError("stdin_prompt cannot be combined with prompt or prompt_index.")
    prompt_index = request.get("prompt_index", len(arguments))
    if type(prompt_index) is not int or not 0 <= prompt_index <= len(arguments):
        raise ValueError("prompt_index must be an integer within arguments.")

    if executable.suffix.lower() == ".ps1":
        powershell = _path(request.get("powershell"), "powershell")
        if powershell.suffix.lower() != ".exe":
            raise ValueError("powershell must be an executable .exe file.")
        command = [str(powershell), "-NoProfile", "-File", str(executable)]
    elif executable.suffix.lower() in {".cmd", ".bat"}:
        raise ValueError("Batch Codex wrappers are unsupported; select codex.exe or a PowerShell script.")
    else:
        if executable.suffix.lower() != ".exe":
            raise ValueError("codex must be an executable .exe file or a PowerShell .ps1 script.")
        command = [str(executable)]

    # Binary input preserves CRLF and trailing whitespace in exec's original
    # UTF-8 task. An interactive invocation leaves the console stdin untouched.
    if stdin_prompt:
        prompt = sys.stdin.buffer.read().decode("utf-8")
    composed = compose_user_input(prompt)
    _string(composed, "composed user input")
    if not stdin_prompt:
        arguments.insert(prompt_index, composed)
    command.extend(arguments)
    check_windows_command_line(command)
    if stdin_prompt:
        return subprocess.run(command, cwd=cwd, input=composed.encode("utf-8"), check=False).returncode
    return subprocess.run(command, cwd=cwd, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8-sig"))
        return launch(request)
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        # Do not print the request or task contents on failure.
        print(f"Almond user guidance: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
