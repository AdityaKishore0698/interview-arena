import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { User } from '@/store/useAuth';

export type ChatMessage = {
  id: string;
  senderId: string;
  text: string;
  timestamp: string;
};

export function ChatPanel({
  messages,
  onSendMessage,
  currentUser,
}: {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  currentUser: User;
}) {
  const [input, setInput] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll only the message list. scrollIntoView() also scrolls every
    // overflow-hidden ancestor, which pushed the session header (round label
    // and timer) out of view whenever a message arrived.
    const list = listRef.current;
    list?.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
  }, [messages]);

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
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center space-y-3 text-center opacity-40">
            <span className="text-2xl">💬</span>
            <p className="text-xs text-muted-foreground">No messages yet. Say hello!</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isMe = msg.senderId === currentUser.id;
            return (
              <div key={msg.id} className={`flex w-full ${isMe ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl p-3 text-sm ${isMe ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-muted text-foreground rounded-bl-sm'}`}>
                  <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                  <span className={`text-[10px] mt-1 block opacity-70 ${isMe ? 'text-right' : 'text-left'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="border-t border-border/60 bg-surface/60 p-4">
        <div className="relative flex items-center">
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
    </div>
  );
}
