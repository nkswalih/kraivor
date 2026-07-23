'use client';

import { memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AdaptiveTable } from './adaptive-table';

const baseProse = [
  'text-foreground leading-relaxed',
  'space-y-2',
].join(' ');

const headingBase = 'font-bold text-foreground scroll-mt-12';

function buildComponents(compact: boolean): any {
  const p = compact ? '10px' : '11px';
  const h = (factor: number) =>
    compact ? `${11 + factor * 0.8}px` : `${12 + factor}px`;

  return {
    h1: ({ children, ...props }: any) => (
      <h1
        className={`${headingBase} animate-in-up`}
        style={{ fontSize: h(3), marginTop: compact ? '12px' : '16px', marginBottom: compact ? '6px' : '8px' }}
        {...props}
      >
        {children}
      </h1>
    ),
    h2: ({ children, ...props }: any) => (
      <h2
        className={`${headingBase} animate-in-up`}
        style={{ fontSize: h(2), marginTop: compact ? '12px' : '16px', marginBottom: compact ? '4px' : '8px' }}
        {...props}
      >
        {children}
      </h2>
    ),
    h3: ({ children, ...props }: any) => (
      <h3
        className={`font-semibold text-foreground animate-in-up`}
        style={{ fontSize: h(1), marginTop: compact ? '10px' : '14px', marginBottom: compact ? '4px' : '6px' }}
        {...props}
      >
        {children}
      </h3>
    ),
    h4: ({ children, ...props }: any) => (
      <h4
        className="font-semibold text-foreground"
        style={{ fontSize: h(0), marginTop: '8px', marginBottom: '4px' }}
        {...props}
      >
        {children}
      </h4>
    ),
    h5: ({ children, ...props }: any) => (
      <h5 className="font-semibold text-text-secondary" style={{ fontSize: p }} {...props}>
        {children}
      </h5>
    ),
    h6: ({ children, ...props }: any) => (
      <h6 className="font-semibold text-text-tertiary" style={{ fontSize: p }} {...props}>
        {children}
      </h6>
    ),
    p: ({ children, ...props }: any) => (
      <p className="text-foreground leading-relaxed" style={{ fontSize: p, marginBottom: '6px' }} {...props}>
        {children}
      </p>
    ),
    strong: ({ children, ...props }: any) => (
      <strong className="font-semibold text-foreground" {...props}>
        {children}
      </strong>
    ),
    em: ({ children, ...props }: any) => (
      <em className="italic" {...props}>
        {children}
      </em>
    ),
    ul: ({ children, ...props }: any) => (
      <ul
        className="list-disc pl-4 space-y-1"
        style={{ fontSize: p, marginBottom: '6px' }}
        {...props}
      >
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: any) => (
      <ol
        className="list-decimal pl-4 space-y-1"
        style={{ fontSize: p, marginBottom: '6px' }}
        {...props}
      >
        {children}
      </ol>
    ),
    li: ({ children, ...props }: any) => (
      <li className="text-foreground leading-relaxed" {...props}>
        {children}
      </li>
    ),
    blockquote: ({ children, ...props }: any) => (
      <blockquote
        className="border-l-2 border-venom-yellow/30 pl-3 italic text-text-tertiary my-2"
        style={{ fontSize: p }}
        {...props}
      >
        {children}
      </blockquote>
    ),
    code: ({ className, children, ...props }: any) => {
      const isInline = !className;
      if (isInline) {
        return (
          <code
            className="bg-krait-surface3 text-text-secondary px-1.5 py-0.5 rounded font-mono"
            style={{ fontSize: compact ? '9.5px' : '10.5px' }}
            {...props}
          >
            {children}
          </code>
        );
      }
      return (
        <code
          className={`block font-mono whitespace-pre ${className ?? ''}`}
          style={{
            fontSize: compact ? '10px' : '11px',
            lineHeight: '1.6',
          }}
          {...props}
        >
          {children}
        </code>
      );
    },
    pre: ({ children, ...props }: any) => (
      <pre
        className="bg-krait-surface3 rounded-lg overflow-x-auto my-3"
        style={{ padding: compact ? '10px' : '14px' }}
        {...props}
      >
        {children}
      </pre>
    ),
    a: ({ children, href, ...props }: any) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-venom-yellow hover:underline"
        {...props}
      >
        {children}
      </a>
    ),
    hr: ({ ...props }: any) => (
      <hr className="border-border my-4" {...props} />
    ),
    table: ({ children }: any) => <AdaptiveTable>{children}</AdaptiveTable>,
    thead: ({ children }: any) => (
      <thead className="border-b border-border bg-krait-surface2 sticky top-0 z-10">
        {children}
      </thead>
    ),
    th: ({ children, ...props }: any) => (
      <th
        className="text-left font-semibold text-foreground px-2 py-1.5 whitespace-nowrap"
        style={{ fontSize: compact ? '10px' : '11px' }}
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }: any) => (
      <td
        className="px-2 py-1.5 text-text-secondary border-t border-border align-top break-words"
        style={{ fontSize: compact ? '10px' : '11px', maxWidth: compact ? '120px' : '200px' }}
        {...props}
      >
        <span className="[&_code]:text-[10px] [&_code]:bg-krait-surface3 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:font-mono">
          {children}
        </span>
      </td>
    ),
    tr: ({ children, ...props }: any) => (
      <tr
        className="transition-colors duration-100 hover:bg-krait-surface1/50 even:bg-krait-surface1/20"
        {...props}
      >
        {children}
      </tr>
    ),
  };
}

export const MarkdownRenderer = memo(function MarkdownRenderer({
  content,
  compact = false,
  className = '',
}: {
  content: string | null | undefined;
  compact?: boolean;
  className?: string;
}) {
  const components = useMemo(() => buildComponents(compact), [compact]);

  const hasContent = content && content.trim().length > 0;
  if (!hasContent) return null;

  return (
    <div className={`${baseProse} ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
