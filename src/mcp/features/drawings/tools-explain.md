# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
When to use: Browse available drawing recipes by purpose and projection before choosing a style.
Before calling: No prerequisite; this catalogue query does not change Rhino.
Inputs from earlier results: None required. Set include_ids=true to obtain recipe_id for get_drawing_recipe or apply_drawing_style; field_groups=["scales"] includes available recommended scales.
Interpretation: A recipe shortlist describes authored conventions, not proof that the current document follows them. Inspect the chosen recipe only if its settings are unknown.
Limits: The list does not include full layer/style settings; use get_drawing_recipe with field_groups=["parameters"] for those. Other optional groups are source, audit and all; audit enables available timestamps.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
When to use: Inspect a known drawing recipe's conventions and execution settings without modifying Rhino.
Before calling: Supply recipe_id; list recipes only when that ID is unknown.
Inputs from earlier results: Reuse recipe_id from list_drawing_recipes with include_ids=true. Request field_groups=["parameters"] for layers, style and review_preparation, or ["scales"] for scale guidance; retain the supplied ID for apply_drawing_style.
Interpretation: Default output is a compact recipe summary, not a current-document audit. Review-preparation settings describe intended follow-up, not actions already executed.
Limits: This neither applies layers nor prepares PrintDisplay. The supplied ID is not echoed; include_ids exposes other unsupplied handles. Optional source, audit and all expose available evidence, with timestamps under audit.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
When to use: Create or update the active Rhino document's layer hierarchy, plot weights, colours and linetypes from a drawing recipe.
Before calling: Use a known recipe_id or accept technical_axon_v1; fetch recipe parameters only if the intended layer changes are unknown. A connected active Rhino document is required.
Inputs from earlier results: Reuse recipe_id from list_drawing_recipes with include_ids=true; get_drawing_recipe with field_groups=["parameters"] exposes layer and review settings when needed.
Interpretation: Success confirms the layer-style operation, not a finished drawing or print review. The A4 plan/section recipe may return review_preparation with an unexecuted rhinocode template: reuse a pipe confirmed for this connection's Rhino PID and saved document path, discover only if unknown, and skip if Document-scoped Model/Layout PrintDisplay On with Print colours is already confirmed.
Limits: The tool does not inspect or change PrintDisplay. Explicit linetype_segments need positive lengths and is_solid; conflicting named patterns or malformed segments are rejected before layer changes, while matching patterns are reused. Recipes without segments retain name-based behaviour. On timeout, inspect document state before repeating changes.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
When to use: Add an indexed drawing asset's PAT hatch definitions to the active Rhino document's hatch pattern table.
Before calling: Supply an available .pat drawing asset_id and an active Rhino connection; no recipe or placement prerequisite exists.
Inputs from earlier results: Reuse asset_id from drawing asset discovery with include_ids=true. Request field_groups=["paths"] if the source extension is not known; the tool resolves the path itself.
Interpretation: Returned pattern names identify available definitions; the message distinguishes newly added patterns from already present names. Existing names are reused, not overwritten.
Limits: Only .pat files from the controlled asset/drawing/DrawingAssetfiles manifest are accepted. This imports definitions, not hatch objects or regions, and does not certify pattern appearance at a drawing scale.
<!-- /instruction:import_drawing_hatch_patterns -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
