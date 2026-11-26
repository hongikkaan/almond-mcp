"""Exercise the actual Update entry point with document and geometry boundaries replaced."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class Point:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z
        self.IsValid = True


class Plane:
    def __init__(self, origin, x_axis=None, y_axis=None):
        self.Origin, self.XAxis, self.YAxis = (
            (origin.Origin, origin.XAxis, origin.YAxis)
            if isinstance(origin, Plane)
            else (origin, x_axis, y_axis)
        )
        self.IsValid = True

    OriginX = property(lambda self: self.Origin.X)
    OriginY = property(lambda self: self.Origin.Y)
    OriginZ = property(lambda self: self.Origin.Z)


Plane.WorldXY = Plane(Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0))


class Dictionary(dict):
    def ContainsKey(self, key):
        return key in self


class Attributes:
    def __init__(self, texts, typed=None):
        self.text = dict(texts)
        self.UserDictionary = Dictionary(typed or {})

    def GetUserString(self, key):
        return self.text.get(key)

    def Duplicate(self):
        return Attributes(self.text, self.UserDictionary)


class Clipping:
    Id = "ccb9aeaf-d185-47b5-8165-75985b869510"
    Name = "Third floor"
    IsReference = False
    Attributes = Attributes({})
    ClippingPlaneGeometry = SimpleNamespace(Plane=Plane.WorldXY)


class Events:
    def __iadd__(self, handler):
        return self

    def __isub__(self, handler):
        return self


def load_plan_section():
    rhino = SimpleNamespace(
        Geometry=SimpleNamespace(Plane=Plane, Point3d=Point, Vector3d=Point),
        DocObjects=SimpleNamespace(ClippingPlaneObject=Clipping, ObjectEnumeratorSettings=SimpleNamespace),
        RhinoApp=SimpleNamespace(Wait=lambda: None, EscapeKeyPressed=Events()),
    )
    modules = {
        "clr": SimpleNamespace(),
        "Rhino": rhino,
        "System": SimpleNamespace(),
        "System.Drawing": SimpleNamespace(Color=object),
        "System.Collections.Generic": SimpleNamespace(List=list, IEnumerable=list),
    }
    script = Path(__file__).resolve().parents[1] / "PlanSection.py"
    spec = importlib.util.spec_from_file_location("plan_section_update", script)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


def document_with_drawing(*placements):
    clip = Clipping()
    text = {
        "ps:generator": "PlanSection/2",
        "ps:clip": clip.Id,
        "ps:placement": json.dumps({
            "origin": [1800, -450, 25],
            "xaxis": [1, 0, 0],
            "yaxis": [0, 1, 0],
        }),
    }
    previous = []
    for identity, point in placements:
        typed = {"ps:placement": point} if point is not None else {}
        previous.append(SimpleNamespace(Id=identity, IsReference=False, Attributes=Attributes(text, typed)))
    doc = SimpleNamespace(
        Objects=SimpleNamespace(GetObjectList=lambda _: [clip, *previous]),
        Layers=SimpleNamespace(FindByFullPath=lambda *_: -1),
        Views=SimpleNamespace(Redraw=lambda: None),
        CurrentUndoRecordSerialNumber=1,
    )
    return doc, clip, previous


def generate(_doc, _clip, _hatch, _elevation, placement, *_style, **_options):
    return {"target": placement, "objects": [], "extraction": {}, "report": {}}


class UpdatePlacement(unittest.TestCase):
    def test_legacy_and_typed_objects_keep_the_same_placed_height(self):
        ps = load_plan_section()
        doc, clip, previous = document_with_drawing(("legacy-outline", None), ("typed-hatch", Point(1800, -450, 25)))
        placed = []

        def bake(_doc, _clip, drawing, _target, _cancelled):
            placed[:] = [drawing["target"].Origin]
            previous[:] = []
            return ["regenerated-outline"]

        with patch.object(ps, "generate", generate), patch.object(ps, "bake", bake), redirect_stdout(io.StringIO()):
            result = ps.run(doc, "Update", [clip.Id])

        self.assertEqual(result["status"], "completed")
        updated = result["results"][0]
        self.assertEqual(updated["object_ids"], ["regenerated-outline"])
        self.assertEqual(updated["draw_plane"]["origin"], [1800, -450, 25])
        self.assertEqual([(point.X, point.Y, point.Z) for point in placed], [(1800, -450, 25)])

    def test_conflicting_typed_placement_preserves_previous_drawing(self):
        ps = load_plan_section()
        doc, clip, previous = document_with_drawing(("typed-hatch", Point(1800, -450, 90)))
        before = [obj.Id for obj in previous]

        def bake(_doc, _clip, _drawing, _target, _cancelled):
            previous[:] = []
            return ["regenerated-at-the-wrong-height"]

        with patch.object(ps, "generate", generate), patch.object(ps, "bake", bake), redirect_stdout(io.StringIO()):
            result = ps.run(doc, "Update", [clip.Id])

        self.assertEqual(result["status"], "failed")
        self.assertIn("conflicts with the JSON", result["results"][0]["error"])
        self.assertEqual([obj.Id for obj in previous], before)


if __name__ == "__main__":
    unittest.main()
