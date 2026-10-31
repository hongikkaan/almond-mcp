export function modelPlacementState(asset) {
  if (asset?.kind !== 'model') return 'not_model';
  if (asset.source_only || asset.model_status === 'needs_conversion' || asset.format !== '3dm') return 'needs_conversion';
  if (asset.model_status === 'needs_refresh') return 'needs_refresh';
  if (asset.available !== true || typeof asset.model !== 'string' || !asset.model) return 'missing';
  return asset.model_status === 'ready' ? 'ready' : 'unverified';
}

export function modelPlacementAction(asset) {
  const state = modelPlacementState(asset);
  return state === 'ready' ? 'Place' : state === 'unverified' ? 'Verify & place' : '';
}

export function placementNotice(asset) {
  const state = modelPlacementState(asset);
  return state === 'needs_conversion' ? '3DM conversion required' :
    state === 'needs_refresh' ? 'Source changed; refresh asset' :
    state === 'missing' ? '3DM source not installed' : '';
}
