import axios from 'axios';
import { useAuth } from '@/store/useAuth';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercept requests to attach JWT token
api.interceptors.request.use((config) => {
  const token = useAuth.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Requests where a 401 means "wrong credentials", not "your session expired" —
// these happen while there's no active session yet, so they shouldn't show
// the session-expired notice or clear a (nonexistent) session.
const UNAUTHENTICATED_ROUTES = ['/api/v1/auth/login', '/api/v1/auth/guest'];

// Intercept responses to handle global 401 unauthenticated
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url: string = error.config?.url || '';
      const isAuthAttempt = UNAUTHENTICATED_ROUTES.some((path) => url.includes(path));
      const hadSession = !!useAuth.getState().token;
      if (!isAuthAttempt && hadSession) {
        useAuth.getState().logoutWithNotice('Your session has expired. Please sign in again.');
      } else {
        useAuth.getState().logout();
      }
    }
    return Promise.reject(error);
  }
);
