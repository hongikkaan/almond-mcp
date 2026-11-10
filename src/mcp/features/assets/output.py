"""Drawing/repository shortlist fields and explicit detail groups."""
from almond_mcp.query_output import select_fields, select_records, requires_full_evidence


CORE = {"asset_id", "id", "name", "product", "variant", "category", "kind", "file_available",
        "drawing_ready", "drawing_status", "ready", "available", "format", "match_status",
        "asset_kind", "model_status", "source_only", "source_available", "next_tool", "next_step_guide", "conversion_target", "verification_issue"}
GROUPS = {
    "dimensions": {"dimensions_mm", "dimension_basis", "bounds_mm", "spatial", "clearance_mm"},
    "source": {"source", "source_url", "warehouse_url", "license", "provenance", "sha256"},
    "paths": {"file", "model", "preview", "contract", "generation_image", "model_path", "preview_uri",
              "package_dir", "dimensions_path", "library_dir", "source_path", "source_file"},
    "drawing": {"drawing", "drawing_roles", "lod", "drawing_package", "drawing_manifest"},
    "metadata": {"metadata", "description", "tags", "series", "material_id", "render_material_id", "passport"},
    "audit": {"created_at", "updated_at", "generated_at", "verification_basis"},
}


def with_next_step(record: dict) -> dict:
    """Explain existing readiness hints without choosing an asset or hiding missing inputs."""
    tool = record.get("next_tool")
    if tool not in {"prepare_drawing_asset", "refresh_asset"}:
        return record
    if tool == "refresh_asset":
        hint = "원본의 저장된 변경을 반영하려면 조회에 사용한 asset_id로 refresh_asset을 호출합니다."
    else:
        hint = ("get_drawing_asset(field_groups=['paths'])로 원본 경로를 확인하고, "
                "Plan을 선택한 뒤 prepare_drawing_asset(stage='inspect')의 source_file에 프로젝트 기준 경로를 넣고 원본 단위를 입력합니다.")
    return {**record, "next_step_guide": hint}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("asset", "assets"):
        if key in result:
            records = result[key]
            records = [with_next_step(item) for item in records] if isinstance(records, list) else with_next_step(records)
            result[key] = select_records(records, groups, CORE, GROUPS)
    # get_asset_drawing's manifest and URI are the requested, intrinsically bounded payload.
    return select_fields(result, groups,
        {"status", "library_id", "purpose", "asset", "assets", "total", "limit", "offset",
         "truncated", "has_more", "manifest", "plan_svg_uri", "asset_id", "hint"}, GROUPS)
