"""Public MCP names and their stable internal operation identifiers.

Registration uses literal public names so schema discovery remains inert.
Internal Python/native/DB contracts keep their existing identifiers; this map
is only used where public calls enter execution policy or descriptions.
"""
import re

PUBLIC_TOOL_NAMES = {
    'list_connections': 'connect_01-list_up',
    'connect': 'connect_02-session',
    'start_session': 'connect_03-start_session',
    'disconnect': 'connect_04-disconnect',
    'close_session': 'connect_05-close_session',
    'project_info': 'context_04-get_project_info',
    'get_policy': 'context_01-get_policy',
    'create_phase': 'plan_01-create_phase',
    'create_plan': 'plan_02-create',
    'execute_looping': 'plan_03-execute_looping',
    'get_phase_plan_step': 'plan_05-get_phase_plan_step',
    'list_phases': 'plan_06-list_phases',
    'list_plan_revisions': 'plan_07-list_revisions',
    'list_plans': 'plan_08-list',
    'rename_artifact_folder': 'plan_09-rename_artifact_folder',
    'set_working_plan': 'plan_10-set_working',
    'update_phase': 'plan_11-update_phase',
    'update_plan': 'plan_12-update',
    'update_step': 'plan_13-update_step',
    'analyze_block_reculviely': 'inspect_01-analyze_nested_blocks',
    'get_objects': 'inspect_02-get_objects',
    'get_rhino_context': 'inspect_03-get_document_context',
    'get_selection_references': 'inspect_04-get_selection_references',
    'resolve_targets': 'inspect_05-resolve_targets',
    'capture_conditioning_pass': 'capture_01-conditioning_pass',
    'capture_rhino_inspection': 'capture_02-inspection',
    'get_current_viewcapture': 'capture_03-current_view',
    'get_defined_viewcapture': 'capture_04-defined_view',
    'assign_material': 'model_01-assign_material',
    'edit_planar_face': 'model_02-edit_planar_face',
    'edit_planar_faces': 'model_03-edit_planar_faces',
    'list_materials': 'model_04-list_materials',
    'setup_modeling': 'model_05-setup',
    'execute_project_python': 'script_01-run_project_python',
    'execute_rhino_script': 'script_02-run_rhino',
    'get_rhino_execution': 'script_03-get_execution',
    'save_rhino_document': 'script_04-save_document',
    'add_scene_objects': 'scene_01-add_objects',
    'create_design_scene': 'scene_02-create',
    'focus_holons': 'scene_03-focus_holons',
    'get_design_scene': 'scene_04-get',
    'get_ontological_holon': 'scene_05-get_holon',
    'get_scene_objects': 'scene_06-get_objects',
    'list_design_scenes': 'scene_07-list',
    'list_ontological_holons': 'scene_08-list_holons',
    'remove_ontological_holon': 'scene_09-remove_holon',
    'remove_scene_objects': 'scene_10-remove_objects',
    'sync_ontological_holon': 'scene_11-sync_holon',
    'update_design_scene': 'scene_12-update',
    'upsert_ontological_holon': 'scene_13-upsert_holon',
    'get_object_intersections': 'intersect_01-find',
    'resolve_object_intersection': 'intersect_02-resolve',
    'audit_asset_drawing': 'asset_01-audit_drawing',
    'generate_asset_drawing_views': 'asset_02-generate_drawing_views',
    'get_asset_drawing': 'asset_03-get_drawings',
    'get_drawing_asset': 'asset_04-get',
    'list_drawing_assets': 'asset_05-list',
    'place_drawing_asset': 'asset_06-place',
    'prepare_drawing_asset': 'asset_07-prepare',
    'refresh_asset': 'asset_08-refresh',
    'register_drawing_asset': 'asset_09-register',
    'search_asset_repository': 'asset_10-search_repository',
    'search_drawing_assets': 'asset_11-search',
    'get_diagram_asset': 'diagram_01-get',
    'list_diagram_assets': 'diagram_02-list',
    'place_diagram_asset': 'diagram_03-place',
    'search_diagram_assets': 'diagram_04-search',
    'apply_drawing_style': 'drawing_01-apply_style',
    'get_drawing_recipe': 'drawing_02-get_recipe',
    'get_plan_section_result': 'drawing_03-get_plan_section_result',
    'import_drawing_hatch_patterns': 'drawing_04-import_hatches',
    'list_drawing_recipes': 'drawing_05-list_recipes',
    'plan_section': 'drawing_06-generate_plan_section',
    'get_logic_by_id': 'grasshopper_01-get_logic',
    'list_capsules': 'grasshopper_02-list_capsules',
    'list_library': 'grasshopper_03-list_library',
    'run_gh_definition': 'grasshopper_04-run_definition',
    'get_construction_guidance': 'research_01-get_construction_guidance',
    'get_typology_narrative': 'research_02-get_typology_narrative',
    'search_detail_sources': 'research_03-search_details',
    'check_egress': 'analysis_01-check_egress',
    'export_structural_report': 'analysis_02-export_structural_report',
    'list_design_codes': 'analysis_03-list_design_codes',
    'validate_structure': 'analysis_04-validate_structure',
    'visualize_structure': 'analysis_05-visualize_structure',
    'export_asset_contract': 'exchange_01-export_asset_contract',
    'get_blender_helper_script': 'exchange_02-get_blender_script',
    'import_asset_contract': 'exchange_03-import_asset_contract',
    'publish_objects_to_chestnut': 'exchange_04-publish_chestnut_advanced',
    'publish_to_chestnut': 'exchange_05-publish_chestnut',
}
INTERNAL_TOOL_NAMES = {public: internal for internal, public in PUBLIC_TOOL_NAMES.items()}


def internal_tool_name(name: str) -> str:
    """Resolve an execution-policy key, never register a compatibility alias."""
    return INTERNAL_TOOL_NAMES.get(name, name)


def public_tool_name(name: str) -> str:
    return PUBLIC_TOOL_NAMES.get(name, name)


_REFERENCE = re.compile(r"(?<![A-Za-z0-9_-])(" + "|".join(
    sorted(map(re.escape, PUBLIC_TOOL_NAMES), key=len, reverse=True)) + r")(?![A-Za-z0-9_-])")


def tool_references(text: str) -> str:
    """Render authored tool references, never apply this to arbitrary user data."""
    return _REFERENCE.sub(lambda match: public_tool_name(match[0]) + " tool", text)
