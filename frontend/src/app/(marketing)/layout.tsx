import React from 'react';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[100dvh] w-full bg-background text-foreground">
      <main className="flex-1 flex flex-col min-h-0">{children}</main>
    </div>
  );
}
