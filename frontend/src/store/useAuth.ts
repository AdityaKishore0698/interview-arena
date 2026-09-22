import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserType = 'GUEST' | 'REGISTERED';

export interface User {
  id: string;
  type: UserType;
  display_name?: string;
  email?: string;
  avatar_url?: string | null;
}

interface AuthState {
  token: string | null;
  user: User | null;
  /** Transient, not persisted — a message to surface once (e.g. "session expired"). */
  authNotice: string | null;
  /** False until zustand/persist has read localStorage on the client. On a
   * server-rendered page this is always false for the first client render
   * too (matching the server's `user: null`, to avoid a hydration
   * mismatch) — a page that redirects unauthenticated visitors away should
   * wait for this before trusting a null `user`, or it can act on a stale
   * "not logged in" read and redirect a real session away. See ProfilePage
   * for the pattern; other pages have this same latent race but are out of
   * scope for this change. */
  hasHydrated: boolean;
  setAuth: (token: string, user: User) => void;
  updateUser: (patch: Partial<User>) => void;
  logout: () => void;
  logoutWithNotice: (notice: string) => void;
  clearAuthNotice: () => void;
  isAuthenticated: () => boolean;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      authNotice: null,
      hasHydrated: false,
      setAuth: (token, user) => set({ token, user }),
      updateUser: (patch) => set((s) => (s.user ? { user: { ...s.user, ...patch } } : {})),
      logout: () => set({ token: null, user: null }),
      logoutWithNotice: (notice) => set({ token: null, user: null, authNotice: notice }),
      clearAuthNotice: () => set({ authNotice: null }),
      isAuthenticated: () => !!get().token,
    }),
    {
      name: 'auth-storage', // saves to localStorage
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => () => {
        useAuth.setState({ hasHydrated: true });
      },
    }
  )
);
