'use client';

import { useAuth } from '@/store/useAuth';
import { Button } from '@/components/ui/button';
import { LogOut, UserCog } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ThemeToggle } from './ThemeToggle';

import { api } from '@/lib/api';

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await api.post('/api/v1/auth/logout');
    } catch {
      // Ignore API errors on logout
    }
    logout();
    router.push('/');
  };

  return (
    <nav className="sticky top-0 z-50 flex h-16 items-center border-b border-border/60 bg-background/70 px-6 backdrop-blur-md lg:px-8">
      <button
        type="button"
        className="group flex flex-1 items-center gap-2 text-lg font-bold tracking-tight"
        onClick={() => router.push(user ? '/dashboard' : '/')}
      >
        <div className="flex items-center font-mono text-lg font-bold text-primary transition-transform group-hover:-translate-y-px">
          &lt;/&gt;
        </div>
        Interview Arena
      </button>

      <div className="flex items-center gap-4 sm:gap-6">
        <ThemeToggle />
        {user && (
          <div className="flex items-center gap-4 border-l border-border/60 pl-4 sm:pl-6">
            <div className="hidden flex-col items-end leading-none sm:flex">
              <span className="text-sm font-medium text-foreground">{user.display_name || 'Guest'}</span>
              <span className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">{user.type}</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push('/account')}
              title="Account Settings"
              className="rounded-full text-muted-foreground transition-all hover:bg-surface hover:text-foreground"
            >
              <UserCog className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="Logout"
              className="rounded-full text-muted-foreground transition-all hover:bg-destructive/10 hover:text-destructive"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </nav>
  );
}
