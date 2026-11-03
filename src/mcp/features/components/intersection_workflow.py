"""Review one live overlap, then apply an explicit numbered choice on that pair."""
import base64
import io
import json
from threading import Lock
from uuid import uuid4

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image

from almond_mcp.features.components.intersection_queries import handle
from almond_mcp.features.context.capture_artifacts import save_png
from almond_mcp.features.context.object_queries import dispatch, object_ids
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


def result(value):
    """Deliver a verified comparison PNG and preserve native mutation evidence on error."""
    content = []
    picture = value.pop("image", None)
    if picture is not None and value.get("status") == "success":
        try:
            raw = base64.b64decode(picture["data"], validate=True)
            if not 0 < len(raw) <= 4 * 1024 * 1024 or picture.get("mime_type") != "image/png":
                raise ValueError("Comparison must be a PNG of at most 4 MiB.")
            dimensions = (picture["width"], picture["height"])
            if dimensions != (1280, 504):
                raise ValueError("Unexpected comparison dimensions.")
            with Image.open(io.BytesIO(raw)) as decoded:
                if decoded.format != "PNG" or decoded.size != dimensions:
                    raise ValueError("Comparison PNG does not match its metadata.")
                decoded.load()
            content.append(ImageContent(type="image", data=picture["data"], mimeType="image/png"))
            value["image_file"] = save_png(raw, "inspection")
        except Exception as exc:
            value.update(status="error", error_code="invalid_intersection_image", message=str(exc))
    serialized = json.dumps(value, ensure_ascii=False)
    content.append(TextContent(type="text", text=serialized))
    return ToolResult(content=content, structured_content=value, is_error=value.get("status") == "error")


