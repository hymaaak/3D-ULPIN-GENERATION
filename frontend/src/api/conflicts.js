import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listConflicts(params) {
  return unwrap(client.get('/conflicts', { params }));
}

export function getConflict(id) {
  return unwrap(client.get(`/conflicts/${id}`));
}

export function resolveConflict(id, payload) {
  return unwrap(client.put(`/conflicts/${id}/resolve`, payload || {}));
}

export function detectConflicts(payload) {
  return unwrap(client.post('/conflicts/detect', payload || {}));
}
