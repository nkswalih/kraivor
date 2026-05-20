'use client';

import React, { useRef, useState, KeyboardEvent, ClipboardEvent } from 'react';
import { cn } from '@/lib/utils';

interface OtpInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export const OtpInput: React.FC<OtpInputProps> = ({
  length = 6,
  value,
  onChange,
  error,
  disabled = false,
}) => {
  const [activeInput, setActiveInput] = useState<number>(0);
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);

  const handleOtpChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const val = e.target.value;
    if (!/^[0-9]*$/.test(val)) return;

    const newValue = value.padEnd(length, ' ').split('');
    newValue[index] = val.substring(val.length - 1);
    
    // Clean up spaces when reconstructing
    const combinedValue = newValue.join('').replace(/ /g, '');
    onChange(combinedValue);

    if (val && index < length - 1) {
      setActiveInput(index + 1);
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      setActiveInput(index - 1);
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text/plain').slice(0, length).replace(/[^0-9]/g, '');
    if (pastedData) {
      onChange(pastedData);
      const focusIndex = Math.min(pastedData.length, length - 1);
      setActiveInput(focusIndex);
      inputRefs.current[focusIndex]?.focus();
    }
  };

  return (
    <div className="w-full flex flex-col items-center">
      <div className="flex gap-2 sm:gap-3 w-full justify-center">
        {Array.from({ length }).map((_, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={value[index] || ''}
            onChange={(e) => handleOtpChange(e, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onFocus={() => setActiveInput(index)}
            onPaste={handlePaste}
            disabled={disabled}
            className={cn(
              "w-10 h-12 sm:w-12 sm:h-14 text-center text-xl font-semibold bg-[#151515] text-white",
              "border border-white/10 rounded-xl transition-all duration-200",
              "focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 focus:-translate-y-1",
              activeInput === index && !disabled && "border-primary/50 ring-1 ring-primary/50 -translate-y-1",
              error && "border-red-500/50 focus:border-red-500 focus:ring-red-500/20",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          />
        ))}
      </div>
      {error && <p className="text-xs text-red-400 mt-3 animate-fade-in">{error}</p>}
    </div>
  );
};
