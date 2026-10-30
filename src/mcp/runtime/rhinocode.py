"""Official RhinoCode execution with durable, independently retrievable completion.

This is trusted synchronous user-code execution, not a sandbox. A subprocess
timeout never cancels, repeats, or discards a dispatched Rhino operation.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from uuid import uuid4

from project import process_start_ticks, read_json, verify_process, write_json


LANGUAGES = frozenset({"python", "python2", "csharp-script", "command"})
# Each mode passed saved-document modeling and single Undo/Redo live acceptance
# on Rhino 8.34. New language modes must pass their own gate before being added.
VERIFIED_LANGUAGES: frozenset[str] = frozenset({"python", "python2", "csharp-script", "command"})
RECEIPT_LIMIT = 65536
RESULT_LIMIT = 16 * 1024 * 1024
LOG_LIMIT = 1024 * 1024
SOURCE_LIMIT = 262144
_UUID = re.compile(r"[0-9a-f]{32}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_IDENTITY = ("token", "operation_id", "request_id", "nonce", "source_hash", "target")


def _normal_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(value))


def _document_serial(value) -> int:
    if type(value) is int and 0 < value <= 0xffffffff:
        return value
    if (isinstance(value, str) and value.isascii() and value.isdecimal()
            and 0 < int(value) <= 0xffffffff):
        return int(value)
    raise ValueError("The binding needs a positive document runtime serial.")


def _valid_ticks(value) -> bool:
    return (isinstance(value, str) and value.isascii() and value.isdecimal()
            and 1 <= len(value) <= 19 and not value.startswith("0")
            and int(value) <= 0x7fffffffffffffff)


def _owned(path: Path, root: Path) -> Path:
    path, root = path.absolute(), root.absolute()
    if path == root or not path.is_relative_to(root):
        raise ValueError("Execution files must be inside the bound call directory.")
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("Execution files cannot use directory links.")
        if item == root:
            break
    if path.resolve() != path:
        raise ValueError("Execution path resolves outside its owned location.")
    return path


def _validate_journal(journal: dict) -> None:
    if (not isinstance(journal, dict)
            or journal.get("schema") != "almond-rhinocode-execution"
            or type(journal.get("version")) is not int or journal["version"] != 1):
        raise ValueError("Unknown RhinoCode execution journal.")
    for field in ("token", "operation_id", "request_id", "nonce"):
        if not isinstance(journal.get(field), str) or not _UUID.fullmatch(journal[field]):
            raise ValueError("Invalid execution " + field + ".")
    if not isinstance(journal.get("source_hash"), str) or not _HASH.fullmatch(journal["source_hash"]):
        raise ValueError("Invalid execution source hash.")
    if journal.get("language") not in LANGUAGES:
        raise ValueError("Invalid execution language.")
    if "layout" in journal and journal["layout"] != "compact-v1":
        raise ValueError("Unknown RhinoCode execution storage layout.")
    target = journal.get("target")
    if (not isinstance(target, dict) or type(target.get("pid")) is not int or target["pid"] <= 0
            or not _valid_ticks(target.get("process_start_ticks"))
            or type(target.get("document_serial")) is not int or not 0 < target["document_serial"] <= 0xffffffff
            or not isinstance(target.get("model_path"), str) or not target["model_path"]
            or not isinstance(target.get("pipe_id"), str) or not target["pipe_id"]):
        raise ValueError("Invalid RhinoCode target identity.")


def _matches_binding(journal: dict, binding: dict) -> None:
    _validate_journal(journal)
    target = journal["target"]
    if (journal["token"] != binding.get("token")
            or target["pid"] != binding.get("pid")
            or target["process_start_ticks"] != str(binding.get("process_start_ticks"))
            or target["document_serial"] != _document_serial(binding.get("document_serial"))
            or _normal_path(target["model_path"]) != _normal_path(str(binding.get("model_path", "")))):
        raise ValueError("RhinoCode journal does not match the bound session.")


def _process_alive(record: dict) -> bool | None:
    # Imported when called, after both modules are initialized. Reuse the same
    # three-state Windows process check as retired-session cleanup.
    from storage_cleanup import process_identity_alive
    return process_identity_alive(record)


def _receipt(path: Path, journal: dict) -> dict:
    if path.stat().st_size > RECEIPT_LIMIT:
        raise ValueError("RhinoCode completion receipt exceeds its limit.")
    result = read_json(path)
    if (result.get("schema") != "almond-rhinocode-completion"
            or type(result.get("version")) is not int or result["version"] != 1
            or result.get("execution_complete") is not True
            or result.get("status") not in {"success", "error", "rejected"}
            or result.get("mutation_state") not in {"completed", "partial", "not_started", "unknown"}
            or ("layout" in result) != ("layout" in journal)
            or result.get("layout") != journal.get("layout")
            or any(result.get(key) != journal[key] for key in _IDENTITY)):
        raise ValueError("Completion does not match this exact RhinoCode request.")
    return result


def execution_directory(call_root, journal: dict) -> Path:
    """Derive owned paths from validated identity; no paths come from receipts."""
    _validate_journal(journal)
    root = Path(call_root).absolute()
    operation = root / journal["operation_id"]
    directory = (operation / ("rc-" + journal["request_id"][:12]) if journal.get("layout") == "compact-v1"
                 else operation / "rhinocode" / journal["request_id"])
    return _owned(directory, root)


def find_request_manifest(call_root, request_id: str) -> Path | None:
    """Locate both supported layouts, checking the full ID after short-leaf lookup."""
    if not isinstance(request_id, str) or not _UUID.fullmatch(request_id):
        raise ValueError("request_id must be a returned execution ID.")
    root = Path(call_root).absolute()
    candidates = list(root.glob("*/rc-" + request_id[:12] + "/request.json"))
    candidates.extend(root.glob("*/rhinocode/" + request_id + "/request.json"))
    matches = []
    for candidate in candidates:
        manifest = _owned(candidate, root)
        journal = read_json(manifest)
        if execution_directory(root, journal) / "request.json" != manifest:
            raise ValueError("Retained execution path does not match its manifest.")
        if journal["request_id"] == request_id:
            matches.append(manifest)
    if len(matches) > 1:
        raise ValueError("Multiple retained executions have the same full request_id.")
    return matches[0] if matches else None


def _write_request(path: Path, value: dict) -> None:
    # Only the owning dispatch handle writes this manifest. Exclusive creation
    # plus atomic replacement permits a short temporary name without overwrites.
    temporary = path.with_name(path.name + ".new")
    created = False
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            created = True
            json.dump(value, stream, ensure_ascii=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)


def inspect_execution(journal: dict, *, receipt_path=None, process_inspector=None) -> dict:
    """Inspect persisted evidence without reviving a worker or executing Rhino."""
    state = dict(request_id=journal.get("request_id", "") if isinstance(journal, dict) else "",
                 pending=False, uncertain=True, completed=False, status="unconfirmed",
                 completion_state="unconfirmed", native_completed=False)
    try:
        _validate_journal(journal)
        state.update(operation_id=journal["operation_id"], language=journal["language"])
        if journal.get("not_dispatched") is True and "child" in journal and journal["child"] is None:
            if not isinstance(journal.get("dispatch_error"), str) or not journal["dispatch_error"]:
                raise ValueError("An undispatched execution needs its launch failure.")
            return dict(state, uncertain=False, completed=True, status="error",
                        completion_state="not_started", mutation_state="not_started",
                        not_dispatched=True, error=journal["dispatch_error"])
        final = None
        error = None
        try:
            if receipt_path is None:
                raise ValueError("A derived completion receipt path is required.")
            final = _receipt(Path(receipt_path), journal)
            # Native outcome is useful even if a worker died before journaling
            # its CLI identity. Expose it without claiming lifecycle completion
            # or releasing any execution fence.
            state.update(native_completed=True, native_status=final["status"], completion=final)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            error = str(exc)
        child = journal.get("child")
        if (not isinstance(child, dict) or type(child.get("pid")) is not int or child["pid"] <= 0
                or not _valid_ticks(child.get("process_start_ticks"))):
            raise ValueError("The dispatched CLI process identity is not yet confirmed.")
        alive = (process_inspector or _process_alive)(child)
        if alive not in (True, False, None):
            alive = None
        if alive is False and final is not None:
            return dict(state, pending=False, uncertain=False, completed=True,
                        completion_state="completed", status=final["status"],
                        mutation_state=final["mutation_state"], completion=final)
        if alive is True:
            state.update(pending=True, completion_state="finishing" if final else "running",
                         status="pending")
        elif alive is False and final is None:
            # The official CLI can acknowledge dispatch and exit before Rhino
            # begins the queued script. Its exit is not a native completion.
            state.update(pending=True, completion_state="awaiting_receipt", status="pending")
        state["message"] = (error if error else
                            "The exact completion exists; CLI process exit is not yet confirmed.")
        if alive is None:
            state["message"] = "CLI process access is inconclusive. " + state["message"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        state["message"] = str(exc)
    return state


def inspect_session(session_dir, *, process_inspector=None) -> dict:
    session = Path(session_dir).absolute()
    journal_path = session / "rhinocode.json"
    try:
        if not journal_path.exists():
            return dict(request_id="", pending=False, uncertain=False, completed=True,
                        status="idle", completion_state="idle")
        journal, binding = read_json(journal_path), read_json(session / "ready.json")
        _matches_binding(journal, binding)
        if journal["token"] != session.name:
            raise ValueError("Execution token does not own this session directory.")
        root = session.parent.parent / "tmp" / "python" / session.name
        receipt = execution_directory(root, journal) / "complete.json"
        return inspect_execution(journal, receipt_path=receipt, process_inspector=process_inspector)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        return dict(request_id="", pending=False, uncertain=True, completed=False,
                    status="unconfirmed", completion_state="unconfirmed", message=str(exc))


def find_binary(explicit=None) -> Path:
    choices = [explicit, os.environ.get("ALMOND_RHINOCODE"), shutil.which("rhinocode")]
    if sys.platform == "win32":
        choices.append(str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) /
                           "Rhino 8" / "System" / "rhinocode.exe"))
    else:
        choices.append("/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode")
    for candidate in choices:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if not path.is_file():
                if candidate == explicit or candidate == os.environ.get("ALMOND_RHINOCODE"):
                    raise FileNotFoundError("Configured RhinoCode executable does not exist.")
                continue
            if sys.platform == "win32" and path.suffix.lower() != ".exe":
                raise ValueError("RhinoCode must be the native executable, not a shell script.")
            return path
    raise FileNotFoundError("RhinoCode was not found. Rhino 8.11 or later is required.")


def discover_instances(binary=None) -> list[dict]:
    executable = find_binary(binary)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    result = subprocess.run([str(executable), "list", "--json"], shell=False,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=10,
                            creationflags=flags)
    if result.returncode:
        raise RuntimeError("RhinoCode discovery failed: " +
                           result.stderr.decode("utf-8", "replace")[:2000])
    if len(result.stdout) > 1024 * 1024:
        raise ValueError("RhinoCode discovery exceeded its output limit.")
    instances = json.loads(result.stdout.decode("utf-8-sig"))
    if not isinstance(instances, list) or any(not isinstance(item, dict) for item in instances):
        raise ValueError("RhinoCode returned an invalid instance list.")
    return instances


def select_instance(binding: dict, instances: list[dict]) -> dict:
    """PID alone never selects a target: start identity and discovered doc agree."""
    verify_process(binding)
    matches = [item for item in instances if item.get("processId") == binding["pid"]]
    if len(matches) != 1:
        raise RuntimeError("No unique ScriptServer for the bound Rhino. Run StartScriptServer in that Rhino.")
    item = matches[0]
    if (not isinstance(item.get("pipeId"), str) or not item["pipeId"]
            or _normal_path(str(item.get("activeDoc", {}).get("location", ""))) !=
            _normal_path(binding["model_path"])):
        raise RuntimeError("The discovered ScriptServer does not have the bound saved document.")
    match = re.match(r"(\d+)\.(\d+)", str(item.get("processVersion", "")))
    if not match or tuple(map(int, match.groups())) < (8, 11):
        raise RuntimeError("The bound ScriptServer does not report Rhino 8.11 or later.")
    return item


def _child_identity(process) -> dict:
    # The owned Popen handle remains valid even if a very fast CLI already exited.
    # project.process_start_ticks deliberately rejects exited processes.
    if sys.platform != "win32":
        return dict(pid=process.pid, process_start_ticks=process_start_ticks(process.pid))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    values = [wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(int(process._handle), *(ctypes.byref(value) for value in values)):
        raise ctypes.WinError(ctypes.get_last_error())
    ticks = ((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime) + 504911232000000000
    return dict(pid=process.pid, process_start_ticks=str(ticks))


def build_wrapper(request: dict, source: str, directory: Path, *, project_root: str,
                  artifact_dir: str, executable: Path) -> tuple[str, str]:
    payload = dict(request=request, source=source, directory=str(directory),
                   project_root=project_root, artifact_dir=artifact_dir,
                   result_limit=RESULT_LIMIT)
    language = request["language"]
    if language == "csharp-script":
        template = Path(__file__).with_name("rhinocode_csharp.cs.txt").read_text(encoding="utf-8")
        data = base64.b64encode(json.dumps(payload, ensure_ascii=True).encode("utf-8")).decode("ascii")
        assembly = executable.parent / "Newtonsoft.Json.dll"
        if not assembly.is_file():
            raise FileNotFoundError("The installed Rhino Newtonsoft.Json assembly is required for C# receipts.")
        # Rhino's package directive parser does not recognize C# verbatim
        # literals here. A quoted forward-slash path matches the official #r syntax.
        text = template.replace("__JSON_ASSEMBLY__", assembly.as_posix().replace('"', '\\"'))
        child = directory / "child.cs"
        child.write_text(text.replace("__PAYLOAD__", data).replace("__USER_BODY__", source),
                         encoding="utf-8", newline="\n")
        payload["child_path"] = str(child)
        # A compile error happens before a C# script's try/finally exists. The
        # stable Python ScriptEditor parent observes its synchronous RunScript
        # return and publishes the outer completion even for compilation errors.
    template = Path(__file__).with_name("rhinocode_python.py.txt").read_text(encoding="utf-8")
    data = base64.b64encode(json.dumps(payload, ensure_ascii=True).encode("utf-8")).decode("ascii")
    runtime = "2" if language == "python2" else "3"
    execute = ("exec compiled in namespace" if language == "python2"
               else "exec(compiled, namespace, namespace)")
    return (".py2" if language == "python2" else ".py",
            template.replace("__PYTHON__", runtime).replace("__PAYLOAD__", data)
            .replace("__EXEC_SOURCE__", execute))


class _Execution:
    def __init__(self, owner, journal, directory):
        self.owner, self.journal, self.directory = owner, journal, directory
        self.request_id = journal["request_id"]
        self.process = None
        self.readers = []
        self.log_info = {}
        self.dispatching = True

    def publish(self):
        _write_request(self.directory / "request.json", self.journal)
        write_json(self.owner.journal_path, self.journal)

    def snapshot(self):
        if self.dispatching:
            return dict(request_id=self.request_id, pending=True, uncertain=True,
                        completed=False, status="pending", completion_state="dispatching")
        def inspector(record):
            if self.process is not None and record == self.journal.get("child"):
                return self.process.poll() is None
            return _process_alive(record)
        state = inspect_execution(self.journal, receipt_path=self.directory / "complete.json",
                                  process_inspector=inspector)
        if self.process is not None:
            state["exit_code"] = self.process.poll()
        return state

    def _drain(self, name, pipe):
        retained, total = 0, 0
        stream = None
        try:
            stream = (self.directory / ("cli_" + name + ".txt")).open("xb")
            while chunk := getattr(pipe, "read1", pipe.read)(8192):
                total += len(chunk)
                available = max(0, LOG_LIMIT - retained)
                if available:
                    stream.write(chunk[:available])
                    stream.flush()
                    retained += min(available, len(chunk))
        except BaseException as exc:
            self.log_info["cli_" + name + "_error"] = str(exc)[:1000]
            # A log write failure must not block the child's stdout pipe.
            try:
                while pipe.read(8192):
                    pass
            except OSError:
                pass
        finally:
            if stream:
                stream.close()
            pipe.close()
            self.log_info["cli_" + name] = dict(bytes=retained, total_bytes=total, truncated=total > retained)

    def launch(self, executable, wrapper):
        try:
            macro = '_-ScriptEditor _Run "' + str(wrapper) + '"'
            self.process = subprocess.Popen(
                [str(executable), "--rhino", self.journal["target"]["pipe_id"], "command", macro],
                cwd=self.owner.locations["project_dir"], shell=False, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        except OSError as exc:
            self.journal.update(not_dispatched=True, dispatch_error=str(exc)[:2000])
            self.dispatching = False
            self.publish()
            return
        try:
            self.journal["child"] = _child_identity(self.process)
            self.publish()
        finally:
            # Even an identity/persistence error after CreateProcess must drain
            # output and retain the dispatched process. It is never replayed.
            for name in ("stdout", "stderr"):
                thread = threading.Thread(target=self._drain, args=(name, getattr(self.process, name)),
                                          daemon=True)
                thread.start()
                self.readers.append(thread)
            self.dispatching = False


def _result_page(value, fields, offset, limit):
    if fields is not None and (not isinstance(fields, list) or any(not isinstance(x, str) for x in fields)):
        raise ValueError("result_fields must be an array of top-level field names.")
    pages = {}
    def page(items, key):
        total = len(items)
        pages[key] = dict(total=total, offset=offset, returned=len(items[offset:offset + limit]),
                          next_offset=offset + limit if offset + limit < total else None)
        return items[offset:offset + limit]
    if isinstance(value, dict):
        keys = list(value) if fields is None else fields
        unknown = set(keys) - set(value)
        if unknown:
            raise ValueError("Unknown result_fields: " + ", ".join(sorted(unknown)))
        result = {key: page(value[key], key) if isinstance(value[key], list) else value[key] for key in keys}
        info = dict(type="object", available_fields=list(value)[:128],
                    field_count=len(value), fields_truncated=len(value) > 128, pages=pages)
    elif isinstance(value, list):
        result = page(value, "result")
        if fields is not None:
            if any(not isinstance(row, dict) for row in result):
                raise ValueError("result_fields needs object rows in an array result.")
            result = [{key: row[key] for key in fields if key in row} for row in result]
        info = dict(type="array", pages=pages)
    elif isinstance(value, str):
        if fields:
            raise ValueError("String results have no result_fields.")
        result, info = page(value, "result"), dict(type="string", unit="characters", pages=pages)
    else:
        if fields:
            raise ValueError("Scalar results have no result_fields.")
        result, info = value, dict(type="scalar")
    return result, info


def _execution_summary(value):
    """Keep routine design answers small; detailed evidence remains retrievable."""
    if value.get("completed") is not True or value.get("status") != "success":
        return value
    keys = {"status", "completed", "request_id", "mutation_state", "result",
            "result_error", "result_display_error", "diagnostics_truncated"}
    summary = {key: item for key, item in value.items() if key in keys}
    page = value.get("result_page", {})
    has_more = any(item.get("next_offset") is not None for item in page.get("pages", {}).values())
    if has_more or page.get("metadata_truncated"):
        summary["result_page"] = page
    if has_more or "result_display_error" in value:
        for key in ("result_file", "result_bytes", "result_sha256"):
            if key in value:
                summary[key] = value[key]
    return summary


def execution_output(value, *, include_diagnostics=False):
    """Project a public result read without changing retained/lifecycle evidence."""
    if type(include_diagnostics) is not bool:
        raise ValueError("include_diagnostics must be a boolean.")
    if (include_diagnostics or not isinstance(value, dict)
            or value.get("completed") is not True or value.get("status") != "success"
            or value.get("exit_code") not in (None, 0)
            or value.get("mutation_state") in {"partial", "unknown"}):
        return value
    flags = ("pending", "uncertain", "native_pending", "native_uncertain",
             "external_pending", "external_uncertain")
    runtime = value.get("runtime_completion", {})
    if (not isinstance(runtime, dict)
            or any(value.get(key) or runtime.get(key) for key in flags)
            or any(value.get(key) for key in ("error", "result_error", "result_display_error", "cleanup_errors", "diagnostics_truncated"))
            or value.get("result_page", {}).get("metadata_truncated")):
        return value
    keys = {"request_id", "completed", "status", "mutation_state", "result", "result_page",
            "message", "warnings", "connection_state", "requires_reconnect", "recovery_only",
            "target_identity", "rhino_process_alive", "log_capture"}
    # Preserve explicitly requested log chunks and their byte paging/capture notes.
    for stream in ("stdout", "stderr", "cli_stdout", "cli_stderr"):
        keys.update((stream, stream + "_page", stream + "_capture", stream + "_display_error"))
    if "result" not in value:
        keys.add("result_available")
    return {key: item for key, item in value.items() if key in keys}


class RhinocodeExecution:
    def __init__(self, binding: dict, locations: dict, *, binary=None,
                 enabled_languages=None, command_enabled=None):
        self.binding, self.locations = dict(binding), dict(locations)
        self.binary = binary
        self.enabled_languages = set(VERIFIED_LANGUAGES if enabled_languages is None else enabled_languages)
        self.command_enabled = ("command" in VERIFIED_LANGUAGES) if command_enabled is None else command_enabled
        self.journal_path = Path(locations["session_dir"]) / "rhinocode.json"
        self.handles = {}

    def availability(self):
        try:
            executable = find_binary(self.binary)
            instance = select_instance(self.binding, discover_instances(executable))
            languages = sorted(self.enabled_languages - (set() if self.command_enabled else {"command"}))
            return dict(available=bool(languages), executable=str(executable),
                        pipe_id=instance["pipeId"], version=instance["processVersion"],
                        languages=languages)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            return dict(available=False, languages=[], message=str(exc))

    def execute(self, script, language, timeout_seconds, *, operation_id, operation_dir,
                register, artifact_dir=""):
        if language not in LANGUAGES or language not in self.enabled_languages:
            raise ValueError("This RhinoCode language has not passed its live acceptance gate.")
        if language == "command" and not self.command_enabled:
            raise ValueError("Command completion has not passed its synchronous execution gate.")
        if not isinstance(script, str) or not script.strip() or len(script.encode("utf-8")) > SOURCE_LIMIT:
            raise ValueError("script must be nonempty UTF-8 source at most 262144 bytes.")
        if re.search(r"(?im)^\s*(?:#|//)\s*async\s*:\s*true\b", script):
            raise ValueError("Asynchronous script bodies are outside the completion contract.")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be an integer from 1 to 600.")
        if not isinstance(operation_id, str) or not _UUID.fullmatch(operation_id):
            raise ValueError("Invalid operation identity.")
        prior = inspect_session(self.locations["session_dir"])
        if prior["completed"] is not True:
            raise RuntimeError("A previous RhinoCode execution still needs exact completion recovery.")
        executable = find_binary(self.binary)
        instance = select_instance(self.binding, discover_instances(executable))
        call_root = Path(self.locations["call_root"]).absolute()
        operation = _owned(Path(operation_dir), call_root)
        if operation != call_root / operation_id:
            raise ValueError("The execution operation directory does not match its identity.")
        request_id = uuid4().hex
        directory = _owned(operation / ("rc-" + request_id[:12]), call_root)
        # The installed Python 2/.NET file APIs may retain MAX_PATH even when
        # external Python accepts longer paths. Check every generated receipt's
        # atomic temporary name before any process can be dispatched.
        if sys.platform == "win32" and len(str(directory / "child-complete.json.new").encode("utf-16-le")) // 2 >= 260:
            raise ValueError("The project path is too long for guaranteed Rhino completion files; "
                             "use a shorter project/storage path before executing.")
        directory.mkdir(parents=True, exist_ok=False)
        target = dict(pid=self.binding["pid"], process_start_ticks=str(self.binding["process_start_ticks"]),
                      document_serial=_document_serial(self.binding["document_serial"]),
                      model_path=self.binding["model_path"],
                      pipe_id=instance["pipeId"])
        journal = dict(schema="almond-rhinocode-execution", version=1, layout="compact-v1",
                       token=self.binding["token"],
                       operation_id=operation_id, request_id=request_id, nonce=uuid4().hex,
                       source_hash=hashlib.sha256(script.encode("utf-8")).hexdigest(),
                       language=language, target=target, child=None)
        _validate_journal(journal)
        suffix, wrapper_text = build_wrapper(journal, script, directory,
            project_root=self.locations["project_dir"], artifact_dir=str(artifact_dir), executable=executable)
        wrapper = directory / ("wrapper" + suffix)
        wrapper.write_text(wrapper_text, encoding="utf-8", newline="\n")
        source_suffix = ".cs" if language == "csharp-script" else suffix
        (directory / ("source" + source_suffix)).write_text(script, encoding="utf-8", newline="\n")
        handle = _Execution(self, journal, directory)
        register(handle)
        self.handles[request_id] = handle
        try:
            handle.publish()  # Durable fence precedes CreateProcess.
        except BaseException:
            handle.journal.update(not_dispatched=True, dispatch_error="Could not persist the execution fence.")
            handle.dispatching = False
            raise
        handle.launch(executable, wrapper)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            state = handle.snapshot()
            if state["completed"]:
                break
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        result = self.get_execution(request_id=request_id, limit=20, include_ids=True)
        if not result["completed"]:
            result["timed_out"] = True
            result["message"] = ("Execution is retained. Retrieve this request with get_rhino_execution; "
                                 "do not repeat the Rhino work.")
        return _execution_summary(result)

    def _load(self, request_id):
        if request_id:
            root = Path(self.locations["call_root"]).absolute()
            manifest = find_request_manifest(root, request_id)
            if manifest is None:
                raise ValueError("No unique retained execution for this request_id.")
            journal = read_json(manifest)
        else:
            journal = read_json(self.journal_path)
            root = Path(self.locations["call_root"]).absolute()
            _validate_journal(journal)
            manifest = execution_directory(root, journal) / "request.json"
        _matches_binding(journal, self.binding)
        if execution_directory(root, journal) / "request.json" != manifest:
            raise ValueError("Retained execution path does not match its manifest.")
        return journal, manifest.parent

    def has_execution(self, request_id):
        manifest = find_request_manifest(self.locations["call_root"], request_id)
        if manifest is None:
            return False
        _matches_binding(read_json(manifest), self.binding)
        return True

    def get_execution(self, request_id="", *, include_result=True, include_stdout=False,
                      result_fields=None, offset=0, limit=100, include_ids=True):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("offset must be nonnegative and limit must be 1-1000.")
        if any(type(flag) is not bool for flag in (include_result, include_stdout, include_ids)):
            raise ValueError("Execution output switches must be booleans.")
        if not request_id and not self.journal_path.exists():
            return dict(request_id="", pending=False, uncertain=False, completed=True,
                        status="idle", completion_state="idle")
        journal, directory = self._load(request_id)
        handle = self.handles.get(journal["request_id"])
        result = (handle.snapshot() if handle else
                  inspect_execution(journal, receipt_path=directory / "complete.json"))
        final = result.pop("completion", None)
        if final:
            for key in ("execution_complete", "mutation_state", "error", "result_error",
                        "cleanup_errors", "undo", "user_code_started", "user_code_completed", "diagnostics_truncated"):
                if key in final:
                    result[key] = final[key]
            result["result_available"] = final.get("result_available") is True
            if result["result_available"]:
                result["result_bytes"] = final.get("result_bytes")
                result["result_sha256"] = final.get("result_sha256")
                try:
                    result["result_file"] = str(_owned(directory / "result.json",
                                                      Path(self.locations["call_root"])))
                except (OSError, ValueError, TypeError) as exc:
                    result["result_display_error"] = str(exc)
            if include_result and result["result_available"]:
                try:
                    path = _owned(directory / "result.json", Path(self.locations["call_root"]))
                    if path.stat().st_size > RESULT_LIMIT:
                        raise ValueError("Retained result exceeds its storage limit.")
                    raw = path.read_bytes()
                    if (len(raw) != final.get("result_bytes")
                            or hashlib.sha256(raw).hexdigest() != final.get("result_sha256")):
                        raise ValueError("Retained result no longer matches its completion receipt.")
                    value = json.loads(raw.decode("utf-8-sig"))
                    selected, info = _result_page(value, result_fields, offset, limit)
                    if not include_ids:
                        from almond_mcp.query_output import project_query
                        selected = project_query(selected, include_ids=False)
                    if len(json.dumps(info, ensure_ascii=True).encode("ascii")) > 8192:
                        info = dict(type=info["type"], metadata_truncated=True,
                                    message="Result field/page metadata exceeds 8192 bytes; inspect result_file.")
                    result["result_page"] = info
                    if len(json.dumps(selected, ensure_ascii=True).encode("ascii")) <= RECEIPT_LIMIT:
                        result["result"] = selected
                    else:
                        result["result_display_error"] = "This page exceeds 65536 bytes. Select result_fields or a smaller limit."
                except (OSError, ValueError, TypeError, RecursionError) as exc:
                    result["result_display_error"] = str(exc)[:4000]
        if include_stdout:
            for name in ("stdout", "stderr", "cli_stdout", "cli_stderr"):
                try:
                    path = _owned(directory / (name + ".txt"), Path(self.locations["call_root"]))
                    if path.exists():
                        with path.open("rb") as stream:
                            stream.seek(offset)
                            data = stream.read(min(limit * 256, RECEIPT_LIMIT))
                        result[name] = data.decode("utf-8", "replace")
                        result[name + "_page"] = dict(offset=offset, returned_bytes=len(data),
                            retained_bytes=path.stat().st_size,
                            next_offset=offset + len(data) if offset + len(data) < path.stat().st_size else None)
                except (OSError, ValueError, TypeError) as exc:
                    result[name + "_display_error"] = str(exc)
            if handle:
                result["log_capture"] = dict(handle.log_info)
            if final:
                result["stdout_capture"] = final.get("stdout_capture", {})
                result["stderr_capture"] = final.get("stderr_capture", {})
        return result
