import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium transition-colors font-mono',
  {
    variants: {
      variant: {
        default: 'bg-krait-surface3 text-text-primary border border-krait-border',
        success: 'bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/20',
        error: 'bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20',
        warning: 'bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20',
        venom: 'bg-venom-yellow text-text-inverse border border-venom-gold font-semibold',
        outline: 'bg-transparent text-text-secondary border border-krait-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
