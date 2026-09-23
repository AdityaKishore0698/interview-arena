'use client';

import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/lib/api';
import { AxiosError } from 'axios';
import { CheckCircle2, Loader2, Play, Send, WandSparkles, XCircle } from 'lucide-react';

const LANGUAGES: { id: string; label: string; monaco: string }[] = [
  { id: 'python', label: 'Python', monaco: 'python' },
  { id: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { id: 'typescript', label: 'TypeScript', monaco: 'typescript' },
  { id: 'java', label: 'Java', monaco: 'java' },
  { id: 'cpp', label: 'C++', monaco: 'cpp' },
  { id: 'c', label: 'C', monaco: 'c' },
  { id: 'csharp', label: 'C#', monaco: 'csharp' },
  { id: 'go', label: 'Go', monaco: 'go' },
  { id: 'ruby', label: 'Ruby', monaco: 'ruby' },
];

// Prettier runs client-side and gives genuinely polished output for these
// two. Monaco's built-in "reindent lines" action was tried as a fallback for
// the rest, but verified (via direct testing) to be a no-op for languages
// like Python in this bundle — no indentation rules are registered for them,
// so it silently did nothing.
const PRETTIER_LANGUAGES = new Set(['javascript', 'typescript']);

// These go through the backend's real formatters instead — black (Python),
// clang-format (C/C++), and google-java-format (Java) — since there's no
// good client-side formatter for them. See app/interview/code_formatting.py.
// Every other language in the picker has no formatter wired up at all, so
// the Format button stays hidden outside this set and PRETTIER_LANGUAGES.
const SERVER_FORMAT_LANGUAGES = new Set(['python', 'c', 'cpp', 'java']);

// No code execution provider is wired up with real quota yet (Piston's free
// public API went whitelist-only; Judge0 CE has no free RapidAPI tier) — the
// backend endpoint and this component's Run handling are fully built and
// tested, just switched off here until that's sorted out. Flip this back on
// once CODE_EXECUTION_API_KEY is live.
const RUN_ENABLED = false;

interface TestCaseResult {
  input: string;
  expected_output: string;
  actual_output: string;
  stderr: string;
  passed: boolean;
  timed_out: boolean;
}

interface RunResponse {
  results: TestCaseResult[];
  passed_count: number;
  total: number;
}

interface CodeEditorProps {
  sessionId: string;
  roundId: string;
  initialCode?: string | null;
  initialLanguage?: string | null;
  onSubmitted?: () => void;
}

/** Mirrors ThemeToggle's own DOM-class approach (there's no theme context in
 * this app) so the editor's colors follow the site's light/dark toggle. */
function useIsDarkTheme(): boolean {
  // The initial read happens in useState's lazy initializer (runs once,
  // synchronously, during the first render) rather than inside the effect
  // below — the effect exists only to subscribe to later changes. Guarded
  // for SSR, where `document` doesn't exist — this component is only ever
  // reached once session data has loaded client-side, but the guard costs
  // nothing and removes any doubt.
  const [isDark, setIsDark] = useState(
    () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  );
  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => setIsDark(root.classList.contains('dark')));
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  return isDark;
}

async function formatWithPrettier(code: string, language: string): Promise<string> {
  const prettier = await import('prettier/standalone');
  const estree = await import('prettier/plugins/estree');
  if (language === 'typescript') {
    const ts = await import('prettier/plugins/typescript');
    return prettier.format(code, { parser: 'typescript', plugins: [ts.default ?? ts, estree.default ?? estree] });
  }
  const babel = await import('prettier/plugins/babel');
  return prettier.format(code, { parser: 'babel', plugins: [babel.default ?? babel, estree.default ?? estree] });
}

