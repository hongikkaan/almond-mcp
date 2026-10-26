"""Plan-owned artifact folders and their current references in the shared store."""
from datetime import datetime
import json
from pathlib import Path
import re

from almond_mcp.managed_paths import project_path, relative_path
from project import read_json, write_json


def folder_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("artifact_name must be a nonempty folder name.")
    name = name.strip()
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith((".", " ")) or name in {".", ".."}:
        raise ValueError("artifact_name must be one Windows folder name, not a path.")
    # All runtime hosts are local Windows processes using the user's local date.
    return name if re.match(r"^\d{6}_", name) else datetime.now().strftime("%y%m%d_") + name


class Workspace:
    def __init__(self, locations: dict, store):
        self.locations, self.store = locations, store
        self.root = Path(locations["project_dir"])
        self.state_path = Path(locations["session_dir"]) / "work.json"

    def current(self) -> dict:
        try:
            state = read_json(self.state_path)
        except FileNotFoundError:
            return {"plan_id": "", "step_id": "", "artifact_dir": ""}
        plan = self.store.get_plan(state["plan_id"])
        if plan is None:
            raise ValueError("The selected Plan no longer exists.")
        return {"plan_id": state["plan_id"], "step_id": state.get("step_id", ""),
                "artifact_dir": plan["artifact_dir"]}

    def artifact_path(self) -> Path:
        value = self.current()["artifact_dir"]
        if not value:
            raise ValueError("Select a Plan with set_working_plan before writing artifacts.")
        return project_path(value, base=self.root)

    def select(self, plan_id: str, step_id: str = "", artifact_name: str = "") -> dict:
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            plan = self.store._read_generation_plan(db, plan_id)
            if plan is None:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            if step_id and not any(step["step_id"] == step_id for step in plan["steps"]):
                raise KeyError(f"Unknown step_id: {step_id}")
            directory = plan["artifact_dir"]
            if not directory:
                label = artifact_name or re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', plan["goal"])[:60].strip('. ') or "work"
                directory = "tmp/" + folder_name(label)
                existing = db.execute("SELECT 1 FROM generation_plans WHERE artifact_dir = ?", (directory,)).fetchone()
                if existing or project_path(directory, base=self.root).exists():
                    if artifact_name:
                        raise ValueError("That artifact folder is already in use; choose another name.")
                    directory += "_" + plan_id.removeprefix("plan_")
                if project_path(directory, base=self.root).exists():
                    raise ValueError("The artifact folder already exists and is not owned by this Plan.")
                db.execute("UPDATE generation_plans SET artifact_dir = ? WHERE plan_id = ?", (directory, plan_id))
                self.store._record_generation_revision(db, plan_id, "set_artifact_dir")
            elif artifact_name and directory != "tmp/" + folder_name(artifact_name):
                raise ValueError("This Plan already owns an artifact folder. Use rename_artifact_folder to rename it.")
        # Selection is connection-local; the folder and refs are shared Plan data.
        write_json(self.state_path, {"plan_id": plan_id, "step_id": step_id})
        return self.current()

    def rename(self, name: str, plan_id: str = "") -> dict:
        plan_id = plan_id or self.current()["plan_id"]
        destination = "tmp/" + folder_name(name)
        moved = False
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            plan = self.store._read_generation_plan(db, plan_id)
            if not plan or not plan["artifact_dir"]:
                raise ValueError("Select an existing Plan artifact folder before renaming it.")
            original = plan["artifact_dir"]
            source, target = project_path(original, base=self.root), project_path(destination, base=self.root)
            if source == target:
                return {"artifact_dir": original}
            if target.exists() or db.execute("SELECT 1 FROM generation_plans WHERE artifact_dir = ?", (destination,)).fetchone():
                raise ValueError("The target artifact folder already exists or belongs to another Plan.")
            if source.parent != self.root.resolve() / "tmp":
                raise ValueError("Only a directly owned project tmp folder can be renamed.")

            def rewrite(ref):
                value = relative_path(ref, str(self.root)).replace("\\", "/")
                return destination + value[len(original):] if value == original or value.startswith(original + "/") else ref

            try:
                if source.exists():
                    source.rename(target)
                    moved = True
                for row in db.execute("SELECT plan_id FROM generation_plans").fetchall():
                    current = self.store._read_generation_plan(db, row["plan_id"])
                    refs = [rewrite(ref) for ref in current["artifact_refs"]]
                    changed = current["plan_id"] == plan_id or refs != current["artifact_refs"]
                    db.execute("UPDATE generation_plans SET artifact_refs_json = ?, artifact_dir = ? WHERE plan_id = ?",
                               (json.dumps(refs), destination if current["plan_id"] == plan_id else current["artifact_dir"], current["plan_id"]))
                    for step in current["steps"]:
                        inputs, outputs = [rewrite(ref) for ref in step["input_refs"]], [rewrite(ref) for ref in step["output_refs"]]
                        if (inputs, outputs) != (step["input_refs"], step["output_refs"]):
                            changed = True
                            db.execute("UPDATE generation_plan_steps SET input_refs_json = ?, output_refs_json = ? WHERE plan_id = ? AND step_id = ?",
                                       (json.dumps(inputs), json.dumps(outputs), current["plan_id"], step["step_id"]))
                    if changed:
                        self.store._record_generation_revision(db, current["plan_id"], "rename_artifact_folder")
                db.commit()
            except BaseException:
                db.rollback()
                if moved:
                    target.rename(source)
                raise
        return {"artifact_dir": destination, "previous_artifact_dir": original}
