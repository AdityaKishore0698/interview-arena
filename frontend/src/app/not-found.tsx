import Link from 'next/link';
import { Compass } from 'lucide-react';
import { buttonVariants } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Compass className="h-7 w-7 text-primary" />
      </div>
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Nothing here</h1>
      <p className="mt-3 max-w-sm text-muted-foreground">
        The page you&rsquo;re looking for doesn&rsquo;t exist, or the interview session has already ended.
      </p>
      <Link href="/" className={buttonVariants({ size: 'lg', className: 'mt-8' })}>
        Return home
      </Link>
    </div>
  );
}
