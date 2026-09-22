import { FormEvent, StrictMode, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const api = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const mediaAssetUrl = (url: string) =>
  url.startsWith('/') ? `${api.replace(/\/api\/v1$/, '')}${url}` : url;
type Page =
  | 'Dashboard'
  | 'Question bank'
  | 'Categories'
  | 'Schedule'
  | 'Scheduled'
  | 'Users'
  | 'Admins'
  | 'Moderation'
  | 'Analytics';
type Question = {
  question_id: string;
  question_version_id: string;
  slug: string;
  title: string;
  status: string;
  topic: string;
  difficulty: number;
  category_id: string;
  level: string;
  version_number: number;
};
type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  level: string;
  is_active: boolean;
  created_at: string;
};
type OperationalUser = User & {
  session_version: number;
  submission_count: number;
  xp_total: number;
  current_streak: number;
  badge_count: number;
};
type UserActivity = {
  user: OperationalUser;
  recent_submissions: {
    id: string;
    status: string;
    language: string;
    attempt_number: number;
    passed_test_count: number | null;
    total_test_count: number | null;
    created_at: string;
  }[];
  recent_xp_transactions: { id: string; amount: number; reason: string; created_at: string }[];
  streak_calendar: { date: string; shielded: boolean; submission_id: string | null }[];
  badges: { code: string; name: string; icon: string; awarded_at: string }[];
};
type ModerationReport = {
  id: string;
  status: string;
  reason: string;
  details: string | null;
  resolution_note: string | null;
  created_at: string;
  handled_at: string | null;
  reporter_display_name: string;
  target_display_name: string;
  handled_by_display_name: string | null;
};
type AnalyticsOverview = {
  dau: number;
  wau: number;
  mau: number;
  completion_rate: number;
  execution_failure_rate: number;
  evaluated_submissions: number;
  average_attempt_number: number;
  queue_depth: number;
  daily: {
    date: string;
    active_users: number;
    submissions: number;
    passed_submissions: number;
    execution_failures: number;
  }[];
};
type AuditLog = {
  id: string;
  action: string;
  target_type: string;
  target_id: string;
  metadata_json: { before?: Record<string, unknown>; after?: Record<string, unknown> };
  created_at: string;
  actor_display_name: string;
  actor_email: string;
};
type Assignment = {
  id: string;
  assignment_date: string;
  level: string;
  question_version_id: string;
  title: string;
  topic: string;
};
type Submission = {
  id: string;
  user_display_name: string;
  user_email: string;
  language: string;
  status: string;
  passed_test_count: number | null;
  total_test_count: number | null;
  created_at: string;
  test_results: Record<string, unknown> | null;
};
type TestInput = {
  position: number;
  input_data: unknown;
  expected_output: unknown;
  explanation?: string;
};
type HintInput = { position: number; content_markdown: string; xp_penalty: number };
type QuestionDetail = Question & {
  statement_markdown: string;
  examples: { input: unknown; output: unknown; explanation?: string; image_url?: string | null }[];
  constraints_markdown: string | null;
  starter_code: Record<string, string>;
  solution_code: Record<string, string>;
  explanation_markdown: string | null;
  explanation_en: string | null;
  explanation_ml: string | null;
  solution_trace: Record<string, unknown>[];
  solution_notes_en: string[];
  solution_notes_ml: string[];
  solution_video_url: string | null;
  solution_image_urls: string[];
  complexity_notes: string | null;
  alternative_approaches: {
    title: string;
    summary_markdown: string;
    time_complexity: string;
    space_complexity: string;
  }[];
  public_tests: TestInput[];
  hidden_tests: TestInput[];
  hints: HintInput[];
};
type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  question_count: number;
};
const nav: [string, Page][] = [
  ['⌂', 'Dashboard'],
  ['◉', 'Question bank'],
  ['#', 'Categories'],
  ['▦', 'Schedule'],
  ['♙', 'Users'],
  ['⚑', 'Moderation'],
  ['◌', 'Analytics'],
];
const pages: Page[] = [...nav.map(([, page]) => page), 'Scheduled', 'Admins'];

function SignIn({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const response = await fetch(`${api}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const body = await response.json();
      if (!response.ok) {
        setError(body.detail ?? 'Unable to sign in. Check your credentials and try again.');
        return;
      }
      const me = await fetch(`${api}/auth/me`, {
        headers: { Authorization: `Bearer ${body.access_token}` },
      });
      const profile = await me.json();
      if (!me.ok || !['admin', 'super_admin'].includes(profile.role)) {
        setError('This account does not have admin access.');
        return;
      }
      localStorage.setItem('codele_admin_token', body.access_token);
      onSuccess(body.access_token);
    } catch {
      setError('The API is unavailable. Start the backend and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <main className="admin-auth">
      <section className="admin-auth-form">
        <div className="brand admin-auth-brand">
          <img src="/codele-logo.png" alt="Codele" /> codele <small>ADMIN</small>
        </div>
        <div className="admin-auth-content">
          <p className="eyebrow">OPERATIONS CONSOLE</p>
          <h1>Welcome back.</h1>
          <p className="admin-auth-intro">
            Sign in to author challenges, publish updates, and plan daily learning.
          </p>
          <form onSubmit={submit}>
            <label>
              Work email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@yourcompany.com"
                autoComplete="email"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            {error && <p className="error auth-error">{error}</p>}
            <button disabled={isSubmitting}>
              {isSubmitting ? 'Signing in…' : 'Sign in to admin'}
            </button>
          </form>
          <p className="admin-auth-help">
            Admin access is granted only by an existing administrator.
          </p>
        </div>
      </section>
      <aside className="admin-auth-visual" aria-hidden="true">
        <div className="admin-glow admin-glow-one" />
        <div className="admin-glow admin-glow-two" />
        <div className="admin-visual-copy">
          <span className="admin-visual-label">CODELE / CONTENT STUDIO</span>
          <h2>Turn great problems into daily practice.</h2>
          <p>One calm workspace for every challenge, test case, hint, and release.</p>
        </div>
        <div className="admin-code-window">
          <div className="admin-code-top">
            <i />
            <i />
            <i />
            <span>publish-challenge.ts</span>
          </div>
          <code>
            <span className="code-dim">const</span> challenge = await{' '}
            <span className="code-blue">review</span>({'{'}
            <br />
            &nbsp;&nbsp;tests: <span className="code-green">'verified'</span>,<br />
            &nbsp;&nbsp;hints: <span className="code-green">'ready'</span>,<br />
            &nbsp;&nbsp;status: <span className="code-orange">'published'</span>
            <br />
            {'}'});
            <br />
            <br />
            <span className="code-dim">await</span> calendar.
            <span className="code-blue">assign</span>(challenge);
          </code>
        </div>
        <div className="admin-visual-stat">
          <b>24</b>
          <span>challenges ready to schedule</span>
        </div>
      </aside>
    </main>
  );
}

const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` });

async function readError(response: Response) {
  const body = await response.json().catch(() => ({}));
  return typeof body.detail === 'string' ? body.detail : 'The request could not be completed.';
}

const today = () => new Date().toISOString().slice(0, 10);
const dateTime = (value: string) => new Date(value).toLocaleString();

function DashboardHome({ token, goTo }: { token: string; goTo: (page: Page) => void }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    Promise.all([
      fetch(`${api}/admin/questions`, { headers: authHeaders(token) }),
      fetch(`${api}/admin/users`, { headers: authHeaders(token) }),
    ])
      .then(async ([questionsResponse, usersResponse]) => {
        if (!questionsResponse.ok || !usersResponse.ok) throw new Error();
        setQuestions(await questionsResponse.json());
        setUsers(await usersResponse.json());
      })
      .catch(() => setNotice('Could not load dashboard data. Confirm that the API is running.'));
  }, [token]);
  const cards: [string, string, number, string, Page][] = [
    ['◉', 'QUESTION VERSIONS', questions.length, 'Browse question bank', 'Question bank'],
    [
      '✓',
      'READY TO SCHEDULE',
      questions.filter((q) => q.status === 'ready').length,
      'Plan calendar',
      'Schedule',
    ],
    [
      '▣',
      'PUBLISHED',
      questions.filter((q) => q.status === 'published').length,
      'Open question bank',
      'Question bank',
    ],
    ['♙', 'USERS', users.length, 'View users', 'Users'],
  ];
  return (
    <>
      <p className="eyebrow">CODELE ADMINISTRATION</p>
      <h2>Dashboard overview</h2>
      <p className="subtitle">
        Manage content, publishing workflow, and the daily challenge calendar.
      </p>
      {notice && <p className="error">{notice}</p>}
      <section className="grid">
        {cards.map(([icon, title, value, action, page]) => (
          <article key={title}>
            <div className="icon">{icon}</div>
            <span className="arrow">↗</span>
            <p>{title}</p>
            <strong>{value}</strong>
            <hr />
            <button onClick={() => goTo(page)}>
              {action} <em>•</em>
            </button>
          </article>
        ))}
      </section>
      <section className="recent">
        <div>
          <h3>Recent question versions</h3>
          <p>Latest changes in your learning content.</p>
        </div>
        <button className="outline" onClick={() => goTo('Question bank')}>
          Open question bank
        </button>
        {questions.length === 0 && (
          <p className="empty">
            No questions yet. Create your first challenge in the question bank.
          </p>
        )}
        {questions.slice(0, 5).map((question) => (
          <div className="row" key={question.question_version_id}>
            <b>{question.title}</b>
            <span>
              {question.topic} · v{question.version_number}
            </span>
            <mark className={question.status}>{question.status}</mark>
          </div>
        ))}
      </section>
    </>
  );
}

