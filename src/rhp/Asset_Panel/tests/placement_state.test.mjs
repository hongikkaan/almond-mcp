import {test} from 'node:test';
import assert from 'node:assert/strict';
import {modelPlacementState, modelPlacementAction, placementNotice} from '../web/placement-state.mjs';

test('registered 3DM is placeable regardless of generated or imported origin', () => {
  for (const id of ['gen-chair-1', 'drawing-chair-1', 'Desk.02_A']) {
    assert.equal(modelPlacementState({id, kind:'model', format:'3dm', available:true,
      model:'/files/drawing/registered/chair/model.3dm', model_status:'ready'}), 'ready');
  }
});

test('source-only GLB never enables placement and explains the conversion', () => {
  const source = {kind:'model', format:'glb', available:true, model:'/files/generated/chair.glb'};
  assert.equal(modelPlacementState(source), 'needs_conversion');
  assert.match(placementNotice(source), /3DM conversion/);
});

test('changed, missing and 2D records cannot be mistaken for ready 3DM sources', () => {
  assert.equal(modelPlacementState({kind:'model', format:'3dm', available:true, model:'/m', model_status:'needs_refresh'}), 'needs_refresh');
  assert.equal(modelPlacementState({kind:'model', format:'3dm', available:true, model:null}), 'missing');
  assert.equal(modelPlacementState({kind:'element', format:'svg', available:true, model:'/s'}), 'not_model');
});

test('unverified sources require verification rather than claiming ready', () => {
  const source = {kind:'model', format:'3dm', available:true, model:'/m', model_status:'unverified'};
  assert.equal(modelPlacementState(source), 'unverified');
  assert.equal(modelPlacementAction(source), 'Verify & place');
  assert.equal(modelPlacementAction({...source, model_status:'needs_refresh'}), '');
  assert.equal(modelPlacementAction({...source, model_status:'ready'}), 'Place');
});
