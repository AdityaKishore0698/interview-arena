'use client';

import { AlertTriangle, X } from 'lucide-react';
import { useAuth } from '@/store/useAuth';

/**
 * A dismissible banner for transient auth events — currently just
 * "your session expired" — so a logout is never silent. Mounted once in
 * the root layout so it survives whatever redirect follows the logout.
 */
export function AuthNotice() {
  const authNotice = useAuth((s) => s.authNotice);
  const clearAuthNotice = useAuth((s) => s.clearAuthNotice);

  if (!authNotice) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-[100] flex justify-center px-4 pt-4 animate-in fade-in slide-in-from-top-2 duration-300">
      <div className="flex w-full max-w-md items-center gap-3 rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning shadow-elev-md backdrop-blur-md">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-foreground/90">{authNotice}</span>
        <button
          type="button"
          onClick={clearAuthNotice}
          aria-label="Dismiss"
          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-warning/20 hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
