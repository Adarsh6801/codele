'use client';
import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { AuthLayout } from '../components/auth-layout';
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
export default function Reset() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setEmailError('Enter a valid email address.');
      return;
    }
    setEmailError('');
    setIsSubmitting(true);
    try {
      const response = await fetch(`${api}/auth/password-reset/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(
          typeof body.detail === 'string' ? body.detail : 'Unable to request a password reset.',
        );
        return;
      }
      setMessage(body.message ?? 'Your password reset request has been accepted.');
      setSent(true);
    } catch {
      setError('Cannot reach the API. Start the backend at http://localhost:8000 and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <AuthLayout
      eyebrow="ACCOUNT RECOVERY"
      title="Reset your password."
      description="Enter the email linked to your account and we’ll guide you through the next step."
    >
      {sent ? (
        <div className="reset-confirmation">
          <span>✓</span>
          <h2>Reset request received</h2>
          <p>
            {message} Email delivery needs to be configured before reset links can leave this local
            installation.
          </p>
          <Link className="button" href="/login">
            Back to sign in
          </Link>
        </div>
      ) : (
        <form className="auth-form" onSubmit={submit} noValidate>
          <label>
            Email address
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setEmailError('');
              }}
              aria-invalid={Boolean(emailError)}
              required
            />
            {emailError && <span className="field-error">{emailError}</span>}
          </label>
          <button className="button" disabled={isSubmitting}>
            {isSubmitting ? (
              'Sending request…'
            ) : (
              <>
                Continue <span>→</span>
              </>
            )}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      )}
      <p className="auth-switch">
        <Link href="/login">← Back to sign in</Link>
      </p>
    </AuthLayout>
  );
}
