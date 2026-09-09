'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Minimal, correct 1:1 WebRTC lifecycle for the interview arena.
 *
 * Contract:
 * - Exactly one RTCPeerConnection per session/client lifecycle. It is owned by
 *   the interview page (which stays mounted across prep/round/feedback phases),
 *   NOT by the collapsible VideoPanel.
 * - Deterministic offer/answer ownership: the participant whose id sorts first
 *   is the sole offerer. The other participant only ever answers.
 * - The WebSocket is signalling transport only; media never touches the backend.
 * - ICE candidates that arrive before the remote description is set are queued
 *   and flushed afterwards.
 * - Signals tagged with a superseded negotiation id are ignored.
 * - Tracks are never added to a closed connection; effect re-mounts (React
 *   StrictMode) rebuild cleanly instead of throwing.
 */

export type RtcSignal =
  | { kind: 'call' }
  | { kind: 'bye' }
  | { kind: 'offer'; negId: string; sdp: RTCSessionDescriptionInit }
  | { kind: 'answer'; negId: string; sdp: RTCSessionDescriptionInit }
  | { kind: 'ice'; negId: string; candidate: RTCIceCandidateInit };

interface UseWebRTCArgs {
  /** True while the session is live (not completed / abandoned / loading). */
  enabled: boolean;
  /** Deterministic: this client owns the offer. */
  isOfferer: boolean;
  /** Stable session id — used to persist "call requested" across reloads. */
  sessionId: string;
  /** Send a signal to the peer over the existing WebSocket. */
  sendSignal: (signal: RtcSignal) => void;
}

const ICE_SERVERS: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }];

