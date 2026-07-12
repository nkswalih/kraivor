'use client';

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AiCodeBlock } from '@/components/features/ai-code-block';
import { useDebounce } from '@/lib/hooks/use-debounce';
import {
  MarkdownTable,
  MarkdownTHead,
  MarkdownTBody,
  MarkdownTR,
  MarkdownTH,
  MarkdownTD,
} from '@/components/features/markdown-table';

interface AiMarkdownProps {
  content: string;
  isStreaming?: boolean;
}

/* We use `any` for custom component props because react-markdown passes
   HAST node data + children + intrinsic element props + ExtraProps.
   The precise type (Components from react-markdown) is not exported
   from the default entry point in v10. */

/* eslint-disable @typescript-eslint/no-explicit-any */

const H1 = (props: any) => (
  <h1 className="text-[20px] font-bold text-text-primary mt-8 mb-4 leading-snug tracking-tight" {...props} />
);

const H2 = (props: any) => (
  <h2 className="text-[17px] font-semibold text-text-primary mt-6 mb-3 leading-snug tracking-tight" {...props} />
);

const H3 = (props: any) => (
  <h3 className="text-[15px] font-semibold text-text-primary mt-5 mb-2 leading-snug" {...props} />
);

const P = (props: any) => (
  <p className="text-[14px] leading-[1.7] text-text-secondary mb-4 last:mb-0" {...props} />
);

const UL = (props: any) => (
  <ul className="text-[14px] leading-[1.7] text-text-secondary mb-4 space-y-1.5 pl-6" {...props} />
);

const OL = (props: any) => (
  <ol className="text-[14px] leading-[1.7] text-text-secondary mb-4 space-y-1.5 pl-6 list-decimal" {...props} />
);

const LI = (props: any) => (
  <li className="pl-1" {...props} />
);

const Strong = (props: any) => (
  <strong className="font-semibold text-text-primary" {...props} />
);

const Em = (props: any) => (
  <em className="italic text-text-primary" {...props} />
);

const InlineCode = ({ className, ...props }: any) => {
  if (!className) {
    return (
      <code
        className="bg-krait-surface3 border border-krait-border px-1.5 py-0.5 rounded-md text-[13px] font-mono text-venom-yellow/90"
        {...props}
      />
    );
  }
  return null;
};

const Pre = (props: any) => {
  const child = props?.children;
  const code = child?.props?.children ?? '';
  const lang = (child?.props?.className ?? '').replace(/^language-/, '');
  const codeStr = typeof code === 'string' ? code : String(code);
  return <AiCodeBlock code={codeStr} language={lang} />;
};

const BlockQuote = (props: any) => (
  <blockquote
    className="border-l-2 border-venom-yellow/40 pl-4 py-1 my-4 text-[14px] text-text-secondary italic bg-venom-glow rounded-r-lg"
    {...props}
  />
);

const Link = (props: any) => (
  <a
    target="_blank"
    rel="noopener noreferrer"
    className="text-venom-yellow underline underline-offset-2 decoration-venom-yellow/30 hover:decoration-venom-yellow/70 transition-colors"
    {...props}
  />
);

const HR = () => <hr className="my-6 border-krait-border" />;

const Table = (props: any) => <MarkdownTable {...props} />;
const THead = (props: any) => <MarkdownTHead {...props} />;
const TBody = (props: any) => <MarkdownTBody {...props} />;
const TR = (props: any) => <MarkdownTR {...props} />;
const TH = (props: any) => <MarkdownTH {...props} />;
const TD = (props: any) => <MarkdownTD {...props} />;

/* eslint-enable @typescript-eslint/no-explicit-any */

export const AiMarkdown = memo(function AiMarkdown({ content, isStreaming }: AiMarkdownProps) {
  const displayContent = useDebounce(content, isStreaming ? 200 : 0);

  return (
    <div className="prose-custom max-w-none">
      {displayContent ? (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: H1,
            h2: H2,
            h3: H3,
            p: P,
            ul: UL,
            ol: OL,
            li: LI,
            strong: Strong,
            em: Em,
            code: InlineCode,
            pre: Pre,
            blockquote: BlockQuote,
            a: Link,
            hr: HR,
            table: Table,
            thead: THead,
            tbody: TBody,
            tr: TR,
            th: TH,
            td: TD,
          }}
        >
          {displayContent}
        </ReactMarkdown>
      ) : null}
      {isStreaming && (
        <span className="inline-block w-[2px] h-[16px] bg-venom-yellow animate-pulse-venom ml-0.5 align-text-bottom" />
      )}
    </div>
  );
}, (prev, next) => prev.content === next.content);
