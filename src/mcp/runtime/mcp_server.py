"""External Almond MCP launcher for the editable checkout.

Example (Windows, outside Rhino):
  Normally started by the single top-level start button through codex.ps1.

The loopback endpoint is selected ONLY in this Python process's memory.
Models in one directory share DB. Connection metadata and scratch are separate.
The selected endpoint and managed sender are supplied when the server is built.
"""
from __future__ import annotations
from almond_mcp.tool_declarations import public_tool

import argparse
import asyncio
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from pydantic import StrictBool, StrictInt
from almond_mcp.managed_paths import relative_path
from project import (ExclusiveFile, SharedStorageLease, STORAGE_PROTOCOL,
                     process_start_ticks, read_binding, read_json, verify_process, write_json)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True,
                        help="Extra Rhino bridge port, e.g. 5501 through 5510")
    parser.add_argument("--state-db", type=Path,
                        help="Must match the selected model's .almond database")
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--expected-version", help="Require this exact installed almond-mcp version")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535 or args.port == 5000:
        parser.error("Choose an unused port from 1024 to 65535, excluding 5000.")
    return args


def configure_rhino_session_instructions(mcp) -> None:
    """Expose the modeling-guide entry point to this Rhino-bound MCP session."""
    from almond_mcp.modeling_guidance import startup_instructions

    mcp.instructions = startup_instructions()


