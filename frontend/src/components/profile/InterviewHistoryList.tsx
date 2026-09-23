'use client';

import { useMemo, useState } from 'react';
import { Search, Star, CalendarDays } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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

const SCORE_LABELS: Record<string, string> = {
  communication: 'Communication',
  technicalKnowledge: 'Technical Knowledge',
  problemSolving: 'Problem Solving',
};

const DATE_RANGES = {
  all: { label: 'All time', days: null },
  '7': { label: 'Last 7 days', days: 7 },
  '30': { label: 'Last 30 days', days: 30 },
  '90': { label: 'Last 90 days', days: 90 },
} as const;
type DateRangeKey = keyof typeof DATE_RANGES;

const SORTS = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  rating_desc: 'Highest rated',
  rating_asc: 'Lowest rated',
} as const;
type SortKey = keyof typeof SORTS;

function averageRating(session: HistorySession, userId: string): number | null {
  let total = 0;
  let count = 0;
  for (const round of session.rounds) {
    for (const fb of round.feedbacks) {
      if (fb.receiver_user_id !== userId || !fb.scores) continue;
      for (const v of Object.values(fb.scores)) {
        total += v;
        count += 1;
      }
    }
  }
  return count > 0 ? total / count : null;
}

export function InterviewHistoryList({ history, userId }: { history: HistorySession[]; userId: string }) {
  const [query, setQuery] = useState('');
  const [roomFilter, setRoomFilter] = useState('all');
  const [modeFilter, setModeFilter] = useState('all');
  const [dateRange, setDateRange] = useState<DateRangeKey>('all');
  const [sortBy, setSortBy] = useState<SortKey>('newest');

  const roomOptions = useMemo(() => {
    const names = new Set<string>();
    for (const s of history) names.add(s.room?.name ?? 'Interview');
    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }, [history]);

  const modeOptions = useMemo(() => {
    const modes = new Set<string>();
    for (const s of history) modes.add(s.mode);
    return Array.from(modes).sort();
  }, [history]);

  const enriched = useMemo(
    () => history.map((s) => ({ session: s, rating: averageRating(s, userId) })),
    [history, userId]
  );

  // A "now" snapshot taken once when the list mounts — reading the wall
  // clock during render is impure, so this captures it via useState's lazy
  // initializer (which React guarantees runs exactly once, on mount) rather
  // than reading Date.now() directly in the render body. A date-range
  // filter doesn't need millisecond freshness, so staying fixed for the
  // component's lifetime is fine.
  const [mountedAt] = useState(() => Date.now());

  const rangeDays = DATE_RANGES[dateRange].days;
  const cutoff = rangeDays ? mountedAt - rangeDays * 24 * 60 * 60 * 1000 : null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    let rows = enriched.filter(({ session }) => {
      const roomName = session.room?.name ?? 'Interview';
      if (q && !roomName.toLowerCase().includes(q)) return false;
      if (roomFilter !== 'all' && roomName !== roomFilter) return false;
      if (modeFilter !== 'all' && session.mode !== modeFilter) return false;
      if (cutoff !== null && new Date(session.created_at).getTime() < cutoff) return false;
      return true;
    });

    rows = [...rows].sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return new Date(a.session.created_at).getTime() - new Date(b.session.created_at).getTime();
        case 'rating_desc':
          return (b.rating ?? -1) - (a.rating ?? -1);
        case 'rating_asc':
          return (a.rating ?? 6) - (b.rating ?? 6);
        case 'newest':
        default:
          return new Date(b.session.created_at).getTime() - new Date(a.session.created_at).getTime();
      }
    });

    return rows;
  }, [enriched, query, roomFilter, modeFilter, cutoff, sortBy]);

  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 bg-surface/20 p-5 text-sm text-muted-foreground">
        No completed interviews yet — join a queue from the dashboard to get started.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="relative min-w-[180px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by room…"
            className="h-8 pl-8 text-sm"
          />
        </div>

        <Select value={roomFilter} onValueChange={(v) => setRoomFilter(v ?? 'all')}>
          <SelectTrigger size="sm" className="min-w-[130px]">
            <SelectValue placeholder="Room" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All rooms</SelectItem>
            {roomOptions.map((name) => (
              <SelectItem key={name} value={name}>{name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={modeFilter} onValueChange={(v) => setModeFilter(v ?? 'all')}>
          <SelectTrigger size="sm" className="min-w-[120px]">
            <SelectValue placeholder="Mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All modes</SelectItem>
            {modeOptions.map((m) => (
              <SelectItem key={m} value={m}>{m.charAt(0) + m.slice(1).toLowerCase()}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={dateRange} onValueChange={(v) => setDateRange(v as DateRangeKey)}>
          <SelectTrigger size="sm" className="min-w-[130px]">
            <SelectValue placeholder="Date" />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(DATE_RANGES) as DateRangeKey[]).map((key) => (
              <SelectItem key={key} value={key}>{DATE_RANGES[key].label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortKey)}>
          <SelectTrigger size="sm" className="min-w-[140px]">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(SORTS) as SortKey[]).map((key) => (
              <SelectItem key={key} value={key}>{SORTS[key]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <p className="text-xs text-muted-foreground">
        {filtered.length} of {history.length} interview{history.length === 1 ? '' : 's'}
      </p>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/60 bg-surface/20 p-5 text-sm text-muted-foreground">
          No interviews match these filters.
        </div>
      ) : (
        <div className="max-h-[640px] space-y-3 overflow-y-auto pr-1">
          {filtered.map(({ session, rating }) => {
            const received = session.rounds
              .map((r) => ({
                round: r.round_number,
                fb: r.feedbacks.find((f) => f.receiver_user_id === userId),
              }))
              .filter((e) => e.fb);

            return (
              <div key={session.id} className="space-y-3 rounded-2xl border border-border/50 bg-surface/40 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">{session.room?.name ?? 'Interview'}</h3>
                      {session.room?.difficulty && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                          {session.room.difficulty}
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{session.mode.charAt(0) + session.mode.slice(1).toLowerCase()} Mode</span>
                      <span aria-hidden="true">·</span>
                      <span className="flex items-center gap-1">
                        <CalendarDays className="h-3 w-3" />
                        {new Date(session.created_at).toLocaleDateString(undefined, {
                          year: 'numeric', month: 'short', day: 'numeric',
                        })}
                      </span>
                    </div>
                  </div>
                  {rating !== null && (
                    <span className="flex shrink-0 items-center gap-1 rounded-full bg-warning/10 px-2.5 py-1 text-xs font-semibold text-warning">
                      <Star className="h-3 w-3 fill-current" />
                      {rating.toFixed(1)}
                      <span className="font-normal text-warning/70">/5</span>
                    </span>
                  )}
                </div>

                {received.length > 0 ? (
                  <div className="space-y-2 border-t border-border/40 pt-3">
                    {received.map(({ round, fb }) => (
                      <div key={round} className="text-xs">
                        <span className="font-semibold uppercase tracking-wider text-muted-foreground">
                          Round {round}
                        </span>
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
                          {Object.entries(fb!.scores ?? {}).map(([k, v]) => (
                            <span key={k}>
                              {SCORE_LABELS[k] ?? k}{' '}
                              <span className="font-mono text-foreground">{v}/5</span>
                            </span>
                          ))}
                        </div>
                        {fb!.comments && (
                          <p className="mt-1 line-clamp-2 text-foreground/80">&ldquo;{fb!.comments}&rdquo;</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="border-t border-border/40 pt-3 text-xs text-muted-foreground">
                    No feedback recorded.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
