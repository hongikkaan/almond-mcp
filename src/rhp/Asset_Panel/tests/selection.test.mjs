import test from 'node:test';
import assert from 'node:assert/strict';
import {modelPlacementState, modelPlacementAction, placementNotice} from '../web/placement-state.mjs';
import {filterRows, sortRows, memberRows} from '../web/results-view.mjs';

test('placement offers actions only for installed, usable 3DM models', () => {
  const ready = {kind:'model', format:'3dm', model_status:'ready', available:true, model:'chair.3dm'};
  assert.equal(modelPlacementAction(ready), 'Place');
  assert.equal(modelPlacementAction({...ready, model_status:'unknown'}), 'Verify & place');
  for (const bad of [{source_only:true}, {model_status:'needs_refresh'}, {available:false}, {model:''}, {format:'glb'}]) {
    assert.equal(modelPlacementAction({...ready, ...bad}), '');
  }
  assert.equal(modelPlacementState({kind:'drawing'}), 'not_model');
  assert.match(placementNotice({...ready, model_status:'needs_refresh'}), /refresh/i);
});

test('result selection and sorting preserve partial and missing data', () => {
  const rows = memberRows({result:{results:{per_element_utilization:[{source_guids:['abc'], utilization:1.2},{source_guids:['def']}]}}});
  assert.equal(rows[0].partial, true);
  assert.deepEqual(filterRows(rows, 'fail', 'ABC').map(r => r.id), ['M1']);
  assert.deepEqual(sortRows(rows, 'utilization').map(r => r.id), ['M1', 'M2']);
  assert.equal(rows[1].utilization, null);
});
