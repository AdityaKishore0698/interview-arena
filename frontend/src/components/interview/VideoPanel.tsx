'use client';

import { useEffect, useRef } from 'react';
import { Camera, CameraOff, Loader2, Mic, MicOff, Video } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface VideoPanelProps {
  localStream: MediaStream | null;
  remoteStream: MediaStream | null;
  connected: boolean;
  callRequested: boolean;
  mediaError: string | null;
  hasMedia: boolean;
  audioEnabled: boolean;
  videoEnabled: boolean;
  onStartCall: () => void;
  onToggleAudio: () => void;
  onToggleVideo: () => void;
}

export function VideoPanel({
  localStream,
  remoteStream,
  connected,
  callRequested,
  mediaError,
  hasMedia,
  audioEnabled,
  videoEnabled,
  onStartCall,
  onToggleAudio,
  onToggleVideo,
}: VideoPanelProps) {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);

  // The streams are owned by the page-level hook; this panel only attaches them
  // to its <video> elements whenever it (re)mounts between session phases.
  useEffect(() => {
    if (localVideoRef.current && localVideoRef.current.srcObject !== localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  useEffect(() => {
    if (remoteVideoRef.current && remoteVideoRef.current.srcObject !== remoteStream) {
      remoteVideoRef.current.srcObject = remoteStream;
    }
  }, [remoteStream]);

  return (
    <div className="flex shrink-0 flex-col border-b border-border/60 bg-background/50">
      <div className="relative aspect-video w-full overflow-hidden bg-black/90">
        <video
          ref={remoteVideoRef}
          autoPlay
          playsInline
          className={`h-full w-full object-cover transition-opacity ${connected ? 'opacity-100' : 'opacity-0'}`}
        />

        {connected ? (
          <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/55 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest text-white backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Connected
          </div>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface/20 backdrop-blur-md">
              {callRequested && !mediaError ? (
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              ) : (
                <Video className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
            <p className="max-w-[220px] text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
              {mediaError
                ? `Media unavailable: ${mediaError}`
                : callRequested
                  ? 'Connecting…'
                  : 'Waiting for opponent...'}
            </p>
            {!callRequested && !mediaError && (
              <Button
                onClick={onStartCall}
                variant="outline"
                size="sm"
                className="border-border/30 bg-background/20 backdrop-blur-md"
              >
                Connect Audio/Video
              </Button>
            )}
          </div>
        )}

        {/* Local preview */}
        <div className="absolute bottom-3 right-3 aspect-video w-24 overflow-hidden rounded-lg border border-white/10 bg-black/80 shadow-2xl">
          <video ref={localVideoRef} autoPlay playsInline muted className="mirror h-full w-full object-cover" />
          {!videoEnabled && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/80">
              <CameraOff className="h-4 w-4 text-white/70" />
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-2 bg-surface/60 p-3">
        <Button
          variant={audioEnabled ? 'secondary' : 'destructive'}
          size="icon"
          onClick={onToggleAudio}
          disabled={!hasMedia}
          aria-label={audioEnabled ? 'Mute microphone' : 'Unmute microphone'}
          aria-pressed={!audioEnabled}
        >
          {audioEnabled ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
        </Button>
        <Button
          variant={videoEnabled ? 'secondary' : 'destructive'}
          size="icon"
          onClick={onToggleVideo}
          disabled={!hasMedia}
          aria-label={videoEnabled ? 'Turn camera off' : 'Turn camera on'}
          aria-pressed={!videoEnabled}
        >
          {videoEnabled ? <Camera className="h-4 w-4" /> : <CameraOff className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