type TestCaseFormValue = { input: string; output: string };
type TextQuestionFormKey = Exclude<keyof QuestionFormValue, 'publicTests' | 'hiddenTests'>;

type QuestionFormValue = {
  slug: string;
  title: string;
  statement: string;
  constraints: string;
  level: string;
  categoryId: string;
  difficulty: string;
  examples: string;
  starterPython: string;
  starterJavascript: string;
  solutionPython: string;
  solutionJavascript: string;
  explanation: string;
  explanationEnglish: string;
  explanationMalayalam: string;
  solutionTrace: string;
  solutionNotesEnglish: string;
  solutionNotesMalayalam: string;
  solutionVideoUrl: string;
  solutionImages: string;
  complexity: string;
  alternatives: string;
  publicTests: TestCaseFormValue[];
  hiddenTests: TestCaseFormValue[];
  hintOne: string;
  hintTwo: string;
  hintThree: string;
};
const emptyQuestion: QuestionFormValue = {
  slug: '',
  title: '',
  statement: '',
  constraints: '',
  level: 'rookie',
  categoryId: '',
  difficulty: '1',
  examples: '[]',
  starterPython: '',
  starterJavascript: '',
  solutionPython: '',
  solutionJavascript: '',
  explanation: '',
  explanationEnglish: '',
  explanationMalayalam: '',
  solutionTrace:
    '[\n  {\n    "step": 1,\n    "array": [1, 2, 4, 5],\n    "cursor": 0,\n    "note_en": "Compare the first two values.",\n    "note_ml": "ആദ്യ രണ്ട് മൂല്യങ്ങൾ താരതമ്യം ചെയ്യുക."\n  }\n]',
  solutionNotesEnglish: 'Describe the initial state.',
  solutionNotesMalayalam: 'ആരംഭ നില വിവരിക്കുക.',
  solutionVideoUrl: '',
  solutionImages: '',
  complexity: '',
  alternatives:
    '[\n  {\n    "title": "Brute-force baseline",\n    "summary_markdown": "Describe the simplest correct approach and its trade-offs.",\n    "time_complexity": "O(n²)",\n    "space_complexity": "O(1)"\n  }\n]',
  publicTests: [{ input: '[]', output: '[]' }],
  hiddenTests: [{ input: '[]', output: '[]' }],
  hintOne: '',
  hintTwo: '',
  hintThree: '',
};
const parseJson = (value: string) => JSON.parse(value);
const valueJson = (value: string) => {
  try {
    return parseJson(value);
  } catch {
    return value;
  }
};

const fileAsDataUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read the selected image.'));
    reader.onload = () => resolve(String(reader.result));
    reader.readAsDataURL(file);
  });

function questionFormFrom(detail?: QuestionDetail): QuestionFormValue {
  if (!detail) return emptyQuestion;
  return {
    slug: detail.slug,
    title: detail.title,
    statement: detail.statement_markdown,
    constraints: detail.constraints_markdown ?? '',
    level: detail.level,
    categoryId: detail.category_id,
    difficulty: String(detail.difficulty),
    examples: JSON.stringify(detail.examples, null, 2),
    starterPython: detail.starter_code.python ?? '',
    starterJavascript: detail.starter_code.javascript ?? '',
    solutionPython: detail.solution_code.python ?? '',
    solutionJavascript: detail.solution_code.javascript ?? '',
    explanation: detail.explanation_markdown ?? '',
    explanationEnglish: detail.explanation_en ?? detail.explanation_markdown ?? '',
    explanationMalayalam: detail.explanation_ml ?? '',
    solutionTrace: JSON.stringify(detail.solution_trace ?? [], null, 2),
    solutionNotesEnglish: (detail.solution_notes_en ?? []).join('\n'),
    solutionNotesMalayalam: (detail.solution_notes_ml ?? []).join('\n'),
    solutionVideoUrl: detail.solution_video_url ?? '',
    solutionImages: (detail.solution_image_urls ?? []).join('\n'),
    complexity: detail.complexity_notes ?? '',
    alternatives: JSON.stringify(detail.alternative_approaches, null, 2),
    publicTests: detail.public_tests.map((test) => ({
      input: JSON.stringify(test.input_data),
      output: JSON.stringify(test.expected_output),
    })),
    hiddenTests: detail.hidden_tests.map((test) => ({
      input: JSON.stringify(test.input_data),
      output: JSON.stringify(test.expected_output),
    })),
    hintOne: detail.hints.find((hint) => hint.position === 1)?.content_markdown ?? '',
    hintTwo: detail.hints.find((hint) => hint.position === 2)?.content_markdown ?? '',
    hintThree: detail.hints.find((hint) => hint.position === 3)?.content_markdown ?? '',
  };
}

function makeQuestionPayload(form: QuestionFormValue) {
  return {
    title: form.title,
    statement_markdown: form.statement,
    examples: parseJson(form.examples),
    constraints_markdown: form.constraints || null,
    level: form.level,
    category_id: form.categoryId,
    difficulty: Number(form.difficulty),
    starter_code: {
      ...(form.starterPython && { python: form.starterPython }),
      ...(form.starterJavascript && { javascript: form.starterJavascript }),
    },
    solution_code: {
      ...(form.solutionPython && { python: form.solutionPython }),
      ...(form.solutionJavascript && { javascript: form.solutionJavascript }),
    },
    explanation_markdown: form.explanation || null,
    explanation_en: form.explanationEnglish || null,
    explanation_ml: form.explanationMalayalam || null,
    solution_trace: parseJson(form.solutionTrace),
    solution_notes_en: form.solutionNotesEnglish
      .split('\n')
      .map((note) => note.trim())
      .filter(Boolean),
    solution_notes_ml: form.solutionNotesMalayalam
      .split('\n')
      .map((note) => note.trim())
      .filter(Boolean),
    solution_video_url: form.solutionVideoUrl.trim() || null,
    solution_image_urls: form.solutionImages
      .split('\n')
      .map((url) => url.trim())
      .filter(Boolean),
    complexity_notes: form.complexity || null,
    alternative_approaches: parseJson(form.alternatives),
    public_tests: form.publicTests.map((test, index) => ({
      position: index + 1,
      input_data: valueJson(test.input),
      expected_output: valueJson(test.output),
    })),
    hidden_tests: form.hiddenTests.map((test, index) => ({
      position: form.publicTests.length + index + 1,
      input_data: valueJson(test.input),
      expected_output: valueJson(test.output),
    })),
    hints: [form.hintOne, form.hintTwo, form.hintThree].map((content_markdown, index) => ({
      position: index + 1,
      content_markdown,
      xp_penalty: 0,
    })),
  };
}

type TracePreviewStep = {
  step: number;
  array: unknown[];
  cursor: number | null;
  noteEn: string;
  noteMl: string;
  context: [string, unknown][];
};

const traceRecord = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};

