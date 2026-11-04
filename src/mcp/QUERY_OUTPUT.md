# Public query and write responses

The public MCP query API returns feature summaries by default. `field_groups` is an explicit optional array: omitted, null and [] mean summary; selected groups add fields, and `all` restores the complete existing payload. Unknown groups fail with `invalid_arguments` before store or native work. Group selection never changes persisted records or the Python store API.

Except for planning queries described below, `include_ids` remains an independent strict boolean, default false. It enables handles in the selected records, without enabling geometry, references, steps or timestamps. Supplied target IDs are not repeated. Technical timestamps (`created_at`, `updated_at`, `observed_at`, `generated_at`) require `audit` or `all`.
Pagination, status, availability, counts and required revisions remain useful.
Errors, warnings, incomplete/unsupported work, mutation uncertainty, conflicts, reconciliation requirements and native completion/proof are never hidden by projection, ID display or timestamp preferences. Uncertain outcomes retain their full evidence and must not be retried automatically.

Feature tools project their own records. Collections keep their original envelopes, totals and pagination. A requested asset drawing manifest, parsed Grasshopper logic or helper script is intrinsically the useful payload and stays available by default. `list_library` also returns logic_names so discovery remains useful with IDs hidden. Field groups are additive: a selected optional field can be absent when the source record does not contain it.

Successful Plan/Phase/Scene writes acknowledge their needed handle, revision and counts, rather than echoing whole records, geometry or input metadata. Existing envelope names remain. Use the matching get query for details.
Component mutation acknowledgements are owned by the Component feature.

Planning update tools return changed and unsummarized per-item issues. status is success when no item was skipped (including a clean no-op), partial_success when changes and skips coexist, or no_change when skips exist but no stored value changed. Step updates also acknowledge the Step ID/status separately from the Plan status/revision. General-field validation and revision conflicts reject the entire request; typed-input errors are rejected before the tool body. Creation and unrelated write contracts remain unchanged.

## Follow-up guidance

`next_step` is conditional call guidance, not a Plan Step, an execution command or a requirement to call every named tool. It identifies the public tool and maps available response/input handles to its arguments; when IDs, paths, units or a user choice are missing, it says how to obtain or choose them. It does not imply that a prior operation succeeded or authorize a mutation.

- Default `get_rhino_context` offers current-view capture; explicit sections omit this hint.
- Whole-scope intersection counts guide positive results into `resolve_object_intersection` using the original object scope. Zero needs no resolution. Each valid comparison supplies `review_id` and numbered choices; choice 1/2 trims that object, while skip preserves both. Errors/completion do not fabricate another actionable comparison.
- Phase/Plan lists and Plan/Step details link IDs to detail/workspace selection. Saved revisions retain their historical read context and require a current read before selecting work.
- Asset records with `next_tool` keep matching `next_step` in summary output, even when IDs/paths are omitted; the hint explains those missing inputs. Ready/empty records do not invent conversion work. A source-only placement rejection carries the same conversion guidance.
- Preparation retains `next_stage` and adds its concrete tool/job/hash inputs. Final preview approval is distinct from producing previews. Errors clear the next stage; status only rereads saved evidence and does not reconcile late native completion or promote an unconfirmed job.
- Contract export maps the returned contract path to an import only when importing into a destination is intended. The Blender helper supports export/materials, not import.

Tool descriptions and input-schema property descriptions carry the same argument contract. Dynamic instructions must use current public names and survive the relevant response projection. Legacy non-public asset helper functions do not expand the MCP tool catalogue.

## Planning queries

Phase/Plan/Step discovery and related target/selection queries always expose IDs and have no `include_ids` option. `list_phases` and `list_plans` provide `next_step` call guidance. `list_plans` has no field groups: its rows contain plan_id/title/scope/status/revision.

