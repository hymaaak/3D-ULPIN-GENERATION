import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listParcels(params) {
  return unwrap(client.get('/parcels', { params }));
}

export function getParcel(id) {
  return unwrap(client.get(`/parcels/${id}`));
}

export function createParcel(payload) {
  return unwrap(client.post('/parcels', payload));
}

export function updateParcel(id, payload) {
  return unwrap(client.put(`/parcels/${id}`, payload));
}

export function deleteParcel(id) {
  return unwrap(client.delete(`/parcels/${id}`));
}

export function getParcelBuildings(id) {
  return unwrap(client.get(`/parcels/${id}/buildings`));
}

export function getParcelTiles(id) {
  return unwrap(client.get(`/parcels/${id}/3d-tiles`));
}

export function searchParcelsGeo(payload) {
  return unwrap(client.post('/parcels/search', payload));
}
