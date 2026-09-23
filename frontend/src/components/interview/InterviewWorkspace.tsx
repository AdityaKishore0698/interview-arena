import { useState } from 'react';
import { BookOpen, ChevronLeft, ChevronRight, Code2, NotebookPen } from 'lucide-react';
import { QuestionPicker } from './QuestionPicker';
import { CodeEditor } from './CodeEditor';
import { CodeViewer } from './CodeViewer';

interface Problem {
  id: string | null;
  title: string;
  prompt: string;
  difficulty: string | null;
  custom?: boolean;
}

interface InterviewWorkspaceProps {
  roomName: string;
  roomDifficulty?: string;
  role: string;
  isPreparation: boolean;
  problem?: Problem | null;
  /** Needed only to offer the picker during preparation; omit to hide it
   * entirely (e.g. for account types the picker doesn't support). */
  sessionId?: string;
  roundId?: string;
  onProblemSelected?: () => void;
  /** The interviewee's optional code editor is off by default — see the
   * Notes/Code tab toggle below. Omit alongside sessionId/roundId to hide it
   * entirely (e.g. for account types the picker doesn't support either). */
  submittedCode?: string | null;
  submittedLanguage?: string | null;
  onCodeSubmitted?: () => void;
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
  sessionId,
  roundId,
  onProblemSelected,
  submittedCode,
  submittedLanguage,
  onCodeSubmitted,
}: InterviewWorkspaceProps) {
  const isSystemDesign = roomName.toLowerCase().includes('system design');
  const isInterviewer = role === 'INTERVIEWER';
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'notes' | 'code'>('notes');
  const canUseCodeEditor = !!sessionId && !!roundId;
  // Lets either side shrink the problem panel to a slim strip so the
  // notes/code panel can take up most of the width — handy once the
  // candidate is deep into writing code and just needs a quick glance back
  // at the prompt rather than half the screen.
  const [problemCollapsed, setProblemCollapsed] = useState(false);
  // The interviewer may pick or change the question for whichever round is
  // current — during preparation or once it's live — in both round 1 and
  // round 2 (this component is reused for both; `role`/`problem` already
  // reflect "the current round" generically). Only unavailable when the
  // parent withholds sessionId/roundId (guest sessions — see the caller).
  const canOfferPicker = isInterviewer && !!sessionId && !!roundId && !!onProblemSelected;

  // This component isn't remounted between rounds — only its props change —
  // so a picker left open at the end of round 1 would otherwise still show
  // as "open" once round 2's props arrive. Reset during render (React's
  // sanctioned pattern for "adjust state when a prop changes") rather than
  // in an effect.
  const [syncedRoundId, setSyncedRoundId] = useState(roundId);
  if (roundId !== syncedRoundId) {
    setSyncedRoundId(roundId);
    setPickerOpen(false);
    setActiveTab('notes');
  }

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

            {isInterviewer ? (
              problem && !pickerOpen ? (
                <div className="space-y-3 border-t border-border/60 pt-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                      Your question for this round
                    </h4>
                    {canOfferPicker && (
                      <button
                        type="button"
                        onClick={() => setPickerOpen(true)}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        Change
                      </button>
                    )}
                  </div>
                  <div className="rounded-xl border border-border/60 bg-surface/40 p-4">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <h5 className="text-base font-semibold text-foreground">{problem.title}</h5>
                      {problem.difficulty && <DifficultyBadge value={problem.difficulty} />}
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-foreground/80">{problem.prompt}</p>
                  </div>
                </div>
              ) : canOfferPicker ? (
                <QuestionPicker
                  sessionId={sessionId!}
                  roundId={roundId!}
                  onSelected={() => { setPickerOpen(false); onProblemSelected!(); }}
                />
              ) : null
            ) : problem ? (
              <div className="space-y-3 border-t border-border/60 pt-6">
                <h4 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                  Your interviewer has chosen this question
                </h4>
                <div className="rounded-xl border border-border/60 bg-surface/40 p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h5 className="text-base font-semibold text-foreground">{problem.title}</h5>
                    {problem.difficulty && <DifficultyBadge value={problem.difficulty} />}
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-foreground/80">{problem.prompt}</p>
                </div>
              </div>
            ) : (
              <p className="border-t border-border/60 pt-6 text-sm text-muted-foreground">
                Your interviewer hasn&apos;t picked a question yet — one will be chosen automatically once the round begins.
              </p>
            )}
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
              {problemCollapsed ? (
                <button
                  type="button"
                  onClick={() => setProblemCollapsed(false)}
                  title="Show the problem"
                  className="flex shrink-0 flex-col items-center gap-3 rounded-2xl border border-border/60 bg-surface/40 py-4 text-muted-foreground shadow-elev-sm transition-colors hover:bg-surface/70 hover:text-foreground md:w-12"
                >
                  <ChevronRight className="h-4 w-4" />
                  <span className="text-xs font-semibold uppercase tracking-widest [writing-mode:vertical-rl]">
                    {isInterviewer ? 'Problem to ask' : 'Problem'}
                  </span>
                </button>
              ) : (
                <div className="flex flex-[5] flex-col overflow-hidden rounded-2xl border border-border/60 bg-surface/40 shadow-elev-sm">
                  <div className="flex items-center justify-between border-b border-border/60 bg-surface/60 px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setProblemCollapsed(true)}
                        title="Minimize — give the code editor more room"
                        className="-ml-1 rounded-md p-1 normal-case text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                      </button>
                      <span>{isInterviewer ? 'Problem to ask' : 'Problem'}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {!pickerOpen && problem?.difficulty && <DifficultyBadge value={problem.difficulty} />}
                      {canOfferPicker && (
                        <button
                          type="button"
                          onClick={() => setPickerOpen((v) => !v)}
                          className="normal-case tracking-normal text-primary hover:underline"
                        >
                          {pickerOpen ? 'Cancel' : 'Change question'}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-6 text-sm leading-relaxed text-foreground/90">
                    {canOfferPicker && pickerOpen ? (
                      <QuestionPicker
                        sessionId={sessionId!}
                        roundId={roundId!}
                        onSelected={() => { setPickerOpen(false); onProblemSelected!(); }}
                      />
                    ) : problem ? (
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
              )}

              {/* Candidate notes, and — optionally — a real code editor */}
              <div className={`flex flex-col overflow-hidden rounded-2xl border border-border/60 bg-surface/40 shadow-elev-md ${problemCollapsed ? 'flex-1' : 'flex-[5]'}`}>
                <div className="flex items-center justify-between border-b border-border/60 bg-surface/60 px-2 py-1.5 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setActiveTab('notes')}
                      className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition-colors ${activeTab === 'notes' ? 'bg-primary/10 text-primary' : 'hover:text-foreground'}`}
                    >
                      <NotebookPen className="h-3.5 w-3.5" />
                      {isSystemDesign ? 'Design Notes' : 'Notes'}
                    </button>
                    {canUseCodeEditor && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('code')}
                        className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition-colors ${activeTab === 'code' ? 'bg-primary/10 text-primary' : 'hover:text-foreground'}`}
                      >
                        <Code2 className="h-3.5 w-3.5" />
                        Code
                      </button>
                    )}
                  </div>
                  <span className="normal-case tracking-normal text-muted-foreground/70">
                    {activeTab === 'notes' ? 'Local only' : isInterviewer ? "Interviewee's editor" : 'Visible once submitted'}
                  </span>
                </div>

                {activeTab === 'code' && canUseCodeEditor ? (
                  isInterviewer ? (
                    submittedCode ? (
                      <CodeViewer code={submittedCode} language={submittedLanguage ?? null} />
                    ) : (
                      <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                        Nothing submitted yet — ask your candidate to code the solution, and it&apos;ll appear here once they submit.
                      </div>
                    )
                  ) : (
                    <CodeEditor
                      sessionId={sessionId!}
                      roundId={roundId!}
                      initialCode={submittedCode}
                      initialLanguage={submittedLanguage}
                      onSubmitted={onCodeSubmitted}
                    />
                  )
                ) : (
                  <textarea
                    className="w-full flex-1 resize-none bg-transparent p-6 font-mono text-sm leading-relaxed outline-none focus:ring-1 focus:ring-inset focus:ring-primary/20"
                    placeholder={
                      isSystemDesign
                        ? 'Sketch your design — components, API contracts, trade-offs…'
                        : 'Work through the problem here…'
                    }
                    spellCheck={false}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
