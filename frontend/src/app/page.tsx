'use client';

import { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import { api, API_BASE_URL } from '@/lib/api';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowRight, CheckCircle2 } from 'lucide-react';
import { ThemeToggle } from '@/components/layout/ThemeToggle';

type Mode = 'login' | 'register' | 'forgot' | 'reset';

const RESET_TTL_SECONDS = 900;

function useCountdown(active: boolean, seconds: number, restartKey = 0) {
  const [remaining, setRemaining] = useState(seconds);

  // Re-sync during render when the countdown (re)activates or is restarted
  // (a new code was issued) — this is React's sanctioned pattern for "adjust
  // state when a condition changes" and avoids a synchronous setState in the
  // effect body below.
  const [wasActive, setWasActive] = useState(active);
  const [syncedKey, setSyncedKey] = useState(restartKey);
  if (active !== wasActive || restartKey !== syncedKey) {
    setWasActive(active);
    setSyncedKey(restartKey);
    if (active) setRemaining(seconds);
  }

  useEffect(() => {
    if (!active) return;
    const interval = setInterval(() => {
      setRemaining((r) => Math.max(0, r - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [active]);
  return remaining;
}

function formatMMSS(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function AuthContent() {
  const { user, setAuth, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [loadingGuest, setLoadingGuest] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

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
      if (searchParams.get('mode') === 'register' && user.type === 'GUEST') {
        // A guest deep-linking into "create a free account" (e.g. from the
        // dashboard history upsell) — abandon the ephemeral guest session
        // instead of bouncing them back to /dashboard.
        logout();
      } else {
        router.push('/dashboard');
      }
    }
  }, [user, router, searchParams, setAuth, logout]);

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

  const [mode, setMode] = useState<Mode>(() =>
    searchParams.get('mode') === 'register' ? 'register' : 'login'
  );

  // Next.js can reuse an already-mounted `/` instance for a client-side nav
  // (e.g. the guest "Create a free account" deep link), which skips the
  // lazy initializer above. Re-sync during render (React's sanctioned
  // pattern for this) whenever the query param itself changes, without
  // fighting a manual mode switch the user makes afterwards.
  const [syncedSearchParams, setSyncedSearchParams] = useState(searchParams);
  if (searchParams !== syncedSearchParams) {
    setSyncedSearchParams(searchParams);
    if (searchParams.get('mode') === 'register') setMode('register');
  }
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [resetOtp, setResetOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loadingAuth, setLoadingAuth] = useState(false);
  // DEMO recovery: the backend returns the reset code instead of emailing it.
  const [demoCode, setDemoCode] = useState<string | null>(null);
  const [codeVersion, setCodeVersion] = useState(0);

  const resetTimeLeft = useCountdown(mode === 'reset', RESET_TTL_SECONDS, codeVersion);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setInfoMessage(null);
  };

  // Ask the backend for a DEMO reset code and show it on the reset screen.
  const requestResetCode = async () => {
    const res = await api.post('/api/v1/auth/password/forgot', { email });
    const code: string = res.data.demo_code;
    setDemoCode(code);
    setResetOtp(code);
    setCodeVersion((v) => v + 1);
  };

  const handleNewCode = async () => {
    setLoadingAuth(true);
    setError(null);
    try {
      await requestResetCode();
    } catch (err: unknown) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Failed to get a new code' : 'An unexpected error occurred');
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setLoadingAuth(true);
    setError(null);
    setInfoMessage(null);
    try {
      if (mode === 'register') {
        if (!password || !displayName) {
          setError('Display name and password required');
          setLoadingAuth(false);
          return;
        }
        // The account is created and a JWT returned in one step — no email
        // verification — so sign straight in, exactly like the login path.
        const res = await api.post('/api/v1/auth/register', {
          email,
          password,
          display_name: displayName,
        });
        const data = res.data;
        const meRes = await api.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${data.access_token}` }
        });
        setAuth(data.access_token, meRes.data);
        router.push('/dashboard');
        return;
      }

      if (mode === 'forgot') {
        await requestResetCode();
        switchMode('reset');
        setLoadingAuth(false);
        return;
      }

      if (mode === 'reset') {
        if (!resetOtp || !newPassword) return;
        if (newPassword !== confirmPassword) {
          setError('Passwords do not match');
          setLoadingAuth(false);
          return;
        }
        await api.post('/api/v1/auth/password/reset', { email, otp: resetOtp, new_password: newPassword });
        switchMode('login');
        setPassword('');
        setDemoCode(null);
        setResetOtp('');
        setNewPassword('');
        setConfirmPassword('');
        setInfoMessage('Password updated. Sign in with your new password.');
        setLoadingAuth(false);
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
        // FastAPI validation errors (422) come back as a list of {msg} objects.
        const detail = err.response?.data?.detail;
        setError(
          typeof detail === 'string' ? detail
            : Array.isArray(detail) && detail[0]?.msg ? String(detail[0].msg).replace(/^Value error, /, '')
            : `Failed to ${mode}`
        );
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoadingAuth(false);
    }
  };

  if (user) return null;

  const heading =
    mode === 'forgot' ? 'Reset your password' :
    mode === 'reset' ? 'Choose a new password' :
    'Access the Arena';
  const subheading =
    mode === 'forgot' ? "Enter your account email to get a demo reset code. No email is sent." :
    mode === 'reset' ? 'Use the demo reset code below and choose a new password.' :
    'Sign in to your account or continue as a guest to start practicing immediately.';

  return (
    <div className="relative z-10 flex w-full items-center justify-center border-t border-border/60 bg-surface/40 p-8 backdrop-blur-md md:w-[480px] md:border-t-0 md:border-l md:p-12 lg:w-[540px]">
      <div className="w-full max-w-sm space-y-8">

        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">{heading}</h2>
          <p className="text-sm text-muted-foreground">{subheading}</p>
        </div>

        {error && (
          <div className="rounded-r-md border-l-2 border-destructive bg-destructive/10 p-4 text-sm text-destructive" aria-live="polite">
            {error}
          </div>
        )}
        {infoMessage && !error && (
          <div className="flex items-start gap-2 rounded-r-md border-l-2 border-success bg-success/10 p-4 text-sm text-success" aria-live="polite">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{infoMessage}</span>
          </div>
        )}

        <div className="space-y-4">
          {(mode === 'login' || mode === 'register') && (
            <>
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
            </>
          )}

          <form onSubmit={handleAuth} className="space-y-4">
            {mode === 'forgot' ? (
              <input
                placeholder="Email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                required
              />
            ) : mode === 'reset' ? (
              <>
                {demoCode && (
                  <div className="rounded-r-md border-l-2 border-primary bg-primary/10 p-4 text-sm" aria-live="polite">
                    <p className="text-xs font-semibold uppercase tracking-widest text-primary">Demo recovery code</p>
                    <p className="mt-1 font-mono text-2xl font-semibold tracking-[0.3em]" data-testid="demo-reset-code">{demoCode}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      This is a demo: no email is sent, so the code is shown here instead.
                    </p>
                  </div>
                )}
                <input
                  placeholder="6-digit reset code"
                  type="text"
                  value={resetOtp}
                  onChange={(e) => setResetOtp(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary tracking-widest"
                  maxLength={6}
                  required
                />
                <input
                  placeholder="New password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                  minLength={8}
                  required
                />
                <input
                  placeholder="Confirm new password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-transparent border-b border-border/60 pb-2 pt-3 px-1 text-sm outline-none transition-colors focus:border-primary"
                  minLength={8}
                  required
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{resetTimeLeft > 0 ? `Code expires in ${formatMMSS(resetTimeLeft)}` : 'Code expired'}</span>
                  {resetTimeLeft === 0 && (
                    <button
                      type="button"
                      onClick={handleNewCode}
                      disabled={loadingAuth}
                      className="font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:text-muted-foreground disabled:no-underline"
                    >
                      Get a new code
                    </button>
                  )}
                </div>
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
                {mode === 'login' && (
                  <div className="text-right">
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="text-xs text-muted-foreground hover:text-primary hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}
              </>
            )}

            <Button type="submit" className="h-12 w-full justify-between" disabled={loadingAuth || loadingGuest}>
              {loadingAuth && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {mode === 'login' ? 'Sign In'
                : mode === 'register' ? 'Create Account'
                : mode === 'forgot' ? 'Get Demo Reset Code'
                : 'Reset Password'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          {(mode === 'login' || mode === 'register') && (
            <div className="text-center">
              <button
                type="button"
                onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
                className="text-sm text-primary hover:underline transition-all"
              >
                {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign in'}
              </button>
            </div>
          )}
          {(mode === 'forgot' || mode === 'reset') && (
            <div className="text-center">
              <button
                type="button"
                onClick={() => switchMode('login')}
                className="text-sm text-primary hover:underline transition-all"
              >
                Back to sign in
              </button>
            </div>
          )}

          {(mode === 'login' || mode === 'register') && (
            <>
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
                Guest activity is temporary and automatically expires within 24 hours.
              </p>
            </>
          )}

          <div className="flex items-center justify-center gap-3 pt-6 text-[11px] text-muted-foreground/70">
            <Link href="/terms" className="hover:text-foreground hover:underline">Terms</Link>
            <span aria-hidden>·</span>
            <Link href="/privacy" className="hover:text-foreground hover:underline">Privacy</Link>
            <span aria-hidden>·</span>
            <a href="https://github.com/AdityaKishore0698/interview-arena" target="_blank" rel="noreferrer" className="hover:text-foreground hover:underline">
              GitHub
            </a>
          </div>
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

const HOW_IT_WORKS = [
  { title: 'Pick a topic and join the queue', body: 'Choose DSA, System Design, or OOP/LLD and a Quick or Standard round length.' },
  { title: 'Get matched and swap roles', body: "You'll interview your partner in round one, then switch — they interview you in round two." },
  { title: 'Rate each other, instantly', body: 'Submit structured feedback right after each round; see what your partner said about you at the end.' },
];

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden text-foreground md:flex-row">
      {/* Absolute Header for Theme Switcher */}
      <div className="absolute top-0 right-0 z-50 p-6">
        <ThemeToggle />
      </div>

      {/* Left Panel: Brand & Value Prop */}
      <div className="relative z-10 flex flex-1 flex-col justify-center overflow-y-auto px-8 py-14 md:px-16 md:py-16 lg:px-24">
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

          <div className="space-y-4 border-t border-border/60 pt-8">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">How it works</h2>
            <ol className="space-y-4">
              {HOW_IT_WORKS.map((step, i) => (
                <li key={step.title} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-foreground">{step.title}</p>
                    <p className="text-sm text-muted-foreground">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>

      {/* Right Panel: Authentication Controls */}
      <Suspense fallback={<div className="flex w-full items-center justify-center md:w-[540px]"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
        <AuthContent />
      </Suspense>
    </div>
  );
}
