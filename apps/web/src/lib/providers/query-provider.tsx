'use client';

import dynamic from 'next/dynamic';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

const ReactQueryDevtools = dynamic(
  () => import('@tanstack/react-query-devtools').then(m => m.ReactQueryDevtools),
  { ssr: false }
);

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: 0,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