function normalizeTracePreviewStep(
  raw: Record<string, unknown>,
  fallbackStep: number,
): TracePreviewStep {
  // Accept a legacy nested state while keeping the saved contract flat and easy to author.
  const value = { ...traceRecord(raw.state), ...raw };
  const arrayValue = value.array ?? value.values;
  const textValue = value.text;
  const array = Array.isArray(arrayValue)
    ? arrayValue
    : typeof textValue === 'string'
      ? [...textValue]
      : [];
  const candidateCursor = value.cursor ?? value.index ?? value.left ?? value.middle;
  const cursor =
    typeof candidateCursor === 'number' && candidateCursor >= 0
      ? candidateCursor
      : array.length
        ? Math.min(fallbackStep - 1, array.length - 1)
        : null;
  const reserved = new Set([
    'step',
    'array',
    'values',
    'text',
    'cursor',
    'index',
    'left',
    'middle',
    'note_en',
    'note_ml',
    'note',
    'state',
  ]);

  return {
    step: typeof value.step === 'number' ? value.step : fallbackStep,
    array,
    cursor,
    noteEn:
      typeof value.note_en === 'string'
        ? value.note_en
        : typeof value.note === 'string'
          ? value.note
          : '',
    noteMl: typeof value.note_ml === 'string' ? value.note_ml : '',
    context: Object.entries(value).filter(([key]) => !reserved.has(key)),
  };
}

function TracePlaybackPreview({
  trace,
  error,
}: {
  trace: Record<string, unknown>[];
  error: string;
}) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [language, setLanguage] = useState<'en' | 'ml'>('en');
  const traceKey = JSON.stringify(trace);
  const steps = useMemo(
    () =>
      trace
        .map((step, position) => normalizeTracePreviewStep(step, position + 1))
        .sort((left, right) => left.step - right.step),
    [traceKey],
  );
  const current = steps[index];
  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [traceKey]);
  useEffect(() => {
    if (!playing || steps.length < 2) return;
    const timer = window.setInterval(() => {
      setIndex((currentIndex) => {
        if (currentIndex >= steps.length - 1) {
          setPlaying(false);
          return currentIndex;
        }
        return currentIndex + 1;
      });
    }, 1300 / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, steps.length]);
  return (
    <section className="trace-preview wide" aria-live="polite">
      <header className="admin-trace-header">
        <div>
          <p className="eyebrow">PUBLISH PREVIEW</p>
          <h4>Walkthrough trace</h4>
          <p>This is the same interactive walkthrough learners see after solving.</p>
        </div>
        <div className="admin-trace-languages" aria-label="Preview language">
          <button
            type="button"
            className={language === 'en' ? 'active' : ''}
            onClick={() => setLanguage('en')}
          >
            English
          </button>
          <button
            type="button"
            className={language === 'ml' ? 'active' : ''}
            onClick={() => setLanguage('ml')}
          >
            മലയാളം
          </button>
        </div>
      </header>
      {error ? (
        <p className="error">{error}</p>
      ) : current ? (
        <>
          <div className="admin-trace-steps" aria-label="Walkthrough steps">
            {steps.map((step, stepIndex) => (
              <button
                type="button"
                key={`${step.step}-${stepIndex}`}
                className={stepIndex === index ? 'active' : ''}
                onClick={() => {
                  setIndex(stepIndex);
                  setPlaying(false);
                }}
              >
                {step.step}
              </button>
            ))}
          </div>
          <div className="admin-trace-stage">
            <div className="admin-trace-stage-top">
              <b>
                Step {current.step} of {steps.length}
              </b>
              <span>
                {current.array.length
                  ? 'Follow the highlighted position'
                  : 'Read the state and explanation'}
              </span>
            </div>
            {current.array.length > 0 && (
              <div className="admin-trace-array" aria-label="Array state">
                {current.array.map((item, arrayIndex) => (
                  <div className="admin-trace-item" key={`${arrayIndex}-${String(item)}`}>
                    {current.cursor === arrayIndex && (
                      <span className="admin-trace-cursor">cursor ↓</span>
                    )}
                    <span className={current.cursor === arrayIndex ? 'focus' : ''}>
                      {String(item)}
                    </span>
                    <small>{arrayIndex}</small>
                  </div>
                ))}
              </div>
            )}
            {current.context.length > 0 && (
              <div className="admin-trace-context">
                {current.context.map(([key, value]) => (
                  <span key={key}>
                    <b>{key.replace(/_/g, ' ')}</b>{' '}
                    {typeof value === 'string' ? value : JSON.stringify(value)}
                  </span>
                ))}
              </div>
            )}
            <p className="admin-trace-note">
              <span>{language === 'ml' ? 'വിശദീകരണം' : 'What happens now'}</span>
              {language === 'ml' && !current.noteMl
                ? 'ഈ ഘട്ടത്തിനായുള്ള മലയാളം വിശദീകരണം ചേർക്കുക.'
                : language === 'ml'
                  ? current.noteMl
                  : current.noteEn || 'Add an English explanation for this step.'}
            </p>
          </div>
          <div className="admin-trace-controls">
            <button
              type="button"
              onClick={() => setIndex((value) => Math.max(0, value - 1))}
              disabled={index === 0}
            >
              ← Previous
            </button>
            <button
              type="button"
              onClick={() => setPlaying((value) => !value)}
              disabled={steps.length < 2}
            >
              {playing ? '❚❚ Pause' : '▶ Play'}
            </button>
            <button
              type="button"
              onClick={() => setIndex((value) => Math.min(steps.length - 1, value + 1))}
              disabled={index === steps.length - 1}
            >
              Next →
            </button>
            <label>
              Speed
              <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>
                <option value={0.5}>0.5×</option>
                <option value={1}>1×</option>
                <option value={2}>2×</option>
              </select>
            </label>
          </div>
        </>
      ) : (
        <p className="error">
          A walkthrough needs at least one visible state before it can publish.
        </p>
      )}
    </section>
  );
}

