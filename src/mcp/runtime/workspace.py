"""Plan-owned artifact folders and their current references in the shared store."""
from datetime import datetime
import json
import ntpath
from pathlib import Path
import re

from almond_mcp.managed_paths import project_path, relative_path
from almond_mcp.instruction_text import read_instruction
from project import read_json, write_json


ARTIFACT_ROOT = ".almond/produced"


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
        selected = state.get("loop_no", 0)
        current = plan["loop_no"]
        if selected != current:
            plan = self.store.get_plan(state["plan_id"], loop_no=selected)
            if plan is None:
                raise ValueError("The selected Loop no longer exists; select current work again.")
        return {"plan_id": state["plan_id"], "step_id": state.get("step_id", ""),
                "loop_no": selected, "read_only": selected != current,
                "plan_artifact_dir": plan["artifact_dir"], "artifact_dir": plan["loop_artifact_dir"]}

    def artifact_path(self) -> Path:
        work = self.current()
        if work.get("read_only"):
            raise ValueError("The selected Loop is now read-only. Select the current Loop before writing artifacts.")
        value = work["artifact_dir"]
        if not value:
            raise ValueError("Select a Plan with plan_10-set_working tool before writing artifacts.")
        self._artifact_path(work["plan_artifact_dir"])
        return project_path(value, base=self.root)

    def _artifact_path(self, value: str) -> Path:
        target = project_path(value, base=self.root)
        if target.parent != project_path(ARTIFACT_ROOT, base=self.root):
            raise ValueError("Plan artifacts must be under .almond/produced. "
                             "Use plan_09-rename_artifact_folder tool with this Plan ID to migrate its legacy folder.")
        return target

    def select(self, plan_id: str, step_id: str = "", artifact_name: str = "", loop_no: int | None = None) -> dict:
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            plan = self.store._read_generation_plan(db, plan_id)
            if plan is None:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            self.store._check_current_loop(plan, loop_no)
            if step_id and not any(step["step_id"] == step_id for step in plan["steps"]):
                raise KeyError(f"Unknown step_id: {step_id}")
            directory = plan["artifact_dir"]
            if not directory:
                label = artifact_name or re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', plan["goal"])[:60].strip('. ') or "work"
                directory = ARTIFACT_ROOT + "/" + folder_name(label)
                existing = db.execute("SELECT 1 FROM generation_plans WHERE artifact_dir = ? COLLATE NOCASE", (directory,)).fetchone()
                if existing or project_path(directory, base=self.root).exists():
                    if artifact_name:
                        raise ValueError("That artifact folder is already in use; choose another name.")
                    directory += "_" + plan_id.removeprefix("plan_")
                if project_path(directory, base=self.root).exists():
                    raise ValueError("The artifact folder already exists and is not owned by this Plan.")
                db.execute("UPDATE generation_plans SET artifact_dir = ? WHERE plan_id = ?", (directory, plan_id))
                plan = self.store._record_generation_revision(db, plan_id, "set_artifact_dir")
            else:
                self._artifact_path(directory)
                if artifact_name and directory != ARTIFACT_ROOT + "/" + folder_name(artifact_name):
                    raise ValueError("This Plan already owns an artifact folder. Use plan_09-rename_artifact_folder tool to rename it.")
        # Selection is connection-local; the folder and refs are shared Plan data.
        write_json(self.state_path, {"plan_id": plan_id, "step_id": step_id, "loop_no": plan["loop_no"]})
        return {"plan_id": plan_id, "step_id": step_id, "loop_no": plan["loop_no"],
                "plan_artifact_dir": directory, "artifact_dir": plan["loop_artifact_dir"],
                "revision": plan["revision"]}

    def execute_looping(self, plan_id: str, resume: bool = False, feedback: str = "", artifact_name: str = "") -> dict:
        before = self.store.get_plan(plan_id)
        if before is None:
            raise KeyError(f"Unknown plan_id: {plan_id}")
        if resume and before["loop_no"] == 0:
            raise ValueError("No Loop has been executed. Call plan_03-execute_looping tool without resume first.")
        selected = self.select(plan_id, artifact_name=artifact_name)
        number = selected["loop_no"] if resume else selected["loop_no"] + 1
        candidate = project_path(f"{selected['plan_artifact_dir']}/{number:02d}", base=self.root)
        if not resume and candidate.exists():
            raise ValueError("The next Loop folder already exists; preserve or relocate those files before starting this Loop.")
        plan = self.store.execute_looping(plan_id, resume=resume, feedback=feedback)
        selection = self.select(plan_id, loop_no=plan["loop_no"])
        previous = self.store.get_plan(plan_id, loop_no=plan["loop_no"]-1)
        return {**selection, "title": plan["title"], "goal": plan["goal"], "plan_status": plan["status"],
                "feedback": plan["feedback"], "steps": plan["steps"],
                "next_step_id": next((s["step_id"] for s in plan["steps"] if s["status"] != "completed"), None),
                "previous_loop": None if previous is None else {"loop_no": previous["loop_no"], "steps": previous["steps"]},
                "policy_reminder": read_instruction(__file__, "looping-reminder")}

    def rename(self, name: str, plan_id: str = "") -> dict:
        plan_id = plan_id or self.current()["plan_id"]
        destination = ARTIFACT_ROOT + "/" + folder_name(name)
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
            if plan["loop_no"] > 0:
                raise ValueError("Cannot rename a Plan folder after plan_03-execute_looping tool; earlier Loop file paths must remain unchanged.")
            if target.exists() or db.execute("SELECT 1 FROM generation_plans WHERE artifact_dir = ? COLLATE NOCASE", (destination,)).fetchone():
                raise ValueError("The target artifact folder already exists or belongs to another Plan.")
            allowed_roots = {project_path(relative, base=self.root)
                             for relative in (ARTIFACT_ROOT, "tmp", ".almond/tmp")}
            if source.parent not in allowed_roots:
                raise ValueError("Only a directly owned Plan artifact folder can be renamed.")

            def rewrite(ref):
                # URI/opaque references are not filesystem paths. A Windows
                # absolute drive path is the exception to the scheme prefix.
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", ref) and not re.match(r"^[A-Za-z]:[/\\]", ref):
                    return ref
                value = ntpath.normpath(relative_path(ref, str(self.root))).replace("\\", "/")
                prefix = ntpath.normpath(original).replace("\\", "/")
                key, prefix_key = ntpath.normcase(value), ntpath.normcase(prefix)
                matches = key == prefix_key or key.startswith(prefix_key + "\\")
                return destination + value[len(prefix):] if matches else ref

            # A different Plan may already have consumed this pre-execution
            # folder. Its immutable past Loop paths must not be invalidated.
            for row in db.execute("""SELECT r.snapshot_json FROM generation_plan_revisions r
                JOIN generation_plans p ON p.plan_id=r.plan_id WHERE r.loop_no<p.loop_no"""):
                snapshot = json.loads(row[0])
                refs = list(snapshot.get("artifact_refs", []))
                for step in snapshot.get("steps", []):
                    refs.extend(step.get("input_refs", []))
                    refs.extend(step.get("output_refs", []))
                if any(rewrite(ref) != ref for ref in refs):
                    raise ValueError("Cannot rename a folder referenced by a past Loop; its file paths must remain unchanged.")

            try:
                if source.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
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
                            db.execute("UPDATE generation_loop_steps SET input_refs_json = ?, output_refs_json = ? WHERE plan_id = ? AND loop_no = ? AND step_id = ?",
                                       (json.dumps(inputs), json.dumps(outputs), current["plan_id"], current["loop_no"], step["step_id"]))
                    if changed:
                        self.store._record_generation_revision(db, current["plan_id"], "rename_artifact_folder")
                db.commit()
            except BaseException:
                db.rollback()
                if moved:
                    target.rename(source)
                raise
        return {"artifact_dir": destination, "previous_artifact_dir": original}
