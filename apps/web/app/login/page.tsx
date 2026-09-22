'use client';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { AuthLayout } from '../components/auth-layout';
const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
export default function Login() {
  const r = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({ email: '', password: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const nextErrors = {
      email: /^\S+@\S+\.\S+$/.test(email.trim()) ? '' : 'Enter a valid email address.',
      password: password ? '' : 'Enter your password.',
    };
    setFieldErrors(nextErrors);
    if (nextErrors.email || nextErrors.password) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`${api}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(
          typeof body.detail === 'string'
            ? body.detail
            : 'Unable to sign in. Check your email and password.',
        );
        return;
      }
      localStorage.setItem('codele_token', body.access_token);
      r.push('/dashboard');
    } catch {
      setError('Cannot reach the API. Start the backend at http://localhost:8000 and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <AuthLayout
      eyebrow="WELCOME BACK"
      title="Sign in to keep your streak alive."
      description="Your next challenge — and your progress — are waiting for you."
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <label>
          Email address
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setFieldErrors({ ...fieldErrors, email: '' });
            }}
            aria-invalid={Boolean(fieldErrors.email)}
            required
          />
          {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
        </label>
        <label>
          Password <Link href="/reset">Forgot password?</Link>
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setFieldErrors({ ...fieldErrors, password: '' });
            }}
            aria-invalid={Boolean(fieldErrors.password)}
            required
          />
          {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
        </label>
        <button className="button" disabled={isSubmitting}>
          {isSubmitting ? (
            'Signing in…'
          ) : (
            <>
              Sign in <span>→</span>
            </>
          )}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
      <p className="auth-switch">
        New to Codele? <Link href="/register">Create a free account</Link>
      </p>
    </AuthLayout>
  );
}
