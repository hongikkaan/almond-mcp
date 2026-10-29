"""Read-only contracts against disposable SQLite files; never touch a Rhino model."""

import hashlib
import http.client
import json
import sqlite3
import threading
from contextlib import closing
from urllib.parse import urlencode

import pytest

from dashboard.database import CELL_LIMIT, Database
from dashboard.server import DashboardServer


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "한글 space # % 자료.sqlite3"
    with closing(sqlite3.connect(path)) as db:
        db.executescript('''
            CREATE TABLE groups (id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE items (id INTEGER PRIMARY KEY, group_id INTEGER REFERENCES groups(id),
                                label TEXT, amount REAL, metadata TEXT, payload BLOB);
            INSERT INTO groups VALUES (1, '공간');
            CREATE VIEW item_names AS SELECT label FROM items;
        ''')
        db.executemany("INSERT INTO items VALUES (?,1,?,?,?,?)", [
            (i, "100%_" if i == 1 else f"부재 {i}", i * 1.5, '{"layer":"구조","nested":[1,2]}', b"\x00\xff")
            for i in range(1, 124)
        ])
        db.commit()
    return Database(path)


def test_schema_relations_views_and_live_schema_change(database):
    schema = database.schema()
    tables = {t["name"]: t for t in schema["tables"]}
    assert tables["item_names"]["type"] == "view"
    assert tables["items"]["relations"][0]["target"] == "groups"
    assert len(tables["items"]["columns"]) == 6
    with closing(sqlite3.connect(database.path)) as writer:
        writer.executescript("ALTER TABLE items ADD COLUMN progress TEXT; CREATE TABLE future_type(new_field INTEGER);")
    updated = {t["name"]: t for t in database.schema()["tables"]}
    assert "future_type" in updated
    assert updated["items"]["columns"][-1]["name"] == "progress"
    assert database.rows("items")["columns"][-1]["name"] == "progress"


def test_reads_do_not_change_database_and_writes_are_refused(database):
    before = hashlib.sha256(database.path.read_bytes()).hexdigest()
    siblings = set(database.path.parent.iterdir())
    database.schema()
    database.rows("items", search="부재", sort="amount", descending=True)
    database.profile("items")
    with database.connect() as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert db.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            db.execute("DELETE FROM items")
    assert hashlib.sha256(database.path.read_bytes()).hexdigest() == before
    assert set(database.path.parent.iterdir()) == siblings


def test_pagination_sort_literal_search_and_missing_table(database):
    first = database.rows("items")
    assert len(first["rows"]) == 50 and first["has_more"]
    assert first["rows"][0][0] == 1
    last = database.rows("items", offset=100)
    assert len(last["rows"]) == 23 and not last["has_more"]
    assert database.rows("items", sort="amount", descending=True)["rows"][0][0] == 123
    assert len(database.rows("items", search="%_")["rows"]) == 1
    assert not database.rows("items", search="' OR 1=1 --")["rows"]
    with pytest.raises(ValueError):
        database.rows('items; DROP TABLE groups;')
    with pytest.raises(ValueError):
        database.rows("items", sort="unknown")


def test_quoted_identifiers_composite_keys_generated_columns_and_blobs(database):
    with closing(sqlite3.connect(database.path)) as db:
        db.executescript('''CREATE TABLE "odd table" ("a""b" TEXT, n INTEGER, doubled INTEGER AS (n*2),
                            PRIMARY KEY("a""b",n)) WITHOUT ROWID;''')
        db.execute('INSERT INTO "odd table" VALUES (?,?)', ("한글", 3))
        db.execute("INSERT INTO items VALUES (?,1,?,NULL,NULL,?)", (2**62, "x" * (CELL_LIMIT + 100), b"x" * 100000))
        db.commit()
    assert database.rows("odd table", search="한글", sort='a"b')["rows"] == [["한글", 3, 6]]
    row = database.rows("items", sort="id", descending=True)["rows"][0]
    assert row[0] == {"kind": "integer", "value": str(2**62)}
    assert row[2]["truncated"] and len(row[2]["value"]) == CELL_LIMIT
    assert row[3] is None
    assert row[5]["bytes"] == 100000 and len(row[5]["hex"]) == 64


def test_committed_wal_is_visible_without_waiting_for_writer(tmp_path):
    path = tmp_path / "wal.sqlite3"
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE data(value)")
        writer.execute("INSERT INTO data VALUES ('committed')")
        writer.commit()
        db = Database(path)
        writer.execute("INSERT INTO data VALUES ('uncommitted')")
        assert db.rows("data")["rows"] == [["committed"]]
        writer.commit()
        assert db.rows("data")["rows"] == [["committed"], ["uncommitted"]]


