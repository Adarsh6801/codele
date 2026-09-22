'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AppShell } from '../../components/app-shell';
import { SubmissionReview, SubmissionReviewView } from '../../components/submission-review';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export default function SubmissionDetailPage() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const [submission, setSubmission] = useState<SubmissionReview | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('codele_token');
    if (!token || !submissionId) return;
    setError('');
    fetch(`${api}/submissions/${submissionId}/review`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (response.status === 404)
          throw new Error('This submission does not exist or is not yours.');
        if (!response.ok) throw new Error('Could not load this submission.');
        return response.json();
      })
      .then((data: SubmissionReview) => setSubmission(data))
      .catch((reason: Error) => setError(reason.message));
  }, [submissionId]);

  return (
    <AppShell>
      {error ? (
        <main className="submission-detail-page submission-detail-message">
          <p className="submission-error">{error}</p>
          <Link href="/submissions" className="submission-back">
            ← Return to submissions
          </Link>
        </main>
      ) : submission ? (
        <SubmissionReviewView submission={submission} />
      ) : (
        <main className="submission-detail-page submission-detail-message" aria-live="polite">
          Loading your saved submission…
        </main>
      )}
    </AppShell>
  );
}
