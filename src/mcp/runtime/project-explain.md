# project.py explain

`project_paths` and `connection_paths` normally require an existing saved local `.3dm`. Their internal `recovery=True` option resolves the original absolute locator after that model file was renamed or deleted. This option is read only:
combining it with `create=True` is rejected before writing any folder or file.
Local-drive, canonical-path, model-extension and storage/link checks still apply.
The recovery reader also verifies the retained ready and execution identities; this option never attaches to a missing model or starts a worker. It does not search for a moved project directory or recreate removed session evidence.
