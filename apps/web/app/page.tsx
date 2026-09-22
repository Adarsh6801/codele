import Link from 'next/link';
import Image from 'next/image';

export default function Home() {
  return (
    <main className="landing">
      <div className="code-orbit orbit-one">{'{ }'}</div>
      <div className="code-orbit orbit-two">&lt;/&gt;</div>
      <div className="code-orbit orbit-three">01</div>
      <nav className="landing-nav">
        <Link className="wordmark" href="/">
          <Image src="/codele-logo.png" alt="Codele" width={38} height={38} priority /> codele
        </Link>
        <div>
          <Link href="/login">Sign in</Link>
          <Link className="button small-button" href="/register">
            Start free
          </Link>
        </div>
      </nav>
      <section className="hero">
        <div className="hero-copy">
          <p className="pill">
            <i /> A better way to practise
          </p>
          <h1>
            Build your coding <em>streak.</em> One challenge at a time.
          </h1>
          <p className="hero-text">
            Codele turns focused daily problems into a practice habit you can actually keep — with
            instant feedback and progress that feels real.
          </p>
          <div className="hero-actions">
            <Link className="button" href="/register">
              Start your streak <span>→</span>
            </Link>
            <Link className="text-link" href="/login">
              I already have an account
            </Link>
          </div>
          <div className="trust">
            <span>✦ No credit card</span>
            <span>✦ Built for consistency</span>
            <span>✦ All skill levels</span>
          </div>
        </div>
        <div className="hero-visual" aria-label="Example coding challenge">
          <div className="visual-top">
            <span className="traffic">
              <i />
              <i />
              <i />
            </span>
            <span>daily_challenge.py</span>
            <span>•••</span>
          </div>
          <div className="code-lines">
            <p>
              <b>01</b> <i>def</i> <strong>two_sum</strong>(nums, target):
            </p>
            <p>
              <b>02</b> &nbsp;&nbsp;seen = {'{}'}
            </p>
            <p>
              <b>03</b> &nbsp;&nbsp;<i>for</i> index, value <i>in</i> enumerate(nums):
            </p>
            <p>
              <b>04</b> &nbsp;&nbsp;&nbsp;&nbsp;need = target - value
            </p>
            <p>
              <b>05</b> &nbsp;&nbsp;&nbsp;&nbsp;<i>if</i> need <i>in</i> seen:
            </p>
            <p>
              <b>06</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>return</i> [seen[need], index]
            </p>
            <p>
              <b>07</b> &nbsp;&nbsp;&nbsp;&nbsp;seen[value] = index
            </p>
          </div>
          <div className="passed">
            <span>✓</span>
            <div>
              <b>All sample tests passed</b>
              <small>+ 20 XP earned</small>
            </div>
            <strong>01:24</strong>
          </div>
        </div>
      </section>
      <section className="landing-stats">
        <div>
          <b>5 min</b>
          <span>daily focus</span>
        </div>
        <div>
          <b>3 levels</b>
          <span>grow at your pace</span>
        </div>
        <div>
          <b>∞ streaks</b>
          <span>keep showing up</span>
        </div>
      </section>
      <footer className="landing-footer">
        <Link className="wordmark" href="/">
          <Image src="/codele-logo.png" alt="Codele" width={28} height={28} /> codele
        </Link>
        <p>© 2026 Codele. Build your coding habit.</p>
        <div>
          <Link href="/login">Sign in</Link>
          <Link href="/register">Get started</Link>
        </div>
      </footer>
    </main>
  );
}
