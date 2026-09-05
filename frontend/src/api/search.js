import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function searchUlpin(params) {
  return unwrap(client.get('/search/ulpin', { params }));
}

export function searchOwner(params) {
  return unwrap(client.get('/search/owner', { params }));
}

export function searchSpatial(payload) {
  return unwrap(client.post('/search/spatial', payload));
}
