# mcp_server.py explain

## project_info

<!-- instruction:project_info -->
Read the bound model, DB, artifact_dir and Almond usage instructions before the first Rhino action.

Use artifact_dir as the explicit absolute base for task-local reports,
screenshots and temporary code, including C# executed inside Rhino and
shell/image reads. mcp_temp/effective_temp belong to Python; Rhino's original
TEMP (rhino_temp_at_attach) may differ and is not the project output path.
This is binding metadata, not a live active-document check. For a terminal
connection, use /exit, switch the saved document, then almond to reconnect.
<!-- /instruction:project_info -->

## response-90

<!-- instruction:response-90 -->
This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.
<!-- /instruction:response-90 -->

## response-92

<!-- instruction:response-92 -->
Do not connect this model to another project database.
<!-- /instruction:response-92 -->

## response-96

<!-- instruction:response-96 -->
Connection changed. Exit Codex and reconnect with almond.
<!-- /instruction:response-96 -->

## response-97

<!-- instruction:response-97 -->
Use artifact_dir explicitly in Rhino C# and shell file paths; do not infer it from Rhino TEMP or an old global scratch folder.
<!-- /instruction:response-97 -->
