'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const origin = api.replace('/api/v1', '');
type Entry = {
  rank: number;
  user_id: string;
  display_name: string;
  profile_image_url: string | null;
  score: number;
  current_streak: number;
  is_current_user: boolean;
};
type Leaderboard = {
  scope: 'global' | 'friends';
  period: 'all' | 'weekly';
  page: number;
  page_size: number;
  total: number;
  entries: Entry[];
};
type Friend = {
  id: string;
  user_id: string;
  display_name: string;
  profile_image_url: string | null;
  leaderboard_visible: boolean;
  accepted_at: string | null;
};
type Request = Friend & { direction: 'incoming' | 'outgoing'; created_at: string };

const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('codele_token')}` });
async function errorMessage(response: Response) {
  const body = await response.json().catch(() => ({}));
  return typeof body.detail === 'string' ? body.detail : 'Something went wrong.';
}

export default function LeaderboardPage() {
  const [scope, setScope] = useState<'global' | 'friends'>('global');
  const [period, setPeriod] = useState<'all' | 'weekly'>('weekly');
  const [page, setPage] = useState(1);
  const [board, setBoard] = useState<Leaderboard | null>(null);
  const [friends, setFriends] = useState<Friend[]>([]);
  const [requests, setRequests] = useState<Request[]>([]);
  const [name, setName] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    const [leaderboardResponse, friendsResponse, requestsResponse] = await Promise.all([
      fetch(`${api}/leaderboards/${scope}?period=${period}&page=${page}&page_size=25`, {
        headers: headers(),
      }),
      fetch(`${api}/social/friends`, { headers: headers() }),
      fetch(`${api}/social/requests?direction=incoming`, { headers: headers() }),
    ]);
    if (!leaderboardResponse.ok) throw new Error(await errorMessage(leaderboardResponse));
    setBoard((await leaderboardResponse.json()) as Leaderboard);
    if (friendsResponse.ok) setFriends((await friendsResponse.json()) as Friend[]);
    if (requestsResponse.ok) setRequests((await requestsResponse.json()) as Request[]);
  };
  useEffect(() => {
    void load().catch((reason) => setError(reason.message));
  }, [scope, period, page]);
  const sendRequest = async () => {
    if (!name.trim()) return;
    setError('');
    setNotice('');
    const response = await fetch(`${api}/social/requests`, {
      method: 'POST',
      headers: { ...headers(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: name.trim() }),
    });
    if (!response.ok) return setError(await errorMessage(response));
    setName('');
    setNotice('Friend request sent.');
  };
  const accept = async (id: string) => {
    const response = await fetch(`${api}/social/requests/${id}/accept`, {
      method: 'POST',
      headers: headers(),
    });
    if (!response.ok) return setError(await errorMessage(response));
    setNotice('You are now connected.');
    await load();
  };
  const remove = async (id: string) => {
    const response = await fetch(`${api}/social/friends/${id}`, {
      method: 'DELETE',
      headers: headers(),
    });
    if (!response.ok) return setError(await errorMessage(response));
    setNotice('Connection removed.');
    await load();
  };
  return (
    <AppShell>
      <main className="leaderboard-page">
        <section className="leaderboard-hero">
          <div>
            <p className="eyebrow">COMMUNITY</p>
            <h1>Make progress visible.</h1>
            <p>
              Rankings are calculated from verified XP rewards. Ties are resolved consistently by
              streak, name, then account ID.
            </p>
          </div>
          <div className="leaderboard-tabs">
            <button
              className={scope === 'global' ? 'active' : ''}
              onClick={() => {
                setScope('global');
                setPage(1);
              }}
            >
              Global
            </button>
            <button
              className={scope === 'friends' ? 'active' : ''}
              onClick={() => {
                setScope('friends');
                setPage(1);
              }}
            >
              Friends
            </button>
          </div>
        </section>
        <section className="leaderboard-layout">
          <article className="leaderboard-card">
            <div className="leaderboard-card-head">
              <div>
                <h2>{scope === 'global' ? 'Global rankings' : 'Friends rankings'}</h2>
                <p>
                  {board?.total ?? 0} visible learner{board?.total === 1 ? '' : 's'}
                </p>
              </div>
              <div className="period-switch">
                <button
                  className={period === 'weekly' ? 'active' : ''}
                  onClick={() => {
                    setPeriod('weekly');
                    setPage(1);
                  }}
                >
                  This week
                </button>
                <button
                  className={period === 'all' ? 'active' : ''}
                  onClick={() => {
                    setPeriod('all');
                    setPage(1);
                  }}
                >
                  All time
                </button>
              </div>
            </div>
            <div className="rank-list">
              {board?.entries.length ? (
                board.entries.map((entry) => (
                  <article key={entry.user_id} className={entry.is_current_user ? 'you' : ''}>
                    <b className="rank-number">#{entry.rank}</b>
                    <span className="rank-avatar">
                      {entry.profile_image_url ? (
                        <img src={`${origin}${entry.profile_image_url}`} alt="" />
                      ) : (
                        entry.display_name.slice(0, 1).toUpperCase()
                      )}
                    </span>
                    <div>
                      <strong>
                        {entry.display_name}
                        {entry.is_current_user ? ' (You)' : ''}
                      </strong>
                      <small>♨ {entry.current_streak} day streak</small>
                    </div>
                    <b className="rank-score">⚡ {entry.score.toLocaleString()}</b>
                  </article>
                ))
              ) : (
                <p className="empty-rank">
                  {scope === 'friends'
                    ? 'Add and accept friends to compare progress here.'
                    : 'No public ranking activity yet.'}
                </p>
              )}
            </div>
            {(board?.total ?? 0) > (board?.page_size ?? 25) && (
              <div className="leaderboard-pagination">
                <button disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                  ← Previous
                </button>
                <span>
                  Page {page} of {Math.ceil((board?.total ?? 0) / (board?.page_size ?? 25))}
                </span>
                <button
                  disabled={page * (board?.page_size ?? 25) >= (board?.total ?? 0)}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </article>
          <aside className="social-card">
            <div>
              <p className="eyebrow">FRIENDS</p>
              <h2>Practice together</h2>
            </div>
            <div className="friend-form">
              <input
                aria-label="Friend display name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Display name"
              />
              <button className="button" onClick={() => void sendRequest()}>
                Add
              </button>
            </div>
            {requests.length > 0 && (
              <section className="request-list">
                <h3>Requests</h3>
                {requests.map((request) => (
                  <article key={request.id}>
                    <span>{request.display_name.slice(0, 1).toUpperCase()}</span>
                    <b>{request.display_name}</b>
                    <button onClick={() => void accept(request.id)}>Accept</button>
                    <button className="quiet" onClick={() => void remove(request.id)}>
                      ×
                    </button>
                  </article>
                ))}
              </section>
            )}
            <section className="friend-list">
              <h3>Your friends</h3>
              {friends.length ? (
                friends.map((friend) => (
                  <article key={friend.id}>
                    <span>
                      {friend.profile_image_url ? (
                        <img src={`${origin}${friend.profile_image_url}`} alt="" />
                      ) : (
                        friend.display_name.slice(0, 1).toUpperCase()
                      )}
                    </span>
                    <div>
                      <b>{friend.display_name}</b>
                      <small>
                        {friend.leaderboard_visible ? 'Visible in rankings' : 'Private rankings'}
                      </small>
                    </div>
                    <button className="quiet" onClick={() => void remove(friend.id)}>
                      Remove
                    </button>
                  </article>
                ))
              ) : (
                <p>Search by an exact display name to send a request.</p>
              )}
            </section>
          </aside>
        </section>
        {notice && <p className="profile-notice">✓ {notice}</p>}
        {error && <p className="profile-error">{error}</p>}
      </main>
    </AppShell>
  );
}
