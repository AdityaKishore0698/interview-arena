'use client';

import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import AppLayout from '@/components/layout/AppLayout';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Loader2, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

import { SessionHeader } from '@/components/interview/SessionHeader';
import { InterviewWorkspace } from '@/components/interview/InterviewWorkspace';
import { FeedbackForm } from '@/components/interview/FeedbackForm';
import { ChatPanel, type ChatMessage } from '@/components/interview/ChatPanel';
import { VideoPanel } from '@/components/interview/VideoPanel';
import { useWebRTC, type RtcSignal } from '@/hooks/useWebRTC';

interface SessionProblem {
  id: string | null;
  title: string;
  prompt: string;
  difficulty: string | null;
  custom?: boolean;
}

interface SessionFeedback {
  evaluated_role: string | null;
  scores: Record<string, number> | null;
  comments: string | null;
  giver_user_id: string | null;
  receiver_user_id: string | null;
}

interface SessionRound {
  id: string;
  round_number: number;
  status: string;
  roles: Record<string, string>;
  problem?: SessionProblem | null;
  feedbacks?: SessionFeedback[];
}

interface SessionRoom {
  id: string;
  slug: string;
  name: string;
  difficulty: string;
  description: string | null;
}

interface SessionData {
  id: string;
  room_id: string;
  room?: SessionRoom | null;
  mode: string;
  status: string;
  version: number;
  current_ends_at?: string;
  participants: { id: string; user_id: string; seat: number }[];
  rounds: SessionRound[];
}

const SCORE_LABELS: Record<string, string> = {
  communication: 'Communication',
  technicalKnowledge: 'Technical Knowledge',
  problemSolving: 'Problem Solving',
};