function QuestionEditor({
  token,
  initial,
  versionOf,
  onDone,
}: {
  token: string;
  initial?: QuestionDetail;
  versionOf?: string;
  onDone: () => void;
}) {
  const [form, setForm] = useState(() => questionFormFrom(initial));
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [mediaUploading, setMediaUploading] = useState(false);
  const [mediaNotice, setMediaNotice] = useState('');
  const [exampleImageIndex, setExampleImageIndex] = useState(0);
  const update = (key: keyof QuestionFormValue, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));
  const uploadImage = async (file: File, destination: 'example' | 'solution') => {
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      setError('Choose a PNG, JPEG, or WebP image.');
      return;
    }
    setError('');
    setMediaNotice('');
    setMediaUploading(true);
    try {
      const response = await fetch(`${api}/admin/question-media`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_data_url: await fileAsDataUrl(file) }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const { image_url: imageUrl } = (await response.json()) as { image_url: string };
      if (destination === 'solution') {
        setForm((current) => ({
          ...current,
          solutionImages: [current.solutionImages.trim(), imageUrl].filter(Boolean).join('\n'),
        }));
        setMediaNotice('Solution image uploaded and added to this version.');
        return;
      }
      const examples = parseJson(form.examples);
      if (!Array.isArray(examples) || examples.length === 0 || !examples[exampleImageIndex]) {
        throw new Error('Add an example in the JSON array before attaching an image.');
      }
      examples[exampleImageIndex] = { ...examples[exampleImageIndex], image_url: imageUrl };
      update('examples', JSON.stringify(examples, null, 2));
      setMediaNotice(`Image added to example ${exampleImageIndex + 1}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not upload the image.');
    } finally {
      setMediaUploading(false);
    }
  };
  useEffect(() => {
    fetch(`${api}/admin/categories`, { headers: authHeaders(token) })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        const values = await response.json();
        setCategories(values);
        setForm((current) => ({
          ...current,
          categoryId: current.categoryId || values[0]?.id || '',
        }));
      })
      .catch((reason: Error) => setError(reason.message));
  }, [token]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      const payload = makeQuestionPayload(form);
      const url =
        initial && !versionOf
          ? `${api}/admin/question-versions/${initial.question_version_id}`
          : versionOf
            ? `${api}/admin/questions/${versionOf}/versions`
            : `${api}/admin/questions`;
      const response = await fetch(url, {
        method: initial && !versionOf ? 'PUT' : 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify(initial || versionOf ? payload : { ...payload, slug: form.slug }),
      });
      if (!response.ok) throw new Error(await readError(response));
      onDone();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save question.');
    } finally {
      setSaving(false);
    }
  };
  const field = (
    label: string,
    key: TextQuestionFormKey,
    props: { type?: string; placeholder?: string } = {},
  ) => (
    <label>
      {label}
      <input
        type={props.type ?? 'text'}
        value={form[key]}
        placeholder={props.placeholder}
        onChange={(e) => update(key, e.target.value)}
        required={['slug', 'title'].includes(key)}
      />
    </label>
  );
  const area = (label: string, key: TextQuestionFormKey, placeholder = '') => (
    <label className="wide">
      {label}
      <textarea
        value={form[key]}
        placeholder={placeholder}
        onChange={(e) => update(key, e.target.value)}
      />
    </label>
  );
  const updateTest = (
    kind: 'publicTests' | 'hiddenTests',
    index: number,
    key: keyof TestCaseFormValue,
    value: string,
  ) => {
    setForm((current) => ({
      ...current,
      [kind]: current[kind].map((test, testIndex) =>
        testIndex === index ? { ...test, [key]: value } : test,
      ),
    }));
  };
  const addTest = (kind: 'publicTests' | 'hiddenTests') => {
    setForm((current) => ({
      ...current,
      [kind]: [...current[kind], { input: '[]', output: '[]' }],
    }));
  };
  const removeTest = (kind: 'publicTests' | 'hiddenTests', index: number) => {
    setForm((current) => ({
      ...current,
      [kind]:
        current[kind].length > 1
          ? current[kind].filter((_, testIndex) => testIndex !== index)
          : current[kind],
    }));
  };
  const testEditor = (kind: 'publicTests' | 'hiddenTests', label: string) => (
    <section className="test-editor wide">
      <div className="test-editor-heading">
        <div>
          <h4>{label}</h4>
          <p>
            {kind === 'publicTests'
              ? 'Visible when a learner runs sample tests.'
              : 'Used only during secure submission evaluation.'}
          </p>
        </div>
        <button type="button" onClick={() => addTest(kind)}>
          + Add test
        </button>
      </div>
      {form[kind].map((test, index) => (
        <div className="test-case-row" key={`${kind}-${index}`}>
          <b>Test {index + 1}</b>
          <label>
            Input (JSON)
            <textarea
              value={test.input}
              onChange={(event) => updateTest(kind, index, 'input', event.target.value)}
              required
            />
          </label>
          <label>
            Expected output (JSON)
            <textarea
              value={test.output}
              onChange={(event) => updateTest(kind, index, 'output', event.target.value)}
              required
            />
          </label>
          <button
            type="button"
            className="remove-test"
            disabled={form[kind].length === 1}
            onClick={() => removeTest(kind, index)}
          >
            Remove
          </button>
        </div>
      ))}
    </section>
  );
  let tracePreview: Record<string, unknown>[] = [];
  let tracePreviewError = '';
  try {
    const parsed = parseJson(form.solutionTrace);
    if (!Array.isArray(parsed) || parsed.some((step) => !step || typeof step !== 'object')) {
      throw new Error();
    }
    tracePreview = parsed as Record<string, unknown>[];
  } catch {
    tracePreviewError =
      'Enter a JSON array of visual states. Each item needs a positive integer "step".';
  }
  let selectedExampleImage = '';
  try {
    const examples = parseJson(form.examples);
    const candidate = Array.isArray(examples) ? examples[exampleImageIndex]?.image_url : null;
    selectedExampleImage = typeof candidate === 'string' ? candidate : '';
  } catch {
    // The JSON textarea displays the validation issue when an author saves it.
  }
  const solutionImagePreviews = form.solutionImages
    .split('\n')
    .map((url) => url.trim())
    .filter(Boolean);
  return (
    <section className="editor">
      <div className="section-title">
        <div>
          <p className="eyebrow">QUESTION AUTHORING</p>
          <h2>
            {versionOf ? 'Create next version' : initial ? 'Edit draft version' : 'New question'}
          </h2>
        </div>
        <button className="outline" type="button" onClick={onDone}>
          Cancel
        </button>
      </div>
      <form className="question-form" onSubmit={submit}>
        {versionOf ? (
          <p className="form-note">
            This creates an immutable next version; historical assignments keep their current
            version.
          </p>
        ) : (
          !initial && field('URL slug', 'slug', { placeholder: 'two-sum' })
        )}
        {field('Title', 'title', { placeholder: 'Two Sum' })}
        <label>
          Category
          <select
            value={form.categoryId}
            onChange={(event) => update('categoryId', event.target.value)}
            required
          >
            <option value="">Select a category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select value={form.level} onChange={(e) => update('level', e.target.value)}>
            <option value="rookie">Rookie</option>
            <option value="hacker">Hacker</option>
            <option value="architect">Architect</option>
          </select>
        </label>
        <label>
          Difficulty
          <select value={form.difficulty} onChange={(e) => update('difficulty', e.target.value)}>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        {area('Problem statement (Markdown)', 'statement')}
        {area('Examples (JSON array)', 'examples', '[{"input": [2,7], "output": 9}]')}
        <section className="media-uploader wide">
          <div>
            <b>Example illustration</b>
            <p>
              Upload an optional visual for an example. The image URL is added to the selected JSON
              example.
            </p>
          </div>
          <label>
            Attach to example
            <select
              value={exampleImageIndex}
              onChange={(event) => setExampleImageIndex(Number(event.target.value))}
            >
              {(() => {
                try {
                  const examples = parseJson(form.examples);
                  return Array.isArray(examples) ? (
                    examples.map((_, index) => (
                      <option key={index} value={index}>
                        Example {index + 1}
                      </option>
                    ))
                  ) : (
                    <option value={0}>Add an example first</option>
                  );
                } catch {
                  return <option value={0}>Fix example JSON first</option>;
                }
              })()}
            </select>
          </label>
          <label className="media-upload-control">
            <span>{mediaUploading ? 'Uploading image…' : 'Upload example image'}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={mediaUploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadImage(file, 'example');
                event.target.value = '';
              }}
            />
          </label>
          {selectedExampleImage && (
            <div className="media-preview">
              <img
                src={mediaAssetUrl(selectedExampleImage)}
                alt={`Preview for example ${exampleImageIndex + 1}`}
              />
              <small>Image attached to example {exampleImageIndex + 1}</small>
            </div>
          )}
        </section>
        {area('Constraints (Markdown)', 'constraints')}
        <h3 className="wide">Starter code</h3>
        {area('Python', 'starterPython')}
        {area('JavaScript', 'starterJavascript')}
        <h3 className="wide">Tests</h3>
        {testEditor('publicTests', 'Public test cases')}
        {testEditor('hiddenTests', 'Hidden test cases')}
        <h3 className="wide">Hints and solution</h3>
        {area('Hint 1', 'hintOne')}
        {area('Hint 2', 'hintTwo')}
        {area('Hint 3', 'hintThree')}
        {area('Reference solution — Python', 'solutionPython')}
        {area('Reference solution — JavaScript', 'solutionJavascript')}
        {area('Legacy explanation (optional)', 'explanation')}
        <h3 className="wide">Bilingual learning path</h3>
        {area('English explanation', 'explanationEnglish', 'Explain the approach in English.')}
        {area('Malayalam explanation', 'explanationMalayalam', 'മലയാളത്തിൽ പരിഹാരം വിശദീകരിക്കുക.')}
        {field('YouTube solution walkthrough (optional)', 'solutionVideoUrl', {
          placeholder: 'https://www.youtube.com/watch?v=…',
        })}
        {area(
          'Solution image URLs (one per line)',
          'solutionImages',
          'Upload below, or paste image URLs.',
        )}
        <section className="media-uploader wide">
          <div>
            <b>Solution visuals</b>
            <p>These optional images appear in the learner&apos;s unlocked solution review.</p>
          </div>
          <label className="media-upload-control">
            <span>{mediaUploading ? 'Uploading image…' : 'Upload solution image'}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={mediaUploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadImage(file, 'solution');
                event.target.value = '';
              }}
            />
          </label>
          {solutionImagePreviews.length > 0 && (
            <div className="media-preview media-preview-gallery">
              {solutionImagePreviews.map((url, index) => (
                <img key={url} src={mediaAssetUrl(url)} alt={`Solution image ${index + 1}`} />
              ))}
            </div>
          )}
        </section>
        {mediaNotice && <p className="form-note wide">{mediaNotice}</p>}
        <p className="form-note">
          Each walkthrough step is plain JSON: <code>step</code>, <code>array</code>,{' '}
          <code>cursor</code>, <code>note_en</code>, and <code>note_ml</code>. The same player
          renders every question.
        </p>
        {area(
          'Solution walkthrough trace (JSON)',
          'solutionTrace',
          '[{"step":1,"array":[1,2,4,5],"cursor":0,"note_en":"Compare index 0 and 1.","note_ml":"index 0-ഉം 1-ഉം താരതമ്യം ചെയ്യുക."}]',
        )}
        <TracePlaybackPreview trace={tracePreview} error={tracePreviewError} />
        {area('Per-step notes — English (one note per line)', 'solutionNotesEnglish')}
        {area('Per-step notes — Malayalam (one note per line)', 'solutionNotesMalayalam')}
        {area('Complexity notes', 'complexity')}
        {area(
          'Alternative approaches (JSON array)',
          'alternatives',
          '[{"title":"Brute force","summary_markdown":"...","time_complexity":"O(n²)","space_complexity":"O(1)"}]',
        )}
        {error && <p className="error wide">{error}</p>}
        <div className="wide editor-actions">
          <button disabled={saving}>
            {saving
              ? 'Saving…'
              : initial && !versionOf
                ? 'Save draft'
                : versionOf
                  ? 'Create version'
                  : 'Create draft'}
          </button>
        </div>
      </form>
    </section>
  );
}

function QuestionBank({ token }: { token: string }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [status, setStatus] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<QuestionDetail | null>(null);
  const [editor, setEditor] = useState<'new' | 'edit' | 'version' | null>(null);
  const [notice, setNotice] = useState('');
  const load = async () => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (difficulty) params.set('difficulty', difficulty);
    if (categoryId) params.set('category_id', categoryId);
    const response = await fetch(`${api}/admin/questions?${params}`, {
      headers: authHeaders(token),
    });
    if (!response.ok) return setNotice(await readError(response));
    setQuestions(await response.json());
  };
  useEffect(() => {
    void load();
  }, [status, difficulty, categoryId]);
  useEffect(() => {
    fetch(`${api}/admin/categories`, { headers: authHeaders(token) })
      .then((response) => response.json())
      .then(setCategories)
      .catch(() => undefined);
  }, [token]);
  const open = async (question: Question) => {
    const response = await fetch(`${api}/admin/question-versions/${question.question_version_id}`, {
      headers: authHeaders(token),
    });
    if (!response.ok) return setNotice(await readError(response));
    setSelected(await response.json());
    setEditor(null);
  };
  const transition = async (action: 'validate' | 'publish') => {
    if (!selected) return;
    const response = await fetch(
      `${api}/admin/question-versions/${selected.question_version_id}/${action}`,
      { method: 'POST', headers: authHeaders(token) },
    );
    if (!response.ok) return setNotice(await readError(response));
    setSelected(await response.json());
    setNotice(
      action === 'validate' ? 'Question is ready to schedule.' : 'Question has been published.',
    );
    void load();
  };
  const done = () => {
    setEditor(null);
    setSelected(null);
    void load();
  };
  if (editor)
    return (
      <QuestionEditor
        token={token}
        initial={editor === 'new' ? undefined : (selected ?? undefined)}
        versionOf={editor === 'version' ? selected?.question_id : undefined}
        onDone={done}
      />
    );
  if (selected)
    return (
      <section className="detail">
        <div className="section-title">
          <div>
            <p className="eyebrow">QUESTION VERSION {selected.version_number}</p>
            <h2>{selected.title}</h2>
            <p className="subtitle">
              {selected.topic} · {selected.level} · difficulty {selected.difficulty}
            </p>
          </div>
          <button className="outline" onClick={() => setSelected(null)}>
            Back to list
          </button>
        </div>
        <div className="status-line">
          <mark className={selected.status}>{selected.status}</mark>
          {selected.status === 'draft' && (
            <>
              <button onClick={() => setEditor('edit')}>Edit draft</button>
              <button className="secondary" onClick={() => void transition('validate')}>
                Validate & mark ready
              </button>
            </>
          )}
          {selected.status === 'ready' && (
            <button onClick={() => void transition('publish')}>Publish version</button>
          )}
          <button className="outline" onClick={() => setEditor('version')}>
            Create next version
          </button>
        </div>
        {notice && <p className="error">{notice}</p>}
        <article className="detail-card">
          <h3>Validation checklist</h3>
          <p>
            Public tests: {selected.public_tests.length} · Hidden tests:{' '}
            {selected.hidden_tests.length} · Hints: {selected.hints.length}
          </p>
          <p>
            Solution: {Object.keys(selected.solution_code).length ? 'provided' : 'missing'} ·
            English: {selected.explanation_en ? 'provided' : 'missing'} · Malayalam:{' '}
            {selected.explanation_ml ? 'provided' : 'missing'} · Trace:{' '}
            {selected.solution_trace.length} step(s) · Complexity:{' '}
            {selected.complexity_notes ? 'provided' : 'missing'}
          </p>
        </article>
        <article className="detail-card">
          <h3>Problem statement</h3>
          <pre>{selected.statement_markdown}</pre>
        </article>
      </section>
    );
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">CONTENT LIBRARY</p>
          <h2>Question bank</h2>
          <p className="subtitle">Author, validate, version, and publish coding challenges.</p>
        </div>
        <button onClick={() => setEditor('new')}>+ New question</button>
      </div>
      <section className="filters">
        <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {['draft', 'ready', 'published', 'scheduled', 'retired'].map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
        <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
          <option value="">All difficulties</option>
          {[1, 2, 3, 4, 5].map((value) => (
            <option key={value} value={value}>
              Difficulty {value}
            </option>
          ))}
        </select>
      </section>
      {notice && <p className="error">{notice}</p>}
      <section className="data-table">
        <div className="table-head">
          <span>Question</span>
          <span>Category</span>
          <span>Level</span>
          <span>Status</span>
          <span />
        </div>
        {questions.length === 0 && (
          <p className="empty">No question versions match these filters.</p>
        )}
        {questions.map((question) => (
          <button
            className="table-row"
            onClick={() => void open(question)}
            key={question.question_version_id}
          >
            <b>
              {question.title}
              <small>
                v{question.version_number} · difficulty {question.difficulty}
              </small>
            </b>
            <span>{question.topic}</span>
            <span>{question.level}</span>
            <mark className={question.status}>{question.status}</mark>
            <span>Open →</span>
          </button>
        ))}
      </section>
    </>
  );
}

const categorySlug = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');

function Categories({ token }: { token: string }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [editing, setEditing] = useState<Category | null>(null);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const load = async () => {
    const response = await fetch(`${api}/admin/categories`, { headers: authHeaders(token) });
    if (!response.ok) return setNotice(await readError(response));
    setCategories(await response.json());
  };
  useEffect(() => {
    void load();
  }, [token]);
  const clear = () => {
    setEditing(null);
    setName('');
    setSlug('');
    setDescription('');
    setNotice('');
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setNotice('');
    const response = await fetch(
      editing ? `${api}/admin/categories/${editing.id}` : `${api}/admin/categories`,
      {
        method: editing ? 'PUT' : 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, slug, description: description || null }),
      },
    );
    setSaving(false);
    if (!response.ok) return setNotice(await readError(response));
    clear();
    await load();
  };
  const remove = async (category: Category) => {
    if (!confirm(`Delete the ${category.name} category?`)) return;
    const response = await fetch(`${api}/admin/categories/${category.id}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
    if (!response.ok) return setNotice(await readError(response));
    setNotice('Category deleted.');
    await load();
  };
  const selectCategory = (category: Category) => {
    setEditing(category);
    setName(category.name);
    setSlug(category.slug);
    setDescription(category.description ?? '');
    setNotice('');
  };
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">QUESTION TAXONOMY</p>
          <h2>Categories</h2>
          <p className="subtitle">
            Manage the categories authors assign to every question version.
          </p>
        </div>
        <span className="count-pill">{categories.length} categories</span>
      </div>
      <section className="category-layout">
        <form className="category-form" onSubmit={submit}>
          <h3>{editing ? `Edit ${editing.name}` : 'New category'}</h3>
          <label>
            Name
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                if (!editing) setSlug(categorySlug(event.target.value));
              }}
              placeholder="Arrays"
              required
            />
          </label>
          <label>
            URL slug
            <input
              value={slug}
              onChange={(event) => setSlug(categorySlug(event.target.value))}
              placeholder="arrays"
              required
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Array traversal, indexing, and transformations."
            />
          </label>
          {notice && <p className="error">{notice}</p>}
          <div>
            <button disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save category' : 'Create category'}
            </button>
            {editing && (
              <button type="button" className="outline" onClick={clear}>
                Cancel
              </button>
            )}
          </div>
        </form>
        <section className="data-table categories-table">
          <div className="table-head">
            <span>Category</span>
            <span>Slug</span>
            <span>Questions</span>
            <span>Actions</span>
          </div>
          {categories.length === 0 && (
            <p className="empty">
              Create categories such as Arrays, Linked Lists, and Trees to begin authoring
              questions.
            </p>
          )}
          {categories.map((category) => (
            <div className="table-row" key={category.id}>
              <b>
                {category.name}
                <small>{category.description || 'No description'}</small>
              </b>
              <span>{category.slug}</span>
              <span>{category.question_count} versions</span>
              <span className="row-actions">
                <button onClick={() => selectCategory(category)}>Edit</button>
                <button
                  disabled={category.question_count > 0}
                  title={
                    category.question_count
                      ? 'Reassign all question versions before deleting this category.'
                      : 'Delete category'
                  }
                  onClick={() => void remove(category)}
                >
                  Delete
                </button>
              </span>
            </div>
          ))}
        </section>
      </section>
    </>
  );
}

