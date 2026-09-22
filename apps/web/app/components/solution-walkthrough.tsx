'use client';

import { useEffect, useMemo, useState } from 'react';

export type SolutionTraceStep = {
  step: number;
  array?: unknown[];
  cursor?: number;
  note_en?: string;
  note_ml?: string;
  [key: string]: unknown;
};

type Props = {
  trace: SolutionTraceStep[];
  language: 'en' | 'ml';
};

type NormalizedStep = {
  step: number;
  array: unknown[];
  cursor: number | null;
  noteEn: string;
  noteMl: string;
  context: Record<string, unknown>;
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function normalizeStep(raw: SolutionTraceStep, fallbackStep: number): NormalizedStep {
  // Older traces used a nested `state` object. Flattening it here keeps every
  // previously-authored walkthrough playable while new traces stay plain JSON.
  const nested = record(raw.state);
  const merged = { ...nested, ...raw };
  const sourceArray = merged.array ?? merged.values;
  const array = Array.isArray(sourceArray)
    ? sourceArray
    : typeof merged.text === 'string'
      ? [...merged.text]
      : [];
  const possibleCursor = merged.cursor ?? merged.index ?? merged.left ?? merged.middle;
  const cursor = typeof possibleCursor === 'number' && possibleCursor >= 0 ? possibleCursor : null;
  const context = Object.fromEntries(
    Object.entries(merged).filter(
      ([key]) =>
        ![
          'step',
          'state',
          'array',
          'values',
          'text',
          'cursor',
          'index',
          'left',
          'middle',
          'note',
          'note_en',
          'note_ml',
        ].includes(key),
    ),
  );
  return {
    step: typeof merged.step === 'number' ? merged.step : fallbackStep,
    array,
    cursor,
    noteEn: typeof merged.note_en === 'string' ? merged.note_en : String(merged.note ?? ''),
    noteMl: typeof merged.note_ml === 'string' ? merged.note_ml : '',
    context,
  };
}

export function SolutionWalkthrough({ trace, language }: Props) {
  const steps = useMemo(() => trace.map(normalizeStep).sort((a, b) => a.step - b.step), [trace]);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const active = steps[index];

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [trace]);
  useEffect(() => {
    if (!playing || steps.length < 2) return;
    const timer = window.setInterval(() => {
      setIndex((current) => {
        if (current === steps.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1500 / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, steps.length]);

  if (!active) return null;
  const note = language === 'ml' && active.noteMl ? active.noteMl : active.noteEn;
  return (
    <section className="solution-walkthrough">
      <header className="solution-walkthrough-header">
        <div>
          <p className="eyebrow">SOLUTION WALKTHROUGH</p>
          <h3>Watch the algorithm think</h3>
          <p>Each step highlights the value the algorithm is currently examining.</p>
        </div>
        <label className="walkthrough-speed">
          Playback speed
          <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>
            <option value={0.5}>0.5×</option>
            <option value={1}>1×</option>
            <option value={2}>2×</option>
          </select>
        </label>
      </header>
      <div className="solution-step-tabs" role="tablist" aria-label="Walkthrough steps">
        {steps.map((step, stepIndex) => (
          <button
            key={step.step}
            className={stepIndex === index ? 'active' : ''}
            aria-selected={stepIndex === index}
            onClick={() => {
              setIndex(stepIndex);
              setPlaying(false);
            }}
          >
            Step {stepIndex + 1}
          </button>
        ))}
      </div>
      <div className="trace-stage">
        <div className="trace-stage-heading">
          <span>
            STEP {index + 1} OF {steps.length}
          </span>
          {active.cursor !== null && <b>Cursor at index {active.cursor}</b>}
        </div>
        {active.array.length > 0 ? (
          <div className="trace-array" aria-label="Array state">
            {active.array.map((value, arrayIndex) => (
              <div
                className={`trace-array-cell ${arrayIndex === active.cursor ? 'is-current' : ''}`}
                key={arrayIndex}
              >
                {arrayIndex === active.cursor && <em>cursor ↓</em>}
                <small>index {arrayIndex}</small>
                <strong>{String(value)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="trace-empty-state">This step updates the values shown below.</p>
        )}
        {Object.keys(active.context).length > 0 && (
          <div className="trace-context">
            {Object.entries(active.context).map(([key, value]) => (
              <span key={key}>
                <small>{key.replaceAll('_', ' ')}</small>
                <b>{Array.isArray(value) ? `[${value.join(', ')}]` : String(value)}</b>
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="trace-note" lang={language === 'ml' ? 'ml' : 'en'}>
        <span aria-hidden="true">✦</span>
        <p>{note || 'Move through the steps to see how the algorithm changes its state.'}</p>
      </div>
      <footer className="solution-walkthrough-controls">
        <button
          onClick={() => setIndex((current) => Math.max(0, current - 1))}
          disabled={index === 0}
        >
          ← Previous
        </button>
        <button
          className="play"
          onClick={() => setPlaying((current) => !current)}
          disabled={steps.length < 2}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
        <button
          onClick={() => setIndex((current) => Math.min(steps.length - 1, current + 1))}
          disabled={index === steps.length - 1}
        >
          Next →
        </button>
      </footer>
    </section>
  );
}