function ReceivedFeedback({ rounds, userId }: { rounds: SessionRound[]; userId: string }) {
  const entries = rounds
    .map((r) => ({
      round: r.round_number,
      fb: (r.feedbacks ?? []).find((f) => f.receiver_user_id === userId),
    }))
    .filter((e) => e.fb);

  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Your partner&apos;s feedback will appear here once they submit it.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(({ round, fb }) => (
        <div key={round} className="rounded-2xl border border-border/60 bg-surface/50 p-5 text-left">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Round {round} · as {fb!.evaluated_role === 'INTERVIEWER' ? 'Interviewer' : 'Interviewee'}
          </p>
          <div className="flex flex-wrap gap-3">
            {Object.entries(fb!.scores ?? {}).map(([key, value]) => (
              <div key={key} className="rounded-xl bg-background/60 px-3 py-2">
                <span className="block text-[10px] uppercase tracking-wider text-muted-foreground">
                  {SCORE_LABELS[key] ?? key}
                </span>
                <span className="font-mono text-lg tabular-nums text-foreground">{value}/5</span>
              </div>
            ))}
          </div>
          {fb!.comments && (
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
              “{fb!.comments}”
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default function InterviewPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const sessionId = params.id as string;

  const [wsStatus, setWsStatus] = useState<'CONNECTING' | 'CONNECTED' | 'RECONNECTING'>('CONNECTING');
  const [opponentConnected, setOpponentConnected] = useState<boolean | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const { data: session, isLoading, error, refetch } = useQuery<SessionData>({
    queryKey: ['session', sessionId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/sessions/${sessionId}`);
      return res.data;
    },
    enabled: !!user && !!sessionId,
    refetchOnWindowFocus: false,
  });

  // Deterministic WebRTC roles derived from the authoritative participant list.
  const peerId = useMemo(() => {
    if (!session || !user) return null;
    return session.participants.map((p) => p.user_id).find((id) => id !== user.id) ?? null;
  }, [session, user]);

  const isOfferer = useMemo(() => {
    if (!session || !user || !peerId) return false;
    return [user.id, peerId].sort()[0] === user.id;
  }, [session, user, peerId]);

  const rtcEnabled =
    !!session && !!peerId && session.status !== 'COMPLETED' && session.status !== 'ABANDONED';

  const sendRtcSignal = useCallback((signal: RtcSignal) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'SIGNAL', payload: signal }));
    }
  }, []);

  const webrtc = useWebRTC({
    enabled: rtcEnabled,
    isOfferer,
    sessionId,
    sendSignal: sendRtcSignal,
  });

  // Stable refs so the long-lived WebSocket handler never needs re-binding.
  const handleSignalRef = useRef(webrtc.handleSignal);
  const refetchRef = useRef(refetch);
  const selfIdRef = useRef(user?.id);

  useEffect(() => {
    handleSignalRef.current = webrtc.handleSignal;
    refetchRef.current = refetch;
    selfIdRef.current = user?.id;
  }, [webrtc.handleSignal, refetch, user?.id]);

  useEffect(() => {
    if (!user || !sessionId || !token) return;

    let stopped = false;
    let isInitialConnect = true;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (stopped) return;
      if (!isInitialConnect) setWsStatus('RECONNECTING');

      const wsBase = process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws') || 'ws://localhost:8000';
      const ws = new WebSocket(`${wsBase}/api/v1/sessions/${sessionId}/ws?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (stopped) return;
        setWsStatus('CONNECTED');
        isInitialConnect = false;
        refetchRef.current();
        ws.send(JSON.stringify({ type: 'PING' }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'EVENT') {
            const ev = data.event;
            if (
              [
                'SESSION_STARTED',
                'ROUND_STARTED',
                'FEEDBACK_STARTED',
                'FEEDBACK_SUBMITTED',
                'SESSION_COMPLETED',
                'SESSION_ABANDONED',
                'SESSION_UPDATED',
              ].includes(ev)
            ) {
              refetchRef.current();
            }
            if (ev === 'OPPONENT_CONNECTED') setOpponentConnected(true);
            if (ev === 'OPPONENT_DISCONNECTED') setOpponentConnected(false);
          } else if (data.type === 'CHAT_MESSAGE') {
            const msg: ChatMessage = {
              id: data.payload.id,
              senderId: data.payload.sender_id,
              text: data.payload.text,
              timestamp: data.payload.timestamp,
            };
            // Exactly one rendered message per logical message — dedupe on the
            // server-minted id so our own echo and any reconnect replay collapse.
            setChatMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
          } else if (data.type === 'SIGNAL') {
            if (data.payload.sender_id !== selfIdRef.current) {
              handleSignalRef.current(data.payload.signal as RtcSignal);
            }
          }
        } catch (err) {
          console.error('WS parse error', err);
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        setWsStatus('RECONNECTING');
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      stopped = true;
      clearTimeout(reconnectTimer);
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [sessionId, user?.id, token, user]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'PING' }));
      }
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // When the server marks the session complete, the dashboard history is stale.
  useEffect(() => {
    if (session?.status === 'COMPLETED') {
      queryClient.invalidateQueries({ queryKey: ['history'] });
    }
  }, [session?.status, queryClient]);

  const sendMessage = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'CHAT_MESSAGE', payload: { text } }));
    }
  }, []);

  const authoritativeState = useMemo(() => {
    if (!session || !user) return null;

    const isFeedback = session.status === 'ROUND_1_FEEDBACK' || session.status === 'ROUND_2_FEEDBACK';

    const currentRound: SessionRound | undefined =
      session.rounds.find((r) => ['ACTIVE', 'FEEDBACK'].includes(r.status)) ?? session.rounds[0];

    const userRole = currentRound?.roles?.[user.id];
    const safeRole = userRole === 'INTERVIEWER' || userRole === 'INTERVIEWEE' ? userRole : 'Participant';

    let roundLabel = 'Session';
    if (session.status === 'PREPARATION' || session.status === 'CREATED') roundLabel = 'Preparation Phase';
    else if (session.status === 'ROUND_1_ACTIVE') roundLabel = 'Round 1';
    else if (session.status === 'ROUND_2_ACTIVE') roundLabel = 'Round 2';
    else if (session.status === 'ROUND_1_FEEDBACK') roundLabel = 'Round 1 Feedback';
    else if (session.status === 'ROUND_2_FEEDBACK') roundLabel = 'Round 2 Feedback';
    else if (session.status === 'COMPLETED') roundLabel = 'Session Completed';

    let presenceState: 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'WAITING' = 'CONNECTING';
    if (wsStatus === 'RECONNECTING') presenceState = 'RECONNECTING';
    else if (wsStatus === 'CONNECTED') {
      if (opponentConnected === true) presenceState = 'CONNECTED';
      else if (opponentConnected === false) presenceState = 'DISCONNECTED';
      else presenceState = 'WAITING';
    }

    return {
      currentRound,
      role: safeRole,
      roundLabel,
      presenceState,
      isFeedback,
      isPreparation: session.status === 'PREPARATION' || session.status === 'CREATED',
      isCompleted: session.status === 'COMPLETED',
      isAbandoned: session.status === 'ABANDONED',
    };
  }, [session, user, wsStatus, opponentConnected]);

  if (!user) return null;

  if (isLoading || !session) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center min-h-[70vh] animate-in fade-in zoom-in-95 duration-500" aria-live="polite">
          <div className="relative flex items-center justify-center mb-8">
            <div className="absolute inset-0 bg-primary/10 rounded-full animate-ping duration-1000 scale-[2.5]" />
            <div className="absolute inset-0 bg-primary/20 rounded-full animate-pulse scale-[1.5]" />
            <Loader2 className="w-10 h-10 animate-spin text-primary relative z-10" />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight text-foreground mb-3">Match Found!</h2>
          <p className="text-muted-foreground text-lg">Connecting to your interview partner…</p>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center min-h-[70vh] max-w-lg mx-auto text-center space-y-6 animate-in fade-in duration-500">
          <AlertTriangle className="w-12 h-12 text-destructive mb-2 opacity-80" />
          <h2 className="text-2xl font-semibold tracking-tight text-destructive">Session Unavailable</h2>
          <p className="text-muted-foreground">The session could not be retrieved. It may have expired or you may not have access.</p>
          <Button onClick={() => router.replace('/dashboard')} variant="outline" className="mt-4">Return to Dashboard</Button>
        </div>
      </AppLayout>
    );
  }

  if (!authoritativeState) return null;

  const { isCompleted, isAbandoned, isFeedback, isPreparation, role, roundLabel, currentRound, presenceState } =
    authoritativeState;

  const roomName = session.room?.name ?? 'Interview Room';
  const roomDifficulty = session.room?.difficulty;

  if (isCompleted) {
    return (
      <AppLayout>
        <div className="mx-auto flex min-h-[70vh] w-full max-w-xl flex-col items-center justify-center space-y-8 py-12 text-center animate-in fade-in slide-in-from-bottom-4 duration-700" aria-live="polite">
          <div className="rounded-full bg-success/10 p-4">
            <CheckCircle className="h-12 w-12 text-success" />
          </div>
          <div className="space-y-3">
            <h1 className="text-4xl font-semibold tracking-tight">Interview Complete</h1>
            <p className="text-lg text-muted-foreground">
              Both rounds concluded on {roomName}. Here is the feedback your partner left for you.
            </p>
          </div>
          <div className="w-full">
            <ReceivedFeedback rounds={session.rounds} userId={user.id} />
          </div>
          <div className="pt-2">
            <Button size="lg" onClick={() => router.replace('/dashboard')} className="hover:-translate-y-0.5 transition-transform">
              Return to Dashboard
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (isAbandoned) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center min-h-[70vh] text-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700" aria-live="polite">
          <div className="bg-destructive/10 p-4 rounded-full">
            <XCircle className="w-12 h-12 text-destructive" />
          </div>
          <div className="space-y-3">
            <h1 className="text-4xl font-semibold tracking-tight text-destructive">Session Abandoned</h1>
            <p className="text-lg text-muted-foreground max-w-md mx-auto">
              The interview ended because the connection was lost or one of the participants left early.
            </p>
          </div>
          <div className="pt-8">
            <Button size="lg" variant="outline" onClick={() => router.replace('/dashboard')}>
              Return to Dashboard
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  const evaluatedRole = role === 'INTERVIEWER' ? 'Interviewee' : 'Interviewer';

  return (
    <AppLayout>
      <div className="flex-1 lg:flex-none flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-background/40">
        <SessionHeader
          roundLabel={roundLabel}
          roleLabel={role}
          endsAt={session.current_ends_at}
          roomName={roomName}
          roomDifficulty={roomDifficulty}
          mode={session.mode}
          sessionId={session.id}
          presenceState={presenceState}
        />

        <div className="relative z-10 flex flex-1 flex-col overflow-hidden lg:flex-row">
          <div className="flex min-w-0 flex-1 flex-col overflow-y-auto bg-surface/30 backdrop-blur-sm">
            {isFeedback ? (
              <FeedbackForm
                sessionId={session.id}
                roundId={currentRound?.id || ''}
                evaluatedRole={evaluatedRole}
                roundLabel={roundLabel}
              />
            ) : (
              <InterviewWorkspace
                roomName={roomName}
                roomDifficulty={roomDifficulty}
                role={role}
                isPreparation={isPreparation}
                problem={currentRound?.problem ?? null}
                // The backend resolves picking for both registered rounds
                // (a real row) and guest rounds (their Redis session), so
                // this is passed unconditionally now.
                sessionId={sessionId}
                roundId={currentRound?.id}
                onProblemSelected={refetch}
              />
            )}
          </div>

          {!isPreparation && !isFeedback && (
            <div className="flex shrink-0 flex-col border-t border-border/60 bg-background/50 animate-in fade-in slide-in-from-right-4 duration-500 lg:w-[380px] lg:border-l lg:border-t-0 xl:w-[420px]">
              <VideoPanel
                localStream={webrtc.localStream}
                remoteStream={webrtc.remoteStream}
                connected={webrtc.connected}
                callRequested={webrtc.callRequested}
                connectFailed={webrtc.connectFailed}
                mediaError={webrtc.mediaError}
                hasMedia={webrtc.hasMedia}
                audioEnabled={webrtc.audioEnabled}
                videoEnabled={webrtc.videoEnabled}
                onStartCall={webrtc.startCall}
                onRetry={webrtc.retryConnection}
                onToggleAudio={webrtc.toggleAudio}
                onToggleVideo={webrtc.toggleVideo}
              />
              <div className="flex min-h-0 flex-1 flex-col">
                <ChatPanel messages={chatMessages} onSendMessage={sendMessage} currentUser={user} />
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
