import Link from 'next/link';

export type TestResult = { position: number; passed: boolean; error?: string };

export type SubmissionReview = {
  id: string;
  question_title: string;
  language: string;
  status: string;
  passed_test_count: number | null;
  total_test_count: number | null;
  attempt_number: number;
  created_at: string;
  test_results: {
    public?: TestResult[];
    hidden?: { passed: number; total: number };
    error?: string;
  } | null;
  source_code: string;
  question: {
    title: string;
    statement_markdown: string;
    examples: { input: unknown; output: unknown; explanation?: string | null }[];
    constraints_markdown: string | null;
    level: string;
    topic: string;
    difficulty: number;
    public_tests: {
      position: number;
      input_data: unknown;
      expected_output: unknown;
      explanation?: string | null;
    }[];
  };
};

const readableStatus = (value: string) => value.replace(/_/g, ' ');
const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

export function SubmissionReviewView({ submission }: { submission: SubmissionReview }) {
  const passed = submission.passed_test_count ?? 0;
  const total = submission.total_test_count ?? 0;
  const isPassed = submission.status === 'passed';

  return (
    <main className="submission-detail-page">
      <Link href="/submissions" className="submission-back">
        ← All submissions
      </Link>
      <section className="submission-detail-hero">
        <div>
          <p className="eyebrow">SAVED ATTEMPT #{submission.attempt_number}</p>
          <h1>{submission.question.title}</h1>
          <div className="submission-detail-meta">
            <span>{submission.question.level}</span>
            <span>{submission.question.topic}</span>
            <span>Difficulty {submission.question.difficulty}/5</span>
            <span>{submission.language}</span>
          </div>
          <p className="submission-date">
            Submitted {new Date(submission.created_at).toLocaleString()}
          </p>
        </div>
        <div className={`submission-verdict ${submission.status}`}>
          <span>{isPassed ? '✓' : '×'}</span>
          <div>
            <b>{readableStatus(submission.status)}</b>
            <small>
              {passed}/{total} tests passed
            </small>
          </div>
        </div>
      </section>

      <section className="submission-review-layout">
        <article className="submission-problem-card">
          <div className="submission-card-heading">
            <span>01</span>
            <h2>Problem</h2>
          </div>
          <p className="submission-statement">{submission.question.statement_markdown}</p>

          {submission.question.examples.length > 0 && (
            <section className="submission-section">
              <h3>Examples</h3>
              <div className="submission-examples">
                {submission.question.examples.map((example, index) => (
                  <article key={index}>
                    <b>Example {index + 1}</b>
                    <pre>{`Input\n${prettyJson(example.input)}\n\nOutput\n${prettyJson(example.output)}`}</pre>
                    {example.explanation && <p>{example.explanation}</p>}
                  </article>
                ))}
              </div>
            </section>
          )}

          {submission.question.constraints_markdown && (
            <section className="submission-section">
              <h3>Constraints</h3>
              <p className="submission-statement">{submission.question.constraints_markdown}</p>
            </section>
          )}

          <section className="submission-section">
            <h3>Public test cases</h3>
            <div className="submission-public-tests">
              {submission.question.public_tests.map((test) => (
                <article key={test.position}>
                  <b>Test {test.position}</b>
                  <pre>{`Input\n${prettyJson(test.input_data)}\n\nExpected output\n${prettyJson(test.expected_output)}`}</pre>
                </article>
              ))}
            </div>
          </section>
        </article>

        <article className="submission-code-card">
          <div className="submission-card-heading">
            <span>02</span>
            <h2>Your solution</h2>
            <mark>{submission.language}</mark>
          </div>
          <pre className="submitted-code">
            <code>{submission.source_code}</code>
          </pre>

          <section className="submission-results">
            <div className="submission-card-heading">
              <span>03</span>
              <h2>Test results</h2>
            </div>
            {submission.test_results?.public?.length ? (
              <div className="submission-result-list">
                {submission.test_results.public.map((result) => (
                  <article className={result.passed ? 'passed' : 'failed'} key={result.position}>
                    <span>{result.passed ? '✓' : '×'}</span>
                    <b>Public test {result.position}</b>
                    <small>{result.passed ? 'Passed' : (result.error ?? 'Failed')}</small>
                  </article>
                ))}
              </div>
            ) : (
              <p className="submission-empty-result">
                No public-test detail is available for this attempt.
              </p>
            )}
            {submission.test_results?.hidden && (
              <p className="submission-hidden-result">
                Hidden tests{' '}
                <b>
                  {submission.test_results.hidden.passed}/{submission.test_results.hidden.total}
                </b>{' '}
                passed
              </p>
            )}
            {submission.test_results?.error && (
              <pre className="execution-error">{submission.test_results.error}</pre>
            )}
          </section>
        </article>
      </section>
    </main>
  );
}
