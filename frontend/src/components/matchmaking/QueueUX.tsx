import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, XCircle } from 'lucide-react';

interface QueueUXProps {
  roomName: string;
  mode: string;
  onCancel: () => void;
  isMatched: boolean;
  matchId?: string;
  onTransition: (matchId: string) => void;
}

export function QueueUX({ roomName, mode, onCancel, isMatched, matchId, onTransition }: QueueUXProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [hasJoined, setHasJoined] = useState(false);

  useEffect(() => {
    // Artificial brief "Joining" state
    const timer = setTimeout(() => setHasJoined(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (isMatched) return;
    
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isMatched]);

  useEffect(() => {
    if (isMatched && matchId) {
      // Immediately navigate to the Arena where the connection shell will be displayed
      onTransition(matchId);
    }
  }, [isMatched, matchId, onTransition]);

  // Server timeout is 15 minutes (900 seconds)
  if (elapsedSeconds >= 900 && !isMatched) {
    return (
      <div className="w-full max-w-md mx-auto text-center space-y-6 animate-in fade-in zoom-in-95 duration-300" aria-live="polite">
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight text-destructive">Queue Timeout</h2>
          <p className="text-muted-foreground text-sm">We couldn&apos;t find a match after 15 minutes.</p>
        </div>
        <Button onClick={onCancel} variant="outline" className="w-full sm:w-auto">Return to Dashboard</Button>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const getStatusMessage = () => {
    if (!hasJoined) return "Joining...";
    if (isMatched) return "Match found!";
    if (elapsedSeconds > 30) return "Searching longer...";
    return "Searching...";
  };

  return (
    <div className="w-full max-w-md mx-auto flex flex-col items-center text-center space-y-10 animate-in fade-in zoom-in-95 duration-500" aria-live="polite">
      
      {/* Header Info */}
      <div className="space-y-2">
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground transition-all duration-300">
          {getStatusMessage()}
        </h2>
        <p className="text-muted-foreground font-medium tracking-wide">
          {roomName} <span className="opacity-50 mx-2">•</span> {mode} Mode
        </p>
      </div>
      
      {/* Visual Activity & Timer */}
      <div className="flex flex-col items-center justify-center space-y-8 min-h-[160px]">
        {isMatched ? (
          <div className="text-primary font-medium animate-pulse">
            Connecting…
          </div>
        ) : (
          <>
            <div className="relative flex items-center justify-center">
              {/* Outer pulsing ring for visual atmosphere */}
              <div className="absolute inset-0 bg-primary/10 rounded-full animate-ping duration-1000 scale-150" />
              <Loader2 className="h-10 w-10 animate-spin text-primary relative z-10" />
            </div>
            
            <div 
              className="text-4xl font-mono tabular-nums tracking-tight font-medium text-foreground/80" 
              aria-label={`Elapsed time: ${elapsedSeconds} seconds`}
            >
              {formatTime(elapsedSeconds)}
            </div>
          </>
        )}
      </div>

      {/* Action */}
      {!isMatched && (
        <Button 
          variant="ghost" 
          onClick={onCancel} 
          className="text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded-full px-6 transition-all"
        >
          <XCircle className="w-4 h-4 mr-2 opacity-70" />
          Cancel Queue
        </Button>
      )}
    </div>
  );
}

