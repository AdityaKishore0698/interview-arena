'use client';

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/lib/api';
import { AxiosError } from 'axios';
import { Loader2, PenLine, Search, X } from 'lucide-react';

interface Suggestion {
  id: string;
  title: string;
  prompt: string;
  difficulty: string;
}

interface QuestionPickerProps {
  sessionId: string;
  roundId: string;
  onSelected: () => void;
}

function DifficultyPill({ value }: { value: string }) {
  const tone =
    value.toLowerCase() === 'easy'
      ? 'bg-success/10 text-success'
      : value.toLowerCase() === 'hard'
        ? 'bg-destructive/10 text-destructive'
        : 'bg-warning/10 text-warning';
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${tone}`}>
      {value}
    </span>
  );
}

// Picking a question is a suggestion aid, not a requirement — an interviewer
// who ignores this entirely gets the same auto-picked question as before.
// A plain, always-single-column list (not a grid of cards) so this stays
// usable at any panel width, including the narrow side-by-side layout this
// renders inside during a live round.
export function QuestionPicker({ sessionId, roundId, onSelected }: QuestionPickerProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null); // problem id, or 'custom'
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [customMode, setCustomMode] = useState(false);
  const [customText, setCustomText] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.get(`/api/v1/sessions/${sessionId}/rounds/${roundId}/problems/suggestions`)
      .then((res) => { if (!cancelled) setSuggestions(res.data.problems); })
      .catch(() => { if (!cancelled) setLoadError('Could not load suggested questions.'); });
    return () => { cancelled = true; };
  }, [sessionId, roundId]);

  const filtered = useMemo(() => {
    if (!suggestions) return [];
    const q = search.trim().toLowerCase();
    if (!q) return suggestions;
    return suggestions.filter((s) => s.title.toLowerCase().includes(q) || s.prompt.toLowerCase().includes(q));
  }, [suggestions, search]);

  const pick = async (body: { problem_id: string } | { custom_text: string }) => {
    setSubmitError(null);
    setSubmitting('problem_id' in body ? body.problem_id : 'custom');
    try {
      await api.post(`/api/v1/sessions/${sessionId}/rounds/${roundId}/problem`, body);
      onSelected();
    } catch (err: unknown) {
      setSubmitError(err instanceof AxiosError ? err.response?.data?.detail || 'Could not select this question.' : 'An unexpected error occurred.');
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="space-y-5 border-t border-border/60 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
          Pick a question for this round (optional)
        </h4>
        <span className="text-xs text-muted-foreground">
          If you skip this, one is chosen for you automatically.
        </span>
      </div>

      {submitError && (
        <p className="text-sm text-destructive" aria-live="polite">{submitError}</p>
      )}

      {loadError ? (
        <p className="text-sm text-muted-foreground">{loadError}</p>
      ) : suggestions === null ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading suggestions…
        </div>
      ) : suggestions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No suggested questions for this room yet — write your own below.</p>
      ) : (
        <div className="space-y-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search questions by title or topic…"
              className="h-10 rounded-xl pl-9 pr-9"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {filtered.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No questions match &ldquo;{search}&rdquo;.</p>
          ) : (
            <div className="max-h-[360px] space-y-2 overflow-y-auto rounded-xl border border-border/60 bg-surface/20 p-2">
              {filtered.map((s) => (
                <div
                  key={s.id}
                  className="flex flex-col gap-2 rounded-lg border border-transparent bg-surface/40 p-3 transition-colors hover:border-border/60"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h5 className="text-sm font-semibold text-foreground">{s.title}</h5>
                      <DifficultyPill value={s.difficulty} />
                    </div>
                    <p className="line-clamp-1 text-xs text-muted-foreground">{s.prompt}</p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => pick({ problem_id: s.id })}
                    disabled={submitting !== null}
                    className="w-full"
                  >
                    {submitting === s.id && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                    Use this question
                  </Button>
                </div>
              ))}
            </div>
          )}
          {suggestions.length > 0 && (
            <p className="text-right text-[11px] text-muted-foreground">
              {filtered.length} of {suggestions.length} question{suggestions.length === 1 ? '' : 's'}
            </p>
          )}
        </div>
      )}

      {!customMode ? (
        <button
          type="button"
          onClick={() => setCustomMode(true)}
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <PenLine className="h-3.5 w-3.5" />
          Ask something else instead
        </button>
      ) : (
        <div className="space-y-3 rounded-xl border border-border/60 bg-surface/40 p-4">
          <Textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Write the question you'd like to ask…"
            className="min-h-[100px] resize-none bg-transparent"
            maxLength={2000}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => { setCustomMode(false); setCustomText(''); }}>
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => pick({ custom_text: customText.trim() })}
              disabled={!customText.trim() || submitting !== null}
            >
              {submitting === 'custom' && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
              Use my own question
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
