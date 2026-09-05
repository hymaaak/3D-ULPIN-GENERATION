import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listOwners(params) {
  return unwrap(client.get('/owners', { params }));
}

export function getOwner(id) {
  return unwrap(client.get(`/owners/${id}`));
}

export function createOwner(payload) {
  return unwrap(client.post('/owners', payload));
}
