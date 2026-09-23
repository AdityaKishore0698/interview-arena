'use client';

import { useAuth } from '@/store/useAuth';
import { Button } from '@/components/ui/button';
import { LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ThemeToggle } from './ThemeToggle';

import { api } from '@/lib/api';
import { StreakBadge } from './StreakBadge';
import { Avatar } from './Avatar';

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
        {user && <StreakBadge />}
        {user && (
          <div className="flex items-center gap-4 border-l border-border/60 pl-4 sm:pl-6">
            <button
              type="button"
              onClick={() => router.push('/profile')}
              title="View profile"
              className="hidden flex-col items-end leading-none sm:flex"
            >
              <span className="text-sm font-medium text-foreground hover:text-primary hover:underline">{user.display_name || 'Guest'}</span>
              <span className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">{user.type}</span>
            </button>
            <button
              type="button"
              onClick={() => router.push('/profile')}
              title="View profile"
              className="rounded-full ring-offset-2 ring-offset-background transition-all hover:ring-2 hover:ring-primary/40"
            >
              <Avatar name={user.display_name || 'Guest'} src={user.avatar_url} size={32} />
            </button>
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