def test_locked_db_does_not_unlock_or_write(database):
    with closing(sqlite3.connect(database.path)) as writer:
        writer.execute("BEGIN EXCLUSIVE")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            database.schema()
        assert writer.in_transaction


def test_profile_sample_is_explicit_and_bounded(database):
    with closing(sqlite3.connect(database.path)) as db:
        db.executemany("INSERT INTO items(id,label,amount) VALUES (?,?,?)", [(i, "반복", i) for i in range(124, 700)])
        db.commit()
    profile = database.profile("items")
    assert profile["sample_size"] == 300 and profile["has_more"]
    cols = {c["name"]: c for c in profile["columns"]}
    assert sum(cols["amount"]["bins"]) == 300
    assert cols["label"]["top"][0] == {"label": "반복", "count": 177}
    assert cols["metadata"]["kind"] == "json"


def test_wide_table_is_explicitly_bounded_and_demo_never_overwrites(tmp_path):
    from dashboard.demo import create_demo

    path = create_demo(tmp_path / "demo.sqlite3")
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        create_demo(path)
    assert path.read_bytes() == before
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE wide(" + ",".join(f"c{i} TEXT" for i in range(130)) + ")")
    database = Database(path)
    assert database.rows("wide")["omitted_columns"] == 2
    assert database.profile("wide")["omitted_columns"] == 2
    assert len(next(t for t in database.schema()["tables"] if t["name"] == "wide")["columns"]) == 130


def test_missing_or_invalid_file_never_created(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        Database(missing)
    assert not missing.exists()
    invalid = tmp_path / "invalid.db"
    invalid.write_text("not sqlite")
    with pytest.raises(sqlite3.DatabaseError):
        Database(invalid)
    assert invalid.read_text() == "not sqlite"


def test_internal_fts_tables_marked_and_actual_almond_schema_supported(tmp_path):
    from almond_mcp.retrieval_store import AlmondStore

    path = tmp_path / "almond.sqlite3"
    AlmondStore(path)  # Disposable producer fixture, never called by the dashboard.
    database = Database(path)
    schema = database.schema()
    tables = {t["name"]: t for t in schema["tables"]}
    assert "generation_plans" in tables and "components" in tables
    assert tables["asset_fts_data"]["internal"]
    assert not tables["asset_fts"]["internal"]
    for table in schema["tables"]:
        database.rows(table["name"])
        database.profile(table["name"])


def test_expensive_view_is_interrupted(database):
    with closing(sqlite3.connect(database.path)) as writer:
        writer.executescript("""CREATE VIEW slow AS WITH RECURSIVE seq(n) AS
            (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<1000000000) SELECT sum(n) FROM seq;""")
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        database.rows("slow")


@pytest.fixture
def server(database):
    server = DashboardServer(database.path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(2)


def request(server, path, *, body=None, headers=None, authenticated=True):
    with closing(http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as client:
        combined = {"X-Dashboard-Token": server.token} if authenticated else {}
        combined.update(headers or {})
        client.request("POST" if body is not None else "GET", path, body, combined)
        response = client.getresponse()
        return response.status, response.read(), dict(response.getheaders())


def test_http_assets_and_authenticated_api(server):
    status, content, headers = request(server, "/", authenticated=False)
    assert status == 200 and "DB 안의 자료" in content.decode()
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    for asset in ("/app.js", "/style.css"):
        assert request(server, asset)[0] == 200
    status, content, _ = request(server, "/api/schema")
    assert status == 200 and json.loads(content)["read_only"]
    query = urlencode({"database": str(server.database.path), "table": "items"})
    assert request(server, "/api/rows?" + query)[0] == 200
    assert request(server, "/api/profile?" + query)[0] == 200


def test_http_rejects_external_origins_host_and_missing_token(server):
    assert request(server, "/api/schema", authenticated=False)[0] == 403
    assert request(server, "/api/schema", headers={"Origin": "https://untrusted.example"})[0] == 403
    assert request(server, "/api/schema", headers={"Host": "untrusted.example"})[0] == 403
    assert request(server, "/../server.py")[0] == 404
    assert request(server, "/api/rows?table=items&database=another")[0] == 409


def test_http_open_invalid_file_keeps_current_and_reports_bad_parameters(server, tmp_path):
    original = server.database.path
    missing = str(tmp_path / "missing.db")
    assert request(server, "/api/open", body=json.dumps({"path": missing}))[0] == 400
    assert server.database.path == original
    assert request(server, "/api/open", body="[]")[0] == 400
    query = urlencode({"table": "items", "database": str(original), "limit": "not-an-integer"})
    assert request(server, "/api/rows?" + query)[0] == 400
    status, content, _ = request(server, "/api/open", body=json.dumps({"path": str(original)}))
    assert status == 200 and json.loads(content)["name"] == original.name
