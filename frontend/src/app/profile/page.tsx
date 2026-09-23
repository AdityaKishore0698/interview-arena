'use client';

import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import AppLayout from '@/components/layout/AppLayout';
import { Avatar } from '@/components/layout/Avatar';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Flame, Loader2, Trophy, Target, ListChecks, LayoutGrid, Settings, TrendingUp } from 'lucide-react';
import { ScoreTrendChart, type TrendPoint } from '@/components/profile/ScoreTrendChart';
import { InterviewHistoryList } from '@/components/profile/InterviewHistoryList';

interface HistoryFeedback {
  scores: Record<string, number> | null;
  comments: string | null;
  evaluated_role: string | null;
  giver_user_id: string | null;
  receiver_user_id: string | null;
}

interface HistorySession {
  id: string;
  mode: string;
  created_at: string;
  room: { name: string; slug: string; difficulty: string } | null;
  rounds: { round_number: number; feedbacks: HistoryFeedback[] }[];
}

interface StreakData {
  login_streak: number;
  longest_login_streak: number;
  interview_streak: number;
  longest_interview_streak: number;
}

const SCORE_LABELS: Record<string, string> = {
  communication: 'Communication',
  technicalKnowledge: 'Technical Knowledge',
  problemSolving: 'Problem Solving',
};

