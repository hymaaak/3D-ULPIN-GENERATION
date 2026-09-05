import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listOwnership(params) {
  return unwrap(client.get('/ownership', { params }));
}

export function createOwnership(payload) {
  return unwrap(client.post('/ownership', payload));
}

export function updateOwnership(id, payload) {
  return unwrap(client.put(`/ownership/${id}`, payload));
}

export function getOwnershipHistory(unitId) {
  return unwrap(client.get(`/ownership/history/${unitId}`));
}
