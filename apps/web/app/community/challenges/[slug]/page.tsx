'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AppShell } from '../../../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type Task = {
  id: string;
  position: number;
  day_offset: number;
  kind: string;
  title: string;
  instructions_markdown: string | null;
  video_url: string | null;
  resource_url: string | null;
  available: boolean;
  completed_at: string | null;
  is_required: boolean;
};
type Challenge = {
  id: string;
  title: string;
  summary: string;
  description_markdown: string | null;
  duration_days: number;
  task_count: number;
  enrollment_id: string | null;
  enrollment_status: string | null;
  deadline_at: string | null;
  tasks: Task[];
};

export default function ChallengeProgrammePage() {
  const params = useParams<{ slug: string }>();
  const [challenge, setChallenge] = useState<Challenge>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('codele_token') ?? ''}` });
  const load = async () => {
    try {
      const response = await fetch(`${api}/community/challenges/${params.slug}`, {
        headers: auth(),
      });
      if (!response.ok) throw new Error('Challenge not found.');
      setChallenge(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load challenge.');
    }
  };
  useEffect(() => {
    void load();
  }, [params.slug]);
  const action = async (url: string, label: string) => {
    setBusy(label);
    setError('');
    try {
      const response = await fetch(`${api}${url}`, { method: 'POST', headers: auth() });
      if (!response.ok)
        throw new Error((await response.json()).detail ?? 'Could not update challenge.');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update challenge.');
    } finally {
      setBusy('');
    }
  };
  if (!challenge)
    return (
      <AppShell>
        <main className="community-page">
          <p className="page-state">{error || 'Loading challenge…'}</p>
        </main>
      </AppShell>
    );
  return (
    <AppShell>
      <main className="community-page">
        <Link href="/community" className="back-link">
          ← Community
        </Link>
        <section className="community-hero">
          <div>
            <span>CHALLENGE PROGRAMME</span>
            <h1>{challenge.title}</h1>
            <p>{challenge.summary}</p>
            <p className="programme-meta">
              {challenge.duration_days} day plan · {challenge.task_count} tasks{' '}
              {challenge.deadline_at &&
                `· Complete by ${new Date(challenge.deadline_at).toLocaleDateString()}`}
            </p>
            {!challenge.enrollment_id ? (
              <button
                className="hero-action"
                disabled={!!busy}
                onClick={() => action(`/community/challenges/${challenge.id}/join`, 'join')}
              >
                {' '}
                {busy === 'join' ? 'Joining…' : 'Join challenge'}{' '}
              </button>
            ) : challenge.enrollment_status === 'active' ? (
              <button
                className="hero-action secondary"
                disabled={!!busy}
                onClick={() =>
                  action(`/community/enrollments/${challenge.enrollment_id}/forgo`, 'forgo')
                }
              >
                {busy === 'forgo' ? 'Updating…' : 'Forgo challenge'}
              </button>
            ) : (
              <b>
                {challenge.enrollment_status === 'completed'
                  ? 'Challenge completed'
                  : 'Challenge ended'}
              </b>
            )}
          </div>
        </section>
        {error && <p className="page-error">{error}</p>}
        <section className="programme-tasks">
          <h2>Your schedule</h2>
          {challenge.tasks.map((task) => (
            <article
              className={`programme-task ${task.available ? 'available' : ''}`}
              key={task.id}
            >
              <div className="task-day">DAY {task.day_offset}</div>
              <div>
                <span>
                  {task.kind} {task.is_required ? '· REQUIRED' : '· OPTIONAL'}
                </span>
                <h3>{task.title}</h3>
                {task.available ? (
                  <>
                    <p>{task.instructions_markdown}</p>
                    {task.video_url && (
                      <a href={task.video_url} target="_blank">
                        Watch lesson ↗
                      </a>
                    )}
                    {task.resource_url && (
                      <a href={task.resource_url} target="_blank">
                        Open resource ↗
                      </a>
                    )}
                  </>
                ) : (
                  <p>Unlocks on day {task.day_offset} after you join.</p>
                )}
              </div>
              {task.available && !task.completed_at && challenge.enrollment_id && (
                <button
                  disabled={!!busy}
                  onClick={() =>
                    action(
                      `/community/enrollments/${challenge.enrollment_id}/tasks/${task.id}/complete`,
                      task.id,
                    )
                  }
                >
                  Mark complete
                </button>
              )}
              {task.completed_at && <b className="task-done">Completed ✓</b>}
            </article>
          ))}
        </section>
      </main>
    </AppShell>
  );
}
