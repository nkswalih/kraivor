import { type ReactNode } from 'react';

export function Container({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={`max-w-7xl mx-auto px-3 sm:px-4 lg:px-6${className ? ` ${className}` : ''}`}>
      {children}
    </div>
  );
}
