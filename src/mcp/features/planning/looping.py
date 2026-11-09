"""Loop-local Step state and revision allocation, without Loop workflow states."""
from almond_mcp.store_common import _utc_now


def loop_artifact_dir(plan):
    root = plan["artifact_dir"]
    return f"{root}/{plan['loop_no']:02d}" if root and plan["loop_no"] else root


def initialize_looping(connection):
    """Preserve pre-execution records as number 0, not a synthetic executed Loop."""
    connection.execute("""CREATE TABLE IF NOT EXISTS generation_plan_loops(
        plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
        loop_no INTEGER NOT NULL CHECK(loop_no>0),
        feedback TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
        PRIMARY KEY(plan_id,loop_no))""")
    connection.execute("""CREATE TABLE IF NOT EXISTS generation_loop_steps(
        plan_id TEXT NOT NULL, loop_no INTEGER NOT NULL CHECK(loop_no>=0), step_id TEXT NOT NULL,
        status TEXT NOT NULL REFERENCES workflow_statuses(status) ON DELETE RESTRICT,
        input_refs_json TEXT NOT NULL DEFAULT '[]', output_refs_json TEXT NOT NULL DEFAULT '[]',
        PRIMARY KEY(plan_id,loop_no,step_id),
        FOREIGN KEY(plan_id,step_id) REFERENCES generation_plan_steps(plan_id,step_id) ON DELETE CASCADE)""")
    step_columns = {r["name"] for r in connection.execute("PRAGMA table_info(generation_plan_steps)")}
    if "status" in step_columns:
        connection.execute("""INSERT INTO generation_loop_steps
            SELECT plan_id,0,step_id,status,input_refs_json,output_refs_json FROM generation_plan_steps""")
        # The definition keeps its UUID/type/order. Mutable execution data lives
        # only in generation_loop_steps; there is no second current-state copy.
        for column in ("status", "input_refs_json", "output_refs_json"):
            connection.execute(f"ALTER TABLE generation_plan_steps DROP COLUMN {column}")
    columns = {r["name"] for r in connection.execute("PRAGMA table_info(generation_plan_revisions)")}
    if "loop_no" not in columns:
        extras = [r[0] for r in connection.execute("""SELECT sql FROM sqlite_master
            WHERE tbl_name='generation_plan_revisions' AND type IN ('index','trigger') AND sql IS NOT NULL""")]
        connection.execute("""CREATE TABLE _looping_revisions(
            plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, operation TEXT NOT NULL, snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL, loop_no INTEGER NOT NULL DEFAULT 0 CHECK(loop_no>=0),
            step_id TEXT, PRIMARY KEY(plan_id,loop_no,revision))""")
        connection.execute("""INSERT INTO _looping_revisions(plan_id,revision,operation,snapshot_json,created_at)
            SELECT plan_id,revision,operation,snapshot_json,created_at FROM generation_plan_revisions""")
        connection.execute("DROP TABLE generation_plan_revisions")
        connection.execute("ALTER TABLE _looping_revisions RENAME TO generation_plan_revisions")
        for statement in extras:
            connection.execute(statement)
        connection.execute("""UPDATE generation_plan_revisions SET step_id=(
            SELECT s.step_id FROM generation_plan_steps s WHERE s.plan_id=generation_plan_revisions.plan_id
            AND (s.step_id=substr(operation,13) OR s.legacy_step_id=substr(operation,13)))
            WHERE operation LIKE 'update_step:%'""")
    connection.execute("""CREATE INDEX IF NOT EXISTS generation_revision_step
        ON generation_plan_revisions(plan_id,loop_no,step_id,revision)""")


class LoopingStore:
    @staticmethod
    def _loop_number(value):
        if type(value) is not int or value < 0:
            raise ValueError("loop_no must be a nonnegative integer; 0 means before execute_looping.")
        return value

    def _check_current_loop(self, plan, loop_no=None, expected_revision=None):
        if loop_no is not None and self._loop_number(loop_no) != plan["loop_no"]:
            raise ValueError(f"Only current Loop {plan['loop_no']} can be changed; earlier Loops are read-only.")
        if expected_revision is not None and plan["loop_no"] > 0 and loop_no is None:
            raise ValueError("Supply loop_no with expected_revision; revision numbers repeat in different Loops.")

    def execute_looping(self, plan_id, *, resume=False, feedback=""):
        if type(resume) is not bool or not isinstance(feedback, str):
            raise ValueError("resume must be boolean and feedback must be text.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            plan = self._read_generation_plan(connection, plan_id)
            if plan is None:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            if resume:
                if plan["loop_no"] == 0:
                    raise ValueError("No Loop has been executed. Call execute_looping without resume first.")
                if not feedback or feedback == plan["feedback"]:
                    return plan
                connection.execute("UPDATE generation_plan_loops SET feedback=? WHERE plan_id=? AND loop_no=?",
                                   (feedback,plan_id,plan["loop_no"]))
                return self._record_generation_revision(connection, plan_id, "update_loop_feedback")
            loop_no = connection.execute("SELECT COALESCE(MAX(loop_no),0)+1 FROM generation_plan_loops WHERE plan_id=?",
                                         (plan_id,)).fetchone()[0]
            connection.execute("INSERT INTO generation_plan_loops VALUES(?,?,?,?)",
                               (plan_id,loop_no,feedback,_utc_now()))
            connection.execute("UPDATE generation_plans SET loop_no=?,revision=0 WHERE plan_id=?", (loop_no,plan_id))
            connection.execute("""INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status)
                SELECT plan_id,?,step_id,'pending' FROM generation_plan_steps WHERE plan_id=?""", (loop_no,plan_id))
            return self._record_generation_revision(connection, plan_id, "execute_looping")
