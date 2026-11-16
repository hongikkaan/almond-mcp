"""Project discovery for an explicitly selected Rhino connection."""
import sys
from pathlib import Path

from almond_mcp.features.context.context_query import (
    DISCOVERY_SECTIONS,
    document_metadata,
    observe,
    project_discovery_section,
)
from almond_mcp.managed_paths import relative_output, relative_path
from almond_mcp.query_output import project_query


DEFAULT_SECTIONS = ("project", *DISCOVERY_SECTIONS, "locations")
SECTIONS = (*DEFAULT_SECTIONS, "runtime")


def query_project_info(sections, include_ids, files_limit, files_offset, *,
                       verify_binding, binding, locations, sender, runtime):
    sections = list(DEFAULT_SECTIONS) if sections is None else sections
    if not isinstance(sections, list) or any(section not in SECTIONS for section in sections):
        raise ValueError("sections must contain " + ", ".join(SECTIONS) + ".")
    if type(files_limit) is not int or not 1 <= files_limit <= 500 or type(files_offset) is not int or files_offset < 0:
        raise ValueError("files_limit must be 1–500 and files_offset must be nonnegative integers.")
    verify_binding()
    result = {"status": "success"}
    root = locations["project_dir"]
    observation_sections = [section for section in DISCOVERY_SECTIONS
                            if section in sections or (section == "document" and "project" in sections)]
    if "project" in sections:
        observation_sections.append("worksession_files")
    live = {}
    warnings = []
    if observation_sections:
        if sender is None:
            raise RuntimeError("The live document observer is not connected.")
        live = observe(sender, observation_sections, selection_limit=0)
        if not isinstance(live, dict):
            return {"status": "error", "message": "The live document observation is incomplete."}
        document = live.get("document")
        missing_identity = "document" in observation_sections and (
            not isinstance(document, dict) or not isinstance(document.get("path"), str))
        if live.get("status") != "success" or missing_identity:
            evidence = {key: value for key, value in live.items()
                        if key not in (*DISCOVERY_SECTIONS[1:], "worksession_files")}
            return relative_output({**evidence, "status": "error",
                "message": live.get("message") or "The live document observation is incomplete."})
        warnings.extend(live.get("warnings") or [])
    if "project" in sections:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        page = runtime.workspace.store.list_project_files(files_limit, files_offset)
        path = document["path"]
        is_bound_document = bool(path and Path(path).resolve() == Path(locations["model_path"]).resolve())
        attachments = live.get("worksession_files")
        worksession_files = None
        if isinstance(attachments, list) and all(
            isinstance(row, dict) and isinstance(row.get("file_name"), str)
            and isinstance(row.get("file_path"), str) for row in attachments
        ):
            worksession_files = [{"file_name": row["file_name"],
                "file_path": relative_path(row["file_path"], root, preserve_cross_drive=True)}
                for row in attachments]
        elif not any(str(warning).startswith("worksession_files:") for warning in warnings):
            warnings.append("worksession_files: Rhino did not return the attachment list.")
        result["project"] = {"project_root": root, "file_name": document.get("name"),
            "file_path": relative_path(path, root),
            "is_bound_document": is_bound_document,
            "files": page["files"],
            "worksession_files": worksession_files,
            "files_page": {key: page[key] for key in ("total", "limit", "offset", "truncated")}}
    if "document" in sections:
        result["document"] = document_metadata(document, angle_key="angle_tolerance_radians")
        if include_ids and "runtime_serial_number" in document:
            result["document"]["runtime_serial_number"] = document["runtime_serial_number"]
    for section in observation_sections:
        if section not in ("document", "worksession_files"):
            result[section] = project_discovery_section(section, live.get(section), warnings)
    if warnings:
        result["warnings"] = warnings
    if "locations" in sections:
        work = runtime.workspace.current() if runtime and runtime.workspace else {"artifact_dir": ""}
        result["locations"] = project_query({**work, "artifact_dir": work["artifact_dir"] or None}, include_ids=include_ids)
        result["locations"].update(database=relative_path(locations["state_db"], root),
            path_rule="Managed tools apply ALMOND_PROJECT_ROOT automatically; pass relative paths.",
            artifact_rule="Select a Plan with plan_10-set_working tool; managed outputs use its current Loop folder .almond/produced/YYMMDD_name/01, /02, etc.; before plan_03-execute_looping tool they use the Plan root.")
    if "runtime" in sections:
        result["runtime"] = relative_output({"slot": binding["label"], "port": binding["port"],
            "session_dir": locations["session_dir"], "scratch_root": str(Path(locations["temp"]) / "python"),
            "rhino_temp_at_attach": binding.get("rhino_temp"),
            "rhino_temp_note": "Rhino process TEMP at attach, not the artifact folder.",
            "python_executable": sys.executable, "attachment": binding.get("attachment", "external")})
        if runtime is not None:
            result["runtime"]["rhinocode"] = runtime.rhinocode_availability()
        result["runtime"] = project_query(result["runtime"], include_ids=include_ids)
    result["next_step_guide"] = ("- plan_08-list tool에 request.target='plan'으로 프로젝트 진행상황을 조회합니다.\n"
                                 "- 산출물 작업 공간은 plan_10-set_working tool으로 선택합니다.\n"
                                 "- 객체 상태가 필요하면 inspect_02-get_objects tool로 확인합니다.")
    return result
