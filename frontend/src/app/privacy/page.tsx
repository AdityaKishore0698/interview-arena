import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata = { title: 'Privacy Policy' };

export default function PrivacyPage() {
  return (
    <div className="relative min-h-screen text-foreground">
      <div className="mx-auto max-w-2xl px-6 py-16 md:py-24">
        <Link href="/" className="mb-10 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to Interview Arena
        </Link>

        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Privacy Policy</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated: {new Date().getFullYear()}</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-foreground/90">
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">What we store</h2>
            <ul className="list-disc space-y-1.5 pl-5">
              <li><strong className="text-foreground">Registered accounts:</strong> your email, display name, and a bcrypt-hashed password (or your Google profile email/name if you sign in with Google — we never see your Google password).</li>
              <li><strong className="text-foreground">Guest accounts:</strong> a temporary identifier held only in server memory (Redis) that automatically expires within 24 hours. No email or password is collected for guest sessions.</li>
              <li><strong className="text-foreground">Interview sessions:</strong> which room/mode you practiced, session timestamps, and the structured feedback (numeric ratings and comments) participants submit about each other.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">What we don&rsquo;t store</h2>
            <ul className="list-disc space-y-1.5 pl-5">
              <li><strong className="text-foreground">No audio/video recording.</strong> Video and audio between participants travel peer-to-peer over WebRTC; our server only relays connection setup messages and never receives or stores the media stream.</li>
              <li><strong className="text-foreground">No chat history.</strong> Session chat messages are relayed live and are not written to a database.</li>
              <li>We don&rsquo;t use tracking cookies or third-party analytics. Your session token is kept in your browser&rsquo;s local storage, not a cookie, and is only ever sent to our own API.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">How it&rsquo;s used</h2>
            <p>
              Your data is used only to operate the platform: authenticating you, matching you with
              a peer, running the interview state machine, and showing you the feedback you
              received. We do not sell or share your data with third parties.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">Your controls</h2>
            <p>
              From your account settings you can change your display name and password at any
              time, or permanently delete your account. Deleting your account disables sign-in and
              removes your personal identifiers; interview records you participated in are
              anonymized rather than deleted outright, so the peers you interviewed with keep an
              accurate history of their own sessions.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">Contact</h2>
            <p>
              This is a student/portfolio project. Questions can be raised via the project&rsquo;s{' '}
              <a
                href="https://github.com/AdityaKishore0698/interview-arena"
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                GitHub repository
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
