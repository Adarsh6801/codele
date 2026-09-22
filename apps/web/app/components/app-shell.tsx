'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import { NotificationCenter } from './notification-center';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type Profile = { display_name: string; email: string; profile_image_url: string | null };
type Progress = { current_streak: number };
const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/challenge', label: 'Problems' },
  { href: '/community', label: 'Community' },
  { href: '/submissions', label: 'Submissions' },
  { href: '/leaderboard', label: 'Leaderboard' },
  { href: '/settings', label: 'Profile' },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [streak, setStreak] = useState<number | null>(null);
  useEffect(() => {
    const loadProfile = () => {
      const token = localStorage.getItem('codele_token');
      if (!token) {
        router.replace('/login');
        return;
      }
      fetch(`${api}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(async (response) => (response.ok ? response.json() : Promise.reject()))
        .then(setProfile)
        .catch(() => {
          localStorage.removeItem('codele_token');
          router.replace('/login');
        });
    };
    const loadProgress = () => {
      const token = localStorage.getItem('codele_token');
      if (!token) return;
      fetch(`${api}/progress`, { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => (response.ok ? response.json() : Promise.reject()))
        .then((data: Progress) => setStreak(data.current_streak))
        .catch(() => undefined);
    };
    loadProfile();
    loadProgress();
    window.addEventListener('codele-profile-updated', loadProfile);
    window.addEventListener('codele-progress-updated', loadProgress);
    return () => {
      window.removeEventListener('codele-profile-updated', loadProfile);
      window.removeEventListener('codele-progress-updated', loadProgress);
    };
  }, [router]);
  const signOut = () => {
    localStorage.removeItem('codele_token');
    router.push('/');
  };
  return (
    <div className="app-page">
      <header className="app-nav">
        <Link className="wordmark" href="/dashboard">
          <Image src="/codele-logo.png" alt="Codele" width={34} height={34} /> codele
        </Link>
        <nav aria-label="Main navigation">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? 'selected' : ''}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/dashboard"
          className="nav-streak"
          aria-label={`${streak ?? 0} day current streak. Open dashboard.`}
        >
          <span aria-hidden="true">🔥</span>
          <b>{streak ?? '—'}</b>
          <small>day streak</small>
        </Link>
        <NotificationCenter />
        <div className="nav-profile">
          <Link href="/settings" className="avatar" aria-label="Open profile">
            {profile?.profile_image_url ? (
              <img src={`${api.replace('/api/v1', '')}${profile.profile_image_url}`} alt="" />
            ) : (
              (profile?.display_name?.slice(0, 1).toUpperCase() ?? '…')
            )}
          </Link>
          <div className="profile-copy">
            <b>{profile?.display_name ?? 'Loading'}</b>
            <span>{profile?.email ?? 'Your profile'}</span>
          </div>
          <button className="logout" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}
