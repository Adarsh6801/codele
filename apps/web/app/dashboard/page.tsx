'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AppShell } from '../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type CalendarDay = { date: string; is_shielded: boolean };
type Topic = { topic: string; solved_count: number; xp: number };
type Progress = {
  xp: number;
  xp_level: number;
  xp_level_name: string;
  xp_in_level: number;
  xp_for_next_level: number;
  current_streak: number;
  longest_streak: number;
  shield_available: number;
  shield_cap: number;
  streak_calendar: CalendarDay[];
  topic_progress: Topic[];
};
type Challenge = { title: string; topic: string; difficulty: number; level: string };
type Recommendation = {
  assignment_id: string;
  assignment_date: string;
  title: string;
  topic: string;
  difficulty: number;
  reason: string;
};
type Recommendations = {
  weak_topics: { topic: string; mastery_score: number }[];
  recommendations: Recommendation[];
};

export default function Dashboard() {
  const [progress, setProgress] = useState<Progress>();
  const [challenge, setChallenge] = useState<Challenge>();
  const [recommendations, setRecommendations] = useState<Recommendations>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const loadDashboard = async () => {
    const token = localStorage.getItem('codele_token');
    if (!token) return;
    setLoading(true);
    setError('');
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [progressResponse, challengeResponse, recommendationResponse] = await Promise.all([
        fetch(`${api}/progress`, { headers }),
        fetch(`${api}/daily-assignment`, { headers }),
        fetch(`${api}/recommendations`, { headers }),
      ]);
      if (
        !progressResponse.ok ||
        !recommendationResponse.ok ||
        (!challengeResponse.ok && challengeResponse.status !== 404)
      ) {
        throw new Error('Could not load your dashboard. Please try again.');
      }
      setProgress(await progressResponse.json());
      setChallenge(challengeResponse.ok ? await challengeResponse.json() : undefined);
      setRecommendations(await recommendationResponse.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load your dashboard.');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void loadDashboard();
  }, []);
  const xp = progress?.xp ?? 0;
  const streak = progress?.current_streak ?? 0;
  const week = Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - 6 + index);
    const key = date.toISOString().slice(0, 10);
    return {
      label: date.toLocaleDateString(undefined, { weekday: 'narrow' }),
      day: progress?.streak_calendar.find((item) => item.date === key),
    };
  });
  const levelPercent = progress
    ? Math.round((progress.xp_in_level / progress.xp_for_next_level) * 100)
    : 0;
  return (
    <AppShell>
      <main className="dashboard">
        {loading && (
          <p className="page-state" role="status">
            Loading your dashboard…
          </p>
        )}
        {error && (
          <div className="page-state error-state" role="alert">
            <span>{error}</span>
            <button className="quiet" onClick={() => void loadDashboard()}>
              Try again
            </button>
          </div>
        )}
        {!loading && !error && (
          <>
            <section className="welcome">
              <div>
                <p className="eyebrow">YOUR DAILY PRACTICE</p>
                <h1>Keep the momentum going.</h1>
                <p>Small, deliberate sessions create remarkable progress.</p>
              </div>
              <div className="week">
                {week.map((item, index) => (
                  <span
                    key={index}
                    className={
                      item.day
                        ? item.day.is_shielded
                          ? 'shielded'
                          : 'done'
                        : index === 6
                          ? 'today'
                          : ''
                    }
                  >
                    {item.day ? (item.day.is_shielded ? '◆' : '✓') : item.label}
                  </span>
                ))}
              </div>
            </section>
            <section className="progress-grid">
              <article className="streak-card">
                <span className="metric-icon">♨</span>
                <div>
                  <p>Current streak</p>
                  <b>
                    {streak}
                    <small> days</small>
                  </b>
                  <span>
                    Personal best: {progress?.longest_streak ?? 0} days · Shields{' '}
                    {progress?.shield_available ?? 1}/{progress?.shield_cap ?? 2}
                  </span>
                </div>
                <i className="flame">✦</i>
              </article>
              <article>
                <span className="metric-icon blue">⚡</span>
                <p>
                  Level {progress?.xp_level ?? 1} · {progress?.xp_level_name ?? 'Explorer'}
                </p>
                <b>{xp.toLocaleString()} XP</b>
                <span>
                  {progress?.xp_in_level ?? 0}/{progress?.xp_for_next_level ?? 100} to next level
                </span>
                <div className="xp-track">
                  <i style={{ width: `${levelPercent}%` }} />
                </div>
              </article>
              <article>
                <span className="metric-icon purple">◎</span>
                <p>Strongest topic</p>
                <b>{progress?.topic_progress[0]?.topic ?? '—'}</b>
                <span>{progress?.topic_progress[0]?.solved_count ?? 0} daily solves recorded</span>
                <Link href="/settings">View badges →</Link>
              </article>
            </section>
            <section className="today-layout">
              <article className="today-card">
                <div className="challenge-meta">
                  <span>DAILY CHALLENGE</span>
                  <mark>{challenge?.topic ?? 'Ready when you are'}</mark>
                </div>
                <h2>{challenge?.title ?? 'Your next challenge is waiting'}</h2>
                <p>
                  {challenge
                    ? `${challenge.level} · Difficulty ${challenge.difficulty}/5. Open the problem, run samples, then submit when you are ready.`
                    : 'There is no scheduled challenge for your current level yet. Your admin can schedule one from the calendar.'}
                </p>
                <div className="challenge-bottom">
                  <div>
                    <span className="difficulty">
                      <i />
                      <i />
                      <i />
                      <i />
                      <i />
                    </span>
                    <small>Estimated 15 min</small>
                  </div>
                  <Link className="button" href="/challenge">
                    Open challenge <span>→</span>
                  </Link>
                </div>
              </article>
              <aside className="activity">
                <h3>Streak calendar</h3>
                <div className="activity-chart">
                  {week.map((item, index) => (
                    <span
                      key={index}
                      className={item.day ? (item.day.is_shielded ? 'shield' : 'active') : ''}
                      style={{ height: item.day ? '72%' : '18%' }}
                    />
                  ))}
                </div>
                <div className="chart-days">
                  {week.map((item, index) => (
                    <span key={index}>{item.label}</span>
                  ))}
                </div>
                <p>
                  <b>{streak}</b> day{streak === 1 ? '' : 's'} of practice. ◆ means a shield
                  protected a missed day.
                </p>
              </aside>
            </section>
            <section className="recommendations-panel">
              <div>
                <p className="eyebrow">PERSONALISED PRACTICE</p>
                <h2>Where to focus next</h2>
                <p>
                  {recommendations?.weak_topics.length
                    ? `Your lowest mastery areas: ${recommendations.weak_topics.map((topic) => `${topic.topic} (${topic.mastery_score}%)`).join(', ')}.`
                    : 'Solve a few challenges and we will identify your strongest opportunities.'}
                </p>
              </div>
              <div className="recommendation-list">
                {recommendations?.recommendations.length ? (
                  recommendations.recommendations.map((item) => (
                    <article key={item.assignment_id}>
                      <mark>{item.topic}</mark>
                      <b>{item.title}</b>
                      <span>
                        Difficulty {item.difficulty}/5 · {item.assignment_date}
                      </span>
                      <p>{item.reason}</p>
                    </article>
                  ))
                ) : (
                  <p>No future challenges match your current level yet.</p>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </AppShell>
  );
}