export function CodeEditor({
  sessionId,
  roundId,
  initialCode,
  initialLanguage,
  onSubmitted,
}: CodeEditorProps) {
  const [language, setLanguage] = useState(initialLanguage || 'python');
  const [code, setCode] = useState(initialCode || '');
  const [running, setRunning] = useState(false);
  const [formatting, setFormatting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [justSubmitted, setJustSubmitted] = useState(false);
  const isDark = useIsDarkTheme();

  const handleFormat = async () => {
    setFormatting(true);
    setError(null);
    try {
      if (PRETTIER_LANGUAGES.has(language)) {
        setCode(await formatWithPrettier(code, language));
      } else if (SERVER_FORMAT_LANGUAGES.has(language)) {
        const res = await api.post('/api/v1/sessions/code/format', { language, code });
        setCode(res.data.formatted_code);
      }
      // else: button is hidden for this language — see below
    } catch (err) {
      const detail = err instanceof AxiosError ? err.response?.data?.detail : null;
      setError(detail || 'Could not format this code — check it for syntax errors first.');
    } finally {
      setFormatting(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setRunResult(null);
    try {
      const res = await api.post(`/api/v1/sessions/${sessionId}/rounds/${roundId}/code/run`, { language, code });
      setRunResult(res.data);
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Could not run your code' : 'Something went wrong');
    } finally {
      setRunning(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/v1/sessions/${sessionId}/rounds/${roundId}/code/submit`, { language, code });
      setJustSubmitted(true);
      onSubmitted?.();
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Could not submit your code' : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-surface/60 px-3 py-2">
        <Select value={language} onValueChange={(v) => v && setLanguage(v)}>
          <SelectTrigger size="sm" className="min-w-[130px]">
            <SelectValue placeholder="Language" />
          </SelectTrigger>
          <SelectContent>
            {LANGUAGES.map((l) => (
              <SelectItem key={l.id} value={l.id}>{l.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-2">
          {(PRETTIER_LANGUAGES.has(language) || SERVER_FORMAT_LANGUAGES.has(language)) && (
            <Button type="button" variant="outline" size="sm" onClick={handleFormat} disabled={formatting || !code.trim()}>
              {formatting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <WandSparkles className="mr-1.5 h-3.5 w-3.5" />}
              Format
            </Button>
          )}
          {RUN_ENABLED && (
            <Button type="button" variant="outline" size="sm" onClick={handleRun} disabled={running || !code.trim()}>
              {running ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Play className="mr-1.5 h-3.5 w-3.5" />}
              Run
            </Button>
          )}
          <Button type="button" size="sm" onClick={handleSubmit} disabled={submitting || !code.trim()}>
            {submitting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Send className="mr-1.5 h-3.5 w-3.5" />}
            Submit
          </Button>
        </div>
      </div>

      <div className="min-h-[280px] flex-1">
        <Editor
          height="100%"
          language={LANGUAGES.find((l) => l.id === language)?.monaco}
          value={code}
          onChange={(v) => setCode(v ?? '')}
          theme={isDark ? 'vs-dark' : 'light'}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 12 },
          }}
        />
      </div>

      <div className="shrink-0 space-y-2 border-t border-border/60 bg-surface/40 px-3 py-2 text-xs">
        {error && <p className="text-destructive">{error}</p>}
        {justSubmitted && !error && (
          <p className="flex items-center gap-1.5 text-success">
            <CheckCircle2 className="h-3.5 w-3.5" /> Submitted — your interviewer can now see this code.
          </p>
        )}
        {runResult && (
          <div className="space-y-1.5">
            <p className="font-medium text-foreground">
              {runResult.passed_count} / {runResult.total} sample test cases passed
            </p>
            {runResult.results.map((r, i) => (
              <div key={i} className="flex items-start gap-1.5 text-muted-foreground">
                {r.passed ? (
                  <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-success" />
                ) : (
                  <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-destructive" />
                )}
                <span className="font-mono">
                  Case {i + 1}: {r.timed_out ? 'timed out' : r.passed ? 'passed' : `expected "${r.expected_output}", got "${r.actual_output.trim() || (r.stderr ? r.stderr.slice(0, 120) : '(empty)')}"`}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
