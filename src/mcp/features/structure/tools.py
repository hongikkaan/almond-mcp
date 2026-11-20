"""MCP tools and bridge helpers for structural validation and overlays."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.structure.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
from pydantic import StrictBool
import json
import math
import socket
from pathlib import Path

from almond_mcp import paths
from . import asset_loads, design_codes, native_structure, structure_study

KARAMBA_ONLY_TYPES = ("shell", "gridshell", "membrane")


def register(mcp, context):
    """Register structural tools with overlay state for one application."""
    view_engine = None
    native_report = {}

    @public_tool(mcp, wrapped=True)
    def validate_structure(
        guids: list[str],
        structure_type: str = "beam",
        load_kn: float = 10.0,
        material: str = "Steel",
        engine: str = "auto",
        fixed_supports: bool = True,
        self_weight: bool = True,
        span_m: float | None = None,
        asset_loads: bool = False,
        floor_load_kn_m2: float = 0.0,
        floor_dead_kn_m2: float = 0.0,
        design_basis: str = "en1990",
        uls_combination: str | None = None,
        connections: str = "rigid",
        stability: str = "auto",
        design_code: str = "eurocode",
        detail: bool = False,
        fabrication: str = "cold_formed",
    ) -> str:
        """Rhino 구조 형상을 해석하고 설계기준에 따라 검토합니다.

        완료된 해석은 요청 옵션과 실제 적용 엔진·입력·계산 결과를 이력에 보관합니다. native 이력은 내보낸 모델과 적용 하중 입력을 포함합니다. 이전 이력에 저장되지 않은 옵션은 현재 기본값으로 추정하지 않고 알 수 없음으로 표시합니다.

        Args:
            guids: 해석 범위에 포함되는 현재 Rhino 객체 GUID 문자열입니다.
            structure_type: 사용할 해석 템플릿입니다. 선택지: "beam"은 단순 보의 휨/처짐, "truss"는 축력/좌굴 해석, "shell"은 셸 응력/변위, "frame"은 프레임 모멘트/전단 해석, "canopy"는 캔틸레버 캐노피, "gridshell"은 대변형 그리드셸, "membrane"은 막 구조 형상 탐색, "highrise"는 고층 구조 시스템입니다.
            load_kn: 전체 부과하중(kN)입니다. native에서는 자유 절점에 하향(-Z) 균등 분배합니다. 바닥·자산 하중과 중복 계산되지 않게 산정하며 필요한 경우 0으로 입력합니다.
            material: 재료 유형: "Steel", "S355", "Concrete", "Wood", "Aluminium". 기본값은 "Steel"입니다.
            engine: auto, native, karamba 중 선택합니다. auto는 선형 프레임에 native를, 그 외에는 Karamba를 사용합니다. karamba는 사용 가능한 api, template, rule_based 순으로 시도합니다. 결과의 analysis_method와 warnings를 확인합니다.
            fixed_supports: True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
            self_weight: 부재 자중을 포함합니다.
            span_m: 부재가 모든 절점에서 분할됐을 때 L/250 한계에 사용할 구조 경간(미터)입니다. 예를 들어 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우에 사용합니다. 네이티브 엔진 전용입니다.
            asset_loads: true이면 배치된 라이브러리 자산의 자중·내용물·재실자 하중을 추가합니다. 네이티브 엔진에서 사용합니다. 다른 하중 입력에 이미 포함한 무게를 중복 적용하지 않습니다.
            floor_load_kn_m2: 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
            floor_dead_kn_m2: 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
            design_basis: "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
            uls_combination: "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
            connections: "rigid"(기본값)는 모든 접합부가 모멘트를 전달합니다. "simple"은 보를 핀 접합(강축 휨 해제)으로, 가새를 양축 핀 접합으로 처리하되, 다른 부재가 같은 선상으로 계속 이어지는 지점이 아니라 해당 부재가 끝나는 지점에 적용하며 기둥은 연속으로 유지합니다. 일반적인 볼트 접합 강구조와 목구조 프레임은 "simple"에 더 가깝습니다. 강접합은 보 처짐을 실제보다 유리하게 보이게 할 수 있습니다. 곡선의 사용자 텍스트 almond:release = "pinned" | "pinned_start" | "pinned_end" | "rigid"는 두 모드보다 우선합니다. 네이티브 엔진에 적용됩니다.
            stability: "auto"(기본값)는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 +/-x 및 +/-y 방향의 횡변위 초기 불완전성 phi = 1/200 x alpha_h x alpha_m(5.3.2)을 적용합니다. alpha_cr < 10이면 2차(P-Delta) ULS 해석을 실행하며, alpha_cr <= 1이면 불안정으로 실패 처리합니다. "off"는 초기 불완전성 없는 1차 해석입니다.
            design_code: 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
            detail: true이면 네이티브 해석의 부재별 단면력·사용률·처짐과 지점 반력을 포함합니다.
            fabrication: 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
        """
        engine = (engine or "auto").lower()
        if engine not in ("auto", "native", "karamba"):
            return json.dumps(error_payload("engine must be 'auto', 'native' or 'karamba'."))
        request = {
            "type": "validate",
            "guids": guids,
            "structure_type": structure_type,
            "load_kn": load_kn,
            "material": material,
        }
        if not fixed_supports:
            request["fixed_rotations"] = False
        if not self_weight:
            request["self_weight"] = False

        requested = dict(guids=list(guids), structure_type=structure_type, load_kn=load_kn,
            material=material, engine=engine, fixed_supports=fixed_supports, self_weight=self_weight,
            span_m=span_m, asset_loads=asset_loads, floor_load_kn_m2=floor_load_kn_m2,
            floor_dead_kn_m2=floor_dead_kn_m2, design_basis=design_basis, uls_combination=uls_combination,
            connections=connections, stability=stability, design_code=design_code, detail=detail,
            fabrication=fabrication)

        result, note = None, None
        native_inputs = {}
        spec = None
        floor, err = _floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
        if err:
            return json.dumps(error_payload(err))
        try:
            native_structure.combinations(design_basis, uls_combination, design_code)
            if (connections or "rigid").lower() not in native_structure.CONNECTIONS:
                raise ValueError("connections must be 'rigid' or 'simple'.")
            if (stability or "auto").lower() not in ("auto", "off"):
                raise ValueError("stability must be 'auto' or 'off'.")
        except ValueError as e:
            return json.dumps(error_payload(str(e)))
        if asset_loads:
            if engine == "karamba":
                return json.dumps(error_payload("asset_loads needs the native engine (engine='auto' or 'native')."))
            spec, err = _asset_load_spec()
            if err:
                return json.dumps(error_payload(err))
        if engine == "native" or (engine == "auto" and structure_type.lower() not in KARAMBA_ONLY_TYPES):
            result, note = _native_validation(guids, structure_type, load_kn, material, fixed_supports,
                                              self_weight, span_m, required=engine == "native", asset_spec=spec,
                                              floor_spec=floor, design=(design_basis, uls_combination, design_code),
                                              connections=connections, stability=stability, detail=detail,
                                              fabrication=fabrication, history=native_inputs)
            if isinstance(result, str):          # hard error (explicit native request, or no bridge)
                return result
        if result is None:
            try:
                response = context._send_and_receive(json.dumps(request).encode('utf-8'), timeout=60.0)
            except socket.timeout:
                return json.dumps(error_payload("Structural validation timed out (>60s)."))
            except ConnectionRefusedError:
                return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
            except Exception as e:
                return json.dumps(error_payload(f"Bridge error: {e}"))
            try:
                result = json.loads(response)
            except Exception:
                return response
            if note and isinstance(result, dict):
                result.setdefault("warnings", []).append(note)
            if (spec or floor) and isinstance(result, dict):
                result.setdefault("warnings", []).append(
                    "Asset and floor loads were not applied: the Karamba route does not take them.")
            if note and isinstance(result, dict) and (design_basis or "").lower() == "en1990":   # fell back from native
                result.setdefault("warnings", []).append(
                    "The Karamba route checks unfactored loads; EN 1990 combinations apply to the native engine only.")

        # Attach the constructibility cross-check (curated construction-system
        # span/depth guidance), then persist the run in the state DB so
        # export_structural_report can render an auditable history. Neither step
        # may ever break validation itself.
        try:
            if isinstance(result, dict) and result.get("status") in ("pass", "fail", "indicative"):
                span = None
                results_block = result.get("results")
                if isinstance(results_block, dict):
                    span = results_block.get("span_m")
                try:
                    check = context.construction_library.assess_span(structure_type, material, span)
                    result["construction_check"] = check
                    if check.get("warnings"):
                        result.setdefault("warnings", [])
                        result["warnings"].extend(check["warnings"])
                except Exception:
                    pass
                from almond_mcp import __version__
                method = (results_block or {}).get("analysis_method", "unknown")
                if method == "native":
                    inputs = dict(requested, validation_stations=11,
                        uls_combination=native_inputs["uls_expression"],
                        design_code=native_inputs["design_profile"],
                        deflection_limit_ratio=native_inputs["design_profile"]["values"]["deflection_limit_ratio"],
                        fabrication=native_structure._fabrication(fabrication),
                        connections=(connections or "rigid").lower(), stability=(stability or "auto").lower(),
                        asset_load_report=result.get("asset_loads"), floor_load_report=result.get("floor_loads"),
                        **native_inputs)
                else:
                    # Only the bridge request was applied. Native-only requested options
                    # must not be recorded as if Karamba/template/rule-based used them.
                    inputs = dict(request, fixed_rotations=fixed_supports, self_weight=self_weight)
                analysis = dict(engine=method, version=__version__, inputs=inputs)
                context.retrieval_store.record_validation_run(requested, result, guids, analysis=analysis)
        except Exception:
            pass
        return json.dumps(result)


    def _asset_load_spec():
        """Placements + load table + catalogue facts for asset loads: (spec, None) or (None, error)."""
        try:
            table = asset_loads.LoadTable.from_library(context.GENERATED_LIBRARY_DIR)
        except Exception as e:
            return None, f"The asset load table is unavailable ({e})."
        try:
            reply = json.loads(context._send_and_receive(json.dumps({"type": "asset_placements"}).encode('utf-8'), timeout=60.0))
        except ConnectionRefusedError:
            return None, "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"
        except Exception as e:
            return None, f"Could not read asset placements from Rhino ({e})."
        if not isinstance(reply, dict) or reply.get("status") != "ok":
            return None, "This bridge version cannot export asset placements (update almondbridge)."
        placements = reply.get("placements") or []
        catalogue = structure_study.asset_catalogue(placements, context.generated_asset_indexer.get)
        return {"placements": placements, "table": table, "catalogue": catalogue}, None


    def _floor_spec(imposed, dead, engine):
        """(spec | None, error | None) for floor area loads."""
        imposed, dead = float(imposed or 0.0), float(dead or 0.0)
        if imposed < 0 or dead < 0 or not (math.isfinite(imposed) and math.isfinite(dead)):
            return None, "Floor loads must be finite and non-negative (kN/m2)."
        if not imposed and not dead:
            return None, None
        if engine == "karamba":
            return None, "Floor loads need the native engine (engine='auto' or 'native')."
        return {"imposed": imposed, "dead": dead}, None


    def _native_validation(guids, structure_type, load_kn, material, fixed_supports, self_weight, span_m, required,
                           asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"), connections="rigid",
                           stability="auto", detail=False, fabrication="cold_formed", history=None):
        """Native frame check on the bridge's exported line model.

        Returns (result_dict, None) when it ran, (None, note) to fall back to the Karamba
        route with a note, or (json_error_string, None) when it must stop (explicit native
        request that cannot run, or no bridge)."""
        def unavailable(msg):
            if required:
                return json.dumps(error_payload(msg)), None
            return None, msg + " Fell back to the Karamba route."
        try:
            reply = json.loads(context._send_and_receive(
                json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
        except socket.timeout:
            return unavailable("Exporting the structural model timed out.")
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?")), None
        except Exception as e:
            return unavailable(f"The bridge could not export a structural model ({e}).")
        if not isinstance(reply, dict) or reply.get("status") != "ok" or "members" not in reply:
            return unavailable("This bridge version cannot export structural models (update almondbridge).")
        if reply.get("shells"):
            return unavailable(f"The model contains {reply['shells']} shell element(s), which the native frame solver does not analyse.")
        if not reply["members"]:
            return unavailable("No line members found for the given GUIDs.")
        if history is not None:
            history.update(model=reply, floor_load_spec=floor_spec, asset_load_spec=None)
            if asset_spec is not None:
                catalogue = asset_spec.get("catalogue") or {}
                table = asset_spec["table"]
                history["asset_load_spec"] = dict(placements=asset_spec["placements"], catalogue=catalogue,
                    basis=table.basis, loads={p["asset_id"]: table.lookup(p["asset_id"],
                        (catalogue.get(p["asset_id"]) or {}).get("category", "")) for p in asset_spec["placements"]})
        try:
            code = native_structure.design_profile(design[0], design[2])
            if history is not None:
                history.update(design_profile=code.summary(),
                               uls_expression=code.uls(design[1] or None)[0] if code.factored else "unfactored")
            result = native_structure.validate(reply, structure_type.lower(), load_kn, material,
                                               fixed_supports=fixed_supports, self_weight=self_weight, span_m=span_m,
                                               asset_loads=asset_spec, floor_loads=floor_spec,
                                               design_basis=design[0], uls=design[1], connections=connections,
                                               stability=stability, design_code=code, detail=detail,
                                               fabrication=fabrication)
        except ValueError as e:
            return json.dumps(error_payload(str(e))), None
        return result, None


    @public_tool(mcp, wrapped=True)
    @query_output
    def list_design_codes(include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """구조 해석에 사용할 설계기준 프로필을 조회합니다.

        Args:
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
        """
        validate_field_groups(field_groups, GROUPS)
        return json.dumps(project(design_codes.listing(), field_groups))


    @public_tool(mcp, wrapped=True)
    def visualize_structure(
        guids: list[str] | None = None,
        load_kn: float = 10.0,
        material: str = "Steel",
        beam_diameter_mm: float | None = None,
        beam_wall_mm: float | None = None,
        self_weight: bool = True,
        fixed_supports: bool = True,
        deflection_limit_ratio: float | None = None,
        span_m: float | None = None,
        color_by: str = "displacement",
        scale: float | None = None,
        reveal: float = 1.0,
        reanalyze: bool = True,
        physics: bool = True,
        display_guids: list[str] | None = None,
        title: str = "",
        clear: bool = False,
        engine: str = "auto",
        asset_loads: bool = False,
        floor_load_kn_m2: float = 0.0,
        floor_dead_kn_m2: float = 0.0,
        design_basis: str = "en1990",
        uls_combination: str | None = None,
        connections: str = "rigid",
        stability: str = "auto",
        design_code: str = "eurocode",
        fabrication: str = "cold_formed",
        view: str = "deflection",
    ) -> str:
        """구조 해석 결과를 임시 뷰포트 오버레이로 표시합니다.

        Args:
            guids: 구조 축선의 곡선 GUID와 지점을 표시하는 점 GUID입니다(fixed_supports 참조). 점이 없으면 최하단 절점을 지점으로 사용합니다.
            load_kn: 자유 절점에 하향(-Z)으로 균등 분배할 전체 부과하중(kN)입니다.
            material: "Steel", "S355", "Concrete", "Wood", "Aluminium" 중 하나입니다.
            beam_diameter_mm: 선택 항목인 원형 부재 외경(밀리미터)입니다.
            beam_wall_mm: 선택 항목인 중공 부재의 벽 두께(밀리미터)입니다.
            self_weight: 중력을 포함합니다.
            fixed_supports: True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
            deflection_limit_ratio: 경간/비율 한계입니다. 예를 들어 L/250은 250입니다. 기본값은 설계기준의 한계입니다(Eurocode 프로필: 250).
            span_m: 한계에 사용할 기준 경간(미터)입니다. 기본값은 가장 긴 부재입니다. 부재가 모든 절점에서 분할됐다면 지정합니다. 예: 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우.
            color_by: "displacement" 또는 "utilization"입니다.
            scale: 변형 과장 배율입니다. 생략하면 자동으로 정합니다(경간의 약 6%).
            reveal: 그릴 부재의 비율이며 0..1 범위입니다. 단계별 시공 재생에 사용합니다.
            reanalyze: False이면 마지막 계산을 재사용하고 표시(scale / color_by / reveal / physics / title)만 변경합니다. 애니메이션에 사용할 수 있을 만큼 계산 부담이 작습니다.
            physics: False이면 해석 오버레이 없이 같은 부재를 일반 형상으로 그립니다("physics off"). 전후 비교에 사용합니다.
            display_guids: 이 부재들만 그립니다(예: 단면 보기를 위한 한 줄의 프레임). 해석은 여전히 guids의 모든 부재를 포함합니다.
            title: 범례 제목입니다.
            clear: 오버레이를 제거합니다.
            engine: "auto"(기본값), "native", "karamba" 중 하나입니다. "auto"는 Karamba 없이 Almond 네이티브 프레임 솔버를 사용하되, 선택에 셸이 있거나 브리지가 모델을 내보낼 수 없으면 Karamba를 사용합니다.
            asset_loads: analysis_04-validate_structure tool와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다.
            floor_load_kn_m2: 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
            floor_dead_kn_m2: 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
            design_basis: "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
            uls_combination: "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
            connections: analysis_04-validate_structure tool와 동일한 "rigid" 또는 "simple"입니다. 핀 접합 단부는 작은 원으로 그립니다.
            stability: analysis_04-validate_structure tool와 동일한 "auto" 또는 "off"입니다.
            design_code: 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
            fabrication: 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
            view: "deflection"(기본값) 또는 "buckling"입니다. "buckling"은 처짐 형상 대신 지배 ULS 조합의 첫 번째 좌굴 모드를 alpha_cr과 함께 그립니다(STABLE >= 10, SWAY-SENSITIVE 1-10, UNSTABLE <= 1).
        """
        nonlocal view_engine, native_report
        if not clear and not guids:
            return json.dumps(error_payload("Provide the curve (and support point) GUIDs to analyse."))
        if color_by not in ("displacement", "utilization"):
            return json.dumps(error_payload("color_by must be 'displacement' or 'utilization'."))
        engine = (engine or "auto").lower()
        if engine not in ("auto", "native", "karamba"):
            return json.dumps(error_payload("engine must be 'auto', 'native' or 'karamba'."))
        if deflection_limit_ratio is None:
            try:
                deflection_limit_ratio = native_structure.design_profile(design_basis, design_code).deflection_limit_ratio
            except ValueError as e:
                return json.dumps(error_payload(str(e)))
        request = {
            "type": "structure_view",
            "guids": guids or [],
            "load_kn": load_kn,
            "material": material,
            "self_weight": self_weight,
            "fixed_rotations": fixed_supports,
            "deflection_limit_ratio": deflection_limit_ratio,
            "color_by": color_by,
            "reveal": max(0.0, min(1.0, reveal)),
            "reanalyze": reanalyze,
            "physics": physics,
            "clear": clear,
        }
        if beam_diameter_mm is not None:
            request["beam_diameter_mm"] = beam_diameter_mm
            request["beam_wall_mm"] = beam_wall_mm if beam_wall_mm is not None else beam_diameter_mm / 20.0
        if scale is not None:
            request["scale"] = scale
        if span_m is not None:
            request["span_m"] = span_m
        if display_guids:
            request["display_guids"] = display_guids
        if title:
            request["title"] = title
        note = None
        spec = None
        floor = None
        if not clear and reanalyze:
            floor, err = _floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
            if err:
                return json.dumps(error_payload(err))
            try:
                native_structure.combinations(design_basis, uls_combination, design_code)
                if (connections or "rigid").lower() not in native_structure.CONNECTIONS:
                    raise ValueError("connections must be 'rigid' or 'simple'.")
                if (stability or "auto").lower() not in ("auto", "off"):
                    raise ValueError("stability must be 'auto' or 'off'.")
                if (view or "deflection").lower() not in ("deflection", "buckling"):
                    raise ValueError("view must be 'deflection' or 'buckling'.")
                if (view or "").lower() == "buckling" and engine == "karamba":
                    raise ValueError("view='buckling' needs the native engine.")
            except ValueError as e:
                return json.dumps(error_payload(str(e)))
        if asset_loads and not clear and reanalyze:
            if engine == "karamba":
                return json.dumps(error_payload("asset_loads needs the native engine (engine='auto' or 'native')."))
            spec, err = _asset_load_spec()
            if err:
                return json.dumps(error_payload(err))
        if not clear and not reanalyze and view_engine is not None:
            # An established overlay is display-only regardless of who last
            # replaced it or which engine produced it. HandleDraw errors when
            # it was cleared elsewhere; structure_view would start a new solve.
            draw = {k: v for k, v in request.items() if k not in ("guids", "reanalyze", "clear")}
            draw["type"] = "structure_draw"
            out = _bridge_call(draw, 30.0)
            try:
                parsed = json.loads(out)
                if isinstance(parsed, dict) and parsed.get("status") in ("pass", "fail", "indicative"):
                    overlay_id = parsed.pop("overlay_id", None)
                    cached = native_report
                    # Rhino owns one process-wide overlay; another worker or the
                    # panel may have replaced it since this worker last solved.
                    if overlay_id and overlay_id == cached.get("overlay_id"):
                        _enrich_native_view(parsed, cached["report"])
                    else:
                        native_report = {}
                    _native_verdict(parsed)
                    return json.dumps(parsed)
                native_report = {}
            except (ValueError, TypeError):
                pass
            return out
        if not clear and engine != "karamba":
            reply, note = _native_view(request, guids, required=engine == "native", asset_spec=spec, floor_spec=floor,
                                       design=(design_basis, uls_combination, design_code), connections=connections,
                                       stability=stability, view=view, fabrication=fabrication)
            if reply is not None:
                return reply
        out = _bridge_call(request, 90.0)
        if clear:
            view_engine = None
            native_report = {}
        elif reanalyze:
            view_engine = "api"
            native_report = {}
        try:
            parsed = json.loads(out)
            if isinstance(parsed, dict):
                parsed.pop("overlay_id", None)
                if note:
                    parsed.setdefault("warnings", []).append(note)
                out = json.dumps(parsed)
        except (ValueError, TypeError):
            pass
        return out


    def _bridge_call(message: dict, timeout: float) -> str:
        try:
            return context._send_and_receive(json.dumps(message).encode('utf-8'), timeout=timeout)
        except socket.timeout:
            return json.dumps(error_payload(f"Structure view timed out (>{timeout:.0f}s)."))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:
            return json.dumps(error_payload(f"Bridge error: {e}"))


    def _native_view(request: dict, guids, required: bool, asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"),
                     connections="rigid", stability="auto", view="deflection", fabrication="cold_formed"):
        """Solve natively and draw through the bridge's structure_draw overlay.

        Returns (reply_json, None) when it ran or must stop, (None, note) to fall back to Karamba."""

        nonlocal view_engine, native_report
        def unavailable(msg):
            if required:
                return json.dumps(error_payload(msg)), None
            return None, msg + " Fell back to the Karamba route."
        try:
            model = json.loads(context._send_and_receive(
                json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?")), None
        except Exception as e:
            return unavailable(f"The bridge could not export a structural model ({e}).")
        if not isinstance(model, dict) or model.get("status") != "ok" or "members" not in model:
            return unavailable("This bridge version cannot export structural models (update almondbridge).")
        if model.get("shells"):
            return unavailable(f"The model contains {model['shells']} shell element(s), which the native frame solver does not analyse.")
        if not model["members"]:
            return json.dumps(error_payload("No curve members found for the given GUIDs.")), None
        try:
            result, span = native_structure.view_result(
                model, request["load_kn"], request["material"], fixed_supports=request["fixed_rotations"],
                self_weight=request["self_weight"], diameter_mm=request.get("beam_diameter_mm"),
                wall_mm=request.get("beam_wall_mm"), span_m=request.get("span_m"), asset_loads=asset_spec,
                floor_loads=floor_spec, design_basis=design[0], uls=design[1], connections=connections,
                stability=stability, view=view, design_code=design[2], fabrication=fabrication)
        except native_structure.InstabilityError as e:
            return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                               "stability": e.report, "hint": "view='buckling' draws the buckling mode."}), None
        except native_structure.fs.MechanismError as e:
            return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                               "mechanism_nodes": len(e.nodes)}), None
        except ValueError as e:
            return json.dumps(error_payload(str(e))), None
        draw, reports = structure_study.draw_message(request, result, span)
        report, floor_report, combos = reports["asset_loads"], reports["floor_loads"], reports["combinations"]
        conn_report, stab_report, buckling = reports["connections"], reports["stability"], reports["buckling"]
        code_report = reports["design_code"]
        out = _bridge_call(draw, 60.0)
        try:
            parsed = json.loads(out)
        except Exception:
            return out, None
        if isinstance(parsed, dict) and parsed.get("status") in ("pass", "fail", "indicative"):
            view_engine = "native"
            overlay_id = parsed.pop("overlay_id", None)
            enrichment = {"warnings": result["warnings"]}
            if report is not None:
                enrichment["asset_loads"] = report
            if floor_report is not None:
                enrichment["floor_loads"] = floor_report
            if combos:
                enrichment["combinations"] = combos
            if conn_report:
                enrichment["connections"] = conn_report
            if stab_report:
                enrichment["stability"] = stab_report
            if code_report:
                enrichment["design_code"] = code_report
            enrichment["_indicative"] = bool(reports.get("indicative"))
            if buckling:
                enrichment["buckling"] = buckling
            enrichment["nodes"] = len({tuple(p) for e in result["elements"] for p in (e["start_m"], e["end_m"])})
            native_report = {"overlay_id": overlay_id, "report": enrichment} if overlay_id else {}
            _enrich_native_view(parsed, enrichment)
            _native_verdict(parsed)
        elif not required:
            # a bridge without structure_draw: fall back to the Karamba overlay
            return None, "This bridge version cannot draw native results (update almondbridge)."
        return json.dumps(parsed), None


    def _enrich_native_view(parsed, report):
        # Current bridge observations take precedence, including any warnings
        # reported after the solve. Older bridges report zero native draw nodes.
        for key, value in report.items():
            if key == "warnings":
                parsed[key] = list(dict.fromkeys([*parsed.get(key, []), *value]))
            elif key == "nodes" and not parsed.get(key):
                parsed[key] = value
            else:
                parsed.setdefault(key, value)


    def _native_verdict(parsed):
        indicative = parsed.pop("_indicative", False) or parsed.get("status") == "indicative"
        if indicative and parsed.get("status") == "pass":
            parsed["status"] = "indicative"
        if parsed.get("buckling"):
            # Elastic mode amplitude has no physical deflection magnitude.
            stable = parsed["buckling"]["alpha_cr"] > 1.0
            # Stability alone cannot supply an unsupported material capacity verdict.
            if not stable:
                parsed["status"] = "fail"
            parsed.pop("max_displacement_mm", None)
        parsed["passed"] = None if parsed["status"] == "indicative" else parsed["status"] == "pass"


    def _render_validation_report(runs: list[dict]) -> str:
        """Markdown report of persisted analysis_04-validate_structure tool runs, newest first."""
        from datetime import datetime, timezone

        lines = [
            "# Structural validation report",
            "",
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
            f"by almond-mcp. {len(runs)} run(s), newest first.",
            "",
            "## How a run works",
            "",
            "`analysis_04-validate_structure tool` extracts the referenced Rhino geometry through the bridge.",
            "With `engine='auto'`, line/frame models use **native** — Almond's frame FEA.",
            "Its confidence depends on the material and supported checks. Shell models or",
            "unavailable native model export use the Karamba route. Explicit `engine='native'`",
            "requires native analysis; `engine='karamba'` selects the Karamba route directly.",
            "The Karamba route tries:",
            "",
            "1. **api** — direct Karamba 3.1 solve (real FEA), confidence *high*;",
            "2. **template** — audited capsule GHX definition, confidence *medium*;",
            "3. **rule_based** — span/slenderness heuristics (UDL `w = load/span`,",
            "   `5wL^4/384EI`), confidence *low*. An estimate, not FEA.",
            "",
            "Native validation returns the selected design code, combinations and limits.",
            "PASS means the configured checks passed; it is not a structural safety certification.",
            "FAIL means a configured check failed; consult its verdict and warnings.",
            "**INDICATIVE** means the analysis completed without a material capacity verdict;",
            "it is neither PASS nor FAIL. Consult each run's verdict and warnings.",
            "The applied load defaults to **10 kN** unless load_kn is given.",
            "",
            "## Runs",
            "",
            "| # | when (UTC) | type | method | confidence | span m | defl mm | limit mm | util | reactions kN | members | result |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for run in runs:
            lines.append(
                f"| {run['id']} | {run['ran_at'][:16].replace('T', ' ')} "
                f"| {run['structure_type']} | {run['analysis_method']} "
                f"| {run['confidence']} | {run['span_m']:.1f} "
                f"| {run['max_deflection_mm']:.2f} | {run['deflection_limit_mm']:.1f} "
                f"| {run['utilization_ratio']:.2f} | {run['reactions_kn']:.2f} "
                f"| {run['member_count']} | {run['status'].upper()} |"
            )
        lines.append("")
        lines.append("## Run details")
        for run in runs:
            lines += [
                "",
                f"### Run {run['id']} — {run['structure_type']}, "
                f"{run['analysis_method']} ({run['status'].upper()})",
                "",
                f"- input: {run['member_count']} object(s), load {run['load_kn']:.1f} kN, "
                f"material {run['material']}",
                f"- verdict: {run['verdict']}",
            ]
            if run["warnings"]:
                lines.append("- warnings:")
                lines += [f"  - {w}" for w in run["warnings"]]
            if run.get("analysis") is None:
                lines.append("- applied analysis inputs: unknown (legacy history did not record them)")
            else:
                lines += ["- applied analysis inputs:", "", "```json",
                          json.dumps(run["analysis"], ensure_ascii=False, indent=2), "```"]
        lines += [
            "",
            "## Reading the numbers",
            "",
            '- **native** and **api** runs use finite element analysis. Their reactions_kn',
            '  should balance the modeled load for the reported load combination,',
            "  including enabled self-weight, floor and asset loads (equilibrium).",
            '- Known gaps in karambaCommon 3.1.60519 (issue #6): api-mode',
            '  max_deflection and per-element utilization may read 0.0 due to',
            '  signature drift — trust reactions and stability diagnostics;',
            '  cross-check deflection against the rule_based estimate.',
            '- rule_based results are labeled LOW CONFIDENCE for a reason: treat',
            '  them as sanity checks, not engineering.',
            "",
        ]
        return "\n".join(lines)


    @public_tool(mcp, wrapped=True)
    def export_structural_report(path: str = "", limit: int = 50) -> str:
        """저장된 구조 검증 이력을 Markdown 보고서로 작성합니다.

        각 실행의 실제 엔진과 적용 입력을 함께 표시합니다. 저장 당시 입력이 없던 이전 이력은 알 수 없음으로 표시하며, 현재 기본값으로 과거 설정을 채우지 않습니다.

        Args:
            path: 관리형 세션에서는 선택한 Plan 산출물 디렉터리 아래의 상대 파일 경로이며, 기본값은 reports/structural-validation.md입니다. 독립 실행의 기본값은 사용자 데이터의 reports/structural-validation-<timestamp>.md입니다.
            limit: 포함할 최대 실행 개수입니다. 기본값은 50, 최댓값은 500입니다.
        """
        from datetime import datetime, timezone

        try:
            runs = context.retrieval_store.list_validation_runs(limit=limit)
            if not runs:
                return json.dumps(error_payload('No validation runs recorded yet - call analysis_04-validate_structure tool first.'))
            target = Path(path) if path else (
                paths.user_data_dir() / "reports" /
                f"structural-validation-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_render_validation_report(runs), encoding="utf-8")
            return json.dumps({
                "status": "success",
                "path": str(target),
                "runs": len(runs),
                "latest_method": runs[0]["analysis_method"],
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

    return {
        "validate_structure": validate_structure,
        "list_design_codes": list_design_codes,
        "visualize_structure": visualize_structure,
        "_render_validation_report": _render_validation_report,
        "export_structural_report": export_structural_report,
    }
