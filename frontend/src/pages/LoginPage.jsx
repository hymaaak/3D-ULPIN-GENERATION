import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import * as authApi from '../api/auth.js';
import { useAuth } from '../hooks/useAuth.js';

export default function LoginPage() {
  const { isAuthenticated, setAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={location.state?.from || '/'} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await authApi.login(form);
      const token = data.access_token || data.token || data.accessToken;
      if (!token) throw new Error('Login response did not include a token');
      setAuth(token, data.user || null);
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      setError(
        err?.response?.data?.detail || err?.message || 'Login failed — check credentials and backend.',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center bg-slate-100">
      <div className="card w-full max-w-sm p-6">
        <div className="mb-6 text-center">
          <div className="text-xl font-bold text-slate-800">3D ULPIN</div>
          <div className="text-sm text-slate-500">Vertical Property Mapping System</div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
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
            className="input"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          {error && <div className="text-xs text-red-600">{error}</div>}
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="mt-4 text-center text-xs text-slate-500">
          No account?{' '}
          <Link to="/register" className="font-medium text-brand-600 hover:underline">
            Register
          </Link>
        </div>
        <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
          Demo hint: seed data creates <span className="font-mono">admin@ulpin.gov.in</span>.
        </div>
      </div>
    </div>
  );
}
