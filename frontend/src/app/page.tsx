'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import { api, API_BASE_URL } from '@/lib/api';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowRight } from 'lucide-react';
import { ThemeToggle } from '@/components/layout/ThemeToggle';

function AuthContent() {
  const { user, setAuth } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [loadingGuest, setLoadingGuest] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Check if we came from Google OAuth redirect
    const token = searchParams.get('token');
    if (token) {
      api.get('/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } })
        .then(res => {
          setAuth(token, res.data);
          router.replace('/dashboard');
        })
        .catch(() => {
          setError('Failed to authenticate with Google.');
          router.replace('/');
        });
    } else if (user) {
      router.push('/dashboard');
    }
  }, [user, router, searchParams, setAuth]);

  const handleGuestLogin = async () => {
    setLoadingGuest(true);
    setError(null);
    try {
      const res = await api.post('/api/v1/auth/guest');
      const data = res.data;
      setAuth(data.access_token, {
        id: data.guest_id,
        type: 'GUEST',
        display_name: 'Guest User',
      });
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('Guest login failed:', err);
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to authenticate as guest');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoadingGuest(false);
    }
  };

  const [mode, setMode] = useState<'login' | 'register' | 'verify'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [otp, setOtp] = useState('');
  const [loadingAuth, setLoadingAuth] = useState(false);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setLoadingAuth(true);
    setError(null);
    try {
      if (mode === 'register') {
        if (!password || !displayName) {
          setError('Display name and password required');
          setLoadingAuth(false);
          return;
        }
        await api.post('/api/v1/auth/otp/send', { email, password, display_name: displayName });
        setMode('verify');
        setLoadingAuth(false);
        return;
      }
      
      if (mode === 'verify') {
        if (!otp) return;
        const res = await api.post('/api/v1/auth/otp/verify', { email, otp });
        const data = res.data;
        const meRes = await api.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${data.access_token}` }
        });
        setAuth(data.access_token, meRes.data);
        router.push('/dashboard');
        return;
      }

      // Login
      const res = await api.post('/api/v1/auth/login', { email, password });
      const data = res.data;
      
      const meRes = await api.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });
      
      setAuth(data.access_token, meRes.data);
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('Auth failed:', err);
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || `Failed to ${mode}`);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoadingAuth(false);
    }
  };

  if (user) return null;

  return (
    <div className="relative z-10 flex w-full items-center justify-center border-t border-border/60 bg-surface/40 p-8 backdrop-blur-md md:w-[480px] md:border-t-0 md:border-l md:p-12 lg:w-[540px]">
      <div className="w-full max-w-sm space-y-8">

        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">Access the Arena</h2>
          <p className="text-sm text-muted-foreground">Sign in to your account or continue as a guest to start practicing immediately.</p>
        </div>

        {error && (
          <div className="rounded-r-md border-l-2 border-destructive bg-destructive/10 p-4 text-sm text-destructive" aria-live="polite">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <Button
            type="button"
            variant="outline"
            className="h-12 w-full border-border-strong bg-surface-elevated font-medium hover:bg-surface"
            onClick={() => window.location.href = `${API_BASE_URL}/api/v1/auth/google/login`}
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
            Continue with Google
          </Button>

          <div className="relative py-2 flex items-center justify-center">
            <span className="absolute w-full h-px bg-border/40" />
            <span className="relative bg-surface px-4 text-xs font-medium uppercase tracking-widest text-muted-foreground/70">Or email</span>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {mode === 'verify' ? (
              <>
                <p className="text-sm text-muted-foreground">We sent a verification code to {email}</p>
                <input 
                  placeholder="6-digit OTP" 
                  type="text" 
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary tracking-widest"
                  maxLength={6}
                  required
                />
              </>
            ) : (
              <>
                {mode === 'register' && (
                  <input 
                    placeholder="Display Name" 
                    type="text" 
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                    required
                  />
                )}
                <input 
                  placeholder="Email address" 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                  required
                />
                <input 
                  placeholder="Password" 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                  required
                />
              </>
            )}
            
            <Button type="submit" className="h-12 w-full justify-between" disabled={loadingAuth || loadingGuest}>
              {loadingAuth && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {mode === 'login' ? 'Sign In' : mode === 'register' ? 'Create Account' : 'Verify & Complete'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          {mode !== 'verify' && (
            <div className="text-center">
              <button 
                type="button" 
                onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
                className="text-sm text-primary hover:underline transition-all"
              >
                {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign in'}
              </button>
            </div>
          )}
          
          <div className="relative py-6 flex items-center justify-center">
            <span className="absolute w-full h-px bg-border/40" />
            <span className="relative bg-surface px-4 text-xs font-medium uppercase tracking-widest text-muted-foreground/70">Or</span>
          </div>
          
          <Button
            type="button"
            className="group relative h-12 w-full justify-between overflow-hidden border-0 bg-primary-gradient text-white shadow-glow transition-all duration-300 hover:scale-[1.02] hover:shadow-glow-strong active:scale-[0.98]"
            onClick={handleGuestLogin}
            disabled={loadingGuest || loadingAuth}
          >
            <span className="relative z-10 flex items-center font-medium">
              {loadingGuest && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Continue as Guest
            </span>
            <ArrowRight className="h-4 w-4 relative z-10 transition-transform group-hover:translate-x-1" />
          </Button>

          <p className="text-xs text-center text-muted-foreground pt-4">
            Guest accounts are temporary and securely cleared after your session.
          </p>
        </div>
      </div>
    </div>
  );
}

const VALUE_PROPS = [
  'Server-authoritative rounds — timers and state never drift between peers.',
  'Automatic role reversal so you practice both sides of the table.',
  'Structured 1–5 rubric feedback captured the moment each round ends.',
];

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden text-foreground md:flex-row">
      {/* Absolute Header for Theme Switcher */}
      <div className="absolute top-0 right-0 z-50 p-6">
        <ThemeToggle />
      </div>

      {/* Left Panel: Brand & Value Prop */}
      <div className="relative z-10 flex flex-1 flex-col justify-center px-8 py-14 md:px-16 md:py-0 lg:px-24">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" aria-hidden />
        <div className="relative max-w-xl space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-surface/60 px-3 py-1 text-xs font-medium tracking-wide text-muted-foreground backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Peer-powered mock interviews
          </div>
          <h1 className="flex flex-wrap items-center gap-x-4 gap-y-2 text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
            <span className="font-mono text-primary">&lt;/&gt;</span>
            <span className="text-gradient">Interview Arena</span>
          </h1>
          <p className="text-lg leading-relaxed text-muted-foreground md:text-xl">
            Elevate your engineering career through rigorous, structured peer interviews. Practice
            under real conditions, receive actionable feedback, and master your next technical screen.
          </p>
          <ul className="space-y-3 pt-2">
            {VALUE_PROPS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sm text-foreground/80">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/70" />
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Right Panel: Authentication Controls */}
      <Suspense fallback={<div className="flex w-full items-center justify-center md:w-[540px]"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
        <AuthContent />
      </Suspense>
    </div>
  );
}
