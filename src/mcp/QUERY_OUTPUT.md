# Public query and write responses

The public MCP query API returns feature summaries by default. `field_groups` is
an explicit optional array: omitted, null and [] mean summary; selected groups
add fields, and `all` restores the complete existing payload. Unknown groups fail
with `invalid_arguments` before store or native work. Group selection never
changes persisted records or the Python store API.

`include_ids` remains an independent strict boolean, default false. It enables
handles in the selected records, without enabling geometry, references, steps or
timestamps. Supplied target IDs are not repeated. Technical timestamps
(`created_at`, `updated_at`, `observed_at`, `generated_at`) require `audit` or `all`.
Pagination, status, availability, counts and required revisions remain useful.
Errors, warnings, incomplete/unsupported work, mutation uncertainty, conflicts,
reconciliation requirements and native completion/proof are never hidden by
projection, ID display or timestamp preferences. Uncertain outcomes retain their
full evidence and must not be retried automatically.

Feature tools project their own records. Collections keep their original
envelopes, totals and pagination. A requested asset drawing manifest, parsed
Grasshopper logic or helper script is intrinsically the useful payload and stays
available by default. `list_library` also returns logic_names so discovery remains
useful with IDs hidden. Field groups are additive: a selected optional field can
be absent when the source record does not contain it.

Successful Plan/Phase/Scene and legacy placement writes acknowledge their needed
handle, revision and counts, rather than echoing whole records, geometry or input
metadata. Existing envelope names remain. Use the matching get query for details.
Component mutation acknowledgements are owned by the Component feature.

## Declared field groups

Each row names fields added to the feature's normal summary. The tool description
lists the supported groups; `all` is available for every field-group query.

| Feature | Group | Added fields |
|---|---|---|
| assets | `dimensions` | `bounds_mm`, `clearance_mm`, `dimensions_mm`, `spatial` |
| assets | `source` | `license`, `provenance`, `sha256`, `source`, `source_url`, `warehouse_url` |
| assets | `paths` | `contract`, `dimensions_path`, `file`, `generation_image`, `library_dir`, `model`, `model_path`, `package_dir`, `preview`, `preview_uri` |
| assets | `drawing` | `drawing`, `drawing_manifest`, `drawing_package`, `drawing_roles`, `lod` |
| assets | `metadata` | `description`, `material_id`, `passport`, `render_material_id`, `series`, `tags` |
| assets | `audit` | `created_at`, `generated_at`, `updated_at` |
| components | `references` | `child_component_ids`, `parent_component_id`, `rhino_group_id`, `scene_ids` |
| components | `geometry` | `bounds_mm`, `direct_object_ids`, `effective_object_ids`, `effective_objects`, `intersections`, `object_ids`, `objects`, `pairs`, `pending_objects` |
| components | `scope` | `expected_model_path`, `model_path` |
| components | `audit` | `created_at`, `observed_at`, `updated_at` |
| diagrams | `dimensions` | `bounds_mm`, `dimensions_mm` |
| diagrams | `drawing` | `drawing_roles`, `lod`, `projection` |
| diagrams | `metadata` | `description`, `series`, `tags` |
| diagrams | `source` | `license`, `sha256`, `source`, `source_url`, `warehouse_url` |
| diagrams | `paths` | `file`, `model_path`, `preview`, `preview_uri` |
| diagrams | `audit` | `created_at`, `updated_at` |
| drawings | `scales` | `recommended_scales`, `scales` |
| drawings | `parameters` | `annotations`, `display`, `hatches`, `layers`, `layout`, `linework`, `output`, `parameters`, `projection`, `style`, `units`, `views` |
| drawings | `source` | `license`, `references`, `source` |
| drawings | `audit` | `created_at`, `updated_at` |
| exchange | `notes` | `note` |
| exchange | `audit` | `created_at`, `updated_at` |
| grasshopper | `ports` | `input_ports`, `inputs`, `output_ports`, `outputs` |
| grasshopper | `definition` | `all_descriptions`, `components`, `definition`, `definition_file`, `metadata` |
| grasshopper | `source` | `license`, `provenance`, `source`, `source_url` |
| grasshopper | `paths` | `capsule_library_dir`, `definition_file`, `file_name`, `library_dir` |
| grasshopper | `audit` | `audit`, `audit_status`, `created_at`, `sha256`, `updated_at` |
| guidance | `rules` | `construction_detail`, `construction_notes`, `construction_reference`, `depth_guidance`, `depth_rules`, `elements`, `render_material_ids`, `span_axis`, `span_range_m`, `typical_spacing_m` |
| guidance | `narrative` | `narrative`, `precedents`, `related_construction_systems`, `urban_role` |
| guidance | `source` | `access`, `bci_ref`, `formats`, `gha_ref`, `license`, `reference`, `source`, `url`, `urls` |
| guidance | `metadata` | `description`, `matched_terms`, `notes`, `structure_types`, `tags` |
| guidance | `audit` | `created_at`, `updated_at` |
| modeling | `display` | `base_color`, `emission`, `ior`, `metallic`, `opacity`, `roughness`, `textures`, `ue_material_slot` |
| modeling | `physical` | `density`, `density_kg_m3`, `physical`, `structural_material` |
| modeling | `metadata` | `description`, `tags` |
| modeling | `source` | `license`, `provenance`, `source` |
| modeling | `paths` | `file`, `library_dir` |
| modeling | `audit` | `created_at`, `updated_at` |
| planning | `steps` | `steps` |
| planning | `references` | `component_ids`, `components`, `depends_on`, `input_refs`, `matched_step_ids`, `objects`, `output_refs`, `phase_id`, `scene_ids` |
| planning | `artifacts` | `artifact_dir`, `artifact_refs` |
| planning | `description` | `description` |
| planning | `scope` | `file_name`, `model_path`, `rhino_group_id` |
| planning | `audit` | `created_at`, `updated_at` |
| structure | `parameters` | `deflection_limit_ratio`, `imposed_floor_kn_m2`, `uls_default`, `uls_expression`, `values` |
| structure | `source` | `origin`, `source`, `sources` |
| structure | `audit` | `created_at`, `updated_at` |

