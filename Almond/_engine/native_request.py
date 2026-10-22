"""Bind the existing Almond sender to one operation without another socket layer."""
from __future__ import annotations

import json
import threading
from uuid import uuid4


class RequestBatch:
    """Keep each request's identity until its matching native completion arrives."""

    def __init__(self, token: str, operation_id: str):
        self.token, self.operation_id = token, operation_id
        self.guard = threading.Lock()
        self.sealed = False
        self.uncertain = False
        self.error = None
        self.sequence = 0
        self.requests = []

    def call(self, sender, payload_bytes: bytes, *positional, **keywords) -> str:
        payload = payload_bytes.decode("utf-8")
        with self.guard:
            if self.sealed:
                raise RuntimeError("This operation has ended; no native request was sent.")
            if self.uncertain:
                raise RuntimeError("A previous native request has an unconfirmed result.")
            request = dict(request_id=uuid4().hex, pending=True,
                           acknowledged=False, completion_status="running")
            self.requests.append(request)
        try:
            envelope = dict(schema="almond-native-request", storage_protocol=2,
                            token=self.token, operation_id=self.operation_id,
                            request_id=request["request_id"], payload=payload)
            # Preserve the installed sender's framing, socket ownership and timeout.
            raw = sender(json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                         *positional, **keywords)
            response = json.loads(raw)
            if (not isinstance(response, dict) or response.get("schema") != "almond-native-response"
                    or response.get("storage_protocol") != 2 or response.get("token") != self.token
                    or response.get("operation_id") != self.operation_id
                    or response.get("request_id") != request["request_id"]
                    or response.get("completion_status") not in ("completed", "rejected", "failed")
                    or not isinstance(response.get("payload"), str)
                    or type(response.get("native_sequence")) is not int
                    or response["native_sequence"] < 0
                    or (response["completion_status"] != "rejected" and response["native_sequence"] == 0)):
                raise RuntimeError("Native completion does not match this exact request.")
            with self.guard:
                request["acknowledged"] = True
                request["completion_status"] = response["completion_status"]
                self.sequence = max(self.sequence, response["native_sequence"])
            return response["payload"]
        except BaseException as exc:
            with self.guard:
                self.uncertain, self.error = True, str(exc)
            raise
        finally:
            with self.guard:
                request["pending"] = False

    def seal(self):
        # A background task retains this batch through its copied ContextVar.
        # It cannot borrow the next operation after the owner has finished.
        with self.guard:
            self.sealed = True

    def snapshot(self) -> dict:
        with self.guard:
            pending = sum(bool(item["pending"]) for item in self.requests)
            return dict(pending=pending, uncertain=self.uncertain or pending != 0,
                        operation_id=self.operation_id, native_sequence=self.sequence,
                        requests=[dict(item) for item in self.requests], error=self.error)

    def finish(self) -> dict:
        self.seal()
        return self.snapshot()
