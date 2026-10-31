# project.py explain

`project_paths` and `connection_paths` normally require an existing saved local `.3dm`. Their internal `recovery=True` option resolves the original absolute locator after that model file was renamed or deleted. This option is read only:
combining it with `create=True` is rejected before writing any folder or file.
Local-drive, canonical-path, model-extension and storage/link checks still apply.
The recovery reader also verifies the retained ready and execution identities; this option never attaches to a missing model or starts a worker. It does not search for a moved project directory or recreate removed session evidence.

## response-107

<!-- instruction:response-107 -->
The bound Rhino process ended or its PID was reused. Reconnect.
<!-- /instruction:response-107 -->

## response-108

<!-- instruction:response-108 -->
Connection binding changed. Close this Codex and restart the slot.
<!-- /instruction:response-108 -->

## response-109

<!-- instruction:response-109 -->
Rhino document connection ended or changed. Exit Codex and reconnect with almond.
<!-- /instruction:response-109 -->

## response-111

<!-- instruction:response-111 -->
Use a local drive, not a network share, for the model and its SQLite DB.
<!-- /instruction:response-111 -->

## response-120

<!-- instruction:response-120 -->
Model and .almond folder do not match. Restart the connection.
<!-- /instruction:response-120 -->
