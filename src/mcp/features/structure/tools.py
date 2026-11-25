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
        """Rhino 구조 형상의 해석과 설계기준 검토. 실행 이력에는 요청 옵션, 실제 엔진·입력·결과를 보관. native는 내보낸 모델과 적용한 하중도 기록. 이전 이력에 기록되지 않은 옵션은 알 수 없음으로 표시.

        Args:
            guids: 현재 Rhino 문서의 해석 대상 객체 GUID.
            structure_type: "beam" 단순 보 휨·처짐, "truss" 축력·좌굴, "shell" 셸 응력·변위, "frame" 프레임 모멘트·전단, "canopy" 캔틸레버 캐노피, "gridshell" 대변형 그리드셸, "membrane" 막 구조 형상 탐색, "highrise" 고층 구조 시스템.
            load_kn: 전체 부과하중. native는 자유 절점에 하향(-Z) 균등 분배. 바닥·자산 하중과 중복되지 않게 산정하고 필요 시 0 지정.
            material: "Steel", "S355", "Concrete", "Wood", "Aluminium".
            engine: auto, native, karamba 중 선택. auto는 선형 프레임에 native, 그 외에 Karamba 선택. karamba는 api → template → rule_based 순으로 시도. 실제 적용 방식은 analysis_method·warnings에서 확인.
            fixed_supports: true는 완전 고정, false는 회전이 자유로운 핀 지점.
            span_m: 네이티브 해석에서 부재가 여러 절점으로 분할된 경우 L/250을 적용할 전체 경간(예: 3.1 m 두 구간으로 그린 6.2 m 장선).
            asset_loads: 네이티브 해석에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 입력에 반영한 하중과 중복되지 않게 산정.
            floor_load_kn_m2: 네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.
            floor_dead_kn_m2: 같은 바닥 구획의 구성층·마감 등 추가 고정하중.
            design_basis: 네이티브 하중 조합. "en1990"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. "unfactored"는 Karamba와 같이 둘 다 G + Q 적용.
            uls_combination: "6.10" 또는 "6.10ab". "6.10ab"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환.
            connections: 네이티브 접합 조건. "rigid"는 모든 접합부의 모멘트를 전달하고, "simple"은 보 단부의 강축 휨과 가새 단부의 양축 휨을 해제. 같은 선상으로 이어지는 부재와 기둥은 연속 유지. 일반 볼트 접합 강구조·목구조는 "simple"에 가깝고 강접합은 보 처짐을 과소평가할 수 있음. 곡선 User Text의 release 값("pinned", "pinned_start", "pinned_end", "rigid") 우선.
            stability: "auto"는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 ±X·±Y 횡변위 초기 불완전성 φ = 1/200 × αh × αm(5.3.2) 적용. alpha_cr < 10이면 2차 P-Delta ULS 해석, alpha_cr ≤ 1이면 불안정으로 실패 처리. "off"는 초기 불완전성을 적용하지 않는 1차 해석.
            design_code: 설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. "eurocode"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. "off"는 design_basis="unfactored"와 같이 G + Q 적용.
            detail: 네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.
            fabrication: 강재 중공 단면(CHS/RHS)의 제작 방식. "cold_formed"는 EN 10219 좌굴 곡선 c, "hot_finished"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 "hot_finished" 사용.
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
            code = native_structure.design_profile(design_basis, design_code, uls=uls_combination)
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
                                              self_weight, span_m, engine=engine, asset_spec=spec,
                                              floor_spec=floor, design=(design_basis, uls_combination, code),
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


    def _model_unavailable(engine, message):
        if engine == "native":
            return json.dumps(error_payload(message)), None
        return None, message + " Fell back to the Karamba route."

    def _read_structure_model(guids, engine, *, timeout_message=None):
        """Export the line model or return the native route's error or fallback note."""
        try:
            model = json.loads(context._send_and_receive(
                json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?")), None
        except Exception as e:
            if timeout_message is not None and isinstance(e, socket.timeout):
                return _model_unavailable(engine, timeout_message)
            return _model_unavailable(engine, f"The bridge could not export a structural model ({e}).")
        if not isinstance(model, dict) or model.get("status") != "ok" or "members" not in model:
            return _model_unavailable(engine, "This bridge version cannot export structural models (update almondbridge).")
        if model.get("shells"):
            return _model_unavailable(engine, f"The model contains {model['shells']} shell element(s), which the native frame solver does not analyse.")
        return model, None


    def _native_validation(guids, structure_type, load_kn, material, fixed_supports, self_weight, span_m, engine, *,
                           design, asset_spec=None, floor_spec=None, connections="rigid",
                           stability="auto", detail=False, fabrication="cold_formed", history=None):
        """Native frame check on the bridge's exported line model.

        Returns (result_dict, None) when it ran, (None, note) to fall back to the Karamba
        route with a note, or (json_error_string, None) when it must stop (explicit native
        request that cannot run, or no bridge)."""
        reply, note = _read_structure_model(
            guids, engine, timeout_message="Exporting the structural model timed out.")
        if not isinstance(reply, dict):
            return reply, note
        if not reply["members"]:
            return _model_unavailable(engine, "No line members found for the given GUIDs.")
        if history is not None:
            history.update(model=reply, floor_load_spec=floor_spec, asset_load_spec=None)
            if asset_spec is not None:
                catalogue = asset_spec.get("catalogue") or {}
                table = asset_spec["table"]
                history["asset_load_spec"] = dict(placements=asset_spec["placements"], catalogue=catalogue,
                    basis=table.basis, loads={p["asset_id"]: table.lookup(p["asset_id"],
                        (catalogue.get(p["asset_id"]) or {}).get("category", "")) for p in asset_spec["placements"]})
        try:
            design_basis, uls, code = design
            if history is not None:
                history.update(design_profile=code.summary(),
                               uls_expression=code.uls(uls or None)[0] if code.factored else "unfactored")
            result = native_structure.validate(reply, structure_type.lower(), load_kn, material,
                                               fixed_supports=fixed_supports, self_weight=self_weight, span_m=span_m,
                                               asset_loads=asset_spec, floor_loads=floor_spec,
                                               design_basis=design_basis, uls=uls, connections=connections,
                                               stability=stability, design_code=code, detail=detail,
                                               fabrication=fabrication)
        except ValueError as e:
            return json.dumps(error_payload(str(e))), None
        return result, None


    @public_tool(mcp, wrapped=True)
    @query_output
    def list_design_codes(include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """구조 해석에 사용할 설계기준 프로필 조회.

        Args:
            field_groups: parameters, source, audit, all. 생략하거나 빈 배열이면 요약.
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
        """구조 해석 결과를 임시 뷰포트 오버레이로 표시.

        Args:
            guids: 구조 축선 곡선과 지점 표식 점의 GUID. 지점 표식이 없으면 최하단 절점을 지점으로 사용(fixed_supports 참조).
            load_kn: 자유 절점에 하향(-Z) 균등 분배할 전체 부과하중.
            material: "Steel", "S355", "Concrete", "Wood", "Aluminium".
            beam_diameter_mm: 원형 부재의 외경.
            fixed_supports: true는 완전 고정, false는 회전이 자유로운 핀 지점.
            deflection_limit_ratio: 허용 처짐 L/n의 n. 생략 시 설계기준 한계 사용(예: Eurocode의 L/250은 250).
            span_m: 처짐 한계 평가에 쓸 기준 경간. 생략 시 가장 긴 부재 사용. 6.2 m 장선을 3.1 m씩 분할했다면 6.2 지정.
            color_by: "displacement" 또는 "utilization".
            scale: 변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정.
            reveal: 표시할 부재 비율 0..1. 단계별 시공 재생에 사용.
            reanalyze: false이면 마지막 계산을 재사용하고 표시 옵션(scale, color_by, reveal, physics, title)만 갱신.
            physics: false이면 해석 오버레이 없이 같은 부재의 일반 형상을 그려 전후 비교.
            display_guids: 그릴 부재만 선택(예: 단면을 보여 줄 한 줄의 프레임). 해석은 guids 전체에 적용.
            clear: 현재 해석 오버레이 제거.
            engine: "native", "karamba", "auto". "auto"는 네이티브 프레임 솔버를 우선 사용하고 셸이 포함되거나 브리지에서 모델을 내보낼 수 없으면 Karamba 사용.
            asset_loads: 네이티브 해석에서 analysis_02-validate_structure tool과 같은 배치 자산 하중을 추가하고 작용점에 하중 화살표 표시.
            floor_load_kn_m2: 네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.
            floor_dead_kn_m2: 같은 바닥 구획의 구성층·마감 등 추가 고정하중.
            design_basis: 네이티브 하중 조합. "en1990"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. "unfactored"는 Karamba와 같이 둘 다 G + Q 적용.
            uls_combination: "6.10" 또는 "6.10ab". "6.10ab"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환.
            connections: analysis_02-validate_structure tool과 같은 "rigid" 또는 "simple". 핀 접합 단부는 작은 원으로 표시.
            stability: analysis_02-validate_structure tool과 같은 "auto" 또는 "off".
            design_code: 설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. "eurocode"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. "off"는 design_basis="unfactored"와 같이 G + Q 적용.
            fabrication: 강재 중공 단면(CHS/RHS)의 제작 방식. "cold_formed"는 EN 10219 좌굴 곡선 c, "hot_finished"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 "hot_finished" 사용.
            view: "deflection"은 처짐 형상, "buckling"은 지배 ULS 조합의 첫 좌굴 모드와 alpha_cr 표시(STABLE ≥ 10, SWAY-SENSITIVE 1~10, UNSTABLE ≤ 1).
        """
        nonlocal view_engine, native_report
        if not clear and not guids:
            return json.dumps(error_payload("Provide the curve (and support point) GUIDs to analyse."))
        if color_by not in ("displacement", "utilization"):
            return json.dumps(error_payload("color_by must be 'displacement' or 'utilization'."))
        engine = (engine or "auto").lower()
        if engine not in ("auto", "native", "karamba"):
            return json.dumps(error_payload("engine must be 'auto', 'native' or 'karamba'."))
        code = design_code
        if deflection_limit_ratio is None:
            try:
                code = native_structure.design_profile(design_basis, code)
                deflection_limit_ratio = code.deflection_limit_ratio
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
                code = native_structure.design_profile(design_basis, code, uls=uls_combination)
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
            reply, note = _native_view(request, guids, engine=engine, asset_spec=spec, floor_spec=floor,
                                       design=(design_basis, uls_combination, code), connections=connections,
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


    def _native_view(request: dict, guids, engine: str, asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"),
                     connections="rigid", stability="auto", view="deflection", fabrication="cold_formed"):
        """Solve natively and draw through the bridge's structure_draw overlay.

        Returns (reply_json, None) when it ran or must stop, (None, note) to fall back to Karamba."""

        nonlocal view_engine, native_report
        model, note = _read_structure_model(guids, engine)
        if not isinstance(model, dict):
            return model, note
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
        elif engine != "native":
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
        """Markdown report of persisted analysis_02-validate_structure tool runs, newest first."""
        from datetime import datetime, timezone

        lines = [
            "# Structural validation report",
            "",
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
            f"by almond-mcp. {len(runs)} run(s), newest first.",
            "",
            "## How a run works",
            "",
            "`analysis_02-validate_structure tool` extracts the referenced Rhino geometry through the bridge.",
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
        """구조 검증 이력의 Markdown 보고서 생성. 각 실행에 실제 엔진과 적용 입력을 기록하고, 저장되지 않은 과거 입력은 알 수 없음으로 표시.

        Args:
            path: 관리형은 선택한 Plan 산출물 폴더 기준 상대 경로(생략 시 reports/structural-validation.md). 독립 실행에서 생략 시 사용자 데이터의 reports/structural-validation-<timestamp>.md.
            limit: 최대 500회.
        """
        from datetime import datetime, timezone

        try:
            runs = context.retrieval_store.list_validation_runs(limit=limit)
            if not runs:
                return json.dumps(error_payload('No validation runs recorded yet - call analysis_02-validate_structure tool first.'))
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
