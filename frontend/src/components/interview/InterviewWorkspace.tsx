import { BookOpen, Code2 } from 'lucide-react';

interface Problem {
  id: string;
  title: string;
  prompt: string;
  difficulty: string;
}

interface InterviewWorkspaceProps {
  roomName: string;
  roomDifficulty?: string;
  role: string;
  isPreparation: boolean;
  problem?: Problem | null;
}

function DifficultyBadge({ value }: { value: string }) {
  const tone =
    value.toLowerCase() === 'easy'
      ? 'bg-success/10 text-success'
      : value.toLowerCase() === 'hard'
        ? 'bg-destructive/10 text-destructive'
        : 'bg-warning/10 text-warning';
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${tone}`}>
      {value}
    </span>
  );
}

export function InterviewWorkspace({
  roomName,
  roomDifficulty,
  role,
  isPreparation,
  problem,
}: InterviewWorkspaceProps) {
  const isSystemDesign = roomName.toLowerCase().includes('system design');
  const isInterviewer = role === 'INTERVIEWER';

  return (
    <div className="flex h-full flex-1 flex-col overflow-hidden bg-transparent animate-in fade-in duration-700">
      <div className="flex items-center border-b border-border/50 px-6 py-4">
        {isPreparation ? (
          <BookOpen className="mr-3 h-4 w-4 text-primary" />
        ) : (
          <Code2 className="mr-3 h-4 w-4 text-primary" />
        )}
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {isPreparation ? 'Preparation Instructions' : 'Active Workspace'}
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-10 md:px-12">
        {isPreparation ? (
          <div className="max-w-2xl space-y-12">
            <div className="space-y-4">
              <h2 className="text-4xl font-bold leading-tight tracking-tight text-foreground md:text-5xl">
                Welcome to <br />
                <span className="text-gradient">{roomName}</span>
              </h2>
              <p className="text-xl leading-relaxed text-muted-foreground">
                You have been assigned the role of{' '}
                <span className="font-medium text-foreground">{role}</span> for this round. Take a
                moment to prepare.
              </p>
            </div>

            <div className="space-y-6 border-t border-border/60 pt-6">
              <h4 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                Before we begin
              </h4>
              <ul className="space-y-5 text-base text-foreground/80">
                {[
                  'Introduce yourself to your partner using the chat or audio.',
                  'The round begins automatically when the timer reaches zero. Do not manually refresh.',
                  'After Round 1, roles automatically reverse for Round 2.',
                ].map((item) => (
                  <li key={item} className="flex items-start">
                    <span className="mr-4 mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex h-full w-full max-w-[1200px] flex-col space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-medium tracking-tight text-foreground">
                {isInterviewer ? 'You are the Interviewer' : 'You are the Interviewee'}
              </h3>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-sm uppercase tracking-widest text-primary">
                {roomName}
                {roomDifficulty ? ` · ${roomDifficulty}` : ''}
              </span>
            </div>

            <div className="relative flex flex-1 flex-col gap-6 md:flex-row">
              {/* Problem panel — authoritative content from the backend */}
              <div className="flex flex-[5] flex-col overflow-hidden rounded-2xl border border-border/60 bg-surface/40 shadow-elev-sm">
                <div className="flex items-center justify-between border-b border-border/60 bg-surface/60 px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  <span>{isInterviewer ? 'Problem to ask' : 'Problem'}</span>
                  {problem && <DifficultyBadge value={problem.difficulty} />}
                </div>
                <div className="flex-1 overflow-y-auto p-6 text-sm leading-relaxed text-foreground/90">
                  {problem ? (
                    <div className="space-y-4">
                      {isInterviewer && (
                        <p className="text-xs font-medium text-primary">
                          Present this problem to the candidate and guide the discussion.
                        </p>
                      )}
                      <h4 className="text-lg font-semibold tracking-tight text-foreground">
                        {problem.title}
                      </h4>
                      <p className="whitespace-pre-wrap">{problem.prompt}</p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/60" />
                      Loading the problem for this round…
                    </div>
                  )}
                </div>
              </div>

              {/* Candidate scratchpad — local only */}
              <div className="flex flex-[5] flex-col overflow-hidden rounded-2xl border border-border/60 bg-surface/40 shadow-elev-md">
                <div className="flex justify-between border-b border-border/60 bg-surface/60 px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  <span>{isSystemDesign ? 'Design Notes' : 'Code / Scratchpad'} (Local)</span>
                </div>
                <textarea
                  className="w-full flex-1 resize-none bg-transparent p-6 font-mono text-sm leading-relaxed outline-none focus:ring-1 focus:ring-inset focus:ring-primary/20"
                  placeholder={
                    isSystemDesign
                      ? 'Sketch your design — components, API contracts, trade-offs…'
                      : 'Work through the problem here…'
                  }
                  spellCheck={false}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
