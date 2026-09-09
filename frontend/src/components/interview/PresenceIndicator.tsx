import { WifiOff, Loader2, Hourglass } from 'lucide-react';

export type PresenceState = 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED' | 'WAITING';

export function PresenceIndicator({ state }: { state: PresenceState }) {
  const getIcon = () => {
    switch (state) {
      case 'CONNECTING':
      case 'RECONNECTING':
        return <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />;
      case 'WAITING':
        return <Hourglass className="w-3.5 h-3.5 text-warning" />;
      case 'CONNECTED':
        return <div className="w-2 h-2 rounded-full bg-success relative">
          <div className="absolute inset-0 rounded-full bg-success animate-ping opacity-50" />
        </div>;
      case 'DISCONNECTED':
        return <WifiOff className="w-3.5 h-3.5 text-destructive" />;
    }
  };

  const getLabel = () => {
    switch (state) {
      case 'CONNECTING': return 'Connecting...';
      case 'WAITING': return 'Waiting for opponent';
      case 'CONNECTED': return 'Opponent Connected';
      case 'RECONNECTING': return 'Reconnecting...';
      case 'DISCONNECTED': return 'Opponent Disconnected';
    }
  };

  return (
    <div 
      className="flex items-center space-x-2 text-sm" 
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center justify-center w-4 h-4">
        {getIcon()}
      </div>
      <span className={`font-medium text-xs uppercase tracking-wider ${
        state === 'CONNECTED' ? 'text-success' : 
        state === 'DISCONNECTED' ? 'text-destructive' : 
        'text-muted-foreground'
      }`}>{getLabel()}</span>
    </div>
  );
}
