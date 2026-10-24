"""Drawing Sheet identity, reference integrity and native/ledger recovery contracts."""
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore, DrawingSheetReconciliationError


@pytest.fixture
def store(tmp_path):
    return AlmondStore(tmp_path / "sheets.sqlite3")


@pytest.fixture
def model(store, tmp_path):
    return store._component_model_path(str(tmp_path / "drawing.3dm"))


def native_sheet(request):
    fields = ("sheet_id", "title", "drawing_type", "scale_denominator", "paper_mm",
              "model_bounds_mm", "scene_ids", "component_ids", "plan_id")
    return dict(status="success", sheet=dict(
        {field: request[field] for field in fields}, complete=True,
        model_path=request["expected_model_path"],
        layout_id=request["layout_id"] or str(uuid.uuid5(uuid.NAMESPACE_URL, request["sheet_id"])),
    ))


def register(store, model, **extra):
    arguments = dict(model_path=model, title="Ground floor", drawing_type="plan", scale_denominator=100,
                     paper_mm=[420, 297], model_bounds_mm=[1000, 2000, 0, 21000, 12000, 0],
                     native_apply=native_sheet)
    arguments.update(extra)
    return store.upsert_drawing_sheet(**arguments)


def component(store, model, scene):
    guid = str(uuid.uuid4())
    def native(request):
        return dict(status="success", component=dict(
            complete=True, component_id=request["component_id"], model_path=model,
            rhino_group_id=str(uuid.uuid4()), name=request["name"], scene_ids=request["scene_ids"],
            objects=[dict(rhino_guid=guid, object_type="Brep", component_id=request["component_id"],
                          bounds_mm=[0, 0, 0, 100, 200, 300])],
        ))
    return store.upsert_component(model, "Panel", [guid], [scene], native_apply=native)


def ack(request):
    return dict(status="success", sheet_id=request["sheet_id"],
                model_path=request["expected_model_path"], layout_id=request["layout_id"])


def test_sheet_context_wrapup_and_updates_do_not_rewrite_plan_snapshots(store, model):
    first, second = (store.create_scene(name)["scene_id"] for name in ("First", "Second"))
    comp = component(store, model, first)
    plan = store.create_generation_plan("Draw facade", scope="drawing", scene_ids=[first])
    saved_plan = store.get_generation_plan(plan["plan_id"], revision=1)
    sheet = register(store, model, scene_ids=[second], component_ids=[comp["component_id"]], plan_id=plan["plan_id"])
    assert sheet["live_verified"] is True and sheet["model_bounds_mm"][2] == sheet["model_bounds_mm"][5]
    cached = store.get_drawing_sheet(sheet["sheet_id"])
    assert cached["live_verified"] is False and cached["layout_id"] == sheet["layout_id"]
    listed = store.list_drawing_sheets(plan_id=plan["plan_id"], scene_id=second, component_id=comp["component_id"], model_path=model)
    assert listed["total"] == 1 and listed["sheets"][0]["title"] == "Ground floor"
    requests = []
    def native(request):
        requests.append(request)
        return native_sheet(request)
    changed = register(store, model, title="Revised floor", sheet_id=sheet["sheet_id"], native_apply=native)
    assert changed["scene_ids"] == [second] and changed["component_ids"] == [comp["component_id"]]
    assert changed["plan_id"] == plan["plan_id"] and changed["layout_id"] == sheet["layout_id"]
    assert requests[0]["action"] == "upsert" and requests[0]["layout_id"] == sheet["layout_id"]
    cleared = register(store, model, sheet_id=sheet["sheet_id"], scene_ids=[], component_ids=[], plan_id="")
    assert cleared["scene_ids"] == [] and cleared["component_ids"] == [] and cleared["plan_id"] is None
    assert store.list_drawing_sheets(plan_id=plan["plan_id"])["total"] == 0
    assert store.get_generation_plan(plan["plan_id"]) == plan
    assert store.get_generation_plan(plan["plan_id"], revision=1) == saved_plan


def test_none_plan_id_is_empty_on_native_wire_and_readable_on_sync(store, model):
    calls, snapshots = [], []
    def native(request):
        calls.append(request)
        if request["action"] == "inspect":
            return snapshots[0]
        reply = native_sheet(request)
        snapshots.append(reply)
        return reply
    sheet = register(store, model, native_apply=native)
    assert calls[0]["plan_id"] == ""
    assert sheet["plan_id"] is None
    synced = store.sync_drawing_sheet(model, sheet["sheet_id"], native_inspect=native)
    assert calls[1]["action"] == "inspect"
    assert calls[1]["expected_sheet"]["plan_id"] == ""
    assert synced["plan_id"] is None


