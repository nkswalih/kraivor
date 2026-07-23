'use client';

import { useQuery } from '@tanstack/react-query';
import { aiApi } from '@/lib/api/ai-api';

export function useDailyUsage() {
  return useQuery({
    queryKey: ['ai-daily-usage'],
    queryFn: () => aiApi.getDailyUsage(),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}
