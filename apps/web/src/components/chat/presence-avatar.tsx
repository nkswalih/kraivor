'use client';

type AvatarSize = 'sm' | 'md' | 'lg';

const SIZES: Record<AvatarSize, { box: string; text: string; dot: string; position: string }> = {
  // sm: chat topbar, md: sidebar rows, lg: DM conversation intro.
  sm: { box: 'w-7 h-7', text: 'text-[11px]', dot: 'w-2.5 h-2.5', position: '-bottom-0.5 -right-0.5' },
  md: { box: 'w-8 h-8', text: 'text-[13px]', dot: 'w-3 h-3', position: '-bottom-0.5 -right-0.5' },
  lg: { box: 'w-20 h-20', text: 'text-[30px]', dot: 'w-5 h-5', position: 'bottom-0 right-0' },
};

interface PresenceAvatarProps {
  /** Already-resolved URL: profile upload > OAuth image > null. */
  src?: string | null;
  name: string;
  /** From the app-level presence roster (usePresence). */
  online: boolean;
  size?: AvatarSize;
  /** Badge outline — must match the surface behind the avatar. */
  ringClassName?: string;
  className?: string;
}

/**
 * Avatar wearing the Discord-style presence badge: green while the user has a
 * live session, grey otherwise, so an offline conversation still reads as
 * offline instead of looking unmarked.
 */
export function PresenceAvatar({
  src,
  name,
  online,
  size = 'md',
  ringClassName = 'border-krait-obsidian',
  className = '',
}: PresenceAvatarProps) {
  const s = SIZES[size];

  return (
    <span className={`relative inline-block shrink-0 ${s.box} ${className}`}>
      {src ? (
        <img
          src={src}
          alt={name}
          loading="lazy"
          className="w-full h-full rounded-full object-cover bg-krait-surface3"
        />
      ) : (
        <span
          className={`w-full h-full rounded-full bg-krait-surface3 flex items-center justify-center font-bold text-text-primary ${s.text}`}
        >
          {name.charAt(0).toUpperCase()}
        </span>
      )}
      <span
        title={online ? 'Online' : 'Offline'}
        aria-label={online ? 'Online' : 'Offline'}
        className={`absolute ${s.position} ${s.dot} rounded-full border-2 ${ringClassName} ${
          online ? 'bg-green-400' : 'bg-text-tertiary'
        }`}
      />
    </span>
  );
}
