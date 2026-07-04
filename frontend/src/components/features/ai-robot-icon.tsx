'use client';

/**
 * Cute box-style AI robot icon.
 * Rounded square head with friendly face and antenna.
 * Yellow (#FACC15) accent with soft glow.
 * Gentle floating animation via CSS class.
 */

export function RobotIcon({ className = '' }: { className?: string }) {
  return (
    <span
      className={`relative inline-flex items-center justify-center shrink-0 ai-robot-icon ${className}`}
      style={{ width: 20, height: 20 }}
      aria-hidden="true"
    >
      {/* Glow backdrop */}
      <span
        className="absolute inset-0 rounded-[5px]"
        style={{
          background: 'rgba(250, 204, 21, 0.08)',
          filter: 'blur(3px)',
        }}
      />

      {/* Robot head */}
      <svg
        width={20}
        height={20}
        viewBox="0 0 20 20"
        fill="none"
        className="relative z-[1]"
      >
        {/* Antenna */}
        <line x1="10" y1="2" x2="10" y2="5" stroke="#FACC15" strokeWidth="1.2" strokeLinecap="round" />
        <circle cx="10" cy="1.5" r="1" fill="#FACC15" opacity="0.7" />

        {/* Head body */}
        <rect x="3" y="5" width="14" height="11" rx="3.5" fill="#FACC15" opacity="0.12" />

        {/* Face */}
        <rect x="3" y="5" width="14" height="11" rx="3.5" stroke="#FACC15" strokeWidth="1" opacity="0.55" />

        {/* Left eye */}
        <circle cx="7.5" cy="10" r="1.2" fill="#FACC15" opacity="0.9" />

        {/* Right eye */}
        <circle cx="12.5" cy="10" r="1.2" fill="#FACC15" opacity="0.9" />

        {/* Smile */}
        <path
          d="M7 12.5C8 13.5 12 13.5 13 12.5"
          stroke="#FACC15"
          strokeWidth="0.8"
          strokeLinecap="round"
          opacity="0.7"
        />
      </svg>
    </span>
  );
}