class Workflow:
    """State belongs to this worker connection, and is bound to its document path."""
    def __init__(self, send):
        self.send = send
        self.scope = None
        self.pending = None
        self.skipped = set()
        self.number = 0
        self.blocked = False
        self.lock = Lock()

    def execute(self, ids=None, include_block=False, review_id="", choice=None):
        if not self.lock.acquire(blocking=False):
            return result(error_payload("Finish the pending review call first.", error_code="intersection_review_busy"))
        try:
            return self._execute(ids, include_block, review_id, choice)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            return result(error_payload(str(exc), error_code="invalid_intersection_review"))
        finally:
            self.lock.release()

    def _execute(self, ids, include_block, review_id, choice):
        path = bound_model_path()
        if type(include_block) is not bool or not isinstance(review_id, str):
            raise ValueError("include_block must be boolean and review_id must be a string.")
        if choice is not None and not (type(choice) is int and choice in (1, 2) or choice == "skip"):
            raise ValueError("choice must be 1, 2 or 'skip'. A number trims only that object's overlap.")
        if ids is not None:
            if choice is not None or review_id:
                raise ValueError("Start with object_ids, or answer a review with review_id and choice; do not mix them.")
            normalized = object_ids(ids, 512, required=True)
            self.scope = (path, normalized, include_block)
            self.pending, self.skipped, self.number, self.blocked = None, set(), 0, False
        if self.scope is None or self.scope[0] != path:
            raise ValueError("Start a review with current object_ids in this bound document.")
        if self.blocked:
            raise ValueError("A previous operation has an uncertain outcome. Inspect it before starting a new review; never retry its choice automatically.")
        previous = None
        if choice is not None:
            pending = self.pending
            if pending is None or review_id != pending["review_id"]:
                raise ValueError("Use review_id from the comparison just displayed; this review is no longer pending.")
            # Consume before dispatch: neither a repeated choice nor a transport timeout can edit twice.
            self.pending = None
            if choice == "skip":
                self.skipped.add(pending["key"])
                previous = {"status": "skipped", "number": pending["number"], "geometry_changed": False}
            else:
                trim, keep = pending["handles"][choice - 1], pending["handles"][2 - choice]
                if trim["path"] or keep["path"]:
                    self.pending = pending
                    return result(error_payload("Block members can be reviewed but automatic subtraction is unsupported. Choose skip or edit the block explicitly.",
                                                error_code="unsupported_block_subtraction"))
                response = self._native({"type": "intersection_resolve", "keep": keep, "trim": trim}, mutates_geometry=True)
                detail = response.get("result")
                if response.get("status") == "success" and (
                    response.get("result_error") or not isinstance(detail, dict) or detail.get("edited") is not True
                    or detail.get("keep_id") != keep["object_id"] or detail.get("trim_id") != trim["object_id"]
                    or type(detail.get("geometry_crc")) is not int
                    or detail.get("geometry_crc") == detail.get("previous_geometry_crc")
                ):
                    response.update(status="error", error_code="intersection_resolution_unconfirmed",
                                    requires_reconciliation=True, mutation_state="unknown",
                                    message="The edit result is unconfirmed; inspect the target before any retry.")
                if response.get("status") != "success":
                    self.blocked = bool(response.get("requires_reconciliation") or response.get("mutation_state") == "unknown")
                    return result(response)
                previous = {"status": "resolved", "number": pending["number"], "choice": choice, **detail}
        elif review_id:
            raise ValueError("review_id requires choice 1, 2 or 'skip'.")

        # Every continuation starts from live geometry. A preceding trim invalidates native paging.
        try:
            response = self._advance()
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            response = error_payload(str(exc), error_code="intersection_review_failed")
        if previous is not None:
            response["previous_result"] = previous
        output = result(response)
        if output.is_error:
            self.pending = None  # No numeric decision may follow an undelivered comparison image.
            self.blocked = self.blocked or bool(response.get("requires_reconciliation"))
        return output

    def _native(self, payload, mutates_geometry=False):
        dispatched = False
        try:
            # The new capability gates both image review and stateless live subtraction.
            observed = json.loads(self.send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
            if observed.get("status") != "success" or observed.get("capabilities", {}).get("intersection_review") != 1:
                return error_payload("Load the matching Bridge with intersection_review=1.", error_code="unsupported_intersection_review")
            payload["expected_model_path"] = self.scope[0]
            dispatched = True
            value = json.loads(self.send(json.dumps(payload).encode("utf-8")))
            if not isinstance(value, dict) or value.get("status") not in ("success", "error"):
                raise ValueError("Invalid native review response.")
            return value
        except Exception as exc:
            return {**error_payload(str(exc), error_code="intersection_review_transport_error"),
                    "requires_reconciliation": dispatched, "mutation_state": "unknown" if dispatched else "not_started",
                    "geometry_change_possible": dispatched and mutates_geometry}

    def _advance(self):
        path, ids, include_block = self.scope
        cursor, seen = "", set()
        # Native code stops immediately on a positive pair, with bounded pages for preceding zeros.
        for _ in range(20001):
            try:
                page = json.loads(dispatch(self.send, {"type": "get_object_intersections", "object_ids": ids,
                    "include_blocks": include_block, "max_pairs": 64, "cursor": cursor,
                    "stop_at_first_positive": True}, path,
                    capability_name="intersection_review"))
            except Exception as exc:
                return error_payload(str(exc), error_code="intersection_review_query_failed")
            if page.get("status") == "error":
                return page
            pairs, unsupported = page.get("pairs"), page.get("unsupported_objects")
            if page.get("status") != "success" or not isinstance(pairs, list) or not isinstance(unsupported, list):
                raise ValueError("Intersection query omitted its evidence.")
            failures = [v for v in unsupported if include_block or v.get("reason") != "block_excluded"]
            if failures:
                return {**error_payload("Some objects cannot be checked; narrow or correct the scope.", error_code="intersection_count_incomplete"),
                        "unsupported_objects": failures}
            for pair in pairs:
                status = pair.get("overlap", {}).get("status")
                if status not in ("positive_volume", "zero_volume"):
                    return {**error_payload("A candidate could not be calculated.", error_code="intersection_count_incomplete"), "failed_pairs": [pair]}
                if status == "zero_volume":
                    continue
                handles = [handle(pair[side]["handle"]) for side in ("a", "b")]
                key = tuple(sorted(json.dumps(v, sort_keys=True) for v in handles))
                if key in self.skipped:
                    continue
                review = self._native({"type": "intersection_review", "a": handles[0], "b": handles[1]})
                if review.get("status") != "success":
                    self.blocked = bool(review.get("requires_reconciliation"))
                    return review
                objects = review.get("objects")
                if not isinstance(objects, list) or len(objects) != 2 or not isinstance(review.get("image"), dict):
                    raise ValueError("Comparison omitted its image or numbered objects.")
                if [v.get("number") for v in objects] != [1, 2] or [handle(v.get("handle")) for v in objects] != handles:
                    raise ValueError("Comparison object identities differ from the queried pair.")
                self.number += 1
                identity = uuid4().hex
                self.pending = {"review_id": identity, "number": self.number, "handles": handles, "key": key}
                review.update(state="awaiting_choice", review_id=identity, number=self.number,
                              next_step="이미지와 속성을 검토한 뒤 같은 도구에 review_id와 choice=1 또는 2를 보내 해당 객체의 겹친 부분만 제거하세요. 판단을 보류하면 choice='skip'을 사용하세요.")
                return review
            next_cursor = page.get("next_cursor")
            if page.get("pagination_complete") is True:
                if next_cursor:
                    raise ValueError("A completed query returned a cursor.")
                self.pending = None
                return {"status": "success", "state": "completed", "skipped_pairs": len(self.skipped),
                        "message": "검토할 겹침이 더 없습니다. skip한 쌍은 수정하지 않았습니다."}
            if not pairs or not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen:
                raise ValueError("Intersection pagination did not advance.")
            seen.add(next_cursor)
            cursor = next_cursor
        raise ValueError("Intersection review exceeded the candidate bound.")
