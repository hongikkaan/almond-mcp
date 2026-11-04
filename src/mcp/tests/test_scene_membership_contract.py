"""Disposable Scene membership contract tests; no live Rhino or user DB."""
import json
import tempfile
import unittest
from pathlib import Path

from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.features.scenes.observation import observe_objects

MODEL = r'C:\fixture\house.3dm'
A = '00000000-0000-0000-0000-000000000101'
B = '00000000-0000-0000-0000-000000000102'
MISSING = '00000000-0000-0000-0000-000000000103'

class SceneMembershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AlmondStore(Path(self.tmp.name) / 'test.sqlite3')
        self.scene = self.store.create_scene('Test')['scene_id']
        self.objs = {A: {'rhino_guid': A, 'name': 'Wall', 'object_type': 'Brep'},
                     B: {'rhino_guid': B, 'name': 'Clip', 'object_type': 'ClipPlane'}}
        self.store._scene_group_objects = lambda *args: [self.objs[A]]
        self.observe = lambda model, ids: ({x: self.objs[x] for x in ids if x in self.objs}, set(ids) - set(self.objs))

    def tearDown(self): self.tmp.cleanup()

    def change(self, ids, add):
        return self.store.change_scene_objects(self.scene, MODEL, ids, add, lambda _: None, self.observe)

    def objects(self):
        return self.store.scene_objects(self.scene, MODEL, lambda _: None, self.observe)

    def test_mixed_batches_and_live_union(self):
        result = self.change([B, A, MISSING, B, 'not-guid'], True)
        self.assertEqual(result, {'failed_indices': [2, 4], 'already_present_indices': [1, 3]})
        self.assertEqual({o['rhino_guid'] for o in self.objects()}, {A, B})
        self.assertEqual(next(o for o in self.objects() if o['rhino_guid'] == B)['object_type'], 'ClipPlane')
        self.assertIsNone(self.store.get_scene(self.scene)['objects'])
        self.assertEqual(self.change([A, B, B, MISSING, 'bad'], False),
                         {'failed_indices': [4], 'already_absent_indices': [2, 3]})
        self.assertEqual(self.objects(), [])
        self.assertEqual(self.change([A], True), {'failed_indices': [], 'already_present_indices': []})
        self.assertEqual([o['rhino_guid'] for o in self.objects()], [A])
        reopened = AlmondStore(Path(self.tmp.name) / 'test.sqlite3')
        self.assertEqual(reopened.get_scene(self.scene)['scene_id'], self.scene)

    def test_missing_direct_object_can_be_removed(self):
        self.change([B], True)
        del self.objs[B]
        with self.assertRaisesRegex(ValueError, 'absent'):
            self.objects()
        self.assertEqual(self.change([B], False)['already_absent_indices'], [])
        self.assertEqual([o['rhino_guid'] for o in self.objects()], [A])

    def test_observer_isolates_missing_without_disclosing_guids(self):
        def send(payload):
            req = json.loads(payload)
            if req['type'] == 'get_rhino_context':
                return json.dumps({'status': 'success', 'capabilities': {'object_observation': 2}})
            ids = req['object_ids']
            if MISSING in ids:
                return json.dumps({'status': 'error', 'error_code': 'invalid_arguments', 'message': 'IDs are not top-level model objects: ' + MISSING})
            return json.dumps({'status': 'success', 'complete': True, 'model_path': MODEL,
                               'document_units': 'Meters', 'objects': [{'id': v, 'name': 'x', 'object_type': 'ClipPlane', 'bounds': {'min': [0, 1, 2], 'max': [3, 4, 5]}} for v in ids]})
        found, missing = observe_objects(send, MODEL, [A, MISSING, B])
        self.assertEqual(set(found), {A, B})
        self.assertEqual(found[B]['bounds_mm'], [0, 1000, 2000, 3000, 4000, 5000])
        self.assertEqual(missing, {MISSING})

if __name__ == '__main__': unittest.main()
