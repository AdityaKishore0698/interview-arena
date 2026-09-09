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
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      isAuthenticated: () => !!get().token,
    }),
    {
      name: 'auth-storage', // saves to localStorage
    }
  )
);
