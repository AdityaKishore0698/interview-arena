'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/useAuth';
import AppLayout from '@/components/layout/AppLayout';
import { Avatar } from '@/components/layout/Avatar';
import { AvatarCropDialog } from '@/components/account/AvatarCropDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { api } from '@/lib/api';
import { AxiosError } from 'axios';
import { CheckCircle2, Loader2, ShieldAlert, Upload, X } from 'lucide-react';

/** Just reads the raw file into a data URL for the crop dialog to display —
 * cropping (and the resize down to a small square) happens interactively in
 * AvatarCropDialog once the user has positioned it themselves. */
function readFileAsDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read the file.'));
    reader.onload = () => resolve(reader.result as string);
    reader.readAsDataURL(file);
  });
}

function FieldError({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="text-sm text-destructive" aria-live="polite">{message}</p>;
}

function FieldSuccess({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="flex items-center gap-1.5 text-sm text-success" aria-live="polite">
      <CheckCircle2 className="h-3.5 w-3.5" /> {message}
    </p>
  );
}

function ProfileSection() {
  const { user, updateUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  // undefined = unchanged (omit from the request); null = remove; string = new (cropped) photo.
  const [avatarDraft, setAvatarDraft] = useState<string | null | undefined>(undefined);
  // The just-selected file, shown in the crop dialog before it becomes avatarDraft.
  const [rawImageSrc, setRawImageSrc] = useState<string | null>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const previewSrc = avatarDraft === undefined ? user?.avatar_url : avatarDraft;

  const handleFileChosen = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    if (!file.type.startsWith('image/')) {
      setError('Please choose an image file.');
      return;
    }
    setAvatarBusy(true);
    try {
      setRawImageSrc(await readFileAsDataUri(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read that file.');
    } finally {
      setAvatarBusy(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const body: { display_name: string; avatar_url?: string } = { display_name: displayName };
      if (avatarDraft !== undefined) body.avatar_url = avatarDraft ?? '';
      const res = await api.patch('/api/v1/auth/me', body);
      updateUser({ display_name: displayName, avatar_url: res.data.avatar_url });
      setAvatarDraft(undefined);
      setSuccess('Profile updated.');
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Failed to update profile' : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-5 rounded-2xl border border-border/60 bg-surface/40 p-6">
      <div>
        <h2 className="text-base font-semibold text-foreground">Profile</h2>
        <p className="text-sm text-muted-foreground">Your name and photo, as your interview partners see them.</p>
      </div>

      <div className="flex items-center gap-4">
        <Avatar name={displayName || 'Guest'} src={previewSrc} size={64} />
        <div className="space-y-1.5">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              handleFileChosen(e.target.files?.[0]);
              e.target.value = ''; // allow re-selecting the same file later
            }}
          />
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={avatarBusy}
            >
              {avatarBusy ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Upload className="mr-2 h-3.5 w-3.5" />}
              {previewSrc ? 'Change photo' : 'Upload photo'}
            </Button>
            {previewSrc && (
              <Button type="button" variant="ghost" size="sm" onClick={() => setAvatarDraft(null)}>
                <X className="mr-1.5 h-3.5 w-3.5" />
                Remove
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground">JPEG or PNG. You can drag and zoom to crop it.</p>
        </div>
      </div>

      <AvatarCropDialog
        imageSrc={rawImageSrc}
        onCancel={() => setRawImageSrc(null)}
        onConfirm={(dataUri) => {
          setAvatarDraft(dataUri);
          setRawImageSrc(null);
        }}
      />

      <div className="max-w-sm space-y-2">
        <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Display name</label>
        <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={100} required />
      </div>
      <FieldError message={error} />
      <FieldSuccess message={success} />
      <Button type="submit" disabled={loading || avatarBusy || !displayName.trim()}>
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Save changes
      </Button>
    </form>
  );
}

function PasswordSection() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/v1/auth/password/change', {
        current_password: currentPassword || null,
        new_password: newPassword,
      });
      setSuccess('Password updated.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Failed to update password' : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-4 rounded-2xl border border-border/60 bg-surface/40 p-6">
      <div>
        <h2 className="text-base font-semibold text-foreground">Password</h2>
        <p className="text-sm text-muted-foreground">
          Leave &ldquo;current password&rdquo; blank if you signed up with Google and have never set one.
        </p>
      </div>
      <div className="grid max-w-sm gap-4">
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Current password</label>
          <Input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">New password</label>
          <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Confirm new password</label>
          <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={8} />
        </div>
      </div>
      <FieldError message={error} />
      <FieldSuccess message={success} />
      <Button type="submit" disabled={loading || !newPassword}>
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Update password
      </Button>
    </form>
  );
}

function DangerZone() {
  const router = useRouter();
  const { logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.delete('/api/v1/auth/me');
      logout();
      router.replace('/');
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail || 'Failed to delete account' : 'Something went wrong');
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 rounded-2xl border border-destructive/30 bg-destructive/5 p-6">
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
        <div>
          <h2 className="text-base font-semibold text-foreground">Delete account</h2>
          <p className="text-sm text-muted-foreground">
            This permanently disables sign-in and removes your personal details. Interviews you
            participated in stay on record (anonymized) so your past partners keep their history.
            This cannot be undone.
          </p>
        </div>
      </div>
      <FieldError message={error} />
      <Button variant="destructive" onClick={() => setIsOpen(true)}>Delete my account</Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              You&rsquo;ll be signed out immediately and won&rsquo;t be able to log back in with this
              email. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setIsOpen(false)} disabled={loading}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirm delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function AccountPage() {
  const { user, hasHydrated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for zustand/persist to read localStorage before trusting a null
    // user — see the comment on `hasHydrated` in store/useAuth.ts. Without
    // this, a hard reload or direct link to this page bounced a real,
    // logged-in visitor to `/dashboard` instead of showing settings.
    if (hasHydrated && !user) router.replace('/');
  }, [user, hasHydrated, router]);

  if (!user) return null;

  return (
    <AppLayout>
      <div className="container relative z-10 mx-auto max-w-2xl px-6 py-12">
        <header className="mb-10 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Account</p>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-4xl">Account Settings</h1>
          <p className="text-muted-foreground">{user.email || 'Guest session'}</p>
        </header>

        {user.type === 'GUEST' ? (
          <div className="space-y-4 rounded-2xl border border-dashed border-border/60 bg-surface/30 p-8 text-center">
            <p className="text-foreground">Guest sessions don&rsquo;t have an account to manage.</p>
            <p className="text-sm text-muted-foreground">
              Create a free account to save your interview history, set a display name, and more.
            </p>
            <Button onClick={() => router.push('/?mode=register')}>Create a free account</Button>
          </div>
        ) : (
          <div className="space-y-6">
            <ProfileSection />
            <PasswordSection />
            <DangerZone />
          </div>
        )}
      </div>
    </AppLayout>
  );
}
