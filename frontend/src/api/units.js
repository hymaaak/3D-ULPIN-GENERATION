import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function listUnits(params) {
  return unwrap(client.get('/units', { params }));
}

export function getUnit(id) {
  return unwrap(client.get(`/units/${id}`));
}

export function createUnit(payload) {
  return unwrap(client.post('/units', payload));
}

export function getUnitOwnership(id) {
  return unwrap(client.get(`/units/${id}/ownership`));
}

export function getUnitByUlpin(ulpin) {
  return unwrap(client.get(`/units/ulpin/${encodeURIComponent(ulpin)}`));
}
