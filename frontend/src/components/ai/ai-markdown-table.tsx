'use client';

import {
  memo,
  Children,
  isValidElement,
  useRef,
  useState,
  useCallback,
  useEffect,
} from 'react';

function extractText(node: unknown): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join(' ');
  if (isValidElement(node)) {
    const children = (node.props as { children?: unknown }).children;
    return extractText(children);
  }
  return '';
}

function getShortLabel(text: string): string {
  const t = text.trim();
  if (t.length <= 12) return t;
  return t;
}

function getTableData(children: React.ReactNode): {
  headers: string[];
  rows: React.ReactNode[][];
} {
  const headers: string[] = [];
  const rows: React.ReactNode[][] = [];

  Children.forEach(children, (child) => {
    if (!isValidElement(child)) return;
    const type = (child.type as string) ?? '';
    const childProps = child.props as { children?: React.ReactNode };

    if (type === 'thead') {
      Children.forEach(childProps.children, (tr: unknown) => {
        if (!isValidElement(tr)) return;
        const trProps = (tr.props as { children?: React.ReactNode });
        headers.length = 0;
        Children.forEach(trProps.children, (th: unknown) => {
          if (isValidElement(th)) {
            const thProps = (th.props as { children?: React.ReactNode });
            headers.push(extractText(thProps.children));
          }
        });
      });
    }

    if (type === 'tbody') {
      Children.forEach(childProps.children, (tr: unknown) => {
        if (!isValidElement(tr)) return;
        const trProps = (tr.props as { children?: React.ReactNode });
        const cells: React.ReactNode[] = [];
        Children.forEach(trProps.children, (td: unknown) => {
          if (isValidElement(td)) {
            const tdProps = (td.props as { children?: React.ReactNode });
            cells.push(tdProps.children);
          }
        });
        rows.push(cells);
      });
    }

    if (type === 'tr') {
      const trProps = (child.props as { children?: React.ReactNode });
      const cells: React.ReactNode[] = [];
      const cellElements: unknown[] = [];
      Children.forEach(trProps.children, (cell: unknown) => {
        if (isValidElement(cell)) {
          const cellProps = (cell.props as { children?: React.ReactNode });
          cells.push(cellProps.children);
          cellElements.push(cell);
        }
      });
      const first = cellElements[0];
      const isHeader =
        isValidElement(first) && (first.type as string) === 'th';
      if (isHeader) {
        headers.push(...cells.map((c) => extractText(c)));
      } else {
        rows.push(cells);
      }
    }
  });

  return { headers, rows };
}

function CardRow({
  headers,
  cells,
}: {
  headers: string[];
  cells: React.ReactNode[];
}) {
  return (
    <div className="rounded-lg border border-krait-border bg-krait-surface1/20 overflow-hidden">
      <div className="divide-y divide-krait-border/50">
        {headers.map((header, ci) => (
          <div
            key={ci}
            className="flex items-start gap-3 px-3.5 py-2.5"
          >
            <span className="shrink-0 text-[11px] font-semibold text-text-primary uppercase tracking-wider min-w-[80px]">
              {getShortLabel(header)}
            </span>
            <span className="text-[13px] text-text-secondary leading-relaxed min-w-0 [&_code]:text-[12px] [&_code]:bg-krait-surface3 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:font-mono">
              {cells[ci]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CardView({
  headers,
  rows,
}: {
  headers: string[];
  rows: React.ReactNode[][];
}) {
  if (rows.length === 0) return null;
  return (
    <div className="space-y-2 my-4">
      {rows.map((cells, ri) => (
        <CardRow key={ri} headers={headers} cells={cells} />
      ))}
    </div>
  );
}

interface MarkdownTableProps {
  children: React.ReactNode;
}

export const MarkdownTable = memo(function MarkdownTable({ children }: MarkdownTableProps) {
  const [isMobile, setIsMobile] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const mq = window.matchMedia('(max-width: 639px)');
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  if (isMobile) {
    const { headers, rows } = getTableData(children);
    return (
      <div ref={containerRef} className="my-4">
        <CardView headers={headers} rows={rows} />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-4 rounded-lg border border-krait-border"
    >
      <table className="w-full text-[13px] text-text-secondary border-collapse">
        {children}
      </table>
    </div>
  );
});

export const MarkdownTHead = memo(function MarkdownTHead(props: any) {
  return (
    <thead
      className="sticky top-0 z-20 bg-krait-surface3"
      {...props}
    />
  );
});

export const MarkdownTBody = memo(function MarkdownTBody(props: any) {
  return (
    <tbody className="divide-y divide-krait-border align-top" {...props} />
  );
});

export const MarkdownTR = memo(function MarkdownTR(props: any) {
  return (
    <tr
      className="even:bg-krait-surface1/30 hover:bg-krait-surface3/[0.35] transition-colors duration-100"
      {...props}
    />
  );
});

export const MarkdownTH = memo(function MarkdownTH(props: any) {
  return (
    <th
      className="px-4 py-3 text-left text-[11px] font-semibold text-text-primary uppercase tracking-wider border-r border-krait-border/40 last:border-r-0"
      {...props}
    />
  );
});

export const MarkdownTD = memo(function MarkdownTD({ children, ...rest }: any) {
  return (
    <td
      className="px-4 py-3 text-[13px] text-text-secondary leading-relaxed border-r border-krait-border/40 last:border-r-0"
      style={{
        overflowWrap: 'break-word',
        wordBreak: 'break-word',
        hyphens: 'auto',
      }}
      {...rest}
    >
      {children}
    </td>
  );
});
