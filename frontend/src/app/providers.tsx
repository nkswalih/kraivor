'use client';

import { QueryProvider, AuthProvider, ThemeProvider, ToasterProvider } from '@/lib/providers';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryProvider>
        <AuthProvider>
          {/*
            Inside ThemeProvider so it can read the resolved theme, and inside
            AuthProvider so a toast raised during sign-out still has somewhere
            to render.
          */}
          <ToasterProvider />
          {children}
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
