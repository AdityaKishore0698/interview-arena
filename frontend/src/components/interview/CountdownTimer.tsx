'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

function secondsLeft(endsAt: string): number {
  return Math.max(0, Math.floor((new Date(endsAt).getTime() - Date.now()) / 1000));
}

/**
 * A single authoritative countdown.
 *
 * - Derives entirely from the server's `endsAt` timestamp — it never advances
 *   the interview lifecycle itself.
 * - When it hits zero but the server has not yet published the next transition,
 *   it shows a compact synchronization state instead of a stuck "0:00".
 */
export function CountdownTimer({ endsAt }: { endsAt: string | undefined }) {
  const [timeLeft, setTimeLeft] = useState<number | null>(() => (endsAt ? secondsLeft(endsAt) : null));

  // Re-sync immediately (during render) whenever the authoritative value changes.
  const [trackedEndsAt, setTrackedEndsAt] = useState(endsAt);
  if (endsAt !== trackedEndsAt) {
    setTrackedEndsAt(endsAt);
    setTimeLeft(endsAt ? secondsLeft(endsAt) : null);
  }

  useEffect(() => {
    if (!endsAt) return;
    // `endsAt` is captured fresh here; the effect re-runs whenever it changes.
    const interval = setInterval(() => setTimeLeft(secondsLeft(endsAt)), 1000);
    return () => clearInterval(interval);
  }, [endsAt]);

  if (!endsAt || timeLeft === null) {
    return <span className="font-mono text-3xl tabular-nums leading-none text-muted-foreground/40 md:text-4xl">—:—</span>;
  }

  if (timeLeft <= 0) {
    return (
      <span
        className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-warning"
        aria-live="polite"
      >
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Syncing…
      </span>
    );
  }

  const m = Math.floor(timeLeft / 60);
  const s = timeLeft % 60;
  const isUrgent = timeLeft <= 15;
  const isWarning = timeLeft <= 60 && !isUrgent;

  return (
    <span
      className={`font-mono text-3xl tabular-nums leading-none tracking-tight md:text-4xl ${
        isUrgent ? 'text-destructive' : isWarning ? 'text-warning' : 'text-foreground'
      }`}
      aria-label={`${m} minutes ${s} seconds remaining`}
    >
      {m}:{s.toString().padStart(2, '0')}
    </span>
  );
}
