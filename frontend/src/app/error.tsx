'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { buttonVariants } from '@/components/ui/button';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Unhandled application error:', error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-7 w-7 text-destructive" />
      </div>
      <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Something went wrong</h1>
      <p className="mt-3 max-w-sm text-muted-foreground">
        An unexpected error interrupted this page. You can try again, or head back to the dashboard.
      </p>
      <div className="mt-8 flex items-center gap-3">
        <Button size="lg" variant="outline" onClick={() => reset()}>
          Try again
        </Button>
        <Link href="/dashboard" className={buttonVariants({ size: 'lg' })}>
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
