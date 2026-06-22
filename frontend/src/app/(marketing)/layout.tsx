import React from 'react';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <main className="flex-1 flex flex-col overflow-y-auto min-h-0">{children}</main>
    </div>
  );
}
