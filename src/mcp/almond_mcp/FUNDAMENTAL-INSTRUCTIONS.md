Almond combines Rhino modelling with a semantic asset library.

Before the first Rhino action, call project_info for the bound model and artifact_dir. Use that returned directory as an explicit absolute base for task-local files in Rhino C# and later shell/image reads; Rhino TEMP may differ. Create a fresh task subdirectory when writing, report path errors instead of silently using another location, and honor explicit user input/export paths. Do not move files or save the Rhino model merely to set an output path.

For reusable objects: prepare and visually review a millimeter, Z-up, bottom-center 3DM, then register_drawing_asset. Registration derives plan/front/right DXF and SVG plus dimensions under the same asset ID. Use get_drawing_asset, get_asset_drawing and place_drawing_asset. generate_asset_drawing_views remains available for a custom static GLB; verify outputs with audit_asset_drawing.

search_detail_sources returns candidate directories, not verified construction details. Choose materials with list_materials and use assign_material; existing layers are preserved. Use setup_modeling to register library materials or create construction-system layers.

Register physical assemblies as Components: an object has at most one Component, each Component belongs to one or more Scenes, and raw objects may also link directly to a Scene. Use get_modeling_policy for keys; object names are free. Organize work as Phase > Plan > Step; Plans reference Scenes and Components, Steps may override Component targets. Resolve and inspect live targets before editing. Asset instances and Room bounds remain optional legacy placement checks; validate_scene_layout covers those cached asset instances, not all Component geometry.

Use measured dimensions, not nominal prompt targets. Usage suggestions are heuristics and clearances are design allowances, not certified code compliance.
