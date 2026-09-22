'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

type Notice = {
  id: string;
  type: 'submission' | 'achievement' | 'social' | 'account';
  title: string;
  body: string;
  link: string | null;
  created_at: string;
  read_at: string | null;
};

export function NotificationCenter() {
  const centerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notice[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState('');

  const headers = (): Record<string, string> => {
    const token = localStorage.getItem('codele_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };
  const load = async () => {
    if (!localStorage.getItem('codele_token')) return;
    const response = await fetch(`${api}/notifications`, { headers: headers() });
    if (!response.ok) throw new Error('Could not load notifications.');
    const data = await response.json();
    setItems(data.items ?? []);
    setUnread(data.unread_count ?? 0);
    setError('');
  };
  useEffect(() => {
    void load().catch((reason) => setError(reason.message));
    const interval = window.setInterval(() => void load().catch(() => undefined), 45000);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const closeOnOutsidePress = (event: PointerEvent) => {
      if (centerRef.current && !centerRef.current.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    window.addEventListener('pointerdown', closeOnOutsidePress);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('keydown', closeOnEscape);
      window.removeEventListener('pointerdown', closeOnOutsidePress);
    };
  }, []);
  const markRead = async (id: string) => {
    const current = items.find((item) => item.id === id);
    if (!current || current.read_at) return;
    setItems((previous) =>
      previous.map((item) => (item.id === id ? { ...item, read_at: 'now' } : item)),
    );
    setUnread((count) => Math.max(0, count - 1));
    try {
      await fetch(`${api}/notifications/${id}/read`, { method: 'PATCH', headers: headers() });
    } catch {
      void load().catch(() => undefined);
    }
  };
  const markAllRead = async () => {
    try {
      const response = await fetch(`${api}/notifications/read-all`, {
        method: 'POST',
        headers: headers(),
      });
      if (!response.ok) throw new Error();
      setItems((previous) => previous.map((item) => ({ ...item, read_at: item.read_at ?? 'now' })));
      setUnread(0);
    } catch {
      setError('Could not mark notifications as read.');
    }
  };

  return (
    <div className="notification-center" ref={centerRef}>
      <button
        className={`notification-trigger${unread ? ' has-unread' : ''}`}
        onClick={() => {
          setOpen((visible) => !visible);
          void load().catch(() => undefined);
        }}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
        aria-expanded={open}
        aria-controls="notification-panel"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
        </svg>
        {unread > 0 && <b>{unread > 9 ? '9+' : unread}</b>}
      </button>
      {open && (
        <section className="notification-panel" id="notification-panel" aria-label="Notifications">
          <header>
            <div>
              <p className="eyebrow">ACTIVITY</p>
              <h2>Notifications</h2>
            </div>
            <button className="quiet" onClick={() => void markAllRead()} disabled={!unread}>
              Mark all read
            </button>
          </header>
          {error && (
            <p className="notification-error" role="alert">
              {error}
            </p>
          )}
          {!error && items.length === 0 && (
            <p className="notification-empty">
              You’re all caught up. New activity will appear here.
            </p>
          )}
          <div className="notification-list">
            {items.map((item) => (
              <Link
                href={item.link ?? '/dashboard'}
                className={item.read_at ? 'notification-item' : 'notification-item unread'}
                key={item.id}
                onClick={() => {
                  void markRead(item.id);
                  setOpen(false);
                }}
              >
                <span className={`notification-icon ${item.type}`} aria-hidden="true">
                  {item.type === 'achievement' ? '✦' : item.type === 'social' ? '◌' : '⌁'}
                </span>
                <span>
                  <b>{item.title}</b>
                  <small>{item.body}</small>
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString()}
                  </time>
                </span>
              </Link>
            ))}
          </div>
          <Link
            className="notification-preferences-link"
            href="/settings"
            onClick={() => setOpen(false)}
          >
            Notification preferences →
          </Link>
        </section>
      )}
    </div>
  );
}
