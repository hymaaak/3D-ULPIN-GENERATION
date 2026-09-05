import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Decode a JWT payload without verifying the signature (client-side only,
// used to recover the user role when the profile endpoint is unavailable).
export function decodeJwt(token) {
  try {
    const payload = token.split('.')[1];
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,

      setAuth: (token, user) => {
        const decoded = decodeJwt(token);
        set({
          token,
          user: user || (decoded ? { email: decoded.sub, role: decoded.role } : null),
        });
      },

      setUser: (user) => set({ user }),

      logout: () => set({ token: null, user: null }),

      isAuthenticated: () => Boolean(get().token),

      // Role from the stored profile first, then from the JWT payload.
      role: () => {
        const { token, user } = get();
        return user?.role || decodeJwt(token)?.role || null;
      },
    }),
    { name: 'ulpin-auth' },
  ),
);
