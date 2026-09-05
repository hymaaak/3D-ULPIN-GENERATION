import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listBuildings(params) {
  return unwrap(client.get('/buildings', { params }));
}

export function getBuilding(id) {
  return unwrap(client.get(`/buildings/${id}`));
}

export function createBuilding(payload) {
  return unwrap(client.post('/buildings', payload));
}

export function getBuildingUnits(id) {
  return unwrap(client.get(`/buildings/${id}/units`));
}
