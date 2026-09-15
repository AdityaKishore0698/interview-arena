import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata = { title: 'Terms of Service' };

export default function TermsPage() {
  return (
    <div className="relative min-h-screen text-foreground">
      <div className="mx-auto max-w-2xl px-6 py-16 md:py-24">
        <Link href="/" className="mb-10 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to Interview Arena
        </Link>

        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Terms of Service</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated: {new Date().getFullYear()}</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-foreground/90">
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">1. What Interview Arena is</h2>
            <p>
              Interview Arena is a peer-to-peer mock interview practice tool. It matches two
              participants, structures a two-round interview with automatic role reversal, and
              collects the feedback each participant gives the other. It is a practice and
              portfolio project, not a professional or certified interview coaching service.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">2. Accounts</h2>
            <p>
              You can use Interview Arena as a registered user (email/password or Google) or as a
              temporary guest. You are responsible for the accuracy of the information you provide
              and for keeping your credentials confidential. Guest sessions are ephemeral and are
              not linked to a persistent account.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">3. Conduct during sessions</h2>
            <p>
              Sessions connect you directly with another person over audio/video and text chat.
              Be respectful. Do not use the platform to harass, impersonate, or share unlawful
              content. We may suspend or delete accounts that abuse the platform.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">4. No warranty</h2>
            <p>
              The service is provided &ldquo;as is&rdquo;, without warranties of any kind. Interview
              feedback is provided by other participants, not by Interview Arena, and reflects
              their personal opinion — it is not a professional assessment.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">5. Changes</h2>
            <p>
              This is an evolving student/portfolio project. These terms may change as the product
              changes; continued use after a change means you accept the updated terms.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-foreground">6. Contact</h2>
            <p>
              Questions about these terms can be raised via the project&rsquo;s{' '}
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