`get_phase_plan_step` selects one Phase, Plan or Step using phase_id, plan_id and optional step_id. Its root id/type/status identifies the selected record and workflow state; target details are nested in phase/plan/step. Plan details always include scene_ids, artifact fields, KST creation/update times and Step ID/name/status summaries; include_holons=true adds Plan holon_ids. A selected Step exposes only its own input_refs/output_refs. Detail queries have no audit/field_groups option. Errors still have status=error. See [planning inputs and outputs](features/planning/README.md).

The planning field groups below apply only to list_phases, list_plan_revisions, resolve_targets and get_selection_references, according to each tool's signature; they do not change the unified detail response.

## Declared field groups

Each row names fields added to the feature's normal summary. The tool description lists the supported groups; `all` is available for every field-group query.

| Feature | Group | Added fields |
|---|---|---|
| assets | `dimensions` | `bounds_mm`, `clearance_mm`, `dimension_basis`, `dimensions_mm`, `spatial` |
| assets | `source` | `license`, `provenance`, `sha256`, `source`, `source_url`, `warehouse_url` |
| assets | `paths` | `contract`, `dimensions_path`, `file`, `generation_image`, `library_dir`, `model`, `model_path`, `package_dir`, `preview`, `preview_uri`, `source_file`, `source_path` |
| assets | `drawing` | `drawing`, `drawing_manifest`, `drawing_package`, `drawing_roles`, `lod` |
| assets | `metadata` | `description`, `material_id`, `metadata`, `passport`, `render_material_id`, `series`, `tags` |
| assets | `audit` | `created_at`, `generated_at`, `updated_at`, `verification_basis` |
| components | `references` | `child_holon_ids`, `parent_holon_id`, `rhino_group_id`, `scene_ids` |
| components | `geometry` | `bounds_mm`, `direct_object_ids`, `effective_object_ids`, `effective_objects`, `intersections`, `object_ids`, `objects`, `pairs`, `pending_objects` |
| components | `scope` | `expected_model_path`, `model_path`, `project_file_id`, `file_name` |
| components | `audit` | `created_at`, `observed_at`, `updated_at` |
| diagrams | `dimensions` | `bounds_mm`, `dimensions_mm` |
| diagrams | `drawing` | `drawing_roles`, `lod`, `projection` |
| diagrams | `metadata` | `description`, `series`, `tags` |
| diagrams | `source` | `license`, `sha256`, `source`, `source_url`, `warehouse_url` |
| diagrams | `paths` | `file`, `model_path`, `preview`, `preview_uri` |
| diagrams | `audit` | `created_at`, `updated_at` |
| drawings | `scales` | `recommended_scales`, `scales` |
| drawings | `parameters` | `annotations`, `display`, `hatches`, `layers`, `layout`, `linework`, `output`, `parameters`, `projection`, `review_preparation`, `style`, `units`, `views` |
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
| guidance | `metadata` | `description`, `notes`, `structure_types`, `tags` |
| guidance | `audit` | `created_at`, `updated_at` |
| modeling | `display` | `base_color`, `emission`, `ior`, `metallic`, `opacity`, `roughness`, `textures`, `ue_material_slot` |
| modeling | `physical` | `density`, `density_kg_m3`, `physical`, `structural_material` |
| modeling | `metadata` | `description`, `tags` |
| modeling | `source` | `license`, `provenance`, `source` |
| modeling | `paths` | `file`, `library_dir` |
| modeling | `audit` | `created_at`, `updated_at` |
| planning | `steps` | `steps` |
| planning | `references` | `child_holon_ids`, `holon_id`, `holon_ids`, `depends_on`, `input_refs`, `matched_step_ids`, `output_refs`, `parent_holon_id`, `phase_id`, `related_holon_ids`, `scene_ids` |
| planning | `geometry` | `direct_object_ids`, `effective_object_ids` |
| planning | `artifacts` | `artifact_dir`, `artifact_refs` |
| planning | `description` | `description` |
| planning | `scope` | `file_name`, `project_file_id`, `model_path`, `rhino_group_id` |
| planning | `audit` | `created_at`, `updated_at` |
| structure | `parameters` | `deflection_limit_ratio`, `imposed_floor_kn_m2`, `uls_default`, `uls_expression`, `values` |
| structure | `source` | `origin`, `source`, `sources` |
| structure | `audit` | `created_at`, `updated_at` |
| scenes | `scope` | `file_name`, `project_file_id`, `units`, `model_path` |
| scenes | `state` | `revision` |
| scenes | `geometry` | `bounds_mm`, `holon_id` |
| scenes | `audit` | `created_at`, `updated_at`, `observed_at` |

