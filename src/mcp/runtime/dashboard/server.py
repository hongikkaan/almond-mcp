"""Loopback-only HTTP entry point for the local SQLite dashboard."""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .database import Database

WEB = Path(__file__).with_name("web")


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, database=None, port=0):
        selected = Database(database) if database else None
        super().__init__(("127.0.0.1", port), DashboardHandler)
        self.database = selected
        self.token = secrets.token_urlsafe(32)
        self.open_lock = threading.Lock()

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"

    @property
    def url(self):
        return self.origin + "/#" + self.token


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Paths, query terms and access tokens stay out of HTTP logs.

    def _reply(self, status, payload, content_type="application/json; charset=utf-8"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self, api=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            self._reply(403, {"error": "로컬 대시보드 주소로 접속해 주세요."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin != self.server.origin:
            self._reply(403, {"error": "다른 사이트에서의 요청은 허용되지 않습니다."})
            return False
        if api and not secrets.compare_digest(self.headers.get("X-Dashboard-Token", "").encode("utf-8"), self.server.token.encode("utf-8")):
            self._reply(403, {"error": "실행 창에 표시된 대시보드 주소를 다시 열어 주세요."})
            return False
        return True

    def _error(self, exc):
        if isinstance(exc, sqlite3.OperationalError) and ("locked" in str(exc) or "busy" in str(exc)):
            message = "다른 작업이 DB를 사용 중입니다. 잠시 후 다시 조회해 주세요. 잠금은 변경하지 않았습니다."
        elif isinstance(exc, sqlite3.OperationalError) and "interrupted" in str(exc):
            message = "조회가 2초 제한을 넘었습니다. 검색·정렬을 해제하거나 더 작은 테이블을 선택해 주세요."
        elif isinstance(exc, sqlite3.DatabaseError):
            message = "SQLite DB를 읽지 못했습니다. 파일 형식·접근 권한 또는 선택한 테이블/뷰를 확인해 주세요."
        elif isinstance(exc, OSError):
            message = "파일을 열 수 없습니다. 이 컴퓨터의 DB 파일 경로와 읽기 권한을 확인해 주세요."
        else:
            message = str(exc)
        self._reply(400, {"error": message})

    def do_GET(self):
        request = urlsplit(self.path)
        api = request.path.startswith("/api/")
        if not self._allowed(api):
            return
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8")}
        if request.path == "/favicon.ico":
            self._reply(204, b"", "image/x-icon")
            return
        if request.path in assets:
            name, mime = assets[request.path]
            self._reply(200, (WEB / name).read_bytes(), mime)
            return
        params = parse_qs(request.query)
        get = lambda key, default="": params.get(key, [default])[0]
        try:
            database = self.server.database
            if request.path == "/api/schema":
                self._reply(200, database.schema() if database else {"tables": [], "name": None})
            elif request.path in ("/api/rows", "/api/profile"):
                if database is None:
                    raise ValueError("먼저 DB 파일을 선택해 주세요.")
                # Stale requests cannot accidentally display rows from a newly selected file.
                if get("database") != str(database.path):
                    self._reply(409, {"error": "선택한 DB가 바뀌었습니다. 구조 새로고침을 눌러 주세요."})
                    return
                if request.path.endswith("/rows"):
                    result = database.rows(get("table"), offset=int(get("offset", "0")),
                                           limit=int(get("limit", "50")), search=get("search"),
                                           sort=get("sort"), descending=get("descending") == "true")
                else:
                    result = database.profile(get("table"))
                self._reply(200, result)
            else:
                self._reply(404, {"error": "페이지가 없습니다."})
        except (ValueError, OSError, sqlite3.Error) as exc:
            self._error(exc)

    def do_POST(self):
        if not self._allowed(True):
            return
        if self.path != "/api/open":
            self._reply(404, {"error": "페이지가 없습니다."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16_384:
                raise ValueError("DB 파일 경로가 너무 길거나 비어 있습니다.")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict) or not isinstance(body.get("path"), str) or not body["path"].strip():
                raise ValueError("DB 파일 경로를 입력해 주세요.")
            with self.server.open_lock:
                candidate = Database(body["path"].strip().strip('"'))
                schema = candidate.schema()
                self.server.database = candidate
            self._reply(200, schema)
        except (ValueError, OSError, sqlite3.Error) as exc:
            self._error(exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Almond SQLite 읽기 전용 대시보드")
    parser.add_argument("database", nargs="?", help="SQLite DB 파일 경로")
    parser.add_argument("--port", type=int, default=0, help="기본값: 사용 가능한 로컬 포트 자동 선택")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    try:
        server = DashboardServer(args.database, args.port)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"DB 대시보드 시작 실패: {exc}\n")
    print(f"Almond DB Dashboard: {server.url}", flush=True)
    print("읽기 전용 · 종료: 이 창에서 Ctrl+C", flush=True)
    if not args.no_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
