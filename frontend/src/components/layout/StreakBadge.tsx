'use client';

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Flame, Trophy } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/store/useAuth';

interface StreakData {
  login_streak: number;
  longest_login_streak: number;
  interview_streak: number;
  longest_interview_streak: number;
}

// One check-in call per UTC calendar day per browser — the backend is
// idempotent per day regardless, this just avoids calling it on every mount.
function checkinKeyFor(today: string) {
  return `streak-checkin-${today}`;
}

export function StreakBadge() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isRegistered = user?.type === 'REGISTERED';

  const { data } = useQuery<StreakData>({
    queryKey: ['streaks'],
    queryFn: async () => (await api.get('/api/v1/auth/streaks/me')).data,
    enabled: isRegistered,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (!isRegistered) return;
    const today = new Date().toISOString().slice(0, 10);
    const key = checkinKeyFor(today);
    let cached = false;
    try {
      cached = localStorage.getItem(key) === '1';
    } catch {
      // localStorage unavailable (private browsing, etc.) — fall back to
      // calling check-in every mount; the backend is idempotent per day.
    }
    if (cached) return;

    api.post('/api/v1/auth/streaks/checkin')
      .then((res) => {
        queryClient.setQueryData(['streaks'], res.data);
        try {
          localStorage.setItem(key, '1');
        } catch {
          // Ignore — see above.
        }
      })
      .catch(() => {
        // Non-critical: a missed check-in just means today isn't counted yet.
      });
  }, [isRegistered, queryClient]);

  if (!isRegistered || !data) return null;
  if (data.login_streak === 0 && data.interview_streak === 0) return null;

  return (
    <div className="hidden items-center gap-3 text-xs text-muted-foreground md:flex" aria-label="Streaks">
      {data.login_streak > 0 && (
        <span
          className="flex items-center gap-1"
          title={`${data.login_streak}-day login streak (longest: ${data.longest_login_streak})`}
        >
          <Flame className="h-3.5 w-3.5 text-warning" />
          {data.login_streak}
        </span>
      )}
      {data.interview_streak > 0 && (
        <span
          className="flex items-center gap-1"
          title={`${data.interview_streak}-day interview streak (longest: ${data.longest_interview_streak})`}
        >
          <Trophy className="h-3.5 w-3.5 text-primary" />
          {data.interview_streak}
        </span>
      )}
    </div>
  );
}
