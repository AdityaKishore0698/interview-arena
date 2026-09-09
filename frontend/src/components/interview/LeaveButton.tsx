import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Loader2, LogOut } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';

export function LeaveButton({ sessionId }: { sessionId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const router = useRouter();

  const handleLeave = async () => {
    setIsLeaving(true);
    try {
      await api.post(`/api/v1/sessions/${sessionId}/leave`);
      router.replace('/dashboard');
    } catch (e) {
      console.error(e);
      router.replace('/dashboard');
    }
  };

  return (
    <>
      <Button variant="ghost" onClick={() => setIsOpen(true)} className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors">
        <LogOut className="w-4 h-4 mr-2 opacity-80" />
        Leave
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Leave Interview?</DialogTitle>
            <DialogDescription>
              Are you sure you want to leave? This will permanently abandon the session for both participants.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex space-x-2 justify-end">
            <Button variant="outline" onClick={() => setIsOpen(false)} disabled={isLeaving}>Cancel</Button>
            <Button variant="destructive" onClick={handleLeave} disabled={isLeaving}>
              {isLeaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Confirm Leave
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
