"""Register Grasshopper tools against the owning server's current services."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.grasshopper.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
from pydantic import StrictBool
import json
import os
import socket

from almond_mcp.features.grasshopper.ghx_parser import GHParser


_CAPSULE_GEOMETRY_TYPES = {
    "point", "point[]",
    "curve", "curve[]",
    "mesh", "mesh[]",
    "brep", "brep[]",
}


def _capsule_input_error(port: dict, value) -> str | None:
    """Validate one capsule input value against its manifest port declaration.

    Returns a human-readable error string, or None when the value satisfies the
    contract. Geometry ports must arrive as {"guids": [...]} references to
    objects already in the Rhino document; primitive ports must match their
    declared JSON type exactly.
    """
    name = port.get("name", "?")
    port_type = str(port.get("type", ""))
    units = port.get("units", "")
    units_note = f" (units: {units})" if units else ""

    def _is_number(item) -> bool:
        return (
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and abs(item) != float("inf")
            and item == item
        )

    if port_type in _CAPSULE_GEOMETRY_TYPES:
        if (
            not isinstance(value, dict)
            or set(value.keys()) != {"guids"}
            or not isinstance(value.get("guids"), list)
            or not value["guids"]
            or not all(isinstance(guid, str) and guid.strip() for guid in value["guids"])
        ):
            return (
                f'{name} ({port_type}) must be a GUID reference of the exact form '
                '{"guids": ["<rhino-object-guid>", ...]} with at least one GUID string, '
                "referencing objects already in the Rhino document."
            )
        return None

    if port_type == "number":
        if not _is_number(value):
            return f"{name} must be a finite number{units_note}."
    elif port_type == "integer":
        if not (isinstance(value, int) and not isinstance(value, bool)):
            return f"{name} must be an integer{units_note}."
    elif port_type == "bool":
        if not isinstance(value, bool):
            return f"{name} must be a boolean."
    elif port_type == "string":
        if not isinstance(value, str):
            return f"{name} must be a string."
    elif port_type == "number[]":
        if not (isinstance(value, list) and all(_is_number(item) for item in value)):
            return f"{name} must be a flat list of finite numbers{units_note}."
    elif port_type == "integer[]":
        if not (
            isinstance(value, list)
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
        ):
            return f"{name} must be a flat list of integers{units_note}."
    elif port_type == "string[]":
        if not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            return f"{name} must be a flat list of strings."
    else:
        return (
            '{0} declares unsupported type {1!r} in its manifest; fix the capsule sidecar before running it.'.format(name, port_type)
        )
    return None


def register(mcp, context):
    """Register the existing Grasshopper MCP surface without import-time effects."""

    @public_tool(mcp, wrapped=True)
    @query_output
    def list_library(include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """로컬 Grasshopper 라이브러리에서 색인된 로직 이름을 조회합니다. logic_names의 이름으로 grasshopper_01-get_logic tool에서 상세 내용을 조회할 수 있습니다.

        Args:
            include_ids: true: logic_names와 같은 값의 logic_ids 포함.
            field_groups: paths·all: 라이브러리 경로 포함. ports·definition·source·audit은 목록에 상세를 추가하지 않음.
        """
        validate_field_groups(field_groups, GROUPS)
        return json.dumps(project({
            "library_dir": context.LIBRARY_DIR,
            "total_entries": len(context.indexer.index),
            "logic_names": context.indexer.list_ids(),
            "logic_ids": context.indexer.list_ids(),
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def get_logic_by_id(logic_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """색인된 Grasshopper 로직 파일에서 추출한 물리 관련 항목·설명과 제공된 메타데이터를 조회합니다. JSON만 있는 항목은 메타데이터를 반환합니다. 추출 정보는 완전한 구성·연결 관계나 실행 가능성을 보장하지 않습니다.

        Args:
            logic_id: 확장자를 뺀 라이브러리 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.
            include_ids: true: 다른 식별자 포함. 입력 logic_id는 반복되지 않음.
            field_groups: ports, definition, source, paths, audit, all. 제공된 필드에만 적용.
        """
        validate_field_groups(field_groups, GROUPS)
        query_id = logic_id.lower()
        file_map = context.indexer.index.get(query_id)

        if not file_map:
            return json.dumps(project({"error": "Logic '{0}' not found. Use grasshopper_03-list_library tool() to see available IDs.".format(logic_id)}, field_groups))

        # Prioritize GHX > GH > JSON-only
        target_file = file_map.get('ghx') or file_map.get('gh')
        target_json = file_map.get('json')

        # If only a JSON sidecar exists, return it directly
        if target_json and not target_file:
            try:
                with open(target_json, 'r') as f:
                    data = json.load(f)
                return json.dumps(project({"logic_id": logic_id, "source": target_json, "metadata": data}, field_groups))
            except Exception as e:
                return json.dumps(project({"error": f"Failed to read JSON sidecar: {e}"}, field_groups))

        # Parse via the binary string extractor
        try:
            parser = GHParser(target_file, capsule_dir=context.CAPSULE_LIBRARY_DIR)
            physics_context = parser.parse()
            return json.dumps(project(json.loads(physics_context.model_dump_json()), field_groups))
        except Exception as e:
            return json.dumps(project({"error": f"Failed to parse '{target_file}': {str(e)}"}, field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def list_capsules(capability: str = "", audited_only: bool = False, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """등록된 Grasshopper 캡슐의 기능과 감사 상태를 조회합니다. 포트와 ID를 확인해 grasshopper_04-run_definition tool의 입력을 준비할 수 있습니다. 감사 상태는 정의 파일의 존재나 실행 성공을 보장하지 않습니다.

        Args:
            capability: 기능 필터: analyze, generate, form_find, aggregate. 대소문자 무시.
            audited_only: true: audited로 등록된 캡슐만.
            include_ids: true: capsule_id 포함. all과 별도 지정.
            field_groups: ports, definition, source, paths, audit, all. 생략·빈 배열: 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        page = context.retrieval_store.search_capsules(
            capability=capability,
            audited_only=audited_only,
            limit=50,
        )
        return json.dumps(project({
            "capsule_library_dir": context.CAPSULE_LIBRARY_DIR,
            **page,
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    def run_gh_definition(
        capsule_id: str,
        inputs: dict,
        seed: int | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        """실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다. 모든 출력 포트를 먼저 확인하고 형상 베이크는 하나의 전용 Undo record로 처리합니다. mutation_state는 none·completed·rolled_back·unknown이며 requires_reconciliation=true이면 baked_guids와 현재 문서를 확인하기 전 자동 재시도하지 않습니다.

        Args:
            capsule_id: grasshopper_02-list_capsules tool에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
            inputs: ALMOND_IN_ 포트 이름과 값의 객체입니다. grasshopper_02-list_capsules tool(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다.
            seed: 확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다.
            timeout_s: 솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다.
        """
        manifest = context.retrieval_store.get_capsule(capsule_id)
        if not manifest:
            listing = context.retrieval_store.search_capsules(limit=50)
            return json.dumps({
                "status": "error",
                "message": 'Unknown capsule_id: {0}. Use grasshopper_02-list_capsules tool() to discover capsules.'.format(capsule_id),
                "available_capsules": [
                    capsule["capsule_id"] for capsule in listing["capsules"]
                ],
            })

        if not manifest.get("audited"):
            return json.dumps(error_payload(f"Capsule '{capsule_id}' is not audited: its definition has no verified "
                    "ALMOND_IN_*/ALMOND_OUT_* harness params, so grasshopper_04-run_definition tool refuses to "
                    "execute it. It remains available as retrieval context (grasshopper_01-get_logic tool). "
                    "See asset/capsules/AUTHORING.md for how to harness and audit the definition."))

        if not isinstance(inputs, dict):
            return json.dumps(error_payload("inputs must be an object keyed by ALMOND_IN_* port names."))

        ports = {
            port["name"]: port
            for port in manifest.get("inputs", [])
            if isinstance(port, dict) and isinstance(port.get("name"), str)
        }
        valid_names = sorted(ports)

        unknown = sorted(set(inputs) - set(ports))
        if unknown:
            return json.dumps({
                "status": "error",
                "message": f"Unknown input name(s) for '{capsule_id}': {', '.join(unknown)}.",
                "valid_inputs": valid_names,
            })

        missing = sorted(
            name for name, port in ports.items()
            if port.get("required", True) and name not in inputs
        )
        if missing:
            return json.dumps({
                "status": "error",
                "message": f"Missing required input(s) for '{capsule_id}': {', '.join(missing)}.",
                "valid_inputs": valid_names,
            })

        problems = []
        for name in sorted(inputs):
            problem = _capsule_input_error(ports[name], inputs[name])
            if problem:
                problems.append(problem)
        if problems:
            return json.dumps({
                "status": "error",
                "message": "Input validation failed: " + " ".join(problems),
                "valid_inputs": valid_names,
            })

        if not (isinstance(timeout_s, (int, float)) and not isinstance(timeout_s, bool)
                and timeout_s == timeout_s and 0 < timeout_s <= 600):
            return json.dumps(error_payload("timeout_s must be a number between 0 (exclusive) and 600 seconds."))

        manifest_path = manifest.get("_manifest_path") or os.path.join(
            context.CAPSULE_LIBRARY_DIR, f"{capsule_id}.capsule.json"
        )

        payload = json.dumps({
            "type": "run_definition",
            "capsule_id": capsule_id,
            "manifest_path": manifest_path,
            "inputs": inputs,
            "seed": seed,
            "timeout_s": timeout_s,
        }).encode("utf-8")

        try:
            # Socket budget exceeds the solver budget so the bridge can report its
            # own timeout as structured JSON instead of a dead connection.
            return context._send_and_receive(payload, timeout=float(timeout_s) + 15.0)
        except socket.timeout:
            return json.dumps(error_payload(f"Capsule '{capsule_id}' timed out (>{timeout_s}s solver budget)."))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:
            return json.dumps(error_payload(f"Bridge error: {e}"))

    return {
        "list_library": list_library,
        "get_logic_by_id": get_logic_by_id,
        "list_capsules": list_capsules,
        "run_gh_definition": run_gh_definition,
        "_capsule_input_error": _capsule_input_error,
    }