// Same family as the rest of the theme: `violet` is the app's existing
// primary-gradient accent stop (see .bg-primary-gradient in globals.css),
// not a new color — just used solo here to tell this icon apart from primary.
const STAT_TONES = {
  primary: 'bg-primary/10 text-primary',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  violet: 'bg-[oklch(0.62_0.2_305)]/10 text-[oklch(0.62_0.2_305)]',
} as const;

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  tone = 'primary',
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  tone?: keyof typeof STAT_TONES;
}) {
  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl border border-border/60 bg-surface/40 p-5">
      <div className="flex items-center gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${STAT_TONES[tone]}`}>
          <Icon className="h-4 w-4" />
        </div>
        <p className="text-xs font-semibold uppercase leading-tight tracking-widest text-muted-foreground">{label}</p>
      </div>
      <div className="mt-auto">
        <p className="font-mono text-3xl font-semibold leading-none tracking-tight text-foreground">{value}</p>
        <p className="mt-1.5 h-4 text-xs text-muted-foreground">{sub ?? ' '}</p>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { user, hasHydrated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for zustand/persist to read localStorage before trusting a null
    // user — see the comment on `hasHydrated` in store/useAuth.ts.
    if (hasHydrated && !user) router.replace('/');
  }, [user, hasHydrated, router]);

  const isRegistered = user?.type === 'REGISTERED';

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['history'],
    queryFn: async () => (await api.get('/api/v1/sessions/user/history')).data.history as HistorySession[],
    enabled: isRegistered,
  });

  const { data: streaks, isLoading: streaksLoading } = useQuery({
    queryKey: ['streaks'],
    queryFn: async () => (await api.get('/api/v1/auth/streaks/me')).data as StreakData,
    enabled: isRegistered,
  });

  const stats = useMemo(() => {
    if (!history || !user) return null;
    const received: HistoryFeedback[] = [];
    for (const session of history) {
      for (const round of session.rounds) {
        for (const fb of round.feedbacks) {
          if (fb.receiver_user_id === user.id && fb.scores) received.push(fb);
        }
      }
    }
    const sums: Record<string, { total: number; count: number }> = {};
    for (const fb of received) {
      for (const [key, value] of Object.entries(fb.scores || {})) {
        sums[key] ??= { total: 0, count: 0 };
        sums[key].total += value;
        sums[key].count += 1;
      }
    }
    const order = ['communication', 'technicalKnowledge', 'problemSolving'];
    const averages = Object.entries(sums)
      .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
      .map(([key, { total, count }]) => ({
        label: SCORE_LABELS[key] ?? key,
        average: count > 0 ? (total / count).toFixed(1) : '—',
      }));

    const roomCounts = new Map<string, number>();
    for (const session of history) {
      const name = session.room?.name ?? 'Unknown';
      roomCounts.set(name, (roomCounts.get(name) ?? 0) + 1);
    }

    // One point per completed session, oldest first (the backend returns
    // history newest-first) — the average of every score the user received
    // in that session, across both rounds and all categories.
    const trend: TrendPoint[] = [...history]
      .reverse()
      .map((session) => {
        let total = 0;
        let count = 0;
        for (const round of session.rounds) {
          for (const fb of round.feedbacks) {
            if (fb.receiver_user_id !== user.id || !fb.scores) continue;
            for (const v of Object.values(fb.scores)) { total += v; count += 1; }
          }
        }
        return count > 0 ? { date: session.created_at, average: total / count } : null;
      })
      .filter((p): p is TrendPoint => p !== null);

    return {
      totalSessions: history.length,
      totalFeedbackReceived: received.length,
      averages,
      roomCounts: Array.from(roomCounts.entries()).sort((a, b) => b[1] - a[1]),
      trend,
    };
  }, [history, user]);

  if (!user) return null;

  const loading = historyLoading || streaksLoading;

  return (
    <AppLayout>
      <div className="container relative z-10 mx-auto max-w-3xl px-6 py-12">
        <header className="mb-10 flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <Avatar name={user.display_name || 'Guest'} src={user.avatar_url} size={64} className="shadow-glow" />
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Profile</p>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                {user.display_name || 'Guest'}
              </h1>
              {user.email && <p className="text-sm text-muted-foreground">{user.email}</p>}
            </div>
          </div>
          {isRegistered && (
            <Button variant="outline" size="sm" onClick={() => router.push('/account')} className="gap-1.5">
              <Settings className="h-3.5 w-3.5" />
              Account settings
            </Button>
          )}
        </header>

        {!isRegistered ? (
          <div className="space-y-4 rounded-2xl border border-dashed border-border/60 bg-surface/30 p-8 text-center">
            <p className="text-foreground">Guest sessions don&rsquo;t track progress or stats.</p>
            <p className="text-sm text-muted-foreground">
              Create a free account to build a streak, collect feedback, and see your progress here over time.
            </p>
            <Button onClick={() => router.push('/?mode=register')}>Create a free account</Button>
          </div>
        ) : loading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading your stats…
          </div>
        ) : (
          <div className="space-y-10">
            <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard icon={ListChecks} tone="primary" label="Interviews" value={String(stats?.totalSessions ?? 0)} sub="completed" />
              <StatCard icon={Target} tone="success" label="Feedback" value={String(stats?.totalFeedbackReceived ?? 0)} sub="rounds rated" />
              <StatCard
                icon={Flame}
                tone="warning"
                label="Login streak"
                value={String(streaks?.login_streak ?? 0)}
                sub={`Longest: ${streaks?.longest_login_streak ?? 0}`}
              />
              <StatCard
                icon={Trophy}
                tone="violet"
                label="Interview streak"
                value={String(streaks?.interview_streak ?? 0)}
                sub={`Longest: ${streaks?.longest_interview_streak ?? 0}`}
              />
            </section>

            <section className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                Average feedback received
              </h2>
              {stats && stats.averages.length > 0 ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {stats.averages.map((a) => (
                    <div key={a.label} className="flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-surface/40 p-4 sm:flex-col sm:items-start sm:justify-normal">
                      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{a.label}</p>
                      <p className="font-mono text-2xl font-semibold leading-none text-foreground sm:mt-2">
                        {a.average}<span className="text-sm font-normal text-muted-foreground">/5</span>
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border/60 bg-surface/20 p-5 text-sm text-muted-foreground">
                  Complete an interview and get rated to see this.
                </div>
              )}
            </section>

            <section className="space-y-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" /> Progress over time
              </h2>
              <ScoreTrendChart points={stats?.trend ?? []} />
            </section>

            {stats && stats.roomCounts.length > 0 && (
              <section className="space-y-4">
                <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                  <LayoutGrid className="h-3.5 w-3.5" /> Practice by room
                </h2>
                <div className="space-y-3 rounded-xl border border-border/60 bg-surface/40 p-4">
                  {stats.roomCounts.map(([name, count]) => {
                    const max = stats.roomCounts[0][1];
                    return (
                      <div key={name} className="flex items-center gap-3">
                        <span className="w-32 shrink-0 truncate text-sm text-foreground">{name}</span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface">
                          <div className="h-full rounded-full bg-primary-gradient" style={{ width: `${(count / max) * 100}%` }} />
                        </div>
                        <span className="w-6 shrink-0 text-right font-mono text-xs text-muted-foreground">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            <section id="history" className="scroll-mt-24 space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                Interview history
              </h2>
              {user && <InterviewHistoryList history={history ?? []} userId={user.id} />}
            </section>

          </div>
        )}
      </div>
    </AppLayout>
  );
}
