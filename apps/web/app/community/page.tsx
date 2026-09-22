'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { AppShell } from '../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type Author = { display_name: string; profile_image_url: string | null; role: string };
type Discussion = {
  id: string;
  title: string;
  tags: string[];
  reply_count: number;
  created_at: string;
  author: Author;
};
type Challenge = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  duration_days: number;
  task_count: number;
  thumbnail_url: string | null;
  enrollment_status: string | null;
};

export default function CommunityPage() {
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [posting, setPosting] = useState(false);
  const headers = () => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('codele_token') ?? ''}`,
  });
  const load = async () => {
    try {
      const [discussionResponse, challengeResponse] = await Promise.all([
        fetch(`${api}/community/discussions`),
        fetch(`${api}/community/challenges`, { headers: headers() }),
      ]);
      if (!discussionResponse.ok || !challengeResponse.ok)
        throw new Error('Could not load the community.');
      const discussionData = await discussionResponse.json();
      setDiscussions(discussionData.items);
      setChallenges(await challengeResponse.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load the community.');
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const post = async (event: FormEvent) => {
    event.preventDefault();
    setPosting(true);
    setError('');
    try {
      const response = await fetch(`${api}/community/discussions`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ title, body_markdown: body }),
      });
      if (!response.ok)
        throw new Error((await response.json()).detail ?? 'Could not post your question.');
      setTitle('');
      setBody('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not post your question.');
    } finally {
      setPosting(false);
    }
  };
  return (
    <AppShell>
      <main className="community-page">
        <section className="community-hero">
          <div>
            <span>CODELE COMMUNITY · FREE</span>
            <h1>Train together. Get interview-ready.</h1>
            <p>
              Ask a question, receive mentor-guided answers, and finish focused programmes built to
              prepare you for top tech interviews.
            </p>
          </div>
        </section>
        {error && (
          <p className="page-error" role="alert">
            {error}
          </p>
        )}
        <section className="community-grid">
          <div className="community-main">
            <div className="section-heading">
              <div>
                <span>DISCUSSIONS</span>
                <h2>Get unstuck with the community</h2>
              </div>
            </div>
            <form className="community-post" onSubmit={post}>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What are you working through?"
                minLength={5}
                required
              />
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Add your question, code, or interview context…"
                minLength={10}
                required
              />
              <button disabled={posting}>{posting ? 'Posting…' : 'Ask the community'}</button>
            </form>
            <div className="discussion-list">
              {discussions.length ? (
                discussions.map((item) => (
                  <article className="discussion-card" key={item.id}>
                    <div className="discussion-avatar">
                      {item.author.profile_image_url ? (
                        <img src={item.author.profile_image_url} alt="" />
                      ) : (
                        item.author.display_name[0]
                      )}
                    </div>
                    <div>
                      <h3>{item.title}</h3>
                      <p>
                        {item.author.display_name}{' '}
                        {item.author.role === 'mentor' && <b className="mentor-pill">Mentor</b>} ·{' '}
                        {new Date(item.created_at).toLocaleDateString()}
                      </p>
                      <div>
                        {item.tags.map((tag) => (
                          <span className="tag" key={tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <strong>
                      {item.reply_count}
                      <small>replies</small>
                    </strong>
                  </article>
                ))
              ) : (
                <p className="empty-state">Be the first person to start a discussion.</p>
              )}
            </div>
          </div>
          <aside className="community-side">
            <span>PROGRAMMES</span>
            <h2>Your next challenge</h2>
            {challenges.length ? (
              challenges.map((item) => (
                <Link
                  className="programme-card"
                  href={`/community/challenges/${item.slug}`}
                  key={item.id}
                >
                  <small>
                    {item.enrollment_status === 'active'
                      ? 'IN PROGRESS'
                      : `${item.duration_days} DAYS`}
                  </small>
                  <h3>{item.title}</h3>
                  <p>{item.summary}</p>
                  <b>
                    {item.task_count} tasks <i>→</i>
                  </b>
                </Link>
              ))
            ) : (
              <p className="empty-state">New programmes will appear here.</p>
            )}
          </aside>
        </section>
      </main>
    </AppShell>
  );
}
