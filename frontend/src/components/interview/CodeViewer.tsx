'use client';

import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Code2 } from 'lucide-react';

const MONACO_LANGUAGE: Record<string, string> = {
  python: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  java: 'java',
  cpp: 'cpp',
  c: 'c',
  csharp: 'csharp',
  go: 'go',
  ruby: 'ruby',
};

/** Mirrors CodeEditor's own theme-sync approach — see its comment. */
function useIsDarkTheme(): boolean {
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

export function CodeViewer({ code, language }: { code: string; language: string | null }) {
  const isDark = useIsDarkTheme();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border/60 bg-surface/60 px-3 py-2 text-xs font-medium text-muted-foreground">
        <Code2 className="h-3.5 w-3.5" />
        {language ? MONACO_LANGUAGE[language] ?? language : 'Code'} — read-only
      </div>
      <div className="min-h-[280px] flex-1">
        <Editor
          height="100%"
          language={language ? MONACO_LANGUAGE[language] : undefined}
          value={code}
          theme={isDark ? 'vs-dark' : 'light'}
          options={{
            readOnly: true,
            domReadOnly: true,
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 12 },
          }}
        />
      </div>
    </div>
  );
}