export function useWebRTC({ enabled, isOfferer, sessionId, sendSignal }: UseWebRTCArgs) {
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [connected, setConnected] = useState(false);
  const [callRequested, setCallRequested] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [videoEnabled, setVideoEnabled] = useState(true);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const sendSignalRef = useRef(sendSignal);
  const isOffererRef = useRef(isOfferer);

  useEffect(() => {
    sendSignalRef.current = sendSignal;
    isOffererRef.current = isOfferer;
  }, [sendSignal, isOfferer]);

  // Negotiation bookkeeping
  const negIdRef = useRef<string | null>(null); // negotiation this client is currently part of
  const answeredNegIdRef = useRef<string | null>(null); // last offer we answered
  const makingOfferRef = useRef(false);
  const callActiveRef = useRef(false);
  const pendingIce = useRef<{ negId: string; candidate: RTCIceCandidateInit }[]>([]);
  const mediaStartedRef = useRef(false);

  const storageKey = `arena.call.${sessionId}`;

  const flushPendingIce = useCallback(async () => {
    const pc = pcRef.current;
    if (!pc || !pc.remoteDescription || !negIdRef.current) return;
    const current = negIdRef.current;
    for (const item of pendingIce.current) {
      if (item.negId !== current) continue; // drop stale
      try {
        await pc.addIceCandidate(new RTCIceCandidate(item.candidate));
      } catch (err) {
        console.warn('[webrtc] failed to add queued ICE candidate', err);
      }
    }
    pendingIce.current = [];
  }, []);

  const maybeNegotiate = useCallback(async (opts?: { iceRestart?: boolean }) => {
    const pc = pcRef.current;
    if (!pc || pc.signalingState === 'closed') return;
    if (!isOffererRef.current) return; // deterministic: only the offerer offers
    if (!callActiveRef.current) return; // wait until someone actually asked
    if (!localStreamRef.current) return; // need media first
    if (makingOfferRef.current) return;
    if (pc.signalingState !== 'stable') return; // already negotiating

    try {
      makingOfferRef.current = true;
      const negId = crypto.randomUUID();
      negIdRef.current = negId;
      const offer = await pc.createOffer(opts?.iceRestart ? { iceRestart: true } : undefined);
      if (pc.signalingState !== 'stable') return; // raced with something else
      await pc.setLocalDescription(offer);
      sendSignalRef.current({ kind: 'offer', negId, sdp: pc.localDescription!.toJSON() });
    } catch (err) {
      console.error('[webrtc] failed to create offer', err);
    } finally {
      makingOfferRef.current = false;
    }
  }, []);

  const ensurePeer = useCallback((): RTCPeerConnection => {
    if (pcRef.current && pcRef.current.signalingState !== 'closed') return pcRef.current;

    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current = pc;

    pc.onicecandidate = (event) => {
      if (event.candidate && negIdRef.current) {
        sendSignalRef.current({
          kind: 'ice',
          negId: negIdRef.current,
          candidate: event.candidate.toJSON(),
        });
      }
    };

    pc.ontrack = (event) => {
      let stream = remoteStreamRef.current;
      if (event.streams[0]) {
        stream = event.streams[0];
      } else {
        stream = stream ?? new MediaStream();
        stream.addTrack(event.track);
      }
      remoteStreamRef.current = stream;
      setRemoteStream(stream);
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      if (state === 'connected') setConnected(true);
      if (state === 'failed' || state === 'disconnected' || state === 'closed') {
        setConnected(false);
        // If the peer dropped (e.g. reloaded) mid-call, the offerer re-negotiates
        // with an ICE restart so media re-establishes without a manual reconnect.
        if ((state === 'failed' || state === 'disconnected') && callActiveRef.current && isOffererRef.current) {
          window.setTimeout(() => {
            if (pcRef.current === pc && pc.connectionState !== 'connected') {
              void maybeNegotiate({ iceRestart: true });
            }
          }, 1500);
        }
      }
    };

    pc.onnegotiationneeded = () => {
      void maybeNegotiate();
    };

    // Attach any local tracks acquired before the PC existed.
    const stream = localStreamRef.current;
    if (stream) {
      for (const track of stream.getTracks()) {
        const alreadyAdded = pc.getSenders().some((s) => s.track === track);
        if (!alreadyAdded) pc.addTrack(track, stream);
      }
    }
    return pc;
  }, [maybeNegotiate]);

  const acquireMedia = useCallback(async () => {
    if (mediaStartedRef.current) return;
    mediaStartedRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      const pc = pcRef.current;
      if (!pc || pc.signalingState === 'closed') {
        // PC was torn down (StrictMode remount) before media resolved.
        stream.getTracks().forEach((t) => t.stop());
        mediaStartedRef.current = false;
        return;
      }
      localStreamRef.current = stream;
      setLocalStream(stream);
      setMediaError(null);
      setAudioEnabled(stream.getAudioTracks()[0]?.enabled ?? true);
      setVideoEnabled(stream.getVideoTracks()[0]?.enabled ?? true);
      for (const track of stream.getTracks()) {
        const alreadyAdded = pc.getSenders().some((s) => s.track === track);
        if (!alreadyAdded) pc.addTrack(track, stream);
      }
      void maybeNegotiate();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.warn('[webrtc] media unavailable', err);
      setMediaError(message);
      mediaStartedRef.current = false;
    }
  }, [maybeNegotiate]);

  const teardown = useCallback(() => {
    const pc = pcRef.current;
    if (pc) {
      pc.onicecandidate = null;
      pc.ontrack = null;
      pc.onconnectionstatechange = null;
      pc.onnegotiationneeded = null;
      try {
        pc.close();
      } catch {
        /* already closed */
      }
    }
    pcRef.current = null;
    localStreamRef.current?.getTracks().forEach((t) => t.stop());
    localStreamRef.current = null;
    remoteStreamRef.current = null;
    negIdRef.current = null;
    answeredNegIdRef.current = null;
    makingOfferRef.current = false;
    pendingIce.current = [];
    mediaStartedRef.current = false;
    setLocalStream(null);
    setRemoteStream(null);
    setConnected(false);
  }, []);

  // Lifecycle: bring media + PC up while the session is live, tear down otherwise.
  useEffect(() => {
    if (!enabled) return;
    ensurePeer();
    // getUserMedia resolves asynchronously; the setState calls in acquireMedia
    // happen well after this effect returns (external-device subscription).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void acquireMedia();

    let resume = false;
    try {
      resume = sessionStorage.getItem(storageKey) === '1';
    } catch {
      /* storage unavailable */
    }
    if (resume) {
      callActiveRef.current = true;
      setCallRequested(true);
      sendSignalRef.current({ kind: 'call' });
      void maybeNegotiate();
    }

    return () => {
      teardown();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, sessionId]);

  /** Feed a signal received from the peer over the WebSocket. */
  const handleSignal = useCallback(
    async (signal: RtcSignal) => {
      const pc = ensurePeer();
      if (pc.signalingState === 'closed') return;

      try {
        if (signal.kind === 'call') {
          callActiveRef.current = true;
          setCallRequested(true);
          void maybeNegotiate();
          return;
        }

        if (signal.kind === 'bye') {
          setConnected(false);
          return;
        }

        if (signal.kind === 'offer') {
          if (isOffererRef.current) return; // offerer never answers
          if (answeredNegIdRef.current === signal.negId) return; // duplicate offer
          callActiveRef.current = true;
          setCallRequested(true);
          negIdRef.current = signal.negId;
          await pc.setRemoteDescription(new RTCSessionDescription(signal.sdp));
          await flushPendingIce();
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          answeredNegIdRef.current = signal.negId;
          sendSignalRef.current({
            kind: 'answer',
            negId: signal.negId,
            sdp: pc.localDescription!.toJSON(),
          });
          return;
        }

        if (signal.kind === 'answer') {
          if (!isOffererRef.current) return; // only the offerer consumes answers
          if (signal.negId !== negIdRef.current) return; // stale negotiation
          if (pc.signalingState !== 'have-local-offer') return; // not waiting for an answer
          await pc.setRemoteDescription(new RTCSessionDescription(signal.sdp));
          await flushPendingIce();
          return;
        }

        if (signal.kind === 'ice') {
          if (signal.negId !== negIdRef.current || !pc.remoteDescription) {
            pendingIce.current.push({ negId: signal.negId, candidate: signal.candidate });
            return;
          }
          try {
            await pc.addIceCandidate(new RTCIceCandidate(signal.candidate));
          } catch (err) {
            console.warn('[webrtc] addIceCandidate failed', err);
          }
        }
      } catch (err) {
        console.error('[webrtc] error handling signal', signal.kind, err);
      }
    },
    [ensurePeer, flushPendingIce, maybeNegotiate],
  );

  const startCall = useCallback(() => {
    callActiveRef.current = true;
    setCallRequested(true);
    try {
      sessionStorage.setItem(storageKey, '1');
    } catch {
      /* storage unavailable */
    }
    ensurePeer();
    sendSignalRef.current({ kind: 'call' });
    void maybeNegotiate();
  }, [ensurePeer, maybeNegotiate, storageKey]);

  const toggleAudio = useCallback(() => {
    const track = localStreamRef.current?.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setAudioEnabled(track.enabled);
  }, []);

  const toggleVideo = useCallback(() => {
    const track = localStreamRef.current?.getVideoTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setVideoEnabled(track.enabled);
  }, []);

  return {
    localStream,
    remoteStream,
    connected,
    callRequested,
    mediaError,
    audioEnabled,
    videoEnabled,
    hasMedia: !!localStream,
    handleSignal,
    startCall,
    toggleAudio,
    toggleVideo,
  };
}