function Schedule({ token }: { token: string }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [level, setLevel] = useState('rookie');
  const [versionId, setVersionId] = useState('');
  const [date, setDate] = useState(today());
  const [notice, setNotice] = useState('');
  const load = async () => {
    const bank = await fetch(`${api}/admin/questions`, { headers: authHeaders(token) });
    if (!bank.ok) return setNotice(await readError(bank));
    setQuestions(await bank.json());
  };
  useEffect(() => {
    void load();
  }, [token]);
  const eligible = questions.filter(
    (question) => ['ready', 'published'].includes(question.status) && question.level === level,
  );
  useEffect(() => {
    if (!eligible.some((question) => question.question_version_id === versionId))
      setVersionId(eligible[0]?.question_version_id ?? '');
  }, [level, questions]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setNotice('');
    if (!versionId)
      return setNotice('Create and validate a question for this level before scheduling it.');
    const response = await fetch(`${api}/admin/daily-assignments`, {
      method: 'POST',
      headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assignment_date: date,
        level,
        question_version_id: versionId,
      }),
    });
    if (!response.ok) return setNotice(await readError(response));
    setNotice('Daily challenge scheduled. Historical assignments remain locked to this version.');
    void load();
  };
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">DAILY CHALLENGES</p>
          <h2>Schedule a challenge</h2>
          <p className="subtitle">
            Assign a ready version per date and level. Learners choose their editor language.
          </p>
        </div>
      </div>
      <section className="schedule-layout schedule-create-layout">
        <form className="schedule-form" onSubmit={submit}>
          <h3>Assign challenge</h3>
          <label>
            Date
            <input
              type="date"
              min={today()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </label>
          <label>
            Level
            <select value={level} onChange={(e) => setLevel(e.target.value)}>
              {['rookie', 'hacker', 'architect'].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Ready question version
            <select
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              disabled={!eligible.length}
            >
              <option value="">Select a version</option>
              {eligible.map((question) => (
                <option value={question.question_version_id} key={question.question_version_id}>
                  {question.title} · v{question.version_number}
                </option>
              ))}
            </select>
          </label>
          <button>Schedule challenge</button>
          {notice && <p className={notice.includes('scheduled') ? 'success' : 'error'}>{notice}</p>}
        </form>
        <section className="calendar">
          <div className="schedule-info">
            <p className="eyebrow">SCHEDULING RULES</p>
            <h3>Plan with confidence.</h3>
            <p>Only Ready or Published versions that match the selected level can be assigned.</p>
            <p>
              One question version can be assigned for each date and level. Learners can solve it in
              Python or JavaScript.
            </p>
            <p>Past schedules remain locked to their original question version.</p>
            <p className="schedule-tip">
              Use the <b>Scheduled</b> submenu to filter and review your calendar.
            </p>
          </div>
        </section>
      </section>
    </>
  );
}

