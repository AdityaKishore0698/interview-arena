import { CountdownTimer } from './CountdownTimer';
import { LeaveButton } from './LeaveButton';
import { PresenceIndicator, PresenceState } from './PresenceIndicator';

interface SessionHeaderProps {
  roundLabel: string;
  roleLabel: string;
  endsAt?: string;
  roomName: string;
  roomDifficulty?: string;
  mode: string;
  sessionId: string;
  presenceState: PresenceState;
}

export function SessionHeader({
  roundLabel,
  roleLabel,
  endsAt,
  roomName,
  roomDifficulty,
  mode,
  sessionId,
  presenceState,
}: SessionHeaderProps) {
  return (
    <header className="z-20 flex flex-col justify-between gap-4 border-b border-border/60 bg-surface/40 px-6 py-4 backdrop-blur-md md:flex-row md:items-center">
      {/* Context Left */}
      <div className="flex flex-col gap-1.5">
        <h1 className="flex items-center text-xl font-semibold tracking-tight text-foreground md:text-2xl">
          {roundLabel}
          <span className="sr-only">You are the </span>
          <span className="ml-3 rounded-md border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-primary">
            {roleLabel}
          </span>
        </h1>
        <p className="flex items-center gap-2 text-sm font-medium tracking-wide text-muted-foreground">
          <span className="text-foreground/80">{roomName}</span>
          {roomDifficulty && (
            <>
              <span className="h-1 w-1 rounded-full bg-muted-foreground/40" />
              <span>{roomDifficulty}</span>
            </>
          )}
          <span className="h-1 w-1 rounded-full bg-muted-foreground/40" />
          <span>{mode} Mode</span>
        </p>
      </div>

      {/* Actions Right */}
      <div className="flex items-center gap-4 md:gap-6">
        <PresenceIndicator state={presenceState} />

        <div className="flex min-w-[104px] flex-col items-end border-l border-border/60 pl-4 md:pl-6">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
            Ends in
          </span>
          <div className="flex h-9 items-center md:h-10">
            <CountdownTimer endsAt={endsAt} />
          </div>
        </div>

        <div className="border-l border-border/60 pl-4 md:pl-6">
          <LeaveButton sessionId={sessionId} />
        </div>
      </div>
    </header>
  );
}
