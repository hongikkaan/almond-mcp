"""Read canonical Holon tables without a persistent compatibility view.

Native/store field names remain stable; public_contract exposes Holon names.
This SQL is static application text, never supplied by a caller.
"""

HOLON_READ_SQL = """SELECT
        c.ontological_id AS component_id,l.model_path,c.project_file_id,f.file_name,c.rhino_group_id,c.name,
        c.created_at,c.updated_at,c.parent_ontological_id AS parent_component_id,c.availability,
        (SELECT json_group_array(scene_id) FROM (SELECT scene_id FROM ontological_scene_context
            WHERE ontological_id=c.ontological_id ORDER BY scene_id)) AS scene_ids_json,
        c.geometry_digest,c.object_count,c.effective_object_count,c.effective_summary_stale,c.object_types_json,c.bounds_json
        FROM ontological_holons c JOIN project_files f ON f.file_id=c.project_file_id
        LEFT JOIN _project_file_locations l ON l.file_id=c.project_file_id"""
