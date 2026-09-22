'use client';

import dynamic from 'next/dynamic';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="code-editor-loading" role="status">
      Loading code editor…
    </div>
  ),
});

type CodeEditorProps = {
  language: 'python' | 'javascript';
  value: string;
  onChange: (value: string) => void;
};

export function CodeEditor({ language, value, onChange }: CodeEditorProps) {
  return (
    <div
      className="code-editor"
      aria-label={`${language === 'python' ? 'Python' : 'JavaScript'} editor`}
    >
      <MonacoEditor
        height="100%"
        language={language}
        theme="vs-dark"
        value={value}
        onChange={(nextValue) => onChange(nextValue ?? '')}
        options={{
          ariaLabel: `Your ${language === 'python' ? 'Python' : 'JavaScript'} solution code`,
          automaticLayout: true,
          bracketPairColorization: { enabled: true },
          fontFamily: "'DM Mono', Consolas, 'Courier New', monospace",
          fontSize: 14,
          fontLigatures: true,
          folding: true,
          lineNumbers: 'on',
          lineNumbersMinChars: 3,
          minimap: { enabled: false },
          padding: { top: 16, bottom: 16 },
          renderWhitespace: 'selection',
          scrollBeyondLastLine: false,
          smoothScrolling: true,
          tabSize: language === 'python' ? 4 : 2,
          insertSpaces: true,
          wordWrap: 'on',
        }}
      />
    </div>
  );
}
