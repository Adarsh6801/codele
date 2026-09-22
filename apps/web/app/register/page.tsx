'use client';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { AuthLayout } from '../components/auth-layout';
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type Availability = 'idle' | 'checking' | 'available' | 'taken' | 'invalid' | 'error';
export default function Register() {
  const r = useRouter();
  const [v, setV] = useState({ email: '', display_name: '', password: '' });
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({ display_name: '', email: '', password: '' });
  const [availability, setAvailability] = useState<Availability>('idle');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const displayName = v.display_name.trim();
    if (!displayName) {
      setAvailability('idle');
      return;
    }
    if (!/^[A-Za-z0-9_-]{3,80}$/.test(displayName)) {
      setAvailability('invalid');
      return;
    }
    const controller = new AbortController();
    setAvailability('checking');
    const timeout = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `${api}/auth/display-name-availability?display_name=${encodeURIComponent(displayName)}`,
          { signal: controller.signal },
        );
        if (!response.ok) throw new Error('availability check failed');
        const body = (await response.json()) as { available: boolean };
        setAvailability(body.available ? 'available' : 'taken');
      } catch (requestError) {
        if ((requestError as Error).name !== 'AbortError') setAvailability('error');
      }
    }, 450);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [v.display_name]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const nextErrors = {
      display_name: /^[A-Za-z0-9_-]{3,80}$/.test(v.display_name.trim())
        ? availability === 'taken'
          ? 'This display name is already taken.'
          : availability === 'checking'
            ? 'Checking display name availability…'
            : ''
        : 'Use 3–80 letters, numbers, _ or -.',
      email: /^\S+@\S+\.\S+$/.test(v.email.trim()) ? '' : 'Enter a valid email address.',
      password: v.password.length >= 12 ? '' : 'Password must contain at least 12 characters.',
    };
    setFieldErrors(nextErrors);
    if (nextErrors.display_name || nextErrors.email || nextErrors.password) {
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await fetch(`${api}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...v, display_name: v.display_name.trim() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(typeof body.detail === 'string' ? body.detail : 'Unable to create your account.');
        return;
      }
      const loginResponse = await fetch(`${api}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: v.email, password: v.password }),
      });
      const loginBody = await loginResponse.json().catch(() => ({}));
      if (!loginResponse.ok || typeof loginBody.access_token !== 'string') {
        setError('Your account was created, but automatic sign-in failed. Please sign in once.');
        return;
      }
      localStorage.setItem('codele_token', loginBody.access_token);
      r.push('/dashboard');
    } catch {
      setError('Cannot reach the API. Start the backend at http://localhost:8000 and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <AuthLayout
      eyebrow="START YOUR STREAK"
      title="A better coding habit begins today."
      description="Create your free account and get a focused daily challenge tailored to your growth."
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <label>
          Display name
          <input
            placeholder="e.g. adarsh_codes"
            value={v.display_name}
            onChange={(e) => {
              setV({ ...v, display_name: e.target.value });
              setFieldErrors({ ...fieldErrors, display_name: '' });
            }}
            aria-invalid={Boolean(fieldErrors.display_name)}
            required
          />
          <span className={`availability ${availability}`}>
            {availability === 'idle' && 'Use 3–80 letters, numbers, _ or -'}
            {availability === 'checking' && 'Checking availability…'}
            {availability === 'available' && '✓ Display name is available'}
            {availability === 'taken' && 'This display name is already taken'}
            {availability === 'invalid' && 'Use 3–80 letters, numbers, _ or -'}
            {availability === 'error' && 'Could not check availability. Is the API running?'}
          </span>
          {fieldErrors.display_name && (
            <span className="field-error">{fieldErrors.display_name}</span>
          )}
        </label>
        <label>
          Email address
          <input
            type="email"
            placeholder="you@example.com"
            value={v.email}
            onChange={(e) => {
              setV({ ...v, email: e.target.value });
              setFieldErrors({ ...fieldErrors, email: '' });
            }}
            aria-invalid={Boolean(fieldErrors.email)}
            required
          />
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </label>
        <label>
          Password
          <input
            type="password"
            placeholder="At least 12 characters"
            value={v.password}
            onChange={(e) => {
              setV({ ...v, password: e.target.value });
              setFieldErrors({ ...fieldErrors, password: '' });
            }}
            aria-invalid={Boolean(fieldErrors.password)}
            minLength={12}
            required
          />
          {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
        </label>
        <button
          className="button"
          disabled={isSubmitting || ['checking', 'taken', 'invalid'].includes(availability)}
        >
          {isSubmitting ? (
            'Creating account…'
          ) : (
            <>
              Create my account <span>→</span>
            </>
          )}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
      <p className="auth-switch">
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