def main(argv: list[str] | None = None, *, validate_binding=None, configure=None) -> int:
    args = parse_args(argv)
    if args.expected_version is not None:
        installed = version("almond-mcp")
        if installed != args.expected_version:
            raise RuntimeError(f"Package version mismatch: expected {args.expected_version}, got {installed}.")
    binding, locations = read_binding(args.session, args.token)
    if binding.get('storage_protocol') != STORAGE_PROTOCOL:
        raise RuntimeError('This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.')
    verify_process(binding)
    if binding['port'] != args.port:
        raise RuntimeError('Port and selected project disagree.')
    db = Path(locations['state_db'])
    if args.state_db is not None and args.state_db.resolve() != db:
        raise RuntimeError('Do not connect this model to another project database.')
    try:
        with SharedStorageLease(locations['storage']), ExclusiveFile(Path(locations['session_dir']) / 'mcp.lock'):
            current, _ = read_binding(args.session, args.token)
            if current != binding:
                raise RuntimeError('Connection changed while the worker was starting.')
            if validate_binding is not None:
                validate_binding(args, binding, locations)
            worker_path = Path(locations['session_dir']) / 'worker.json'
            worker = dict(schema='almond-worker', storage_protocol=STORAGE_PROTOCOL, token=args.token,
                          pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
            write_json(worker_path, worker)
            try:
                return serve(args, binding, locations, db, configure=configure)
            finally:
                worker["closed"] = True
                write_json(worker_path, worker)
    finally:
        from shared_store import StoreGate
        from storage_cleanup import cleanup_retired_sessions
        with StoreGate(locations["storage"]):
            cleanup_retired_sessions(Path(locations["storage"]))


async def configure_project_context(mcp, args, binding, locations, *, sender=None, runtime=None):
    """Register tools that use the current connection's workspace."""
    from almond_mcp.features.context.project_info import query_project_info
    from almond_mcp.features.context.project_file_catalog import save_project_file

    def verify_current_binding():
        current, _ = read_binding(args.session, args.token)
        if current != binding:
            raise RuntimeError('Connection changed. Exit Codex and reconnect with almond.')
        verify_process(current)

    def project_file_store():
        verify_current_binding()
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return runtime.workspace.store

    @public_tool(mcp, wrapped=False)
    def project_info(sections: list[str] | None = None, include_ids: StrictBool = False,
                     files_limit: StrictInt = 50, files_offset: StrictInt = 0) -> dict:
        """연결된 Rhino 문서와 프로젝트 작업 정보 조회.

        sections에서 필요한 항목을 선택한다. locations·runtime만 요청하면 Rhino 문서를 직접 관찰하지 않는다. named_views와 layouts는 각각 최대 128개이며 include_ids와 관계없이 ID를 포함한다.

        project.worksession_files는 활성 문서를 제외한 현재 Worksession 첨부 파일이다. 이 목록과 DB 등록 목록인 project.files는 별개다. Worksession 첨부·해제로 DB 등록은 바뀌지 않는다. 파일 등록과 설명 갱신은 context_05-upsert_project_file tool을 사용한다. Phase와 Scene에는 등록 파일명을 지정한다.

        후속 호출에 쓸 Plan·Step ID가 필요하면 include_ids=true. 프로젝트 내부 경로는 project_root를 기준으로 읽는다.

        Args:
            sections: project, document, named_views, layouts, layer_tree, locations, runtime. 생략 시 runtime을 제외한 전체.
            files_limit: 등록 파일 페이지 크기. 정수 1..500.
            files_offset: 등록 파일 페이지의 시작 위치. 0 이상의 정수.
        """
        return query_project_info(sections, include_ids, files_limit, files_offset,
                                  verify_binding=verify_current_binding, binding=binding,
                                  locations=locations, sender=sender, runtime=runtime)

    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def upsert_project_file(file_name: str, description: str | None = None) -> dict:
        """프로젝트 파일 카탈로그에 모델 파일을 등록하거나 설명을 갱신. 파일명 비교는 Windows 기준이며 수정 시 기존 표기를 유지한다. Rhino 문서 열기나 Worksession 첨부는 별도 작업이다.

        등록 목록은 context_04-get_project_info tool의 project.files에서 조회한다. Phase와 Scene에는 목록에 있는 파일명을 사용한다.

        Args:
            file_name: 폴더를 뺀 모델 파일명. 프로젝트 안에서 고유해야 한다.
            description: 생략하거나 null이면 기존 설명 유지. 빈 문자열로 삭제.
        """
        return save_project_file(project_file_store, file_name, description)

    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': True, 'destructiveHint': False})
    def get_rhino_execution(request_id: str = "", include_result: StrictBool = True,
                            include_stdout: StrictBool = False, result_fields: list[str] | None = None,
                            offset: StrictInt = 0, limit: StrictInt = 100, include_ids: StrictBool = True,
                            include_diagnostics: StrictBool = False) -> dict:
        """이전 RhinoCode 실행의 상태와 보관된 결과·로그 조회. 조회는 실행 기록만 읽으며, 연결이 끝난 뒤에도 기록이 남아 있으면 조회할 수 있다. 배열이나 문자열 결과는 페이지로 조회하고 로그는 별도의 바이트 오프셋을 사용한다.

        Args:
            request_id: 생략하면 현재 연결의 최근 실행 조회. beyond에서 지정한 ID로 최초 실행 연결을 찾으며, 시간 초과 후에는 같은 ID를 지정
            include_stdout: stdout·stderr와 CLI 로그 포함
            result_fields: 객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키
            offset: 결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위
            limit: 결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용
        """
        if runtime is None:
            raise RuntimeError("Managed RhinoCode execution is unavailable in this server.")
        if type(include_diagnostics) is not bool:
            raise ValueError("include_diagnostics must be a boolean.")
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("offset must be nonnegative and limit must be 1-1000 rows.")
        if result_fields is not None and (not isinstance(result_fields, list)
                or any(not isinstance(field, str) or not field for field in result_fields)):
            raise ValueError("result_fields must contain nonempty top-level result keys.")
        from rhinocode import execution_output
        result = runtime.get_rhino_execution(request_id, offset, limit, include_result, include_stdout, result_fields, include_ids)
        return execution_output(result, include_diagnostics=include_diagnostics)

    @public_tool(mcp, wrapped=False)
    def set_working_plan(plan_id: str, step_id: str = "", artifact_name: str = "", loop_no: StrictInt | None = None) -> dict:
        """현재 연결의 산출물 작업 대상으로 Plan과 선택적인 Step 지정. 작업 실행과 Plan·Step 상태 변경은 별도.

        최초 선택에서 산출물 경로를 정하면 리비전이 증가할 수 있음. 이후 같은 경로 재사용. `artifact_dir`은 Loop 시작 전 Plan 루트, 시작 후 현재 회차 폴더.

        Args:
            plan_id: plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
            step_id: 생략하면 Plan만 선택.
            artifact_name: 최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
            loop_no: 생략·`null`은 현재 회차. 이전 회차 또는 존재하지 않는 회차는 선택 불가.
        """
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.select(plan_id, step_id, artifact_name, loop_no)}

    @public_tool(mcp, wrapped=False)
    def execute_looping(plan_id: str, resume: StrictBool = False, feedback: str = "", artifact_name: str = "") -> dict:
        """Plan의 새 작업 회차 시작 또는 최신 회차 재개. Step 실행은 에이전트가 직접 수행.

        새 회차의 Step은 `pending`에서 시작하며 이전 회차 기록은 `previous_loop`에서 확인. 실행된 회차가 있어야 `resume=true`로 재개 가능.

        다음 회차를 시작하기 전, 현재 Plan Goal을 사용자의 피드백 및 작업방향에 맞게 align하여 수정하고, 다음 회차에 필요하지 않음이 분명한 라이노 객체, layout, namedview, layer등을 삭제한다.

        Args:
            plan_id: plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.
            resume: `true`면 최신 회차 재개, `false`면 새 회차 시작.
            feedback: 재개 시 생략하거나 비우면 이전 피드백 유지.
            artifact_name: 최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.
        """
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.execute_looping(plan_id, resume, feedback, artifact_name)}

    @public_tool(mcp, wrapped=False)
    def rename_artifact_folder(name: str, plan_id: str = "") -> dict:
        """Plan 산출물 폴더 이름 변경 및 저장된 Plan·Step 경로 참조 갱신. 먼저 plan_10-set_working tool로 산출물 폴더를 지정.

        Loop를 이미 실행했거나 다른 Plan의 과거 회차가 참조하는 폴더는 변경 불가. 같은 이름은 변경 없이 성공. 대상이 이미 존재하거나 다른 Plan 소유이면 실패. 실제 변경 시 새 리비전을 저장하고 이전 리비전은 보존.

        Args:
            name: 경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.
            plan_id: 생략하거나 비우면 현재 선택된 Plan 사용.
        """
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.rename(name, plan_id)}

    @public_tool(mcp, wrapped=False)
    def execute_project_python(code: str, timeout_seconds: StrictInt = 60) -> dict:
        """연결된 Rhino 문서에서 Python 3 코드로 형상을 편집하거나 산출물을 생성. 선택한 Plan·Loop 산출물 폴더가 작업 디렉터리. 쓰기 가능한 공간을 plan_10-set_working tool으로 선택하거나 기존 선택을 재사용한다.

        스크립트 실행만 기록할 때는 출력 또는 반환값에 executed를 사용한다. 작업 목적의 달성 여부는 실제 변경과 산출물로 확인하고, 문서 저장 여부는 별도로 확인한다. 시간 초과 뒤에도 실행이 이어지거나 오류 시 부분 변경이 남을 수 있다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.

        Args:
            code: 동기식 코드. doc과 scriptcontext.doc은 연결된 문서. JSON 호환 반환값은 result에 할당하고 상대 경로는 선택한 산출물 폴더 기준
            timeout_seconds: 완료 근거 대기 한도 1~600초. beyond는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.
        """
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be nonempty Python source.")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be 1-600.")
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        directory = runtime.workspace.artifact_path(runtime.current_workspace())
        # Same process/document fence and late-result recovery as Rhino scripts.
        # Rhino runs asynchronously after CLI acknowledgement, so this tool must
        # never kill a Python child or remove its cwd when waiting expires.
        result = runtime.execute_rhinocode(code, "python", timeout_seconds,
                                          working_directory=str(directory))
        result["artifact_dir"] = relative_path(str(directory))
        return result


