import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserType = 'GUEST' | 'REGISTERED';

export interface User {
  id: string;
  type: UserType;
  display_name?: string;
  email?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  /** Transient, not persisted — a message to surface once (e.g. "session expired"). */
  authNotice: string | null;
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
    }
  )
);
