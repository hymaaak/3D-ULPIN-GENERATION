import { useAuthStore } from '../stores/authStore.js';

// Central auth hook: session state + helpers backed by the persisted
// zustand store (JWT survives reloads via localStorage).
export function useAuth() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const setAuth = useAuthStore((s) => s.setAuth);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const role = useAuthStore((s) => s.role);

  return {
    token,
    user,
    role: user?.role || role?.() || null,
    isAuthenticated: Boolean(token),
    isAdmin: (user?.role || role?.()) === 'admin',
    setAuth,
    setUser,
    logout,
  };
}
