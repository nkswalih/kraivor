'use client';

import { Children, isValidElement, memo } from 'react';
import { useContainerWidth } from './use-container-width';
import type { ContainerWidth } from './use-container-width';

function extractText(node: unknown): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join(' ');
  if (isValidElement(node)) {
    const children = (node.props as { children?: unknown }).children;
    return extractText(children);
  }
  return '';
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

    const childProps = (child.props as { children?: React.ReactNode });

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

function TableCardsView({
  headers,
  rows,
}: {
  headers: string[];
  rows: React.ReactNode[][];
}) {
  if (rows.length === 0) return null;

  return (
    <div className="space-y-2 my-3">
      {rows.map((row, ri) => (
        <div
          key={ri}
          className="rounded-lg border border-border bg-card overflow-hidden animate-in-up"
          style={{ animationDelay: `${ri * 30}ms` }}
        >
          <div className="divide-y divide-border/50">
            {row.map((cell, ci) => (
              <div
                key={ci}
                className="flex items-start gap-2 px-3 py-2 text-[11px]"
              >
                {headers[ci] && (
                  <span className="shrink-0 font-semibold text-foreground min-w-[80px] text-[10px] uppercase tracking-wider">
                    {headers[ci]}
                  </span>
                )}
                <span className="text-text-secondary leading-relaxed [&_code]:text-[10px] [&_code]:bg-krait-surface3 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:font-mono">
                  {cell}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TableStandardView({
  children,
  size,
}: {
  children: React.ReactNode;
  size: ContainerWidth;
}) {
  const isCompact = size === 'medium';

  return (
    <div className="overflow-x-auto rounded-lg border border-border my-3">
      <table
        className={`w-full border-collapse ${
          isCompact ? 'text-[10px]' : 'text-[11px]'
        }`}
      >
        {children}
      </table>
    </div>
  );
}

export const AdaptiveTable = memo(function AdaptiveTable({
  children,
}: {
  children: React.ReactNode;
}) {
  const [ref, widthLabel] = useContainerWidth();

  if (widthLabel === 'narrow') {
    const { headers, rows } = getTableData(children);
    return (
      <div ref={ref}>
        <TableCardsView headers={headers} rows={rows} />
      </div>
    );
  }

  return (
    <div ref={ref}>
      <TableStandardView size={widthLabel}>{children}</TableStandardView>
    </div>
  );
});
