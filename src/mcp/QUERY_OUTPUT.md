# Public query and write responses

The [authored declarations](../../TOOL-DECLARATIONS-CURRENT.md) specify each tool’s inputs, result fields and follow-up calls. `tools/list` publishes the declarations for the current connection. Structured results return a JSON object. A `JsonResult` puts JSON text in `structuredContent.result`, with the decoded shape declared in `contentSchema`. Image results can also carry separate image and usage blocks. Public schema projection leaves the remaining keys and values intact in open fields such as a script’s `result` or an asset `manifest`.

## Field selection

Where a tool accepts `field_groups`, an empty array selects the summary. Named groups add available fields and `all` selects all supported groups. Omission uses the tool’s documented default. For example, `asset_07-prepare` tool includes previews by default. `include_ids` controls optional IDs where offered. Discovery keys such as Scene IDs in `scene_07-list` tool and view IDs in `inspect_03-get_document_context` tool are always available. Detail queries can omit the ID used to select that record. In group-based queries, audit timestamps are available through `audit` or `all` where supported.

Check the returned status, completeness and mutation evidence before acting on a result. Required reconciliation can follow a successful write with a lost acknowledgement. An uncertain operation calls for observation or receipt lookup before retry.

## Planning queries and writes

- `plan_05-get` tool returns `type`, `name`, `status` and the target’s `phase_id`, `plan_id` or `step_id`. Plan and Step also identify the Plan, Loop and revision. `include_details=true` adds the matching `phase`, `plan` or `step` body. Use the same `loop_no` and `revision` when opening a read-only record in more detail.
- `plan_08-list` tool takes `request.target` of `phase`, `plan` or `step`. The Step page and `loop_no`, `revision` and `read_only` come from one Plan snapshot. Select a Step to work on with `plan_10-set_working` tool. After starting or resuming a Loop with `plan_03-execute_looping` tool, pass its `next_step_id` to select the next unfinished Step.
- `plan_12-update` tool returns `updated` when changes were applied, `partial_success` when changes and skips coexist, and `no_change` when values stay the same. `changed` and `issues` report stored changes and skipped items. A Step update also returns its Plan’s revision. The `cleanup_state` and `requires_reconciliation` fields describe failure to confirm the Rhino follow-up after completion.

See [planning inputs and outputs](features/planning/README.md).

## Project and Scene discovery

- `context_04-get_project_info` tool reads the document, layer tree, Named Views, Layouts and project locations by default. `project.files_page` returns `total` and `offset` for the separate registered file catalog. Advance the offset by the number of returned `project.files` rows. `worksession_files` lists paths attached in Rhino. `include_ids=true` also returns the document’s `runtime_serial_number`, selected Plan and Step IDs, and RhinoCode `pipe_id` when their sections are requested. Requesting only `locations` or `runtime` skips document observation.
- `scene_07-list` tool returns paged project Scene IDs and names, with file, revision and time fields available through the corresponding groups. `scene_06-get_objects` tool pages the observed members of a Scene in the connected document, including direct objects and Holon members after exclusions. Both return `total` and `truncated`. For a cached Scene with membership overrides, `scene_04-get` tool returns `objects: null`. Read live group membership with `scene_05-get_holon` tool and `live=true`. Its `requires_sync` identifies a mismatch with the stored registration.

## Other bounded queries and follow-up calls

- `inspect_03-get_document_context` tool returns the requested document, viewport, editor, layer or view-catalog sections. Named Views, Layouts and display modes always carry IDs. `inspect_02-get_objects` tool returns object rows, counts or a hierarchy. For a subsequent object page use `next_offset` and pass `snapshot` as `expected_snapshot`. Use fresh top-level object identities and `geometry_crc` for face edits.
- `inspect_01-analyze_nested_blocks` tool returns `definition_impact` with Model/Layout occurrence paths and counts in `resolve-block` mode. It reports traversal completeness and occurrence truncation separately. Inspect working objects after entering the correct block edit scope before attempting an edit.
- With a positive confirmed count from `intersect_01-find` tool, pass the same object scope to `intersect_02-resolve` tool to review comparisons. Submit the current `review_id` and choice 1 or 2 to remove the overlap from that object, or `skip` to keep both. `previous_result` records the last edit when the next comparison fails.
- Asset queries can return `next_tool` when conversion or refresh is needed. A rejected source-only placement uses `asset_07-prepare` tool. Preparation reports distinct `status` and `state`, with `next_stage` indicating a verification step when applicable. Request `stage="status"` to reread stored evidence. Register the reviewed `source_3dm` when `state="ready"`.
- `script_03-get_execution` tool reads the retained receipt using the execution’s `request_id`. It pages results and logs. `diagnostics` includes available log capture limits and read errors when logs are requested and the recorded target when recovering from a retained connection. `include_diagnostics=true` adds CLI, Undo and invocation evidence for normal completions.