def test_native_float_roundoff_is_allowed_only_for_measured_numeric_fields(store, model):
    def roundoff(request):
        result = native_sheet(request)
        result["sheet"]["scale_denominator"] += 5e-8
        result["sheet"]["paper_mm"][0] += 5e-7
        result["sheet"]["model_bounds_mm"][3] += 5e-6
        return result
    accepted = register(store, model, native_apply=roundoff)
    assert accepted["live_verified"] is True
    assert accepted["model_bounds_mm"][3] > 21000
    def changed_label(request):
        result = roundoff(request)
        result["sheet"]["title"] = "Another sheet"
        return result
    with pytest.raises(DrawingSheetReconciliationError, match="metadata differs"):
        register(store, model, native_apply=changed_label)
    def changed_value(request):
        result = native_sheet(request)
        result["sheet"]["scale_denominator"] += 1e-3
        return result
    with pytest.raises(DrawingSheetReconciliationError, match="metadata differs"):
        register(store, model, native_apply=changed_value)
    assert store.list_drawing_sheets()["total"] == 1


@pytest.mark.parametrize("change", ["duplicate", "model", "layout"])
def test_layout_identity_conflicts_are_rejected_before_native(store, model, tmp_path, change):
    sheet = register(store, model)
    calls = []
    extra = dict(sheet_id=sheet["sheet_id"], native_apply=lambda request: calls.append(request))
    if change == "duplicate":
        extra.update(sheet_id="other-sheet", layout_id=sheet["layout_id"])
    elif change == "model":
        extra["model_path"] = str(tmp_path / "other.3dm")
    else:
        extra["layout_id"] = str(uuid.uuid4())
    before = store.get_drawing_sheet(sheet["sheet_id"])
    with pytest.raises(ValueError):
        register(store, model, **extra)
    assert calls == [] and store.get_drawing_sheet(sheet["sheet_id"]) == before


@pytest.mark.parametrize("extra", [
    {"title": ""}, {"drawing_type": "automatic-section"}, {"scale_denominator": 0},
    {"scale_denominator": True}, {"scale_denominator": float("nan")},
    {"paper_mm": [True, 297]}, {"paper_mm": [420, 0]},
    {"model_bounds_mm": [0, 0, 0, 0, 100, 0]}, {"model_bounds_mm": [0, 0, 2, 100, 100, 1]},
    {"scene_ids": ["missing"]}, {"component_ids": ["missing"]}, {"plan_id": "missing"},
])
def test_invalid_metadata_and_references_never_call_native(store, model, extra):
    calls = []
    with pytest.raises((ValueError, KeyError)):
        register(store, model, native_apply=lambda request: calls.append(request), **extra)
    assert calls == [] and store.list_drawing_sheets()["total"] == 0


def test_additive_sheet_migration_preserves_existing_plan_history_and_components(store, model):
    scene = store.create_scene("Existing")["scene_id"]
    comp = component(store, model, scene)
    plan = store.create_generation_plan("Existing", component_ids=[comp["component_id"]])
    tables = ("scenes", "scene_revisions", "components", "document_objects", "scene_components",
              "generation_plans", "generation_plan_steps", "generation_plan_revisions", "generation_plan_components")
    with store._connect() as connection:
        before = {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
                  for table in tables}
        for table in ("drawing_sheet_scenes", "drawing_sheet_components", "drawing_sheets"):
            connection.execute(f"DROP TABLE {table}")
    migrated = AlmondStore(store.database_path)
    with migrated._connect() as connection:
        after = {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
                 for table in tables}
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert after == before and migrated.get_generation_plan(plan["plan_id"], 1) == plan
    assert migrated.list_drawing_sheets()["total"] == 0


@pytest.mark.parametrize("failure", ["timeout", "malformed", "commit"])
def test_uncertain_native_success_never_retries_and_rolls_back_ledger(store, model, failure):
    if failure == "commit":
        with store._connect() as connection:
            connection.execute("CREATE TRIGGER reject_sheet BEFORE INSERT ON drawing_sheets "
                               "BEGIN SELECT RAISE(ABORT, 'forced ledger failure'); END")
    requests, saved = [], []
    def native(request):
        requests.append(request)
        saved.append(native_sheet(request))
        if failure == "timeout":
            raise TimeoutError("Lost Layout response")
        if failure == "malformed":
            return dict(status="success", sheet={})
        return saved[0]
    with pytest.raises(DrawingSheetReconciliationError) as failure_result:
        register(store, model, native_apply=native)
    assert len(requests) == 1 and requests[0]["action"] == "upsert"
    assert failure_result.value.sheet_id == requests[0]["sheet_id"]
    assert failure_result.value.model_path == model and store.list_drawing_sheets()["total"] == 0
    if failure == "commit":
        with store._connect() as connection:
            connection.execute("DROP TRIGGER reject_sheet")
    def inspect(request):
        assert request["action"] == "inspect" and "expected_sheet" not in request
        return saved[0]
    recovered = store.sync_drawing_sheet(model, requests[0]["sheet_id"], native_inspect=inspect)
    assert recovered["layout_id"] == saved[0]["sheet"]["layout_id"] and recovered["live_verified"] is True


def test_known_native_rejection_is_not_ambiguous(store, model):
    with pytest.raises(ValueError, match="does not fit"):
        register(store, model, native_apply=lambda request: dict(
            status="error", mutation_applied=False, message="Region does not fit paper"))
    assert store.list_drawing_sheets()["total"] == 0


