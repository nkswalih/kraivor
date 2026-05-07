'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/shadcn';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="text-sm text-muted-foreground">
          {error.message || 'An unexpected error occurred'}
        </p>
      </div>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}