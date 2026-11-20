"""Register asset tools and resources against the calling server's live context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.assets.output import GROUPS, project, with_next_step
from almond_mcp.tool_declarations import public_tool

from pydantic import StrictBool, StrictInt
import json
import math
from pathlib import Path
import struct
import tempfile
import uuid

from fastmcp.resources import ResourceContent, ResourceResult

from almond_mcp.features.structure import asset_loads
from almond_mcp import paths, managed_paths
from almond_mcp.features.assets import asset_passport
from almond_mcp.features.assets import drawing_assets, drafting, preparation, model_index
from almond_mcp.features.assets.mutation import send_mutation
from almond_mcp.features.exchange import exchange
from almond_mcp.features.exchange.tools import Exchange


EXPORT_FAILURE = 'Asset files and manifest were published. Reconnect to refresh the index; do not repeat registration: {0}'
UNKNOWN_ASSET_ID = 'No bundled drawing for this asset; generate views on demand'


def register(mcp, context):
    """Register the existing asset API without freezing mutable server services."""

    @public_tool(mcp, wrapped=True)
    @query_output
    def list_drawing_assets(
        category: str = "",
        limit: int = 20,
        offset: int = 0, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """모델·2D 자산 목록과 배치 준비 상태 조회. 상세 조회용 ID는 include_ids=true로 포함.

        Args:
            category: 빈 값은 전체 분류.
            offset: 페이지의 시작 위치(0부터).
            field_groups: dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        page = model_index.for_context(context).search_page(
            category=category,
            limit=limit,
            offset=offset,
        )
        return json.dumps(project({
            "library_id": "model_assets",
            "purpose": "3DM models and 2D representations; legacy sources require explicit conversion",
            **page,
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def search_drawing_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """모델·2D 자산을 검색어·분류·최대 치수로 검색. 단어가 하나라도 일치하면 포함하고 일치 단어가 많은 순으로 반환. 치수 필터는 등록 치수를 비교하며 해당 치수가 없는 자산도 포함할 수 있음. include_ids=true로 얻은 ID를 asset_04-get tool에 전달해 상세 조회.

        Args:
            query: 이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.
            category: 대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.
            max_width_mm: 양수일 때만 필터 적용.
            max_depth_mm: 양수일 때만 필터 적용.
            max_height_mm: 양수일 때만 필터 적용.
            limit: 페이지당 1~100개.
            offset: 페이지의 시작 위치(0부터).
            field_groups: dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        return json.dumps(project(model_index.for_context(context).search_page(
            query=query,
            category=category,
            max_width_mm=max_width_mm,
            max_depth_mm=max_depth_mm,
            max_height_mm=max_height_mm,
            limit=limit,
            offset=offset,
        ), field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def get_drawing_asset(asset_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """모델·2D 자산의 등록 정보와 사용 가능 상태 조회. field_groups에 paths를 지정하면 원본·모델 경로를 확인.

        Args:
            asset_id: 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
            include_ids: 조회에 사용한 asset_id는 응답에 반복되지 않을 수 있음.
            field_groups: dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        index = model_index.for_context(context)
        asset = index.get(asset_id)
        if not asset:
            return json.dumps(project(error_payload(f"Unknown drawing asset_id: {asset_id}"), field_groups))
        return json.dumps(project({"status": "success", "asset": index.public_record(asset)}, field_groups))


    def _extract_drawing_asset(source_path: str, output_path: str) -> dict:
        rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
        if rhino_context.get("status") != "success" or rhino_context.get("capabilities", {}).get("drawing_asset_extract", 0) < 2:
            raise ValueError('Load a Bridge with drawing_asset_extract=2 before registering or refreshing a 3DM asset')
        response = context._send_and_receive(json.dumps({"type": "drawing_asset_extract",
            "source_path": source_path, "output_path": output_path}).encode("utf-8"), timeout=90.0)
        if len(response.encode("utf-8")) > 262144:
            raise ValueError("Native extraction acknowledgement exceeds 256 KiB")
        return json.loads(response)


    @public_tool(mcp, wrapped=False, annotations={'destructiveHint': False, 'openWorldHint': False})
    def prepare_drawing_asset(stage: str, source_file: str = "", job_dir: str = "",
                              input_units: str = "", review: dict | None = None,
                              field_groups: list[str] | None = None,
                              include_ids: StrictBool = False, offset: StrictInt = 0,
                              limit: StrictInt = 50) -> dict:
        """원본 사본을 시각 검토해 등록용 3DM을 준비. inspect로 작업을 만들고, 수정이 필요할 때만 normalize 실행. 첫 verify가 생성한 최종 미리보기를 확인한 뒤 같은 해시·이름·ID로 verify를 다시 호출.

        Args:
            stage: inspect, normalize, verify, status. status는 저장 근거만 조회하며 네이티브 실행 재개나 단계 갱신은 하지 않음.
            source_file: inspect에 사용할 모델. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 원본 바이트는 보존.
            job_dir: 이전 응답의 job_dir. normalize·verify·status에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
            input_units: OBJ/STL/PLY/OFF/GLB/glTF의 측정된 원본 단위(mm, cm, m, in, ft). inspect 이후 생략. 3DM은 내장 단위 유지.
            review: normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID", reason:"사유"}]}. 생략한 변환은 그대로 두며 translation은 원본 단위. 최종 미리보기 확인 후 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}.
            field_groups: summary, parts, previews, provenance, all. 생략 시 미리보기 경로 포함, []는 요약. 페이지 처리는 parts에만 적용.
            offset: 페이지의 시작 위치(0부터).
            limit: 부품 목록 페이지당 1~200개.
        """
        try:
            return preparation.prepare(stage=stage, source_file=source_file, job_dir=job_dir,
                input_units=input_units, review=review, field_groups=field_groups,
                include_ids=include_ids, offset=offset, limit=limit,
                sender=context._send_and_receive, execute=getattr(context, "_execute_rhinocode", None),
                expected_model_path="")
        except Exception as exc:
            return error_payload(str(exc))


    @public_tool(mcp, wrapped=False, annotations={'destructiveHint': False, 'openWorldHint': False})
    def register_drawing_asset(source_3dm: str, asset_id: str, name: str,
                               category: str = "other", tags: list[str] | None = None,
                               description: str = "", source_url: str = "",
                               replace_existing: bool = False, preparation_job: str = "") -> dict:
        """검토한 3DM을 모델 라이브러리에 등록하고 치수·평면·입면 실루엣 도면을 생성. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외. 준비를 마쳤어도 파생 메시가 250,000 삼각형을 넘으면 등록 실패. 등록 결과는 asset_04-get tool에서 확인.

        Args:
            source_3dm: 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.
            asset_id: preparation_job을 지정하면 준비 단계에서 검토한 ID와 일치해야 함.
            name: preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.
            replace_existing: true일 때만 같은 ID의 기존 자산 교체.
            preparation_job: 완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
        """
        try:
            if asset_id in context.diagram_asset_indexer.assets:
                raise ValueError('This asset ID belongs to the separate Diagram collection')
            legacy = context.generated_asset_indexer.get(asset_id)
            previous = context.drawing_asset_indexer.get(asset_id)
            if previous and model_index.is_model_source(previous) and Path(previous.get("file", "")).suffix.lower() != ".3dm":
                legacy = previous
            result = drawing_assets.register_prepared_3dm(Path(context.DRAWING_LIBRARY_DIR),
                source_3dm=source_3dm, asset_id=asset_id, name=name, category=category,
                tags=tags, description=description, source_url=source_url,
                replace_existing=replace_existing, preparation_job=preparation_job,
                extract=_extract_drawing_asset, legacy_source=legacy)
        except drawing_assets.PublicationUnconfirmed as exc:
            return {"status": "error", "registration_applied": None, "requires_reconciliation": True,
                    "error_code": "asset_publication_unconfirmed", "message": str(exc)}
        except Exception as exc:
            return {"status": "error", "registration_applied": False, "message": str(exc)}
        try:
            context.drawing_asset_indexer._load()
        except Exception as exc:
            return {**result, "status": "error", "registration_applied": True,
                    "live_index_refreshed": False,
                    "message": EXPORT_FAILURE.format(exc)}
        return {**result, "registration_applied": True, "live_index_refreshed": True}


    @public_tool(mcp, wrapped=False, annotations={'destructiveHint': False, 'openWorldHint': False})
    def refresh_asset(asset_id: str) -> dict:
        """편집·저장한 등록 3DM을 다시 측정해 평면·입면 도면을 새 리비전으로 발행. 원본 경로와 이전 도면은 보존. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외.

        열린 Rhino 문서의 연결 블록 갱신·저장은 별도. 공유 정의를 갱신하면 기존 인스턴스에 반영되며 배치 당시 메타데이터는 유지.
        """
        try:
            result = drawing_assets.refresh_registered_asset(Path(context.DRAWING_LIBRARY_DIR),
                asset_id, extract=_extract_drawing_asset)
        except Exception as exc:
            return {"status": "error", "registration_applied": False, "message": str(exc)}
        try:
            context.drawing_asset_indexer._load()
        except Exception as exc:
            return {**result, "status": "error", "live_index_refreshed": False,
                    "message": EXPORT_FAILURE.format(exc)}
        return {**result, "live_index_refreshed": True}


    def list_assets(
        category: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """
    Lists the redistributable generated asset library: 3D entourage (people,
    trees, vehicles), site furniture, columns, balustrades,
    sanitary/kitchen fixtures, and unbranded
    furniture placeholders. Every asset is a GLB normalised to real-world
    millimetres with a measured spatial contract and an Almond material_id,
    so placement, collision checks and material restore work without any
    third-party download. Place with place_asset.
    """
        page = context.retrieval_store.search_assets(
            library_id="generated_assets",
            category=category,
            limit=limit,
            offset=offset,
        )
        return json.dumps({
            "library_id": "generated_assets",
            "purpose": "redistributable generated entourage, components and fixtures",
            "license": "CC-BY-4.0",
            **page,
        })


    def search_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0,
    ) -> str:
        """Searches only the generated asset library (FTS over product, variant,
    category and tags; dimension filters use the measured GLB bounds)."""
        return json.dumps(context.retrieval_store.search_assets(
            query=query,
            library_id="generated_assets",
            category=category,
            max_width_mm=max_width_mm,
            max_depth_mm=max_depth_mm,
            max_height_mm=max_height_mm,
            limit=limit,
            offset=offset,
        ))


    def recommend_assets(
        query: str = "", category: str = "", room_type: str = "",
        width_mm: float = 0, depth_mm: float = 0, height_mm: float = 0,
        max_triangles: int = 0, include_clearances: bool = True, limit: int = 5,
    ) -> dict:
        """Shortlist available models with explicit reasons, quality notes and fit
    options. Query matches product/variant/tags; room_type is an inferred usage
    filter (e.g. living_room, dining_room, office, bathroom, landscape).
    Supply width AND depth for rectangular fit at 0/90 degrees; height 0 is
    unbounded. Authored clearances count by default. No Rhino connection needed.
    """
        try:
            return asset_passport.recommend(
                list(context.generated_asset_indexer.assets.values()), query, category, room_type,
                width_mm, depth_mm, height_mm, max_triangles, include_clearances, limit)
        except ValueError as exc:
            return error_payload(str(exc))


    def get_asset_passport(asset_id: str) -> dict:
        """Read portable asset metadata: measured vs nominal dimensions, provenance,
    materials, spatial contract, usage suggestions, quality limits and rights."""
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return error_payload(f"Unknown generated asset_id: {asset_id}")
        if not asset.get("passport"):
            return error_payload('Library has no passport; upgrade the asset pack.')
        out = {"status": "success", "passport": asset["passport"],
               "file_available": asset.get("file_available", False),
               "preview_uri": f"almond://assets/{asset_id}/preview"}
        try:
            table = asset_loads.LoadTable.from_library(context.GENERATED_LIBRARY_DIR)
            entry = table.lookup(asset_id, asset.get("category", ""))
            if entry:
                out["structural_loads"] = {**entry, "basis": table.basis}
        except Exception:
            pass
        return out


    def evaluate_asset_fit(
        asset_id: str, width_mm: float, depth_mm: float, height_mm: float = 0,
        rotation_degrees: float = 0, include_clearances: bool = True,
    ) -> dict:
        """Check one model's rotated clearance envelope against a rectangle in mm.
    This is a preflight size check, not obstacle detection or code certification.
    Mounting heights and actual scene positions are not evaluated."""
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return error_payload(f"Unknown generated asset_id: {asset_id}")
        try:
            return {"status": "success", **asset_passport.evaluate_fit(
                asset, width_mm, depth_mm, height_mm, rotation_degrees, include_clearances)}
        except ValueError as exc:
            return error_payload(str(exc))


    def get_asset_sources(asset_id: str) -> dict:
        """Get original recorded provider/task IDs, prompt, transformations and evidence gaps.
    Includes Higgsfield image job IDs where recorded before the Meshy stage.
    This is local evidence, not an independent provider/account verification."""
        path = Path(context.GENERATED_LIBRARY_DIR)/"source-register.json"
        if not path.exists():
            return error_payload('Source register missing; update the asset pack')
        data = json.loads(path.read_text(encoding="utf-8"))
        record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
        if not record:
            return error_payload("Unknown generated asset ID")
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset or record["model_sha256"] != asset["sha256"]:
            return error_payload("Source register is stale for this asset")
        return {"status": "success", "record": record}


    def registered_source(asset, root):
        if not asset:
            return None
        root = Path(root).resolve()
        source = (root / asset["file"]).resolve()
        source.relative_to(root)
        return source


    def registered_drawing(asset_id):
        asset = model_index.for_context(context).assets.get(asset_id)
        if asset and asset.get("drawing_package"):
            root = Path(asset["_library_root"])
            package = drafting.package_file(root, asset["drawing_package"])
            return package, registered_source(asset, root), True
        root = Path(context.DRAFTING_LIBRARY_DIR).resolve()
        data = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
        record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
        if not record:
            return None
        # Drafting packages were projected from the generated source, even
        # when the preferred model is now a separately registered 3DM.
        source = registered_source(context.generated_asset_indexer.get(asset_id), context.GENERATED_LIBRARY_DIR)
        return drafting.package_file(root, record["package"]), source, False


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': True, 'openWorldHint': False})
    @query_output(preserve_cross_drive_fields={"package_dir"})
    def get_asset_drawing(asset_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> dict:
        """등록 자산의 저장 도면 패키지 조회. 도면은 배치 인스턴스 변환을 적용하지 않은 자산 원본 형상의 투영. manifest에서 파일·축척·치수·출처·투영 한계를 확인.

        Args:
            asset_id: 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
            field_groups: dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        drawing = registered_drawing(asset_id)
        if not drawing:
            return project(error_payload(UNKNOWN_ASSET_ID), field_groups)
        package, _, embedded = drawing
        manifest = drafting.read_package_manifest(package)
        if embedded:
            return project({"status": "success", "asset_id": asset_id, "package_dir": str(package), "manifest": manifest,
                    "dimensions_path": str(package / "dimensions.json"),
                    "plan_svg_uri": f"almond://drawing/{asset_id}/drawing/plan/50"}, field_groups)
        return project({"status": "success", "package_dir": str(package), "manifest": manifest,
                "plan_svg_uri": f"almond://assets/{asset_id}/drawing/plan/50"}, field_groups)


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False, 'openWorldHint': False})
    def generate_asset_drawing_views(asset_id: str = "", source_glb: str = "",
                                     input_units: str = "", up_axis: str = "y",
                                     scales: list[int] | None = None,
                                     source_references: list[dict] | None = None) -> dict:
        """등록 3DM 또는 사용자 GLB 메시의 평면·정면·우측면 실루엣 생성. 실물 크기 mm DXF와 축척 SVG를 출력. 세 뷰가 A3에 들어가면 시트 SVG도 생성하며, 시트 없이도 성공 가능.

        정면은 좌표계 기준. 실루엣에 단면·내부 가시선·은선은 없으며 축척별 단순화로 작은 윤곽이 달라질 수 있음. 결과는 별도 drawing-runs에 저장하고 등록 자산의 도면은 갱신하지 않음.

        Args:
            asset_id: 등록 3DM 자산 ID. source_glb와 택일.
            source_glb: 정적·비압축 삼각형 GLB(최대 100 MB, 250,000 삼각형).
                관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
            input_units: source_glb를 지정하면 GLB 원본 단위 mm 또는 m 필수.
            up_axis: GLB 위쪽 축 y 또는 z. y는 (X, -Z, Y)로 변환. 등록 3DM에는 적용하지 않음.
            scales: 서로 다른 정수 축척 분모 1~4개(5~1000). 생략 시 [50, 100].
            source_references: 도면에 첨부하는 참고 출처. 원본 모델의 생성 이력 증빙과는 별도.
                필수 키: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.
                relationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference.
        """
        try:
            if bool(asset_id) == bool(source_glb):
                raise ValueError('Choose exactly one asset_id or source_glb')
            source_record = None
            if asset_id:
                asset = model_index.for_context(context).get(asset_id)
                if not asset:
                    raise ValueError("Unknown model asset ID")
                if asset.get("source_only"):
                    raise ValueError("Prepare and register this legacy source as a 3DM before generating model views")
                model = Path(asset["_resolved_file"])
                if model.suffix.lower() != ".3dm":
                    raise ValueError("Projection generation requires a 3DM model asset")
                if drafting.sha(model.read_bytes()) != asset["sha256"]:
                    raise ValueError("Source model changed; asset_08-refresh tool updates its registered measurements and drawings")
                source_record = asset.get("source", {})
                name, units, up = asset["product"], "mm", "z"
            else:
                model = Path(source_glb)
                if not model.is_absolute() or model.suffix.lower() != ".glb":
                    raise ValueError("Custom source must be an absolute .glb path")
                if model.stat().st_size > 100_000_000:
                    raise ValueError("GLB exceeds 100 MB limit")
                name, units, up = model.stem, input_units, up_axis
                asset_id = "custom-" + drafting.sha(model.read_bytes())[:16].lower()
                source_record = {"evidence_status": "user_supplied_mesh", "generation_history": "not_supplied"}
            output = paths.user_data_dir()/"drawing-runs"/str(uuid.uuid4())
            if model.suffix.lower() == ".3dm":
                output.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=".extract-", dir=output.parent) as temporary:
                    triangles, _, _ = drawing_assets._native_triangles(model, Path(temporary) / "triangles.json", _extract_drawing_asset)
                    return drafting.create_package(model, output, asset_id=asset_id, name=name,
                        units="mm", up_axis="z", triangles_mm=triangles,
                        scales=[50, 100] if scales is None else scales,
                        references=source_references or [], source_record=source_record)
            return drafting.create_package(model, output, asset_id=asset_id, name=name,
                units=units, up_axis=up, scales=[50, 100] if scales is None else scales,
                references=source_references or [], source_record=source_record)
        except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as exc:
            return error_payload(str(exc))


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': True, 'openWorldHint': False})
    def audit_asset_drawing(package_dir: str, source_glb: str = "") -> dict:
        """저장된 도면 패키지의 SVG·DXF를 파일 해시 목록과 대조. 빈 해시 목록, 누락·변경 파일, 패키지 외부 경로, 파일시스템 링크는 오류. 원본을 찾으면 원본 변경도 검사.

        Args:
            package_dir: 도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.
            source_glb: 원본이 바뀌었는지 비교할 GLB. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 라이브러리에서 원본을 찾을 수 있으면 생략 가능.
        """
        try:
            from almond_mcp.managed_paths import drawing_package_path
            package = drawing_package_path(package_dir, library_roots=[
                paths.user_data_dir() / "drawing-runs", Path(context.DRAWING_LIBRARY_DIR),
                Path(context.GENERATED_LIBRARY_DIR), Path(context.DRAFTING_LIBRARY_DIR)])
            manifest = drafting.read_package_manifest(package)
            source = Path(source_glb) if source_glb else None
            if source is not None and not source.is_absolute():
                raise ValueError("Supply an absolute source GLB path")
            if source is None:
                meta = manifest["source"]
                source_format = "." + meta.get("source_format", "glb")
                for index, root in ((context.drawing_asset_indexer, context.DRAWING_LIBRARY_DIR),
                                    (context.generated_asset_indexer, context.GENERATED_LIBRARY_DIR)):
                    asset = index.get(meta["asset_id"])
                    if asset and Path(asset["file"]).suffix.lower() == source_format:
                        source = registered_source(asset, root)
                        break
            return drafting.audit_package(package, source)
        except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as exc:
            return error_payload(str(exc))


    @mcp.resource("almond://assets/{asset_id}/sources", mime_type="application/json")
    def generation_sources_resource(asset_id: str) -> ResourceResult:
        return ResourceResult([ResourceContent(get_asset_sources(asset_id), mime_type="application/json")])


    @mcp.resource("almond://assets/{asset_id}/drawing/{view}/{scale}", mime_type="image/svg+xml")
    def asset_drawing_resource(asset_id: str, view: str, scale: str) -> ResourceResult:
        if view not in {"plan", "front", "right"} or scale not in {"50", "100"}:
            raise ValueError("Unknown bundled view or scale")
        drawing = registered_drawing(asset_id)
        if not drawing:
            raise ValueError(UNKNOWN_ASSET_ID)
        package, source, _ = drawing
        content = drafting.read_verified_svg(package, asset_id, view, int(scale), source)
        return ResourceResult([ResourceContent(content.decode("utf-8"), mime_type="image/svg+xml")])


    @mcp.resource("almond://drawing/{asset_id}/drawing/{view}/{scale}", mime_type="image/svg+xml")
    def drawing_asset_view_resource(asset_id: str, view: str, scale: str) -> ResourceResult:
        return asset_drawing_resource(asset_id, view, scale)


    @mcp.resource("almond://assets/catalogue", mime_type="application/json")
    def asset_catalogue_resource() -> ResourceResult:
        """Compact catalogue; retrieve individual passports/previews on demand."""
        return ResourceResult([ResourceContent({"library_id": "model_assets", "assets": [
            {"asset_id": a["asset_id"], "product": a.get("product", a["asset_id"]), "category": a.get("category", "other"),
             "dimensions_mm": a.get("dimensions_mm"), "file_available": a.get("file_available"),
             "model_status": a["model_status"], "source_only": a.get("source_only", False),
             "record_uri": f"almond://repository/{a['asset_id']}"}
            for a in model_index.for_context(context).assets.values()]}, mime_type="application/json")])


    @mcp.resource("almond://assets/{asset_id}/passport", mime_type="application/json")
    def asset_passport_resource(asset_id: str) -> ResourceResult:
        return ResourceResult([ResourceContent(get_asset_passport(asset_id), mime_type="application/json")])


    @mcp.resource("almond://assets/{asset_id}/preview", mime_type="image/png")
    def asset_preview_resource(asset_id: str) -> ResourceResult:
        """Existing Blender preview for a known catalogue id."""
        if asset_id not in context.generated_asset_indexer.assets:
            raise ValueError("Unknown generated asset id")
        root = Path(context.GENERATED_LIBRARY_DIR).resolve()
        preview = (root / "previews" / f"{asset_id}.png").resolve()
        preview.relative_to(root)
        return ResourceResult([ResourceContent(preview.read_bytes(), mime_type="image/png")])


    def get_asset(asset_id: str) -> str:
        """Returns one generated asset's measured dimensions, spatial contract,
    material, generation provenance (Meshy task ids, prompt) and availability."""
        asset = context.retrieval_store.get_asset(asset_id, library_id="generated_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown generated asset_id: {asset_id}"))
        return json.dumps({"status": "success", "asset": asset})


    def _dimension_check(asset: dict, bounds: dict | None, scale: float) -> dict | None:
        """Flags gross mismatches between placed AABB and catalogue dimensions.

    Sorted-extent comparison so plan rotations don't false-positive. Only
    returns a payload on failure; a clean placement stays silent.
    """
        dims = asset.get("dimensions_mm") or {}
        expected = [dims.get("width"), dims.get("depth"), dims.get("height")]
        if not bounds or not all(isinstance(v, (int, float)) and v > 0 for v in expected):
            return None
        try:
            placed = sorted(
                abs(float(bounds["max"][i]) - float(bounds["min"][i])) for i in range(3)
            )
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        expected_sorted = sorted(float(v) * scale for v in expected)
        tolerance = 0.15
        mismatched = [
            axis for axis, (p, e) in enumerate(zip(placed, expected_sorted))
            if e > 0 and abs(p - e) / e > tolerance
        ]
        if not mismatched:
            return None
        return {
            "status": "mismatch",
            "expected_sorted_mm": [round(v, 1) for v in expected_sorted],
            "placed_sorted_mm": [round(v, 1) for v in placed],
            "tolerance": tolerance,
            "note": (
                'Placed geometry deviates from catalogue dimensions beyond tolerance; inspect the source model (see '
                'manifest match note).'
            ),
        }


    def _apply_import_correction(object_guid: str, rotate_x_degrees: float, target_z: float) -> bool:
        """Re-orients a placed instance whose source geometry is mis-oriented
    (manifest import_correction), then re-seats it on the placement plane."""
        script = f"""
using System;
using System.Collections.Generic;
using Rhino;
using Rhino.Geometry;

public class Script
{{
    public static List<Guid> Run(RhinoDoc doc)
    {{
        var id = new Guid("{object_guid}");
        var obj = doc.Objects.FindId(id);
        if (obj == null) return new List<Guid>();
        var bb = obj.Geometry.GetBoundingBox(true);
        var rot = Transform.Rotation(RhinoMath.ToRadians({rotate_x_degrees}), Vector3d.XAxis, bb.Center);
        doc.Objects.Transform(id, rot, true);
        var obj2 = doc.Objects.FindId(id);
        if (obj2 != null)
        {{
            var bb2 = obj2.Geometry.GetBoundingBox(true);
            doc.Objects.Transform(id, Transform.Translation(0, 0, {target_z} - bb2.Min.Z), true);
        }}
        doc.Views.Redraw();
        return new List<Guid>();
    }}
}}
"""
        payload = json.dumps({"type": "execute", "script": script}).encode("utf-8")
        try:
            response = json.loads(context._send_and_receive(payload, timeout=30.0))
            return response.get("status") == "success"
        except Exception:
            return False


    @public_tool(mcp, wrapped=True)
    def place_drawing_asset(
        asset_id: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation_degrees: float = 0,
        scale: float = 1,
    ) -> str:
        """모델·2D 자산을 Rhino 문서에 블록으로 배치. 3DM은 원본에 연결되며 정의를 갱신하면 같은 정의를 사용하는 기존 배치에 반영.

        Args:
            asset_id: 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
            x: 원본 기준점의 월드 좌표(문서 단위).
            y: 원본 기준점의 월드 좌표(문서 단위).
            z: 원본 기준점의 월드 좌표(문서 단위).
            rotation_degrees: 월드 Z축 기준.
            scale: 균일 배치 축척(0 초과 100 이하).
        """
        asset = model_index.for_context(context).get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown drawing asset_id: {asset_id}"))
        if asset.get("source_only"):
            return json.dumps(with_next_step({"status": "error", "error_code": "asset_needs_conversion",
                "mutation_state": "not_started", "next_tool": "asset_07-prepare",
                "message": "Prepare and register this source as a 3DM before placement; preserve its asset_id."}))
        if not asset.get("file_available"):
            return json.dumps(error_payload(f"Drawing asset file is missing for {asset_id}."))
        numeric_values = [x, y, z, rotation_degrees, scale]
        if not all(
            isinstance(value, (int, float))
            and abs(value) != float("inf")
            and value == value
            for value in numeric_values
        ):
            return json.dumps(error_payload("Placement values must be finite numbers."))
        if scale <= 0 or scale > 100:
            return json.dumps(error_payload("scale must be greater than 0 and no more than 100."))
        if Path(asset["_resolved_file"]).suffix.lower() == ".3dm":
            try:
                observed = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
                if observed.get("status") != "success" or observed.get("capabilities", {}).get("drawing_asset_linked", 0) < 1:
                    return json.dumps({"status": "error", "error_code": "linked_asset_unsupported", "mutation_state": "not_started",
                        "message": "Load a Bridge with drawing_asset_linked=1 before placing a 3DM model asset."})
            except Exception as exc:
                return json.dumps({"status": "error", "error_code": "linked_asset_not_started", "mutation_state": "not_started", "message": str(exc)})

        payload = json.dumps({
            "type": "place_drawing_asset",
            "asset_id": asset_id,
            "file_path": asset["_resolved_file"],
            "name": f"{asset.get('product', '')} {asset.get('variant', '')}".strip(),
            "position": [x, y, z],
            "rotation_degrees": rotation_degrees,
            "scale": scale,
            "metadata": {
                "library_id": "model_assets",
                "product": asset.get("product"),
                "variant": asset.get("variant"),
                "category": asset.get("category"),
                "dimensions_mm": asset.get("dimensions_mm"),
                "drawing_roles": asset.get("drawing_roles", []),
                "lod": asset.get("lod"),
                "warehouse_url": asset.get("warehouse_url"),
                "match_status": asset.get("match_status"),
                "sha256": asset.get("sha256"),
            },
        }).encode("utf-8")

        return json.dumps(send_mutation(context._send_and_receive, payload, timeout=90.0, action="Drawing asset placement"))


    def place_asset(
        asset_id: str,
        x_mm: float = 0,
        y_mm: float = 0,
        z_mm: float = 0,
        rotation_degrees: float = 0,
        layer: str = "ALMOND-GEN",
    ) -> str:
        """
    Imports a generated-library asset into the open Rhino document and places
    it at a point (contract anchor = bottom centre, mm), restoring its Almond
    material and object metadata and verifying the landed size against the
    contract. Use search_assets to choose an asset_id; afterwards inspect
    the resulting geometry and relevant Rhino views.

    Args:
        asset_id: e.g. "gen-park-bench-1".
        x_mm, y_mm, z_mm: placement point in millimetres.
        rotation_degrees: rotation about world Z.
        layer: destination layer, created if absent.
    """
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown generated asset_id: {asset_id}"))
        if not asset.get("file_available"):
            return json.dumps(error_payload('Model file missing for {0}; run almond-mcp fetch-assets to download it.'.format(asset_id)))
        values = [x_mm, y_mm, z_mm, rotation_degrees]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            return json.dumps(error_payload("Placement values must be finite numbers."))
        contract_rel = str(asset.get("contract_file") or "").strip()
        if not contract_rel:
            return json.dumps(error_payload(f"{asset_id} has no contract_file."))
        library_root = Path(context.GENERATED_LIBRARY_DIR).resolve()
        contract_path = (library_root / contract_rel).resolve()
        try:
            contract_path.relative_to(library_root)
            contract = exchange.load_contract(contract_path)
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))
        importer = Exchange(context._send_and_receive, context.material_library, context.exchange_reports)
        result = importer.receive_contract(contract, x_mm, y_mm, z_mm, rotation_degrees, layer)
        if result.get("status") == "success":
            result.update({
                "library_id": "generated_assets",
                "product": asset.get("product"),
                "dimensions_mm": asset.get("dimensions_mm"),
                "clearance_mm": (asset.get("spatial") or {}).get("clearance_mm"),
                "render_material_id": asset.get("render_material_id"),
                "next_step_guide": 'Inspect the placed geometry and relevant Rhino views before concluding the placement is correct.',
            })
        return json.dumps(result)


    @public_tool(mcp, wrapped=False)
    @query_output
    def search_asset_repository(query: str = "", kind: str = "all", drawing_ready: bool = False, limit: int = 20, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> dict:
        """모델·2D 요소 아카이브 검색. 후보가 limit에서 잘리면 검색어나 유형을 좁혀 다시 조회. 원본만 있는 자산은 변환이 필요할 수 있으며 상세 정보·경로는 후보 ID로 asset_04-get tool에서 조회.

        Args:
            query: 이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.
            kind: all, element, model.
            limit: 1..100으로 보정.
            field_groups: dimensions, source, paths, drawing, metadata, audit, all.
        """
        validate_field_groups(field_groups, GROUPS)
        try:
            return project(asset_repository().search(query, kind, drawing_ready, limit), field_groups)
        except ValueError as exc:
            return project(error_payload(str(exc)), field_groups)


    def asset_repository():
        from almond_mcp.features.assets.asset_repository import AssetRepository

        return AssetRepository({
            "drawing": Path(context.DRAWING_LIBRARY_DIR),
            "drafting": Path(context.DRAFTING_LIBRARY_DIR),
            "generated": Path(context.GENERATED_LIBRARY_DIR),
        }, model_index=model_index.for_context(context))

    @mcp.resource("almond://repository/{asset_id}")
    def repository_asset_resource(asset_id: str) -> str:
        """Unified object metadata, source evidence, representations and local files."""
        repository = asset_repository()
        record = repository.records.get(asset_id)
        if not record:
            raise ValueError("Unknown repository asset ID")
        record = repository.verify_record(record)
        # HTTP URLs are relative to `almond-mcp library`; provide resolved locations
        # for MCP clients that do not have a browser server running.
        urls = {record["model"], record["preview"], record["contract"], record.get("generation_image"), record.get("source_file")}
        if record["drawing"]:
            urls.add(record["drawing"]["record"])
            for view in record["drawing"]["views"]:
                urls.update([view["svg"], view["dxf"]])
            urls.update(sheet["svg"] for sheet in record["drawing"]["sheets"])
        record["local_files"] = {url: str(repository.files[url][1]) for url in urls if url in repository.files}
        return json.dumps(record)


    return {
        "list_drawing_assets": list_drawing_assets,
        "search_drawing_assets": search_drawing_assets,
        "get_drawing_asset": get_drawing_asset,
        "_extract_drawing_asset": _extract_drawing_asset,
        "prepare_drawing_asset": prepare_drawing_asset,
        "register_drawing_asset": register_drawing_asset,
        "refresh_asset": refresh_asset,
        "list_assets": list_assets,
        "search_assets": search_assets,
        "recommend_assets": recommend_assets,
        "get_asset_passport": get_asset_passport,
        "evaluate_asset_fit": evaluate_asset_fit,
        "get_asset_sources": get_asset_sources,
        "get_asset_drawing": get_asset_drawing,
        "generate_asset_drawing_views": generate_asset_drawing_views,
        "audit_asset_drawing": audit_asset_drawing,
        "generation_sources_resource": generation_sources_resource,
        "asset_drawing_resource": asset_drawing_resource,
        "drawing_asset_view_resource": drawing_asset_view_resource,
        "asset_catalogue_resource": asset_catalogue_resource,
        "asset_passport_resource": asset_passport_resource,
        "asset_preview_resource": asset_preview_resource,
        "get_asset": get_asset,
        "_dimension_check": _dimension_check,
        "_apply_import_correction": _apply_import_correction,
        "place_drawing_asset": place_drawing_asset,
        "place_asset": place_asset,
        "search_asset_repository": search_asset_repository,
        "repository_asset_resource": repository_asset_resource,
    }
