"""An output's contributors are not every object sharing its drawing style."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from test_logic import ps
from test_metadata import Attributes


class SectionSourceScope(unittest.TestCase):
    def test_disjoint_surface_sections_keep_their_own_source(self):
        class Surface:
            Faces = NS(Count=1)
            IsSolid = False

            def __init__(self, curve):
                self.curve = curve

        class Mesh:
            pass

        first, second = object(), object()
        records = []
        for identity, name, curve in (("a", "Wall A", first), ("b", "Wall B", second)):
            attrs = Attributes(name)
            attrs.GetCustomSectionStyle = lambda: None
            records.append(dict(source=identity, geometry=Surface(curve), attributes=attrs, resolved=attrs))
        doc = NS(ModelAbsoluteTolerance=.01, ModelAngleToleranceRadians=.01,
                 Layers=[NS(FullPath="Model::Walls")])
        with patch.object(ps, "G", NS(Brep=Surface, Mesh=Mesh)), \
             patch.object(ps, "section_tolerance", return_value=.01), \
             patch.object(ps, "record_bounds", return_value=None), \
             patch.object(ps, "meets_plane", return_value=True), \
             patch.object(ps, "intersect", side_effect=lambda geometry, *_: [geometry.curve]), \
             patch.object(ps, "style_key", return_value=(0, None)), \
             patch.object(ps, "planar_union", return_value=[]), \
             patch.object(ps, "split_crossings", side_effect=lambda curve, *_: ([curve], False, False)), \
             patch.object(ps, "drawing_metadata", return_value={}), \
             patch.object(ps, "drawing_attributes", side_effect=lambda doc, attrs, *_: attrs.Duplicate()):
            outputs = ps.sections(doc, records, "cut", hatch_on=False)

        self.assertEqual([item["geometry"] for item in outputs], [first, second])
        self.assertEqual([set(item["contributors"]) for item in outputs], [{"a"}, {"b"}])
        self.assertEqual([
            ps.consensus_metadata(list(item["contributors"].items()))["name"] for item in outputs
        ], ["Wall A", "Wall B"])


if __name__ == "__main__":
    unittest.main()
