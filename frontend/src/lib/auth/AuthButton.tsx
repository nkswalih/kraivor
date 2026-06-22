'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface AuthButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  variant?: 'primary' | 'secondary' | 'oauth';
  icon?: React.ReactNode;
}

export const AuthButton = React.forwardRef<HTMLButtonElement, AuthButtonProps>(
  ({ className, isLoading, variant = 'primary', icon, children, disabled, ...props }, ref) => {
    const baseStyles =
      'relative w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden';

    const variants = {
      primary:
        'bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_rgba(250,204,21,0.15)] hover:shadow-[0_0_25px_rgba(250,204,21,0.25)]',
      secondary: 'bg-white/5 text-white hover:bg-white/10 border border-white/10',
      oauth:
        'bg-[#151515] border border-white/10 text-white hover:bg-white/5 hover:border-white/20',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
        {!isLoading && icon}
        {children}

        {/* Shine effect for primary button */}
        {variant === 'primary' && !disabled && !isLoading && (
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent hover:animate-[shimmer_1.5s_infinite]" />
        )}
      </button>
    );
  }
);
AuthButton.displayName = 'AuthButton';