function ScheduledAssignments({ token }: { token: string }) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [days, setDays] = useState('30');
  const [startDate, setStartDate] = useState(today());
  const [level, setLevel] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    const params = new URLSearchParams({ days, start_date: startDate });
    if (level) params.set('level', level);
    fetch(`${api}/admin/daily-assignments/preview?${params}`, { headers: authHeaders(token) })
      .then(async (response) => {
        if (!response.ok) return setNotice(await readError(response));
        setAssignments(await response.json());
        setNotice('');
      })
      .catch(() => setNotice('Could not load scheduled challenges.'));
  }, [token, days, startDate, level]);
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">DAILY CHALLENGES</p>
          <h2>Scheduled challenges</h2>
          <p className="subtitle">Review future assignments across every learner level.</p>
        </div>
        <span className="count-pill">{assignments.length} scheduled</span>
      </div>
      <section className="filters schedule-filters">
        <label>
          Preview
          <select value={days} onChange={(e) => setDays(e.target.value)}>
            {[7, 30, 90].map((value) => (
              <option key={value} value={value}>
                {value} days
              </option>
            ))}
          </select>
        </label>
        <label>
          Starts
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          Level
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">All levels</option>
            {['rookie', 'hacker', 'architect'].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </section>
      {notice && <p className="error">{notice}</p>}
      <section className="data-table scheduled-table">
        <div className="table-head">
          <span>Date</span>
          <span>Challenge</span>
          <span>Topic</span>
          <span>Level</span>
        </div>
        {assignments.length === 0 && (
          <p className="empty">No scheduled challenges match these filters.</p>
        )}
        {assignments.map((assignment) => (
          <div className="table-row" key={assignment.id}>
            <b>{assignment.assignment_date}</b>
            <span>{assignment.title}</span>
            <span>{assignment.topic}</span>
            <mark>{assignment.level}</mark>
          </div>
        ))}
      </section>
    </>
  );
}

