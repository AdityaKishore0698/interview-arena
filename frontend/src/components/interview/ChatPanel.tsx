import { useState, useRef, useEffect } from 'react';
import { ImagePlus, Loader2, Maximize2, Send } from 'lucide-react';
import { User } from '@/store/useAuth';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';

export type ChatMessage = {
  id: string;
  senderId: string;
  text: string;
  timestamp: string;
};

export type SharedImage = {
  id: string;
  senderId: string;
  /** data: URI — relayed exactly like a chat message, never persisted
   * anywhere (not even localStorage), so it's gone on reload or when the
   * interview ends. */
  image: string;
  timestamp: string;
};

const MAX_IMAGE_DIMENSION = 1200;
const IMAGE_JPEG_QUALITY = 0.8;

/** Client-side downscale + re-encode before it ever touches the WebSocket —
 * a phone photo can be several MB, and the whole point of the pure-relay
 * approach is keeping that payload reasonable through the WS pipe and Redis
 * pub/sub channel (see the backend's IMAGE_SHARE handler). */
function compressImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read that file.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Could not load that image.'));
      img.onload = () => {
        const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext('2d');
        if (!ctx) { reject(new Error('Could not process that image.')); return; }
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', IMAGE_JPEG_QUALITY));
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  });
}

type TimelineEntry =
  | { kind: 'text'; id: string; senderId: string; timestamp: string; text: string }
  | { kind: 'image'; id: string; senderId: string; timestamp: string; image: string };

export function ChatPanel({
  messages,
  onSendMessage,
  currentUser,
  sharedImages = [],
  onSendImage,
}: {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  currentUser: User;
  sharedImages?: SharedImage[];
  onSendImage?: (dataUri: string) => void;
}) {
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [maximizedImage, setMaximizedImage] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const timeline: TimelineEntry[] = [
    ...messages.map((m): TimelineEntry => ({ kind: 'text', id: m.id, senderId: m.senderId, timestamp: m.timestamp, text: m.text })),
    ...sharedImages.map((img): TimelineEntry => ({ kind: 'image', id: img.id, senderId: img.senderId, timestamp: img.timestamp, image: img.image })),
  ].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  useEffect(() => {
    // Scroll only the message list. scrollIntoView() also scrolls every
    // overflow-hidden ancestor, which pushed the session header (round label
    // and timer) out of view whenever a message arrived.
    const list = listRef.current;
    list?.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
  }, [messages, sharedImages]);

  const handleFileChosen = async (file: File | undefined) => {
    if (!file || !onSendImage) return;
    setUploadError(null);
    if (!file.type.startsWith('image/')) {
      setUploadError('Please choose an image file.');
      return;
    }
    setUploading(true);
    try {
      onSendImage(await compressImageFile(file));
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Could not share that image.');
    } finally {
      setUploading(false);
    }
  };

  const handleSend = () => {
    if (input.trim().length > 0) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface/40">
      <div className="flex items-center justify-between border-b border-border/60 bg-surface/60 px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Session Chat</h3>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">Relayed via server</span>
      </div>

      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {timeline.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center space-y-3 text-center opacity-40">
            <span className="text-2xl">💬</span>
            <p className="text-xs text-muted-foreground">No messages yet. Say hello!</p>
          </div>
        ) : (
          timeline.map((entry) => {
            const isMe = entry.senderId === currentUser.id;
            return (
              <div key={entry.id} className={`flex w-full ${isMe ? 'justify-end' : 'justify-start'}`}>
                {entry.kind === 'text' ? (
                  <div className={`max-w-[85%] rounded-2xl p-3 text-sm ${isMe ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'}`}>
                    <p className="whitespace-pre-wrap break-words">{entry.text}</p>
                    <span className={`text-[10px] mt-1 block opacity-70 ${isMe ? 'text-right' : 'text-left'}`}>
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ) : (
                  <div className={`max-w-[85%] overflow-hidden rounded-2xl ${isMe ? 'rounded-br-sm' : 'rounded-bl-sm'} border border-border/60 bg-muted`}>
                    <button
                      type="button"
                      onClick={() => setMaximizedImage(entry.image)}
                      className="group relative block w-full"
                      aria-label="View full size"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element -- a relayed data: URI, not a next/image-eligible static/remote asset */}
                      <img src={entry.image} alt="Shared during the interview" className="block max-h-72 w-full object-contain" />
                      <span className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all group-hover:bg-black/30 group-hover:opacity-100">
                        <Maximize2 className="h-6 w-6 text-white drop-shadow" />
                      </span>
                    </button>
                    <span className={`block px-3 py-1.5 text-[10px] opacity-70 ${isMe ? 'text-right' : 'text-left'}`}>
                      {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="border-t border-border/60 bg-surface/60 p-4">
        {uploadError && <p className="mb-2 text-xs text-destructive">{uploadError}</p>}
        <div className="relative flex items-center">
          {onSendImage && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  handleFileChosen(e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                aria-label="Share an image"
                title="Share an image"
                className="mr-2 shrink-0 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-surface hover:text-foreground disabled:opacity-50"
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
              </button>
            </>
          )}
          <textarea
            className="w-full resize-none rounded-xl border border-border bg-background py-3 pl-4 pr-12 text-sm transition-colors placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            maxLength={500}
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            aria-label="Send message"
            className="absolute right-2 p-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      <Dialog open={!!maximizedImage} onOpenChange={(open) => { if (!open) setMaximizedImage(null); }}>
        <DialogContent className="max-w-[95vw] border-none bg-transparent p-0 shadow-none sm:max-w-[90vw]">
          <DialogTitle className="sr-only">Shared image, full size</DialogTitle>
          {maximizedImage && (
            // eslint-disable-next-line @next/next/no-img-element -- a relayed data: URI
            <img
              src={maximizedImage}
              alt="Shared during the interview — full size"
              className="max-h-[85vh] w-full rounded-xl object-contain"
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
