'use client';

import { usePathname } from 'next/navigation';

export function PageShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className="flex flex-col h-full">
      {children}
    </div>
  );
}