function Users({ token, group }: { token: string; group: 'user' | 'admin' }) {
  const [users, setUsers] = useState<OperationalUser[]>([]);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selected, setSelected] = useState<OperationalUser | null>(null);
  const [activity, setActivity] = useState<UserActivity | null>(null);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [actionPending, setActionPending] = useState('');
  const [notice, setNotice] = useState('');
  const load = () => {
    const params = new URLSearchParams({ page_size: '100' });
    if (query.trim()) params.set('q', query.trim());
    if (statusFilter) params.set('is_active', statusFilter);
    if (group === 'user') params.set('role', 'user');
    fetch(`${api}/admin/operations/users?${params}`, { headers: authHeaders(token) })
      .then(async (response) => {
        if (!response.ok) return setNotice(await readError(response));
        setUsers((await response.json()).items);
      })
      .catch(() => setNotice('The API is unavailable.'));
  };
  useEffect(load, [token, group, statusFilter]);
  useEffect(() => {
    const timer = setTimeout(load, 280);
    return () => clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    fetch(`${api}/auth/me`, { headers: authHeaders(token) })
      .then((response) => response.json())
      .then((profile) => setIsSuperAdmin(profile.role === 'super_admin'))
      .catch(() => undefined);
  }, [token]);
  const adminRoles = ['moderator', 'admin', 'super_admin'];
  const groupedUsers = users.filter((user) =>
    group === 'admin' ? adminRoles.includes(user.role) : user.role === 'user',
  );
  const openActivity = async (user: OperationalUser) => {
    setSelected(user);
    setActivity(null);
    const response = await fetch(`${api}/admin/operations/users/${user.id}/activity`, {
      headers: authHeaders(token),
    });
    if (!response.ok) return setNotice(await readError(response));
    setActivity(await response.json());
  };
  const accountAction = async (action: 'suspend' | 'restore' | 'revoke-sessions') => {
    if (!selected) return;
    setActionPending(action);
    const response = await fetch(`${api}/admin/operations/users/${selected.id}/${action}`, {
      method: 'POST',
      headers: authHeaders(token),
    });
    setActionPending('');
    if (!response.ok) return setNotice(await readError(response));
    const result = await response.json();
    setNotice(result.message);
    setSelected({ ...selected, ...result });
    load();
  };
  const changeRole = async (role: string) => {
    if (!selected) return;
    setActionPending('role');
    const response = await fetch(`${api}/admin/operations/users/${selected.id}/role`, {
      method: 'PATCH',
      headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    setActionPending('');
    if (!response.ok) return setNotice(await readError(response));
    const result = await response.json();
    setNotice(result.message);
    setSelected({ ...selected, ...result });
    load();
  };
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">ACCOUNT DIRECTORY</p>
          <h2>{group === 'user' ? 'Users' : 'Administrators'}</h2>
          <p className="subtitle">
            {group === 'user'
              ? 'View learner accounts and their current challenge level.'
              : 'View the accounts allowed to manage Codele.'}
          </p>
        </div>
        <span className="count-pill">
          {groupedUsers.length} {group === 'user' ? 'users' : 'admins'}
        </span>
      </div>
      <section className="filters">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            group === 'user' ? 'Search user name or email' : 'Search admin name or email'
          }
        />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All account states</option>
          <option value="true">Active</option>
          <option value="false">Suspended</option>
        </select>
      </section>
      {notice && (
        <p className={notice.includes('cannot') || notice.includes('failed') ? 'error' : 'success'}>
          {notice}
        </p>
      )}
      <section className="data-table users-table">
        <div className="table-head">
          <span>User</span>
          <span>Role</span>
          <span>Level</span>
          <span>Status</span>
          <span>Joined</span>
        </div>
        {groupedUsers.length === 0 && (
          <p className="empty">No {group === 'user' ? 'users' : 'administrators'} found.</p>
        )}
        {groupedUsers.map((user) => (
          <button className="table-row" key={user.id} onClick={() => openActivity(user)}>
            <b>
              {user.display_name}
              <small>{user.email}</small>
            </b>
            <span className="role">{user.role.replace('_', ' ')}</span>
            <span>{user.level}</span>
            <mark className={user.is_active ? 'published' : 'retired'}>
              {user.is_active ? 'active' : 'inactive'}
            </mark>
            <span>
              {user.xp_total} XP · {new Date(user.created_at).toLocaleDateString()}
            </span>
          </button>
        ))}
      </section>
      {selected && (
        <section className="detail-card operations-detail">
          <div className="section-title">
            <div>
              <p className="eyebrow">ACCOUNT ACTIVITY</p>
              <h3>{selected.display_name}</h3>
              <p>
                {selected.email} · session version {selected.session_version}
              </p>
            </div>
            <button
              className="outline"
              onClick={() => {
                setSelected(null);
                setActivity(null);
              }}
            >
              Close
            </button>
          </div>
          <div className="operations-kpis">
            <span>
              <b>{selected.xp_total}</b> XP
            </span>
            <span>
              <b>{selected.current_streak}</b> day streak
            </span>
            <span>
              <b>{selected.submission_count}</b> submissions
            </span>
            <span>
              <b>{selected.badge_count}</b> badges
            </span>
          </div>
          <div className="account-actions">
            <button
              className="secondary"
              disabled={Boolean(actionPending)}
              onClick={() => accountAction(selected.is_active ? 'suspend' : 'restore')}
            >
              {selected.is_active ? 'Suspend account' : 'Restore account'}
            </button>
            <button
              disabled={Boolean(actionPending)}
              onClick={() => accountAction('revoke-sessions')}
            >
              Revoke sessions
            </button>
            {isSuperAdmin && selected.role !== 'super_admin' && (
              <label>
                Role{' '}
                <select
                  value={selected.role}
                  disabled={actionPending === 'role'}
                  onChange={(event) => changeRole(event.target.value)}
                >
                  <option value="user">User</option>
                  <option value="moderator">Moderator</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
            )}
          </div>
          {activity ? (
            <div className="activity-grid">
              <article>
                <h4>Recent submissions</h4>
                {activity.recent_submissions.length ? (
                  activity.recent_submissions.map((item) => (
                    <p key={item.id}>
                      <mark className={item.status}>{item.status}</mark> {item.language} · attempt{' '}
                      {item.attempt_number}
                    </p>
                  ))
                ) : (
                  <p>No submissions yet.</p>
                )}
              </article>
              <article>
                <h4>XP ledger</h4>
                {activity.recent_xp_transactions.length ? (
                  activity.recent_xp_transactions.map((item) => (
                    <p key={item.id}>
                      <b>+{item.amount}</b> {item.reason.replaceAll('_', ' ')}
                    </p>
                  ))
                ) : (
                  <p>No XP events yet.</p>
                )}
              </article>
              <article>
                <h4>Streak calendar</h4>
                <div className="streak-dots">
                  {activity.streak_calendar.map((item) => (
                    <i
                      key={item.date}
                      title={item.date}
                      className={item.shielded ? 'shielded' : ''}
                    />
                  ))}
                </div>
                <p>
                  {activity.streak_calendar.length
                    ? 'Most recent qualifying days.'
                    : 'No streak days yet.'}
                </p>
              </article>
              <article>
                <h4>Badges</h4>
                <p>
                  {activity.badges.length
                    ? activity.badges.map((badge) => `${badge.icon} ${badge.name}`).join(' · ')
                    : 'No badges awarded yet.'}
                </p>
              </article>
            </div>
          ) : (
            <p className="empty">Loading account activity…</p>
          )}
        </section>
      )}
    </>
  );
}

function Moderation({ token }: { token: string }) {
  const [reports, setReports] = useState<ModerationReport[]>([]);
  const [statusFilter, setStatusFilter] = useState('open');
  const [notice, setNotice] = useState('');
  const load = () => {
    const suffix = statusFilter ? `?status=${statusFilter}` : '';
    fetch(`${api}/admin/moderation-reports${suffix}`, { headers: authHeaders(token) })
      .then(async (response) => {
        if (!response.ok) return setNotice(await readError(response));
        setReports((await response.json()).items);
      })
      .catch(() => setNotice('The API is unavailable.'));
  };
  useEffect(load, [token, statusFilter]);
  const updateReport = async (report: ModerationReport, nextStatus: string) => {
    const response = await fetch(`${api}/admin/moderation-reports/${report.id}`, {
      method: 'PATCH',
      headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: nextStatus }),
    });
    if (!response.ok) return setNotice(await readError(response));
    setNotice('Report updated and audited.');
    load();
  };
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">SAFETY OPERATIONS</p>
          <h2>Moderation queue</h2>
          <p className="subtitle">Review abuse and spam reports without database access.</p>
        </div>
        <span className="count-pill">{reports.length} reports</span>
      </div>
      <section className="filters">
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All states</option>
          <option value="open">Open</option>
          <option value="reviewing">Reviewing</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </section>
      {notice && <p className="success">{notice}</p>}
      <section className="data-table moderation-table">
        <div className="table-head">
          <span>Report</span>
          <span>Reporter</span>
          <span>Account</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {reports.length === 0 && <p className="empty">No reports match this queue.</p>}
        {reports.map((report) => (
          <div className="table-row" key={report.id}>
            <b>
              {report.reason}
              <small>{report.details || 'No extra details'}</small>
            </b>
            <span>{report.reporter_display_name}</span>
            <span>{report.target_display_name}</span>
            <mark className={report.status}>{report.status}</mark>
            <span className="row-actions">
              <button onClick={() => updateReport(report, 'reviewing')}>Review</button>
              <button onClick={() => updateReport(report, 'resolved')}>Resolve</button>
            </span>
          </div>
        ))}
      </section>
    </>
  );
}

