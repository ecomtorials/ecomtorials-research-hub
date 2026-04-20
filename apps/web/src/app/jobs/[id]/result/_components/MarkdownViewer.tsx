'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MarkdownViewer({ markdown }: { markdown: string }) {
  return (
    <article className="card prose-invert max-w-none p-8">
      <style>{`
        .md-report h1 { font-size: 1.5rem; font-weight: 600; margin-top: 1.5rem; }
        .md-report h2 { font-size: 1.25rem; font-weight: 600; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--color-border); }
        .md-report h3 { font-size: 1.05rem; font-weight: 600; margin-top: 1.25rem; }
        .md-report p { margin: 0.75rem 0; line-height: 1.65; }
        .md-report ul, .md-report ol { margin: 0.75rem 0; padding-left: 1.25rem; }
        .md-report ul { list-style: disc; }
        .md-report ol { list-style: decimal; }
        .md-report li { margin: 0.25rem 0; }
        .md-report a { color: var(--color-accent); text-decoration: underline; }
        .md-report a:hover { filter: brightness(1.2); }
        .md-report code { background: rgba(255,255,255,0.06); padding: 0.1rem 0.35rem; border-radius: 0.25rem; font-size: 0.875em; }
        .md-report pre { background: rgba(255,255,255,0.04); padding: 0.75rem; border-radius: 0.5rem; overflow-x: auto; }
        .md-report blockquote { border-left: 3px solid var(--color-border); padding-left: 0.75rem; color: var(--color-text-muted); }
        .md-report hr { border: 0; border-top: 1px solid var(--color-border); margin: 1.5rem 0; }
        .md-report table { border-collapse: collapse; margin: 1rem 0; font-size: 0.9em; }
        .md-report th, .md-report td { border: 1px solid var(--color-border); padding: 0.4rem 0.6rem; text-align: left; }
        .md-report th { background: rgba(255,255,255,0.03); font-weight: 600; }
      `}</style>
      <div className="md-report">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </article>
  );
}