## Project Scene discovery

`list_design_scenes(name="", file_name="", limit=50, offset=0)` lists the entire project DB without Plan, live document or per-Scene geometry queries. `name` is a case-insensitive substring; `file_name` is an exact optional match. Default rows are names only. `include_ids=true` adds Scene handles, `scope` adds file_name and units, `state` adds revision and `audit` adds timestamps. One SELECT returns the bounded page and total, including an offset beyond the final row. `limit` is 1–200; offset is non-negative. `get_scene_objects` also returns a bounded page (limit 1–200, offset, total and truncated), with names/types of current semantic-group members and direct Scene objects by default, deduplicated and adjusted for exclusions. It requires complete live observations; direct membership GUIDs are stored per Scene and model. When membership overrides exist, the cached Scene object count is null because an exact deduplicated count requires a live query. Cached component queries return only group summaries with geometry_available=false. A child-only sync invalidates unobserved ancestors' effective count/bounds and sets requires_sync.

## Other bounded/query-specific contracts

- `project_info`: project/document/locations by default, optional runtime. project/document share one live observation; failed identity checks return an error, otherwise project.is_bound_document is a boolean: true for the bound model, false for a different document. Document name/path occur only in project. project.files pages the recorded DB list using files_limit (1–500, default 50) and files_offset; files_page retains total/limit/offset/truncated. Duplicate names remain distinct and include_ids=true exposes project_file_id. Document runtime_serial_number and runtime.rhinocode.pipe_id are also hidden by default. locations contains the project DB and connection-selected Plan folder (null before selection); locations/runtime alone need no live observation. Basic instructions come from get_modeling_guide.
- `get_rhino_context`: explicit document/selection/viewport/editor/display_modes sections, bounded selection expansion and optional current image.
- `analyze_block_reculviely`: outline/resolve-block mode and bounded traversal options. `resolve-block` also returns placed Model/Layout occurrence paths and counts in `definition_impact`, with separate completeness and list truncation. Definition-member IDs and matching working candidates are not document edit identities. Its `next_step` connects impact review to an intended BlockEditNew entry and fresh working-ID observation; it does not grant unsupported editor mutation permission.
- `get_defined_viewcapture`, `get_current_viewcapture`: one bounded image/file result; live-view mutation evidence is never omitted.
- `get_objects`: selected/visible/document/explicit-object/group scopes; flat objects, layer/type counts or numbered group/block hierarchy. Internal block paths are distinct from editable document IDs.
- `get_rhino_context`: requested sections only; Named View/Layout/Display Mode catalogue IDs are always included.
- `get_retrieval_status`: bounded readiness/count diagnostics.
- `get_modeling_policy`: one fixed policy document.
- `get_modeling_guide`: BASIC and public tool names; `include_scripting=true` adds bundled scripting references. Individual tool descriptions come from `tools/list`; there are no topic, tool-name or image arguments. See [guidance delivery](SPEC.md#모델링-안내-전달).
- `audit_asset_drawing`: one requested package's validation/proof result.
- `validate_structure`: its existing detail=false summary/detail=true contract.

Fresh clients derive the explicit signatures through both FastMCP and inert COS catalog generation. Existing client/worker processes need a normal session restart to load changed Python; no catalog export, Rhino rebuild or plugin registration is implied by these Python API changes.
