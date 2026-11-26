import assert from 'node:assert/strict';
import test from 'node:test';
import {modelPlacementAction, placementNotice} from '../web/placement-state.mjs';
import {filterRows, memberRows, sortRows} from '../web/results-view.mjs';

test('placement follows verification and source refresh status', () => {
  const installed = {kind: 'model', format: '3dm', available: true, model: 'chair.3dm'};

  assert.equal(modelPlacementAction(installed), 'Verify & place');
  assert.equal(modelPlacementAction({...installed, model_status: 'ready'}), 'Place');

  const stale = {...installed, model_status: 'needs_refresh'};
  assert.equal(modelPlacementAction(stale), '');
  assert.match(placementNotice(stale), /refresh/i);

  const conversion = {...installed, format: 'glb', model_status: 'ready'};
  assert.equal(modelPlacementAction(conversion), '');
  assert.match(placementNotice(conversion), /3DM conversion/i);
});

test('Karamba rows remain selectable by model object and keep unreported utilization blank', () => {
  const report = {result: {results: {per_element_utilization: [
    {source_guids: ['3D119A'], utilization: 1.26},
    {source_guids: ['AE842B']},
    {source_guids: ['CC3300'], utilization: 0},
  ]}}};
  const rows = memberRows(report);
  const selected = filterRows(rows, 'fail', '3d119a');
  assert.deepEqual(selected.map(row => [row.id, row.source_guids, row.partial]), [
    ['M1', ['3D119A'], true],
  ]);
  assert.deepEqual(sortRows(rows, 'utilization', 1).map(row => [row.id, row.utilization]), [
    ['M3', 0],
    ['M1', 1.26],
    ['M2', null],
  ]);
});
