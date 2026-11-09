"""Stable Step identity with a lossless view of pre-UUID snapshots."""
import json
import uuid


def initialize_step_identity(connection):
    """Run in the store's FK-disabled initialization transaction."""
    legacy = connection.execute(
        "SELECT plan_id,step_id,depends_on_json FROM generation_plan_steps WHERE step_type=''"
    ).fetchall()
    mapping = {(row["plan_id"], row["step_id"]):
               "step_" + uuid.uuid5(uuid.NAMESPACE_URL, f"almond-step:{row['plan_id']}:{row['step_id']}").hex
               for row in legacy}
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for row in legacy:
        pid, old = row["plan_id"], row["step_id"]
        sid = mapping[pid, old]
        dependencies = [mapping.get((pid, value), value) for value in json.loads(row["depends_on_json"])]
        connection.execute("""UPDATE generation_plan_steps
            SET step_id=?,step_type=?,name=?,legacy_step_id=?,depends_on_json=?
            WHERE plan_id=? AND step_id=?""", (sid, old, old, old, json.dumps(dependencies), pid, old))
        for table in ("generation_step_ontological", "_retired_step_targets", "generation_loop_steps"):
            if table in tables:
                connection.execute(f"UPDATE {table} SET step_id=? WHERE plan_id=? AND step_id=?", (sid, pid, old))
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS generation_step_uuid ON generation_plan_steps(step_id)")


def snapshot_step_identity(connection, snapshot):
    """Normalize the read view only; never rewrite stored snapshot bytes."""
    mapping = {row["legacy_step_id"]: row["step_id"] for row in connection.execute(
        "SELECT legacy_step_id,step_id FROM generation_plan_steps WHERE plan_id=? AND legacy_step_id IS NOT NULL",
        (snapshot["plan_id"],))}
    for step in snapshot.get("steps", []):
        old = step["step_id"]
        step.setdefault("step_type", step.get("name", old))
        step.setdefault("name", step["step_type"])
        step["step_id"] = mapping.get(old, old)
        step["depends_on"] = [mapping.get(value, value) for value in step.get("depends_on", [])]
