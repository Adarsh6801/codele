import Image from 'next/image';
import Link from 'next/link';
import { ReactNode } from 'react';

export function AuthLayout({
  children,
  eyebrow,
  title,
  description,
}: {
  children: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <main className="auth-page">
      <section className="auth-form-side">
        <Link className="wordmark auth-wordmark" href="/">
          <Image src="/codele-logo.png" alt="Codele" width={34} height={34} /> codele
        </Link>
        <div className="auth-content">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="auth-description">{description}</p>
          {children}
        </div>
        <p className="auth-copyright">© 2026 Codele</p>
      </section>
      <aside className="auth-code-side">
        <div className="auth-glow" />
        <div className="auth-code-card">
          <div className="auth-code-header">
            <span>
              <i />
              <i />
              <i />
            </span>
            <b>keep_building.ts</b>
          </div>
          <div className="auth-code">
            <p>
              <small>01</small>
              <span>const</span> streak = <em>new</em> Habit();
            </p>
            <p>
              <small>02</small>
            </p>
            <p>
              <small>03</small>streak.<b>showUp</b>(<strong>&apos;today&apos;</strong>);
            </p>
            <p>
              <small>04</small>streak.<b>solve</b>(challenge);
            </p>
            <p>
              <small>05</small>
            </p>
            <p>
              <small>06</small>
              <em>if</em> (streak.<b>isGrowing</b>()) {'{'}
            </p>
            <p>
              <small>07</small>&nbsp;&nbsp;console.<b>log</b>(
              <strong>&apos;Nice work!&apos;</strong>);
            </p>
            <p>
              <small>08</small>
              {'}'}
            </p>
          </div>
          <div className="auth-code-result">
            <span>✓</span>
            <div>
              <b>Practice session complete</b>
              <small>Streak protected · +20 XP</small>
            </div>
          </div>
        </div>
        <div className="auth-quote">
          <span>“</span>
          <p>Consistency beats intensity. Just solve today&apos;s problem.</p>
        </div>
      </aside>
    </main>
  );
}
