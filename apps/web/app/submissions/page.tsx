'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AppShell } from '../components/app-shell';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const pageSize = 20;

type Submission = {
  id: string;
  question_title: string;
  language: string;
  status: string;
  passed_test_count: number | null;
  total_test_count: number | null;
  attempt_number: number;
  created_at: string;
};

type SubmissionPage = {
  items: Submission[];
  total: number;
  page: number;
  page_size: number;
};

const statusLabel = (value: string) => value.replace(/_/g, ' ');

export default function SubmissionHistory() {
  const [data, setData] = useState<SubmissionPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: pageSize,
  });
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
  const end = Math.min(data.page * data.page_size, data.total);

  useEffect(() => {
    const token = localStorage.getItem('codele_token');
    if (!token) return;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    fetch(`${api}/submissions?page=${page}&page_size=${pageSize}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not load submission history.');
        return response.json();
      })
      .then((response: SubmissionPage) => setData(response))
      .catch((reason: Error) => {
        if (reason.name !== 'AbortError') setError(reason.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [page]);

  return (
    <AppShell>
      <main className="submission-history">
        <header className="submission-history-header">
          <div>
            <p className="eyebrow">YOUR CODE EXECUTION</p>
            <h1>Submissions</h1>
            <p>Every attempt you make, saved with its exact code and result.</p>
          </div>
          <Link className="submission-new" href="/challenge">
            Solve today&apos;s challenge →
          </Link>
        </header>

        {error && <p className="submission-error">{error}</p>}
        <section className="submission-table-card" aria-label="Submission history">
          <div className="submission-table-caption">
            <b>All submissions</b>
            <span>{data.total} total attempts</span>
          </div>
          <div className="submission-table-head" aria-hidden="true">
            <span>Problem</span>
            <span>Status</span>
            <span>Language</span>
            <span>Tests</span>
            <span>Submitted</span>
          </div>

          {loading && (
            <p className="empty-history" role="status">
              Loading your submissions…
            </p>
          )}
          {!loading && data.items.length === 0 && (
            <div className="empty-history submission-empty-state">
              <span>⌘</span>
              <b>No submissions yet</b>
              <p>Pick today&apos;s challenge and your attempts will appear here.</p>
              <Link href="/challenge">Open today&apos;s challenge</Link>
            </div>
          )}
          {!loading &&
            data.items.map((submission) => (
              <Link
                className="history-row"
                key={submission.id}
                href={`/submissions/${submission.id}`}
              >
                <div className="history-problem">
                  <b>{submission.question_title}</b>
                  <small>Attempt #{submission.attempt_number}</small>
                </div>
                <mark className={`state ${submission.status}`}>
                  {statusLabel(submission.status)}
                </mark>
                <span className="history-language">{submission.language}</span>
                <strong>
                  {submission.passed_test_count ?? '—'} / {submission.total_test_count ?? '—'}
                </strong>
                <time dateTime={submission.created_at}>
                  {new Date(submission.created_at).toLocaleString()}
                </time>
                <span className="history-arrow" aria-hidden="true">
                  ›
                </span>
              </Link>
            ))}
        </section>

        {!loading && data.total > 0 && (
          <nav className="submission-pagination" aria-label="Submission pages">
            <span>
              Showing {start}–{end} of {data.total}
            </span>
            <div>
              <button
                type="button"
                onClick={() => setPage((value) => value - 1)}
                disabled={page === 1}
              >
                ← Previous
              </button>
              <span>
                Page {data.page} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((value) => value + 1)}
                disabled={page >= totalPages}
              >
                Next →
              </button>
            </div>
          </nav>
        )}
      </main>
    </AppShell>
  );
}