| scenes | `scope`, `state`, `geometry`, `audit` | file_name/units/model_path; revision; bounds_mm/component_id; timestamps |
| placement validation | `details` | collisions, outside_room (bounded by detail_limit) |

## Project Scene discovery

`list_design_scenes(name="", file_name="", limit=50, offset=0)` lists the entire
project DB without Plan, live document or per-Scene geometry queries. `name` is a
case-insensitive substring; `file_name` is an exact optional match. Default rows
are names only. `include_ids=true` adds Scene handles, `scope` adds file_name and
units, `state` adds revision and `audit` adds timestamps. One SELECT returns the
bounded page and total, including an offset beyond the final row. `limit` is
1–200; offset is non-negative. `get_scene_objects` also returns a bounded page
(limit 1–200, offset, total and truncated), with cached object type/directness by
default and optional geometry, scope or audit.

## Other bounded/query-specific contracts

- `project_info`: explicit project/document/artifacts/runtime/instructions sections.
- `get_rhino_context`: explicit document/selection/viewport sections and selection_limit.
- `get_rhino_probe`: named probe and validated options/limits.
- `get_rhino_viewport_image`: one bounded image/result for the selected view.
- `get_retrieval_status`: bounded readiness/count diagnostics.
- `get_modeling_policy`: one fixed policy document.
- `get_modeling_guide`: one named topic, with optional images.
- `audit_asset_drawing`: one requested package's validation/proof result.
- `validate_structure`: its existing detail=false summary/detail=true contract.

Fresh clients derive the explicit signatures through both FastMCP and inert COS
catalog generation. Existing client/worker processes need a normal session restart
to load changed Python; no catalog export, Rhino rebuild or plugin registration
is implied by these Python API changes.
