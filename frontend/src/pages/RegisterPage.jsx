import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import * as authApi from '../api/auth.js';
import { useAuth } from '../hooks/useAuth.js';

const ROLES = ['citizen', 'surveyor', 'urban_planner', 'validator', 'admin'];

export default function RegisterPage() {
  const { isAuthenticated, setAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'citizen',
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await authApi.register(form);
      const token = data.access_token || data.token || data.accessToken;
      if (token) {
        // Backend returned a session — go straight to the dashboard.
        setAuth(token, data.user || null);
        navigate('/', { replace: true });
      } else {
        navigate('/login', { replace: true });
      }
    } catch (err) {
      setError(
        err?.response?.data?.detail || err?.message || 'Registration failed — check the backend.',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center bg-slate-100">
      <div className="card w-full max-w-sm p-6">
        <div className="mb-6 text-center">
          <div className="text-xl font-bold text-slate-800">Create account</div>
          <div className="text-sm text-slate-500">3D ULPIN Cadastre Portal</div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="text"
            required
            className="input"
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <input
            type="email"
            required
            className="input"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <input
            type="password"
            required
            minLength={6}
            className="input"
            placeholder="Password (min 6 chars)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <select
            className="input"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          {error && <div className="text-xs text-red-600">{error}</div>}
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? 'Creating…' : 'Register'}
          </button>
        </form>
        <div className="mt-4 text-center text-xs text-slate-500">
          Already registered?{' '}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
