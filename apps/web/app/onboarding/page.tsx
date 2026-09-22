'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
const questions = [
  'What is your coding experience?',
  'Which languages do you want to practise?',
  'What is your goal?',
  'How much time can you spend daily?',
];
export default function Onboarding() {
  const r = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState(['', 'Python', 'Build consistency', '15 minutes']);
  return (
    <main className="card">
      <p className="eyebrow">Step {step + 1} of 4</p>
      <h1>{questions[step]}</h1>
      <input
        value={answers[step]}
        onChange={(e) => setAnswers(answers.map((v, i) => (i === step ? e.target.value : v)))}
      />
      <button onClick={() => (step === 3 ? r.push('/dashboard') : setStep(step + 1))}>
        {step === 3 ? 'Finish' : 'Continue'}
      </button>
    </main>
  );
}
