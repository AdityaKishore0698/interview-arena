'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import AppLayout from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Loader2, ArrowRight } from 'lucide-react';
import { QueueUX } from '@/components/matchmaking/QueueUX';

interface Room {
  id: string;
  name: string;
  description: string;
  difficulty?: string;
}

interface HistoryFeedback {
  scores: Record<string, number> | null;
  comments: string | null;
  evaluated_role: string | null;
  giver_user_id: string | null;
  receiver_user_id: string | null;
}

interface HistorySession {
  id: string;
  mode: string;
  created_at: string;
  room: { name: string; slug: string; difficulty: string } | null;
  rounds: { round_number: number; feedbacks: HistoryFeedback[] }[];
}

const SCORE_LABELS: Record<string, string> = {
  communication: 'Communication',
  technicalKnowledge: 'Technical',
  problemSolving: 'Problem Solving',
};

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const res = await api.get('/api/v1/sessions/user/history');
      return res.data.history as HistorySession[];
    },
    enabled: !!user && user.type === 'REGISTERED',
  });

  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<string>("QUICK");
  const [isQueuing, setIsQueuing] = useState(false);
  const [matchId, setMatchId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      router.replace('/');
    }
  }, [user, router]);

  // Fetch Rooms
  const { data: roomsData, isLoading: roomsLoading } = useQuery({
    queryKey: ['rooms'],
    queryFn: async () => {
      const res = await api.get('/api/v1/rooms');
      return res.data.rooms as Room[];
    },
    enabled: !!user,
  });

  // Join Queue Mutation
  const joinMutation = useMutation({
    mutationFn: async ({ roomId, mode }: { roomId: string, mode: string }) => {
      const res = await api.post('/api/v1/matchmaking/join', {
        room_id: roomId,
        mode,
        last_partner: "" // not implemented yet
      });
      return res.data;
    },
    onSuccess: (data) => {
      if (data.status === 'MATCH_FOUND' || data.status === 'ALREADY_MATCHED') {
        const foundMatchId = data.match?.match_id || data.match_id;
        if (foundMatchId) {
          setMatchId(foundMatchId);
        }
      }
    },
    onError: (err) => {
      console.error("Matchmaking error:", err);
      handleCancelQueue();
    }
  });

  // Leave Queue Mutation
  const leaveMutation = useMutation({
    mutationFn: async ({ roomId, mode }: { roomId: string, mode: string }) => {
      const res = await api.post('/api/v1/matchmaking/leave', {
        room_id: roomId,
        mode
      });
      return res.data;
    },
    onSettled: () => {
      setIsQueuing(false);
      setMatchId(null);
    }
  });

  // Poll matchmaking status
  const { data: statusData } = useQuery({
    queryKey: ['matchmaking_status'],
    queryFn: async () => {
      const res = await api.get('/api/v1/matchmaking/status');
      return res.data;
    },
    enabled: isQueuing && !matchId,
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (statusData?.status === 'MATCH_FOUND' && statusData?.match_id) {
      setTimeout(() => setMatchId(statusData.match_id), 0);
    }
  }, [statusData]);

  const handleJoinQueue = () => {
    if (!selectedRoomId) return;
    setIsQueuing(true);
    setMatchId(null);
    joinMutation.mutate({ roomId: selectedRoomId, mode: selectedMode });
  };

  const handleCancelQueue = () => {
    if (selectedRoomId) {
      leaveMutation.mutate({ roomId: selectedRoomId, mode: selectedMode });
    } else {
      setIsQueuing(false);
      setMatchId(null);
    }
  };

  const handleTransition = (id: string) => {
    router.push(`/interview/${id}`);
  };

  if (!user) return null;

  return (
    <AppLayout>
      <div className="container mx-auto px-6 py-12 max-w-4xl relative z-10">
        
        {isQueuing ? (
          <div className="flex justify-center items-center min-h-[60vh] animate-in fade-in duration-700">
            <QueueUX 
              roomName={roomsData?.find(r => r.id === selectedRoomId)?.name || 'Unknown Room'}
              mode={selectedMode}
              onCancel={handleCancelQueue}
              isMatched={!!matchId}
              matchId={matchId || undefined}
              onTransition={handleTransition}
            />
          </div>
        ) : (
          <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            <header className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                Interview Arena
              </p>
              <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
                Start an Interview
              </h1>
              <p className="text-lg text-muted-foreground">
                Choose a room and mode. You&apos;ll be matched with a peer and dropped straight into the session.
              </p>
            </header>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mt-8">
              
              {/* Room Selection */}
              <section className="space-y-4">
                <h2 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase flex items-center">
                  <span className="w-6 h-px bg-border mr-4"></span> Room
                </h2>
                
                {roomsLoading ? (
                  <div className="flex items-center space-x-3 text-muted-foreground py-4">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading rooms...</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {roomsData?.map((room) => {
                      const isSelected = selectedRoomId === room.id;
                      return (
                        <div 
                          key={room.id}
                          role="button"
                          tabIndex={0}
                          className={`group relative flex items-center justify-between px-6 py-5 rounded-2xl border border-transparent transition-all duration-300 cursor-pointer overflow-hidden ${
                            isSelected 
                              ? 'bg-surface shadow-[0_4px_20px_rgba(0,0,0,0.05)] border-primary/20 dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)]' 
                              : 'hover:bg-surface/50 border-transparent'
                          }`}
                          onClick={() => setSelectedRoomId(room.id)}
                          onKeyDown={(e) => e.key === 'Enter' && setSelectedRoomId(room.id)}
                        >
                          <div className={`absolute left-0 top-0 bottom-0 w-1 transition-all duration-300 ${isSelected ? 'bg-primary' : 'bg-transparent group-hover:bg-primary/30'}`} />
                          
                          <div className="space-y-1">
                            <h3 className={`text-base font-semibold tracking-tight transition-colors duration-300 ${isSelected ? 'text-primary' : 'text-foreground group-hover:text-foreground/80'}`}>
                              {room.name}
                            </h3>
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {room.description}
                            </p>
                          </div>
                          
                          <div className={`transition-all duration-300 ${isSelected ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}>
                            <ArrowRight className="h-4 w-4 text-primary" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Mode Selection */}
              <section className="space-y-4 transition-all duration-500">
                <h2 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase flex items-center">
                  <span className="w-6 h-px bg-border mr-4"></span> Interview Mode
                </h2>
                
                <div className="flex flex-col gap-3">
                  {[
                    { id: 'QUICK', name: 'Quick', desc: 'Shorter preparation and interview rounds' },
                    { id: 'STANDARD', name: 'Standard', desc: 'Full length mock interview session' }
                  ].map((mode) => {
                    const isSelected = selectedMode === mode.id;
                    const isDisabled = !selectedRoomId;
                    return (
                      <div 
                        key={mode.id}
                        role="button"
                        tabIndex={isDisabled ? -1 : 0}
                        className={`group relative flex flex-col p-6 rounded-2xl border border-transparent transition-all duration-300 ${isDisabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${
                          isSelected && !isDisabled
                            ? 'bg-surface shadow-[0_4px_20px_rgba(0,0,0,0.05)] border-primary/20 dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)]' 
                            : !isDisabled ? 'hover:bg-surface/50' : ''
                        }`}
                        onClick={() => !isDisabled && setSelectedMode(mode.id)}
                        onKeyDown={(e) => e.key === 'Enter' && !isDisabled && setSelectedMode(mode.id)}
                      >
                         <div className={`absolute left-0 top-0 bottom-0 w-1 transition-all duration-300 ${isSelected && !isDisabled ? 'bg-primary' : 'bg-transparent group-hover:bg-primary/30'}`} />
                        
                        <h3 className={`text-base font-semibold tracking-tight transition-colors duration-300 ${isSelected && !isDisabled ? 'text-primary' : 'text-foreground'}`}>
                          {mode.name}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {mode.desc}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </section>
            </div>

              <div className="mx-auto max-w-sm pt-10">
                <Button
                  className={`relative h-14 w-full overflow-hidden rounded-full border-0 bg-primary-gradient text-base font-semibold text-white shadow-glow transition-all duration-300 hover:scale-[1.02] hover:shadow-glow-strong active:scale-[0.98] ${selectedRoomId ? 'opacity-100' : 'pointer-events-none opacity-50'}`}
                  size="lg"
                  onClick={handleJoinQueue}
                  disabled={!selectedRoomId || joinMutation.isPending}
                >
                  <span className="relative z-10 flex items-center">
                    {joinMutation.isPending ? (
                      <>
                        <Loader2 className="mr-3 h-5 w-5 animate-spin opacity-70" />
                        Joining Queue...
                      </>
                    ) : (
                      <>
                        Join Queue
                        <ArrowRight className="ml-3 h-5 w-5 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </span>
                  <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </Button>
              </div>


            {/* History Section */}
            <section className="space-y-4 mt-16 pt-8 border-t border-border/40">
              <h2 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase flex items-center">
                <span className="w-6 h-px bg-border mr-4"></span> Recent Interviews
              </h2>
              {user.type !== 'REGISTERED' ? (
                <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border/50 bg-surface/30 p-8 text-center">
                  <p className="text-foreground">Guest sessions don&apos;t save history.</p>
                  <p className="text-sm text-muted-foreground max-w-sm">
                    Create a free account to keep every round&apos;s feedback and revisit it here later.
                  </p>
                  <Button variant="outline" size="sm" onClick={() => router.push('/?mode=register')} className="mt-1">
                    Create a free account
                  </Button>
                </div>
              ) : historyLoading ? (
                 <div className="flex items-center space-x-3 text-muted-foreground py-4">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading history...</span>
                  </div>
              ) : historyData && historyData.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {historyData.map((session) => {
                    const received = session.rounds
                      .map((r) => ({
                        round: r.round_number,
                        fb: r.feedbacks.find((f) => f.receiver_user_id === user.id),
                      }))
                      .filter((e) => e.fb);
                    return (
                      <div key={session.id} className="space-y-3 rounded-2xl border border-border/40 bg-surface p-5">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold text-foreground">
                              {session.room?.name ?? 'Interview'}
                              {session.room?.difficulty ? (
                                <span className="ml-2 text-xs font-medium text-muted-foreground">
                                  {session.room.difficulty}
                                </span>
                              ) : null}
                            </h3>
                            <p className="text-xs text-muted-foreground">{session.mode} Mode</p>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {new Date(session.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        {received.length > 0 ? (
                          <div className="space-y-2 border-t border-border/40 pt-3">
                            {received.map(({ round, fb }) => (
                              <div key={round} className="text-xs">
                                <span className="font-semibold uppercase tracking-wider text-muted-foreground">
                                  Round {round}
                                </span>
                                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
                                  {Object.entries(fb!.scores ?? {}).map(([k, v]) => (
                                    <span key={k}>
                                      {SCORE_LABELS[k] ?? k}{' '}
                                      <span className="font-mono text-foreground">{v}/5</span>
                                    </span>
                                  ))}
                                </div>
                                {fb!.comments && (
                                  <p className="mt-1 line-clamp-2 text-foreground/80">“{fb!.comments}”</p>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="border-t border-border/40 pt-3 text-xs text-muted-foreground">
                            No feedback recorded.
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 text-center text-muted-foreground bg-surface/30 rounded-2xl border border-dashed border-border/50">
                   No completed interviews yet. Join a queue to get started!
                </div>
              )}
            </section>

          </div>
        )}
      </div>
    </AppLayout>
  );
}
