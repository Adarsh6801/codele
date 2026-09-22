'use client';

import { useEffect, useRef, useState } from 'react';
import * as AlertDialog from '@radix-ui/react-alert-dialog';
import { AppShell } from '../components/app-shell';
import { CodeEditor } from '../components/code-editor';
import { SolutionWalkthrough } from '../components/solution-walkthrough';

const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';
type Example = { input: unknown; output: unknown; image_url?: string | null };
type Hint = { position: number; xp_penalty: number };
type ChallengeData = {
  assignment_id: string;
  question_version_id: string;
  topic: string;
  difficulty: number;
  title: string;
  statement_markdown: string;
  examples: Example[];
  starter_code: Record<string, string>;
  hints: Hint[];
  attempt_status: 'in_progress' | 'solved' | 'quit';
  walkthrough_unlocked_at: string | null;
};
type TestResult = { position: number; passed: boolean; error?: string | null };
type SampleResult = { passed_test_count: number; total_test_count: number; results: TestResult[] };
type Submission = {
  id: string;
  status: 'queued' | 'running' | 'passed' | 'failed' | 'error';
  passed_test_count: number | null;
  total_test_count: number | null;
  test_results: {
    public?: TestResult[];
    hidden?: { passed: number; total: number };
    error?: string;
  } | null;
  attempt_number: number;
};
type Learning = {
  attempt_status: 'solved' | 'quit';
  explanation_en: string;
  explanation_ml: string;
  complexity_notes: string;
  reference_solution: string | null;
  solution_trace: { step: number; [key: string]: unknown }[];
  solution_notes_en: string[];
  solution_notes_ml: string[];
  solution_video_url: string | null;
  solution_image_urls: string[];
  hints_revealed: number;
  alternative_approaches: {
    title: string;
    summary_markdown: string;
    time_complexity: string;
    space_complexity: string;
  }[];
};
const terminalStates = new Set(['passed', 'failed', 'error']);

const mediaUrl = (url: string) =>
  url.startsWith('/') ? `${api.replace(/\/api\/v1$/, '')}${url}` : url;

function youtubeEmbedUrl(url: string) {
  try {
    const parsed = new URL(url);
    const videoId =
      parsed.hostname === 'youtu.be'
        ? parsed.pathname.slice(1)
        : (parsed.searchParams.get('v') ?? parsed.pathname.split('/').filter(Boolean).pop());
    return videoId ? `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}` : null;
  } catch {
    return null;
  }
}

const requestHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('codele_token')}` });
async function responseError(response: Response) {
  const body = await response.json().catch(() => ({}));
  return typeof body.detail === 'string' ? body.detail : 'The request could not be completed.';
}

export default function Challenge() {
  const [challenge, setChallenge] = useState<ChallengeData | null>(null);
  const [language, setLanguage] = useState('python');
  const [codeByLanguage, setCodeByLanguage] = useState<Record<string, string>>({});
  const [sample, setSample] = useState<SampleResult | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [runningSamples, setRunningSamples] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [revealedHints, setRevealedHints] = useState<Record<number, string>>({});
  const [learning, setLearning] = useState<Learning | null>(null);
  const [learningLanguage, setLearningLanguage] = useState<'en' | 'ml'>('en');
  const [givingUp, setGivingUp] = useState(false);
  const [giveUpDialogOpen, setGiveUpDialogOpen] = useState(false);
  const [loadingChallenge, setLoadingChallenge] = useState(true);
  const idempotencyKey = useRef('');

  useEffect(() => {
    if (!localStorage.getItem('codele_token')) return;
    setLoadingChallenge(true);
    fetch(`${api}/daily-assignment`, { headers: requestHeaders() })
      .then(async (response) => {
        if (response.status === 404) return null;
        if (!response.ok) throw new Error('Could not load today’s challenge.');
        return response.json();
      })
      .then((data: ChallengeData | null) => {
        setChallenge(data);
        setCodeByLanguage({
          python: data?.starter_code?.python ?? '',
          javascript: data?.starter_code?.javascript ?? '',
        });
        if (data && data.attempt_status !== 'in_progress') {
          return fetch(`${api}/daily-assignments/${data.assignment_id}/learning?language=python`, {
            headers: requestHeaders(),
          })
            .then((response) => (response.ok ? response.json() : null))
            .then(setLearning);
        }
        return undefined;
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : 'Could not load today’s challenge.'),
      )
      .finally(() => setLoadingChallenge(false));
  }, []);

  useEffect(() => {
    if (!submission || terminalStates.has(submission.status)) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const response = await fetch(`${api}/submissions/${submission.id}`, {
          headers: requestHeaders(),
        });
        if (!response.ok) throw new Error(await responseError(response));
        if (!cancelled) setSubmission((await response.json()) as Submission);
      } catch (reason) {
        if (!cancelled)
          setError(reason instanceof Error ? reason.message : 'Could not check submission status.');
      }
    };
    const timer = window.setInterval(() => void poll(), 1200);
    void poll();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [submission?.id, submission?.status]);

  useEffect(() => {
    if (!submission || submission.status !== 'passed') return;
    fetch(`${api}/submissions/${submission.id}/learning?language=${language}`, {
      headers: requestHeaders(),
    })
      .then((response) => (response.ok ? response.json() : null))
      .then(setLearning)
      .catch(() => undefined);
  }, [submission?.id, submission?.status, language]);

  useEffect(() => {
    if (!challenge || !learning) return;
    fetch(`${api}/daily-assignments/${challenge.assignment_id}/learning?language=${language}`, {
      headers: requestHeaders(),
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => data && setLearning(data))
      .catch(() => undefined);
  }, [challenge?.assignment_id, language]);

  useEffect(() => {
    if (submission && terminalStates.has(submission.status)) {
      window.dispatchEvent(new Event('codele-progress-updated'));
    }
  }, [submission?.id, submission?.status]);

  const runSamples = async () => {
    if (!challenge) return;
    setError('');
    setNotice('');
    setRunningSamples(true);
    try {
      const response = await fetch(`${api}/submissions/run-samples`, {
        method: 'POST',
        headers: { ...requestHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_version_id: challenge.question_version_id,
          language,
          source_code: code,
        }),
      });
      if (!response.ok) throw new Error(await responseError(response));
      setSample((await response.json()) as SampleResult);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not run sample tests.');
    } finally {
      setRunningSamples(false);
    }
  };

  const submitSolution = async () => {
    if (!challenge) return;
    setError('');
    setNotice('');
    setSubmitting(true);
    idempotencyKey.current = crypto.randomUUID();
    try {
      const response = await fetch(`${api}/submissions`, {
        method: 'POST',
        headers: {
          ...requestHeaders(),
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey.current,
        },
        body: JSON.stringify({
          question_version_id: challenge.question_version_id,
          daily_assignment_id: challenge.assignment_id,
          language,
          source_code: code,
        }),
      });
      if (!response.ok) throw new Error(await responseError(response));
      setSubmission((await response.json()) as Submission);
      setNotice('Your solution is queued for secure evaluation.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not submit your solution.');
    } finally {
      setSubmitting(false);
    }
  };

  const giveUpAndLearn = async () => {
    if (!challenge || givingUp) return;
    setError('');
    setNotice('');
    setGivingUp(true);
    try {
      const response = await fetch(`${api}/daily-assignments/${challenge.assignment_id}/quit`, {
        method: 'POST',
        headers: requestHeaders(),
      });
      if (!response.ok) throw new Error(await responseError(response));
      const attempt = (await response.json()) as {
        status: 'quit';
        walkthrough_unlocked_at: string;
      };
      setChallenge((current) =>
        current
          ? {
              ...current,
              attempt_status: attempt.status,
              walkthrough_unlocked_at: attempt.walkthrough_unlocked_at,
            }
          : current,
      );
      const learningResponse = await fetch(
        `${api}/daily-assignments/${challenge.assignment_id}/learning?language=${language}`,
        { headers: requestHeaders() },
      );
      if (!learningResponse.ok) throw new Error(await responseError(learningResponse));
      setLearning((await learningResponse.json()) as Learning);
      setNotice('Solution unlocked. This challenge adds 0 XP, but your daily streak was counted.');
      setGiveUpDialogOpen(false);
      window.dispatchEvent(new Event('codele-progress-updated'));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not unlock the solution.');
    } finally {
      setGivingUp(false);
    }
  };

  const revealHint = async (position: number) => {
    if (!challenge || revealedHints[position]) return;
    setError('');
    try {
      const response = await fetch(
        `${api}/daily-assignments/${challenge.assignment_id}/hints/${position}`,
        {
          method: 'POST',
          headers: requestHeaders(),
        },
      );
      if (!response.ok) throw new Error(await responseError(response));
      const hint = (await response.json()) as { content_markdown: string };
      setRevealedHints((current) => ({ ...current, [position]: hint.content_markdown }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not reveal this hint.');
    }
  };

  const publicResults = submission?.test_results?.public ?? [];
  const code = codeByLanguage[language] ?? '';
  const attemptFinished = challenge?.attempt_status !== 'in_progress';
  return (
    <AppShell>
      <main className="challenge-page">
        {loadingChallenge ? (
          <section className="empty-challenge" role="status">
            <h1>Loading today’s challenge…</h1>
            <p>Preparing the problem and secure coding workspace.</p>
          </section>
        ) : challenge ? (
          <>
            <div className="problem-heading">
              <div>
                <p className="challenge-breadcrumb">Practice / {challenge.topic}</p>
                <h1>{challenge.title}</h1>
                <div className="challenge-tags">
                  <span>Difficulty {challenge.difficulty}/5</span>
                  <span>Today’s challenge</span>
                </div>
              </div>
              <div className="challenge-reward">
                <span className="challenge-xp">+20 XP</span>
                <small>Complete all tests to earn it</small>
              </div>
            </div>
            <div className="challenge-workspace">
              <article className="problem-panel">
                <section className="problem-section statement-section">
                  <p className="panel-label">PROBLEM</p>
                  <p className="problem-copy">{challenge.statement_markdown}</p>
                </section>
                <section className="problem-section">
                  <p className="panel-label">EXAMPLES</p>
                  <div className="example-stack">
                    {challenge.examples.map((example, index) => (
                      <article className="example-card" key={index}>
                        <span>Example {index + 1}</span>
                        {example.image_url && (
                          <img
                            className="example-image"
                            src={mediaUrl(example.image_url)}
                            alt={`Illustration for example ${index + 1}`}
                          />
                        )}
                        <div>
                          <b>Input</b>
                          <code>{JSON.stringify(example.input)}</code>
                        </div>
                        <div>
                          <b>Output</b>
                          <code>{JSON.stringify(example.output)}</code>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
                <section className="problem-section hint-section">
                  <p className="panel-label">HINTS</p>
                  <div className="hint-list">
                    {challenge.hints.map((hint) => (
                      <article key={hint.position}>
                        <span className="hint-number">{hint.position}</span>
                        <div>
                          <b>Hint {hint.position}</b>
                          {revealedHints[hint.position] ? (
                            <p>{revealedHints[hint.position]}</p>
                          ) : (
                            <button
                              className="hint-button"
                              onClick={() => void revealHint(hint.position)}
                            >
                              Reveal hint{hint.xp_penalty ? ` (${hint.xp_penalty} XP` : ''}
                              {hint.xp_penalty ? ')' : ''}
                            </button>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              </article>
              <section className="editor-panel">
                <div className="editor-top">
                  <div className="editor-language">
                    <span className="editor-dot" />
                    <select
                      aria-label="Programming language"
                      value={language}
                      onChange={(event) => setLanguage(event.target.value)}
                    >
                      <option value="python">Python</option>
                      <option value="javascript">JavaScript</option>
                    </select>
                  </div>
                  <span>main.{language === 'python' ? 'py' : 'js'}</span>
                </div>
                <CodeEditor
                  language={language === 'python' ? 'python' : 'javascript'}
                  value={code}
                  onChange={(nextCode) =>
                    setCodeByLanguage((current) => ({ ...current, [language]: nextCode }))
                  }
                />
                <div className="editor-actions">
                  <button
                    className="sample-button"
                    disabled={runningSamples || submitting || attemptFinished}
                    onClick={() => void runSamples()}
                  >
                    {runningSamples ? 'Running samples…' : '▷ Run samples'}
                  </button>
                  <button
                    className="button submit-button"
                    disabled={runningSamples || submitting || attemptFinished}
                    onClick={() => void submitSolution()}
                  >
                    {submitting ? 'Queueing…' : 'Submit solution'}
                  </button>
                  {!attemptFinished && (
                    <button
                      className="give-up-button"
                      disabled={runningSamples || submitting || givingUp}
                      onClick={() => setGiveUpDialogOpen(true)}
                    >
                      {givingUp ? 'Unlocking…' : 'Give up & show solution'}
                    </button>
                  )}
                </div>
                {challenge.attempt_status === 'quit' && (
                  <p className="learning-unlocked">
                    Solution revealed · 0 XP awarded · streak counted
                  </p>
                )}
                {sample && (
                  <section className="execution-result">
                    <h3>
                      Sample tests{' '}
                      <span
                        className={
                          sample.passed_test_count === sample.total_test_count ? 'pass' : 'fail'
                        }
                      >
                        {sample.passed_test_count}/{sample.total_test_count} passed
                      </span>
                    </h3>
                    <TestResults results={sample.results} />
                  </section>
                )}
                {submission && (
                  <section className="execution-result">
                    <h3>
                      Submission{' '}
                      <span className={`state ${submission.status}`}>{submission.status}</span>
                    </h3>
                    {!terminalStates.has(submission.status) && (
                      <p className="pending">Your code is running in an isolated environment…</p>
                    )}
                    {terminalStates.has(submission.status) && (
                      <>
                        <p className="result-summary">
                          {submission.passed_test_count ?? 0}/{submission.total_test_count ?? 0}{' '}
                          tests passed · attempt #{submission.attempt_number}
                        </p>
                        <TestResults results={publicResults} />
                        {submission.test_results?.hidden && (
                          <p className="hidden-summary">
                            Hidden tests: {submission.test_results.hidden.passed}/
                            {submission.test_results.hidden.total} passed
                          </p>
                        )}
                        {submission.test_results?.error && (
                          <pre className="execution-error">{submission.test_results.error}</pre>
                        )}
                      </>
                    )}
                  </section>
                )}
                {notice && <p className="submission-notice">{notice}</p>}
                {error && <p className="submission-error">{error}</p>}
              </section>
            </div>
            {learning && (
              <LearningReview
                learning={learning}
                language={learningLanguage}
                onLanguageChange={setLearningLanguage}
              />
            )}
          </>
        ) : (
          <section className="empty-challenge">
            <h1>No challenge scheduled yet</h1>
            <p>Ask an administrator to schedule a question for your level.</p>
          </section>
        )}
      </main>
      <AlertDialog.Root open={giveUpDialogOpen} onOpenChange={setGiveUpDialogOpen}>
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="give-up-dialog-overlay" />
          <AlertDialog.Content className="give-up-dialog" aria-describedby="give-up-description">
            <div className="give-up-dialog-icon" aria-hidden="true">
              ?
            </div>
            <AlertDialog.Title>Reveal the solution?</AlertDialog.Title>
            <AlertDialog.Description id="give-up-description">
              You can review the bilingual explanation and walkthrough now. This daily challenge
              will earn <b>0 XP</b>, but it will count once toward your streak.
            </AlertDialog.Description>
            <div className="give-up-dialog-actions">
              <AlertDialog.Cancel disabled={givingUp}>Keep solving</AlertDialog.Cancel>
              <AlertDialog.Action
                disabled={givingUp}
                onClick={(event) => {
                  event.preventDefault();
                  void giveUpAndLearn();
                }}
              >
                {givingUp ? 'Unlocking…' : 'Reveal solution · 0 XP'}
              </AlertDialog.Action>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </AppShell>
  );
}

function TestResults({ results }: { results: TestResult[] }) {
  if (results.length === 0) return <p className="pending">No public test details are available.</p>;
  return (
    <div className="test-results">
      {results.map((result) => (
        <article className={result.passed ? 'passed' : 'failed'} key={result.position}>
          <b>Test {result.position}</b>
          <span>{result.passed ? 'Passed' : (result.error ?? 'Failed')}</span>
        </article>
      ))}
    </div>
  );
}

function LearningReview({
  learning,
  language,
  onLanguageChange,
}: {
  learning: Learning;
  language: 'en' | 'ml';
  onLanguageChange: (language: 'en' | 'ml') => void;
}) {
  return (
    <section className="learning-panel">
      <div className="learning-heading">
        <div>
          <p className="eyebrow">
            {learning.attempt_status === 'quit' ? 'SOLUTION REVIEW · 0 XP' : 'POST-SOLVE REVIEW'}
          </p>
          <h2>See how the solution works</h2>
          <p>Follow the visual steps below, then inspect the reference code at your own pace.</p>
        </div>
        <div className="language-picker" role="group" aria-label="Explanation language">
          <span>Read in</span>
          <div className="learning-language-toggle">
            <button
              className={language === 'en' ? 'active' : ''}
              onClick={() => onLanguageChange('en')}
            >
              English
            </button>
            <button
              className={language === 'ml' ? 'active' : ''}
              onClick={() => onLanguageChange('ml')}
            >
              മലയാളം
            </button>
          </div>
          <small>{language === 'en' ? 'English explanation' : 'മലയാളം വിശദീകരണം'}</small>
        </div>
      </div>
      <div className="learning-intro-grid">
        <article className="learning-copy-card">
          <span className="learning-icon" aria-hidden="true">
            ✦
          </span>
          <div className="learning-copy-title">
            <b>{language === 'en' ? 'The idea, simply explained' : 'ലളിതമായി ആശയം'}</b>
            <small>{language === 'en' ? 'English' : 'മലയാളം'}</small>
          </div>
          <p lang={language === 'ml' ? 'ml' : 'en'}>
            {language === 'en' ? learning.explanation_en : learning.explanation_ml}
          </p>
        </article>
        <article className="complexity-box">
          <span className="learning-icon" aria-hidden="true">
            ◷
          </span>
          <b>Complexity</b>
          <p>{learning.complexity_notes}</p>
          <small>
            {learning.hints_revealed
              ? `${learning.hints_revealed} hint${learning.hints_revealed === 1 ? '' : 's'} revealed`
              : 'Solved without revealing a hint'}
          </small>
        </article>
      </div>
      <SolutionWalkthrough trace={learning.solution_trace} language={language} />
      {(learning.solution_image_urls.length > 0 || learning.solution_video_url) && (
        <section className="solution-media-section">
          <div>
            <p className="eyebrow">OPTIONAL VISUAL GUIDE</p>
            <h3>See the solution in action</h3>
            <p>Open the visual explanation or video when you want an extra walkthrough.</p>
          </div>
          {learning.solution_image_urls.length > 0 && (
            <details className="solution-media-details">
              <summary>View solution illustrations ({learning.solution_image_urls.length})</summary>
              <div className="solution-media-gallery">
                {learning.solution_image_urls.map((url, index) => (
                  <img key={url} src={mediaUrl(url)} alt={`Solution illustration ${index + 1}`} />
                ))}
              </div>
            </details>
          )}
          {learning.solution_video_url && youtubeEmbedUrl(learning.solution_video_url) && (
            <details className="solution-media-details">
              <summary>Watch the YouTube walkthrough</summary>
              <iframe
                className="solution-video"
                src={youtubeEmbedUrl(learning.solution_video_url) ?? undefined}
                title="Solution walkthrough"
                loading="lazy"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </details>
          )}
        </section>
      )}
      <div className="learning-lower-grid">
        {learning.reference_solution && (
          <details>
            <summary>View reference solution</summary>
            <pre className="reference-code">{learning.reference_solution}</pre>
          </details>
        )}
        <section className="alternatives-section">
          <h3>Alternative approaches</h3>
          <div className="approach-list">
            {learning.alternative_approaches.map((approach) => (
              <article key={approach.title}>
                <b>{approach.title}</b>
                <p>{approach.summary_markdown}</p>
                <small>
                  Time {approach.time_complexity} · Space {approach.space_complexity}
                </small>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
