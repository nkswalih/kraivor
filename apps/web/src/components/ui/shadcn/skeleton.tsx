import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circle' | 'rect';
}

export function Skeleton({ className, variant = 'text', ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-shimmer bg-gradient-to-r from-krait-surface2 via-krait-surface3 to-krait-surface2 bg-[length:200%_100%]',
        variant === 'circle' && 'rounded-full',
        variant === 'text' && 'rounded-md',
        variant === 'rect' && 'rounded-lg',
        className
      )}
      {...props}
    />
  );
}
