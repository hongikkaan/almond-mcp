"""Interactive cleanup of this Almond installation, not all Rhino/Python/Codex.

No file deletion, TCP script requests, settings changes, elevation, taskkill /IM,
or unbounded process-tree kills. --list [--json] is inspection-only.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes as wt
from dataclasses import dataclass, field
import json
import ntpath
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

ENGINE = Path(__file__).resolve().parent
SLOTS = 'ABCDEFGHIJ'
EPOCH_TICKS = 504911232000000000
HELPER_NAMES = {'python.exe', 'pythonw.exe', 'uv.exe', 'uvx.exe',
                'powershell.exe', 'pwsh.exe', 'cmd.exe', 'node.exe'}


def norm(path):
    return ntpath.normcase(ntpath.normpath(str(path)))


def option(args, name):
    for i, arg in enumerate(args):
        if arg.lower() == name.lower() and i + 1 < len(args):
            return args[i + 1]
    return None


def slot_for_port(value):
    try:
        return SLOTS[int(value) - 5501] if 5501 <= int(value) < 5501 + len(SLOTS) else None
    except (ValueError, TypeError):
        return None


@dataclass
class Process:
    pid: int
    parent: int
    started: int
    name: str
    exe: str
    argv: list[str] = field(default_factory=list)
    windows: list[tuple[int, str]] = field(default_factory=list)
    command: str = ''

    @property
    def key(self):
        return self.pid, self.started


@dataclass
class Target:
    process: Process
    kind: str
    slot: str | None
    reason: str
    model: str = ''
    orphan: bool = False

    def public(self):
        return dict(pid=self.process.pid, started=str(self.process.started),
                    name=self.process.name, kind=self.kind, slot=self.slot,
                    reason=self.reason, model=self.model, orphan=self.orphan,
                    windows=[title for _, title in self.process.windows])


def direct_target(p, engine):
    """Match executable arguments, never a substring embedded in a prompt/-c code."""
    name = p.name.lower()
    args = p.argv
    if not args or not p.started or not p.exe:
        return None
    server = norm(engine / 'mcp_server.py')
    if name in ('python.exe', 'pythonw.exe'):
        i = 1
        while i < len(args) and args[i].startswith('-'):
            if args[i] in ('-c', '-m'):
                return None
            i += 2 if args[i] in ('-X', '-W') else 1
        if i < len(args) and norm(args[i]) == server:
            return Target(p, 'mcp', slot_for_port(option(args[i+1:], '--port')), 'MCP 실행 파일 일치')
    elif name == 'codex.exe':
        overrides = {}
        for i, arg in enumerate(args[:-1]):
            if arg in ('-c', '--config'):
                try:
                    item = tomllib.loads(args[i+1]).get('mcp_servers', {}).get('almond_parallel_cli', {})
                    overrides.update(item)
                except (tomllib.TOMLDecodeError, AttributeError, TypeError):
                    continue
        child = overrides.get('args', [])
        command = norm(overrides.get('command', ''))
        runtimes = {norm(engine / sub / 'Scripts' / 'python.exe') for sub in ('.venv', 'python')}
        runtimes.add(norm(engine.parent.parent / 'engine' / '.venv' / 'Scripts' / 'python.exe'))
        if (command in runtimes and isinstance(child, list) and
                any(norm(x) == server for x in child if isinstance(x, str))):
            return Target(p, 'codex', slot_for_port(option(child, '--port')), 'Almond MCP 실행 설정 일치')
    elif name in ('powershell.exe', 'pwsh.exe'):
        path = option(args, '-File')
        if path and norm(path) in {norm(engine / 'launch.ps1'), norm(engine / 'codex.ps1')}:
            letter = (option(args, '-Target') or '').upper()
            slot = letter if len(letter) == 1 and letter in SLOTS else slot_for_port(option(args, '-Port'))
            return Target(p, 'launcher', slot, '전용 실행 스크립트 일치')
    elif name == 'cmd.exe':
        # Only a direct start-button invocation, not a shell command containing its name.
        paths = []
        for i, arg in enumerate(args[:-1]):
            if arg.lower() in ('/c', '/k'):
                # cmd /c ""path with spaces.cmd" " uses different quoting from
                # CommandLineToArgvW. Rejoin only for an EXACT button-path match.
                paths.append(' '.join(args[i+1:]).strip('" \t'))
        if p.command:
            match = re.match(r'^\s*(?:"[^"\r\n]+"|\S+)\s+(?:(?:/d|/s)\s+)*(?:/c|/k)\s+(.+)$', p.command, re.I)
            if match:
                payload = match[1].strip()
                if payload.startswith('""') and payload.endswith('"'):
                    payload = payload[1:-1].strip()
                direct = re.fullmatch(r'"([^"\r\n]+\.cmd)"(?:\s+"[^"\r\n]+\.3dm")?\s*', payload, re.I)
                if direct:
                    paths.append(direct[1])
        for path in paths:
            if norm(path) == norm(engine / 'Almond 시작.cmd'):
                return Target(p, 'launcher', None, '시작 버튼 일치')
            for slot in SLOTS:
                if norm(path) == norm(engine.parent / (slot + ' 시작.cmd')):
                    return Target(p, 'launcher', slot, '이전 시작 버튼 일치')
    elif name == 'rhino.exe':
        for arg in args:
            if arg.lower().startswith('/runscript='):
                macro = arg.split('=', 1)[1].strip('" ').replace('/', '\\')
                expected = '-_RunPythonScript (' + str(engine / 'rhino_start.py') + ')'
                if macro.lower() == expected.replace('/', '\\').lower():
                    model = next((x for x in args[1:] if x.lower().endswith('.3dm')), '')
                    return Target(p, 'rhino', None, 'Rhino 시작 브리지 일치', model)
    return None


def classify(processes, engine=ENGINE, records=(), protected=()):
    by_pid = {p.pid: p for p in processes}
    forbidden = set(protected)
    # Never terminate the cleanup process or its live ancestors.
    for pid in list(forbidden):
        seen = set()
        while pid in by_pid and pid not in seen:
            seen.add(pid)
            p = by_pid[pid]
            parent = by_pid.get(p.parent)
            if parent is None or parent.started > p.started:
                break
            forbidden.add(parent.pid)
            pid = parent.pid
    found = {}
    for p in processes:
        if p.pid not in forbidden:
            target = direct_target(p, engine)
            if target:
                found[p.pid] = target
    # A saved PID is only corroboration; never the sole reason to terminate a process.
    for r in records:
        try:
            target = found.get(int(r['pid']))
            if target and target.process.started == int(r['process_start_ticks']):
                label = r.get('label')
                if isinstance(label, str) and len(label) == 1 and label in SLOTS:
                    target.slot = label
                if not target.model:
                    target.model = r.get('model_path', r.get('document_path', '')) or ''
        except (KeyError, TypeError, ValueError):
            continue
    # Retain a narrow helper whitelist. Do not sweep plug-in children of Rhino,
    # GUI apps, shared Codex daemons, Windows Terminal or unrelated interpreters.
    for _ in range(len(processes) + 1):
        changed = False
        for p in processes:
            parent = found.get(p.parent)
            if (p.pid not in found and p.pid not in forbidden and parent and
                    parent.kind != 'rhino' and p.name.lower() in HELPER_NAMES and
                    p.started >= parent.process.started and p.exe):
                found[p.pid] = Target(p, 'helper', parent.slot, '전용 실행기의 확인된 자식')
                changed = True
        if not changed:
            break
    # Auto launchers have no slot argument; descendants can establish it.
    for t in found.values():
        if t.kind == 'launcher' and t.slot is None:
            labels = set()
            for child in found.values():
                current, seen = child.process, set()
                while current.parent in by_pid and current.pid not in seen:
                    seen.add(current.pid)
                    parent = by_pid[current.parent]
                    if parent.started > current.started:
                        break
                    if parent.pid == t.process.pid and child.slot:
                        labels.add(child.slot)
                        break
                    current = parent
            if len(labels) == 1:
                t.slot = labels.pop()
    controllers = [t for t in found.values() if t.kind in ('codex', 'launcher')]
    for t in found.values():
        if t.kind in ('mcp', 'helper'):
            t.orphan = bool(t.slot and not any(c.slot is None or c.slot == t.slot for c in controllers))
    return sorted(found.values(), key=lambda t: (t.slot or '?', t.kind, t.process.pid))


def read_records(engine=ENGINE):
    records = []
    for slot in SLOTS:
        for name in ('controller.json', 'active.json', 'ready.json'):
            try:
                r = json.loads((engine / 'data' / slot / name).read_text(encoding='utf-8-sig'))
                if isinstance(r, dict):
                    records.append(r)
            except (OSError, ValueError):
                continue
    return records


class Windows:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Windows에서 실행하세요.')
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        def define(lib, name, args, restype):
            fn = getattr(lib, name); fn.argtypes = args; fn.restype = restype
        define(self.k, 'OpenProcess', [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE)
        define(self.k, 'CloseHandle', [wt.HANDLE], wt.BOOL)
        define(self.k, 'GetProcessTimes', [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)]*4, wt.BOOL)
        define(self.k, 'QueryFullProcessImageNameW', [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)], wt.BOOL)
        define(self.k, 'TerminateProcess', [wt.HANDLE, wt.UINT], wt.BOOL)
        define(self.k, 'WaitForSingleObject', [wt.HANDLE, wt.DWORD], wt.DWORD)
        define(self.k, 'CreateMutexW', [wt.LPVOID, wt.BOOL, wt.LPCWSTR], wt.HANDLE)
        define(self.k, 'ReleaseMutex', [wt.HANDLE], wt.BOOL)
        define(self.k, 'LocalFree', [wt.HLOCAL], wt.HLOCAL)
        define(self.shell, 'CommandLineToArgvW', [wt.LPCWSTR, ctypes.POINTER(ctypes.c_int)], ctypes.POINTER(wt.LPWSTR))
        define(self.u, 'GetWindowThreadProcessId', [wt.HWND, ctypes.POINTER(wt.DWORD)], wt.DWORD)
        define(self.u, 'PostMessageW', [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM], wt.BOOL)
        define(self.u, 'IsWindowVisible', [wt.HWND], wt.BOOL)
        define(self.u, 'GetWindow', [wt.HWND, wt.UINT], wt.HWND)
        define(self.u, 'GetWindowTextLengthW', [wt.HWND], ctypes.c_int)
        define(self.u, 'GetWindowTextW', [wt.HWND, wt.LPWSTR, ctypes.c_int], ctypes.c_int)
        self.callback = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        define(self.u, 'EnumWindows', [self.callback, wt.LPARAM], wt.BOOL)

    def argv(self, command):
        count = ctypes.c_int()
        ptr = self.shell.CommandLineToArgvW(command, ctypes.byref(count))
        if not ptr:
            return []
        try:
            return [ptr[i] for i in range(count.value)]
        finally:
            self.k.LocalFree(ctypes.cast(ptr, wt.HLOCAL))

    def gate(self):
        handle = self.k.CreateMutexW(None, False, 'Local\\Almond_Process_Maintenance')
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if self.k.WaitForSingleObject(handle, 0) not in (0, 0x80):
            self.k.CloseHandle(handle)
            raise RuntimeError('다른 Almond 시작/정리가 진행 중입니다. 그 작업이 끝난 뒤 다시 실행하세요.')
        return handle

    def snapshot(self):
        code = r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$s=(Get-Process -Id $PID).SessionId
$rows=@(Get-CimInstance Win32_Process -Filter "SessionId = $s" | ForEach-Object {
  if($_.Name -notin @('Rhino.exe','codex.exe','python.exe','pythonw.exe','powershell.exe','pwsh.exe','cmd.exe','uv.exe','uvx.exe','node.exe')){return}
  $p=$null
  try {
    $p=[Diagnostics.Process]::GetProcessById($_.ProcessId)
    $handle=$p.Handle
    $start=$p.StartTime.ToUniversalTime()
    if([Math]::Abs(($start-$_.CreationDate.ToUniversalTime()).TotalMilliseconds) -ge 2){return}
    @{pid=[int]$_.ProcessId;parent=[int]$_.ParentProcessId;started=$start.Ticks.ToString();
      name=[string]$_.Name;exe=[string]$_.ExecutablePath;command=[string]$_.CommandLine}
  } catch {} finally {if($p){$p.Dispose()}}
})
ConvertTo-Json -InputObject $rows -Depth 3 -Compress
"""
        ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        result = subprocess.run([str(ps), '-NoLogo', '-NoProfile', '-NonInteractive',
                                 '-EncodedCommand', base64.b64encode(code.encode('utf-16le')).decode()],
                                capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('프로세스 목록 조회에 실패했습니다: ' + result.stderr.decode('utf-8-sig', errors='replace').strip())
        # Windows PowerShell can mix legacy-encoded diagnostic stderr with UTF-8
        # JSON stdout. Decode only the JSON channel strictly, after both pipes drain.
        rows = json.loads(result.stdout.decode('utf-8-sig'))
        output = {r['pid']: Process(r['pid'], r['parent'], int(r['started']), r['name'],
                                   r['exe'], self.argv(r['command']) if r['command'] else [],
                                   command=r['command']) for r in rows}
        @self.callback
        def visit(hwnd, _):
            pid = wt.DWORD()
            self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in output and self.u.IsWindowVisible(hwnd) and not self.u.GetWindow(hwnd, 4):
                size = self.u.GetWindowTextLengthW(hwnd)
                text = ctypes.create_unicode_buffer(size+1)
                self.u.GetWindowTextW(hwnd, text, size+1)
                if text.value:
                    output[pid.value].windows.append((int(hwnd), text.value))
            return True
        self.u.EnumWindows(visit, 0)
        return list(output.values())

    def open_match(self, p, terminate=False):
        # Keep this handle open through the action: a reused PID cannot redirect it.
        access = 0x1000 | 0x100000 | (1 if terminate else 0)
        handle = self.k.OpenProcess(access, False, p.pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                raise ProcessLookupError('이미 종료된 프로세스입니다.')
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            times = [wt.FILETIME() for _ in range(4)]
            if not self.k.GetProcessTimes(handle, *[ctypes.byref(x) for x in times]):
                raise ctypes.WinError(ctypes.get_last_error())
            ticks = (times[0].dwHighDateTime << 32) + times[0].dwLowDateTime + EPOCH_TICKS
            size = wt.DWORD(32768); buf = ctypes.create_unicode_buffer(size.value)
            if not self.k.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            if ticks != p.started or norm(buf.value) != norm(p.exe):
                raise RuntimeError('PID가 재사용됐거나 실행 파일이 바뀌어 건너뛰었습니다.')
            return handle
        except BaseException:
            self.k.CloseHandle(handle)
            raise

    def terminate(self, p):
        handle = self.open_match(p, True)
        try:
            if self.k.WaitForSingleObject(handle, 0) == 0:
                return '이미 종료됨'
            if not self.k.TerminateProcess(handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())
            return '종료됨' if self.k.WaitForSingleObject(handle, 5000) == 0 else '종료 요청 후 대기 중'
        finally:
            self.k.CloseHandle(handle)

    def close_window(self, p):
        handle = self.open_match(p)
        try:
            for hwnd, _ in sorted(p.windows, key=lambda w: 'rhinoceros' not in w[1].lower()):
                owner = wt.DWORD()
                self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if owner.value == p.pid:
                    if not self.u.PostMessageW(hwnd, 0x10, 0, 0):
                        raise ctypes.WinError(ctypes.get_last_error())
                    return 'Rhino에 닫기 요청 (저장창이 뜨면 직접 선택)'
            return '닫을 창을 찾지 못함 — 자동 강제 종료하지 않음'
        finally:
            self.k.CloseHandle(handle)


def planned(targets, mode):
    if mode == 'leftovers':
        return [t for t in targets if t.orphan]
    return list(targets)


def execute(selection, mode, system, engine=ENGINE):
    # Consent only applies to the displayed identities, not newly started processes.
    current = classify(system.snapshot(), engine, read_records(engine), (os.getpid(),))
    current = {t.process.key: t for t in planned(current, mode)}
    reports = []
    helpers_failed = False
    rank = {'codex': 0, 'launcher': 1, 'helper': 2, 'mcp': 3, 'rhino': 4}
    for t in sorted(selection, key=lambda t: (rank[t.kind], -t.process.started)):
        now = current.get(t.process.key)
        if now is None or now.kind != t.kind:
            reports.append(dict(pid=t.process.pid, result='종료됐거나 소속/활동 상태가 바뀌어 건너뜀'))
            continue
        try:
            if t.kind == 'rhino' and mode != 'force':
                if helpers_failed:
                    reports.append(dict(pid=t.process.pid, result='보조 프로세스 종료 실패로 Rhino 닫기 보류'))
                    continue
                message = system.close_window(now.process)
            else:
                message = system.terminate(now.process)
                if t.kind == 'codex':
                    time.sleep(0.4) # Let MCP children see EOF and close SQLite normally.
            reports.append(dict(pid=t.process.pid, result=message))
        except ProcessLookupError:
            reports.append(dict(pid=t.process.pid, result='이미 종료됨'))
        except Exception as exc:
            if t.kind != 'rhino':
                helpers_failed = True
            reports.append(dict(pid=t.process.pid, result='종료하지 못함: ' + str(exc)))
    return reports


def display(targets):
    print('\n이 Almond 설치에서 시작한 것으로 확인된 프로세스')
    for t in targets:
        status = '잔여 보조 프로세스' if t.orphan else ('열린 Rhino — 기본 정리 제외' if t.kind == 'rhino' else '실행 중')
        print(f'  [{t.slot or "?"}] PID {t.process.pid:<7} {t.process.name:<17} {status}')
        if t.model:
            print('      ' + t.model)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='조회만; 프로세스를 종료하지 않음')
    parser.add_argument('--json', action='store_true', help='--list와 함께 사용')
    args = parser.parse_args(argv)
    if args.json and not args.list:
        parser.error('--json requires --list')
    system = Windows()
    gate = system.gate()
    try:
        targets = classify(system.snapshot(), ENGINE, read_records(), (os.getpid(),))
        if args.list:
            if args.json:
                print(json.dumps([t.public() for t in targets], ensure_ascii=True, indent=2))
            else:
                display(targets)
            return 0
        print('Almond 프로세스 정리 — DB·tmp·3dm·설정 파일은 삭제하지 않습니다.')
        print('일반 Rhino/Codex, Windows Terminal 전체, 소속을 확인할 수 없는 프로세스는 제외합니다.')
        print('작업 중에는 실행하지 마세요. 전체 종료 전에는 모델과 필요한 대화 내용을 보존하세요.')
        if not targets:
            print('\n정리할 Almond 프로세스를 찾지 못했습니다. 아무것도 종료하지 않았습니다.')
            return 0
        display(targets)
        print('\n1 / Enter: 남은 보조 프로세스만 정리 (열린 Rhino·Codex는 유지)')
        print('2: 위 Almond 작업 전체 종료 — Codex 종료, Rhino에는 닫기 요청')
        print('3: 위 Almond 작업 전체 강제 종료 — 미저장 모델을 잃을 수 있음')
        print('0: 취소')
        choice = input('선택: ').strip() or '1'
        mode = {'1': 'leftovers', '2': 'close', '3': 'force'}.get(choice)
        if not mode:
            print('취소했습니다.'); return 0
        selection = planned(targets, mode)
        if not selection:
            print('안전하게 정리할 잔여 보조 프로세스가 없습니다. 열린 Rhino/Codex는 유지했습니다.')
            return 0
        print('\n아래 대상에만 적용합니다:')
        display(selection)
        word = {'leftovers': '정리', 'close': '종료', 'force': '강제종료'}[mode]
        if mode != 'leftovers':
            print('Codex 실행 중 작업/대화는 중단됩니다. Rhino 모델 저장을 먼저 확인하세요.')
        if mode == 'force':
            print('경고: Rhino 저장 확인 없이 종료합니다. 미저장 변경은 복구를 보장할 수 없습니다.')
        if input(f'계속하려면 {word} 입력 (그 외 취소): ').strip() != word:
            print('취소했습니다.'); return 0
        for report in execute(selection, mode, system):
            print(f"PID {report['pid']}: {report['result']}")
        time.sleep(0.5)
        remaining = classify(system.snapshot(), ENGINE, read_records(), (os.getpid(),))
        if remaining:
            print('\n남은 프로세스가 있습니다. 저장 확인창은 Rhino에서 직접 처리하세요. 자동 재시도하지 않습니다.')
            display(remaining)
        else:
            print('\n확인된 Almond 프로세스가 모두 종료됐습니다.')
        return 0
    finally:
        system.k.ReleaseMutex(gate)
        system.k.CloseHandle(gate)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print('\n취소했습니다.')
    except Exception as exc:
        print('\n정리하지 못했습니다: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