def managed_exchange_reports(runtime):
    from almond_mcp.features.exchange.tools import ExchangeReports
    from storage_cleanup import plain_descendant

    batch = runtime.scope.get()
    if batch is None or batch.sealed:
        raise RuntimeError("No active operation for Almond asset helper reports.")
    # send() creates this directory only after admitting the capability request.
    # The report helper may use the owned directory, but cannot create it.
    directory = Path(runtime.locations["call_root"]) / batch.operation_id
    return ExchangeReports(plain_descendant(directory, Path(runtime.locations["temp"])), managed=True)


def serve(args, binding, locations, db, *, configure=None):
    from almond_mcp.bridge_transport import BridgeTransport
    from almond_mcp.startup import create_server
    from library_paths import bound_library_dirs
    from shared_store import ProjectRuntime, StoreGate
    from storage_cleanup import migrate_database, cleanup_retired_sessions
    from workspace import Workspace

    # These worker-process values are used by managed path helpers and scripts.
    # The store and transport below receive their configuration explicitly.
    os.chdir(locations['project_dir'])
    os.environ["ALMOND_PROJECT_ROOT"] = locations["project_dir"]
    os.environ["ALMOND_MODEL_PATH"] = locations["model_path"]

    transport = BridgeTransport("127.0.0.1", args.port)
    runtime = ProjectRuntime(args, binding, locations)

    def bound_sender(payload_bytes, *positional, **keywords):
        return runtime.send(transport, payload_bytes, *positional, **keywords)

    # Serialize SQLite initialization, reindexing and closing checkpoints
    # against other workers sharing this project.
    with StoreGate(locations['storage']):
        migrate_database(locations, args.token)
        cleanup_retired_sessions(Path(locations['storage']), exclude_token=args.token)
        library_dirs = bound_library_dirs()
        application = create_server(
            state_db=db,
            library_dirs=library_dirs,
            send=bound_sender,
            execute_source=runtime.execute_rhinocode,
            exchange_reports=lambda: managed_exchange_reports(runtime),
        )
    worker_path = Path(locations['session_dir']) / 'worker.json'
    worker = read_json(worker_path)
    worker['library_dirs'] = library_dirs
    write_json(worker_path, worker)

    runtime.workspace = Workspace(locations, application.features.retrieval_store)
    mcp = application.mcp
    mcp.add_middleware(runtime)

    async def prepare():
        await configure_project_context(mcp, args, binding, locations, sender=bound_sender, runtime=runtime)
        if configure is not None:
            await configure(mcp, args, binding, locations, runtime)

    asyncio.run(prepare())
    configure_rhino_session_instructions(mcp)
    print("[AlmondParallel] Rhino target: {0}:{1}".format(
        transport.host, transport.port), file=sys.stderr)
    print("[AlmondParallel] Scene DB: {0}".format(db), file=sys.stderr)
    # Use the same MCP entry point as Almond's own cmd_serve.
    # stdout is reserved for the MCP protocol.
    print("[AlmondParallel] This is NOT a read-only service. Almond C# queries can create default layers.", file=sys.stderr)
    mcp.run()
    return 0


if __name__ == "__main__":
    try:
        from desktop_runtime import ensure_desktop_runtime
        ensure_desktop_runtime()
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print("[AlmondParallel] Startup/runtime error: {0}".format(exc), file=sys.stderr)
        raise SystemExit(1)
