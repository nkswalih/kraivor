'use client';

import ReactMarkdown from 'react-markdown';
import { AiCodeBlock } from '@/components/features/ai-code-block';

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

const Table = (props: any) => (
  <div className="my-4 overflow-x-auto rounded-lg border border-krait-border">
    <table className="w-full text-[13px] text-text-secondary border-collapse" {...props} />
  </div>
);

const THead = (props: any) => (
  <thead className="bg-krait-surface3 border-b border-krait-border" {...props} />
);

const TBody = (props: any) => (
  <tbody className="divide-y divide-krait-border" {...props} />
);

const TR = (props: any) => (
  <tr className="even:bg-krait-surface1/50" {...props} />
);

const TH = (props: any) => (
  <th className="px-4 py-2.5 text-left text-[12px] font-semibold text-text-primary uppercase tracking-wider" {...props} />
);

const TD = (props: any) => (
  <td className="px-4 py-2.5 text-[13px] text-text-secondary" {...props} />
);

/* eslint-enable @typescript-eslint/no-explicit-any */

export function AiMarkdown({ content, isStreaming }: AiMarkdownProps) {
  return (
    <div className="prose-custom max-w-none">
      {content ? (
        <ReactMarkdown
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
          {content}
        </ReactMarkdown>
      ) : null}
      {isStreaming && (
        <span className="inline-block w-[2px] h-[16px] bg-venom-yellow animate-pulse-venom ml-0.5 align-text-bottom" />
      )}
    </div>
  );
}
