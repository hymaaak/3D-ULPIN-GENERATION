import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

export function login(credentials) {
  return unwrap(client.post('/auth/login', credentials));
}

export function register(payload) {
  return unwrap(client.post('/auth/register', payload));
}

export function fetchMe() {
  return unwrap(client.get('/auth/me'));
}

export function refreshToken() {
  return unwrap(client.post('/auth/refresh'));
}

// Admin user management — the backend may not expose this endpoint; callers
// must tolerate a 404.
export function listUsers() {
  return unwrap(client.get('/auth/users'));
}