def test_sheet_reference_blocks_component_unregister_and_unregistered_sync(store, model):
    scene = store.create_scene("Shared")["scene_id"]
    comp = component(store, model, scene)
    sheet = register(store, model, component_ids=[comp["component_id"]])
    calls = []
    with pytest.raises(ValueError, match="drawing sheet"):
        store.unregister_component(comp["component_id"], native_apply=lambda request: calls.append(request))
    assert calls == []
    proof = dict(status="success", component=dict(comp, complete=True, registration_status="unregistered", scene_ids=[],
        objects=[dict(obj, component_id=None) for obj in comp["objects"]]))
    with pytest.raises(ValueError, match="drawing sheet"):
        store.sync_component(model, comp["component_id"], native_inspect=lambda request: proof)
    assert store.get_component(comp["component_id"]) is not None
    removed = store.remove_drawing_sheet(sheet["sheet_id"], native_apply=ack)
    assert removed["registration_status"] == "unregistered" and removed["layout_id"] == sheet["layout_id"]
    result = store.sync_component(model, comp["component_id"], native_inspect=lambda request: proof)
    assert result["status"] == "unregistered"


def test_lost_sheet_unregister_recovers_through_inspect_without_repeating_mutation(store, model):
    sheet = register(store, model)
    calls = []
    before = store.get_drawing_sheet(sheet["sheet_id"])
    def lost(request):
        calls.append(request["action"])
        raise TimeoutError("Unregister reply lost")
    with pytest.raises(DrawingSheetReconciliationError):
        store.remove_drawing_sheet(sheet["sheet_id"], native_apply=lost)
    assert store.get_drawing_sheet(sheet["sheet_id"]) == before
    def inspect(request):
        calls.append(request["action"])
        assert request["expected_sheet"]["layout_id"] == sheet["layout_id"]
        assert request["expected_sheet"]["model_bounds_mm"] == sheet["model_bounds_mm"]
        return dict(status="success", sheet=dict(complete=True, registration_status="unregistered",
            sheet_id=sheet["sheet_id"], layout_id=sheet["layout_id"], model_path=model))
    result = store.sync_drawing_sheet(model, sheet["sheet_id"], native_inspect=inspect)
    assert result["registration_status"] == "unregistered"
    assert calls == ["unregister", "inspect"] and store.get_drawing_sheet(sheet["sheet_id"]) is None


@pytest.mark.parametrize("fault", ["nested_only", "sheet_id", "layout_id", "model_path"])
def test_unregistration_requires_exact_native_identity_ack_before_delete(store, model, fault):
    sheet = register(store, model)
    before = store.get_drawing_sheet(sheet["sheet_id"])
    def native(request):
        response = ack(request)
        if fault == "nested_only":
            return dict(status="success", sheet=dict(
                complete=True, registration_status="unregistered", sheet_id=request["sheet_id"],
                model_path=request["expected_model_path"], layout_id=request["layout_id"],
            ))
        if fault == "sheet_id":
            response["sheet_id"] = "wrong"
        elif fault == "layout_id":
            response["layout_id"] = str(uuid.uuid4())
        elif fault == "model_path":
            response["model_path"] += ".other.3dm"
        return response
    with pytest.raises(DrawingSheetReconciliationError):
        store.remove_drawing_sheet(sheet["sheet_id"], native_apply=native)
    assert store.get_drawing_sheet(sheet["sheet_id"]) == before


@pytest.mark.parametrize("failure", ["incomplete", "layout", "sheet_id", "model", "truncated"])
def test_sheet_sync_refuses_mismatched_unregistered_proof(store, model, failure):
    sheet = register(store, model)
    proof = dict(complete=True, registration_status="unregistered", sheet_id=sheet["sheet_id"],
                 layout_id=sheet["layout_id"], model_path=model)
    if failure == "incomplete":
        proof["complete"] = False
    elif failure == "layout":
        proof["layout_id"] = str(uuid.uuid4())
    elif failure == "sheet_id":
        proof["sheet_id"] = "other"
    elif failure == "model":
        proof["model_path"] = model.replace("drawing.3dm", "other.3dm")
    else:
        proof["truncated"] = True
    before = store.get_drawing_sheet(sheet["sheet_id"])
    with pytest.raises(ValueError):
        store.sync_drawing_sheet(model, sheet["sheet_id"], native_inspect=lambda request: dict(status="success", sheet=proof))
    assert store.get_drawing_sheet(sheet["sheet_id"]) == before


def test_sheet_sync_cannot_invent_unregistered_identity(store, model):
    with pytest.raises(ValueError, match="existing"):
        store.sync_drawing_sheet(model, "missing", native_inspect=lambda request: dict(
            status="success", sheet=dict(complete=True, registration_status="unregistered")))


def test_sheet_listing_exposes_truncation_and_uses_all_filters(store, model):
    first = register(store, model, title="A")
    register(store, model, title="B")
    listed = store.list_drawing_sheets(limit=1)
    assert listed["total"] == 2 and listed["truncated"] is True and listed["sheets"][0]["sheet_id"] == first["sheet_id"]
    assert store.list_drawing_sheets(plan_id="missing")["total"] == 0
