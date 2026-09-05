import { useQuery } from '@tanstack/react-query';
import * as authApi from '../api/auth.js';
import { useAuth } from '../hooks/useAuth.js';
import { asList } from '../utils/constants.js';

const ALL_ROLES = ['admin', 'surveyor', 'urban_planner', 'validator', 'citizen'];

// Admin-only panel. The backend may not expose a user-management endpoint
// (GET /api/v1/auth/users is not in the spec) — everything here degrades
// gracefully to the current user's profile when that call 404s.
export default function AdminPanel() {
  const { user } = useAuth();

  const meQ = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.fetchMe(),
    retry: false,
  });

  const usersQ = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      try {
        return await authApi.listUsers();
      } catch (err) {
        if (err?.response?.status === 404 || err?.response?.status === 403) return null;
        throw err;
      }
    },
    retry: false,
  });

  const users = usersQ.data ? asList(usersQ.data) : [];
  const me = meQ.data || user;

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-800">Current Session</h2>
        {me ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-600 md:grid-cols-4">
            <div>
              Name: <span className="font-medium text-slate-800">{me.full_name || '—'}</span>
            </div>
            <div>
              Email: <span className="font-medium text-slate-800">{me.email || '—'}</span>
            </div>
            <div>
              Role: <span className="font-medium capitalize text-slate-800">{me.role || '—'}</span>
            </div>
            <div>
              Department: <span className="font-medium text-slate-800">{me.department || '—'}</span>
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-500">
            Profile endpoint unavailable — role taken from the login session.
          </div>
        )}
      </div>

      <div className="card p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Users</h2>
        {usersQ.isLoading ? (
          <div className="text-sm text-slate-500">Loading users…</div>
        ) : usersQ.data === null ? (
          <div className="text-sm text-slate-500">
            The backend does not expose a user-management endpoint (GET /api/v1/auth/users
            returned 404/403). Role management must be done via the API database or a future
            admin endpoint.
          </div>
        ) : usersQ.isError ? (
          <div className="text-sm text-slate-500">Could not load users — backend unreachable.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-slate-400">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Email</th>
                  <th className="pb-2">Role</th>
                  <th className="pb-2">Active</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.user_id || u.id || i} className="border-t border-slate-100">
                    <td className="py-2">{u.full_name || '—'}</td>
                    <td className="py-2 text-xs">{u.email || '—'}</td>
                    <td className="py-2">
                      <span className="badge bg-brand-50 capitalize text-brand-700">
                        {u.role || 'citizen'}
                      </span>
                    </td>
                    <td className="py-2 text-xs">{u.is_active === false ? 'No' : 'Yes'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-800">Roles in this system</h2>
        <div className="flex flex-wrap gap-2">
          {ALL_ROLES.map((r) => (
            <span key={r} className="badge bg-slate-100 capitalize text-slate-700">
              {r.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Role-based access is enforced by the backend (<span className="font-mono">require_role</span>{' '}
          decorator); the frontend only gates navigation.
        </p>
      </div>
    </div>
  );
}
