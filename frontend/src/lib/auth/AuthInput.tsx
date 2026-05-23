'use client';

import React from 'react';
import { cn } from '@/lib/utils';

export interface AuthInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const AuthInput = React.forwardRef<HTMLInputElement, AuthInputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="space-y-1.5 w-full">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-gray-300">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            id={inputId}
            ref={ref}
            className={cn(
              'w-full bg-[#151515] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white',
              'transition-all duration-200 ease-in-out placeholder:text-gray-500',
              'focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              error && 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20',
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p className="text-xs text-red-400 mt-1 animate-fade-in">{error}</p>
        )}
      </div>
    );
  }
);
AuthInput.displayName = 'AuthInput';
