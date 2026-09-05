import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

// Step 3 of the presigned flow: trigger the AI pipeline on the uploaded source.
export function triggerJob(payload) {
  return unwrap(client.post('/jobs/trigger', payload));
}

export function getJob(id) {
  return unwrap(client.get(`/jobs/${id}`));
}

export function listJobs(params) {
  return unwrap(client.get('/jobs', { params }));
}

// WebSocket URL for /ws/jobs/{id}. Derives the host from VITE_API_BASE_URL
// when it points at a real backend; otherwise uses the page origin so the
// Vite dev proxy (or nginx) handles the /ws upgrade.
export function jobSocketUrl(id) {
  const base = import.meta.env.VITE_API_BASE_URL || '';
  if (/^https?:\/\//.test(base)) {
    const wsBase = base.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '');
    return `${wsBase}/ws/jobs/${id}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/jobs/${id}`;
}