function Analytics({ token }: { token: string }) {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [status, setStatus] = useState('');
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditQuery, setAuditQuery] = useState('');
  const [auditAction, setAuditAction] = useState('');
  const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<Submission | null>(null);
  useEffect(() => {
    const suffix = status ? `?status=${status}` : '';
    Promise.all([
      fetch(`${api}/admin/submissions${suffix}`, { headers: authHeaders(token) }),
      fetch(`${api}/admin/analytics/overview?days=30`, { headers: authHeaders(token) }),
    ])
      .then(async ([submissionsResponse, analyticsResponse]) => {
        if (!submissionsResponse.ok || !analyticsResponse.ok) {
          throw new Error('Could not load analytics.');
        }
        setSubmissions(await submissionsResponse.json());
        setOverview(await analyticsResponse.json());
      })
      .catch((error: Error) => setNotice(error.message));
  }, [token, status]);
  const loadAudit = () => {
    const params = new URLSearchParams({ page_size: '50' });
    if (auditQuery.trim()) params.set('q', auditQuery.trim());
    if (auditAction) params.set('action', auditAction);
    fetch(`${api}/admin/audit-logs?${params}`, { headers: authHeaders(token) })
      .then(async (response) => {
        if (!response.ok) return setNotice(await readError(response));
        setAuditLogs((await response.json()).items);
      })
      .catch(() => setNotice('The API is unavailable.'));
  };
  useEffect(loadAudit, [token, auditAction]);
  useEffect(() => {
    const timer = setTimeout(loadAudit, 280);
    return () => clearTimeout(timer);
  }, [auditQuery]);
  const exportAudit = async () => {
    const params = new URLSearchParams();
    if (auditQuery.trim()) params.set('q', auditQuery.trim());
    if (auditAction) params.set('action', auditAction);
    const response = await fetch(`${api}/admin/audit-logs/export?${params}`, {
      headers: authHeaders(token),
    });
    if (!response.ok) return setNotice(await readError(response));
    const href = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'codele-admin-audit-logs.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  };
  const passed = submissions.filter((submission) => submission.status === 'passed').length;
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">PLATFORM HEALTH</p>
          <h2>Analytics and audit</h2>
          <p className="subtitle">
            Server-calculated engagement, execution reliability, and sensitive admin actions.
          </p>
        </div>
        <span className="count-pill">
          {passed}/{submissions.length} passed
        </span>
      </div>
      {overview && (
        <section className="analytics-kpis">
          <article>
            <span>DAU</span>
            <b>{overview.dau}</b>
          </article>
          <article>
            <span>WAU</span>
            <b>{overview.wau}</b>
          </article>
          <article>
            <span>MAU</span>
            <b>{overview.mau}</b>
          </article>
          <article>
            <span>Completion</span>
            <b>{overview.completion_rate}%</b>
          </article>
          <article>
            <span>Failures</span>
            <b>{overview.execution_failure_rate}%</b>
          </article>
          <article>
            <span>Queue</span>
            <b>{overview.queue_depth}</b>
          </article>
        </section>
      )}
      {overview && (
        <section className="daily-chart">
          <div>
            <h3>30-day activity</h3>
            <p>
              {overview.evaluated_submissions} evaluated submissions · average attempt{' '}
              {overview.average_attempt_number}
            </p>
          </div>
          <div className="bars">
            {overview.daily.map((day) => (
              <span
                key={day.date}
                title={`${day.date}: ${day.submissions} submissions`}
                style={{ height: `${Math.max(8, Math.min(100, day.submissions * 12))}%` }}
              />
            ))}
          </div>
        </section>
      )}
      <section className="filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All states</option>
          {['queued', 'running', 'passed', 'failed', 'error'].map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
      </section>
      {notice && <p className="error">{notice}</p>}
      <section className="data-table submissions-table">
        <div className="table-head">
          <span>Developer</span>
          <span>Language</span>
          <span>Result</span>
          <span>Tests</span>
          <span>Submitted</span>
        </div>
        {submissions.length === 0 && <p className="empty">No submissions found.</p>}
        {submissions.map((submission) => (
          <button className="table-row" key={submission.id} onClick={() => setSelected(submission)}>
            <b>
              {submission.user_display_name}
              <small>{submission.user_email}</small>
            </b>
            <span>{submission.language}</span>
            <mark className={submission.status}>{submission.status}</mark>
            <span>
              {submission.passed_test_count ?? '—'} / {submission.total_test_count ?? '—'}
            </span>
            <span>{dateTime(submission.created_at)}</span>
          </button>
        ))}
      </section>
      {selected && (
        <section className="detail-card submission-detail">
          <div className="section-title">
            <div>
              <p className="eyebrow">SUBMISSION DETAILS</p>
              <h3>{selected.user_display_name}</h3>
            </div>
            <button className="outline" onClick={() => setSelected(null)}>
              Close
            </button>
          </div>
          <p>
            {selected.status} · {selected.language} · {selected.passed_test_count ?? '—'} /{' '}
            {selected.total_test_count ?? '—'} tests passed
          </p>
          <pre>
            {JSON.stringify(
              selected.test_results ?? { message: 'Execution has not finished.' },
              null,
              2,
            )}
          </pre>
        </section>
      )}
      <section className="audit-section">
        <div className="section-title">
          <div>
            <p className="eyebrow">IMMUTABLE ADMIN AUDIT LOG</p>
            <h3>Operations trace</h3>
            <p>
              Every account and report action includes an actor, target, timestamp, and before/after
              values.
            </p>
          </div>
          <button onClick={exportAudit}>Export CSV</button>
        </div>
        <section className="filters">
          <input
            value={auditQuery}
            onChange={(event) => setAuditQuery(event.target.value)}
            placeholder="Search actor or target"
          />
          <select value={auditAction} onChange={(event) => setAuditAction(event.target.value)}>
            <option value="">All actions</option>
            <option value="user.suspended">Account suspended</option>
            <option value="user.restored">Account restored</option>
            <option value="user.sessions_revoked">Sessions revoked</option>
            <option value="user.role_changed">Role changed</option>
            <option value="moderation_report.updated">Report updated</option>
          </select>
        </section>
        <section className="data-table audit-table">
          <div className="table-head">
            <span>Action</span>
            <span>Actor</span>
            <span>Target</span>
            <span>Change</span>
            <span>Time</span>
          </div>
          {auditLogs.length === 0 && (
            <p className="empty">No audited operations match these filters.</p>
          )}
          {auditLogs.map((log) => (
            <div className="table-row" key={log.id}>
              <b>{log.action.replaceAll('_', ' ')}</b>
              <span>
                {log.actor_display_name}
                <small>{log.actor_email}</small>
              </span>
              <span>
                {log.target_type} · {log.target_id.slice(0, 8)}
              </span>
              <span>{JSON.stringify(log.metadata_json.after ?? {})}</span>
              <span>{dateTime(log.created_at)}</span>
            </div>
          ))}
        </section>
      </section>
    </>
  );
}

function Dashboard({ token }: { token: string }) {
  const initial = (location.hash.slice(1) as Page) || 'Dashboard';
  const [active, setActive] = useState<Page>(pages.includes(initial) ? initial : 'Dashboard');
  useEffect(() => {
    const onHash = () => {
      const next = location.hash.slice(1) as Page;
      if (pages.includes(next)) setActive(next);
    };
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);
  const goTo = (page: Page) => {
    location.hash = page;
    setActive(page);
  };
  const content =
    active === 'Dashboard' ? (
      <DashboardHome token={token} goTo={goTo} />
    ) : active === 'Question bank' ? (
      <QuestionBank token={token} />
    ) : active === 'Categories' ? (
      <Categories token={token} />
    ) : active === 'Schedule' ? (
      <Schedule token={token} />
    ) : active === 'Scheduled' ? (
      <ScheduledAssignments token={token} />
    ) : active === 'Users' ? (
      <Users token={token} group="user" />
    ) : active === 'Admins' ? (
      <Users token={token} group="admin" />
    ) : active === 'Moderation' ? (
      <Moderation token={token} />
    ) : (
      <Analytics token={token} />
    );
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <img src="/codele-logo.png" alt="Codele" /> codele <small>ADMIN</small>
        </div>
        <nav>
          {nav.map(([icon, label]) =>
            label === 'Schedule' ? (
              <div className="sidebar-group" key={label}>
                <button
                  className={active === 'Schedule' || active === 'Scheduled' ? 'active' : ''}
                  onClick={() => goTo('Schedule')}
                >
                  <span>{icon}</span>
                  Schedule <i>⌄</i>
                </button>
                {(active === 'Schedule' || active === 'Scheduled') && (
                  <div className="sidebar-submenu">
                    <button
                      className={active === 'Schedule' ? 'active' : ''}
                      onClick={() => goTo('Schedule')}
                    >
                      Schedule challenge
                    </button>
                    <button
                      className={active === 'Scheduled' ? 'active' : ''}
                      onClick={() => goTo('Scheduled')}
                    >
                      Scheduled list
                    </button>
                  </div>
                )}
              </div>
            ) : label === 'Users' ? (
              <div className="sidebar-group" key={label}>
                <button
                  className={active === 'Users' || active === 'Admins' ? 'active' : ''}
                  onClick={() => goTo('Users')}
                >
                  <span>{icon}</span>
                  Users <i>⌄</i>
                </button>
                {(active === 'Users' || active === 'Admins') && (
                  <div className="sidebar-submenu">
                    <button
                      className={active === 'Users' ? 'active' : ''}
                      onClick={() => goTo('Users')}
                    >
                      Users
                    </button>
                    <button
                      className={active === 'Admins' ? 'active' : ''}
                      onClick={() => goTo('Admins')}
                    >
                      Admins
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                className={active === label ? 'active' : ''}
                key={label}
                onClick={() => goTo(label)}
              >
                <span>{icon}</span>
                {label}
              </button>
            ),
          )}
        </nav>
        <div className="sidebar-foot">
          <button
            onClick={() => {
              localStorage.removeItem('codele_admin_token');
              location.reload();
            }}
          >
            ⇥ Sign out
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <button className="crumb" onClick={() => goTo('Dashboard')}>
            ‹
          </button>
          <h1>{active}</h1>
          <div className="profile">
            <span className="bell">●</span>
            <b>A</b>
          </div>
        </header>
        <main>{content}</main>
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('codele_admin_token') ?? '');
  return token ? <Dashboard token={token} /> : <SignIn onSuccess={setToken} />;
}
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
