'use client';

interface AvatarProps {
  src?: string;
  fallbackSrc?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function Avatar({ src, fallbackSrc, name, size = 'md' }: AvatarProps) {
  const sizeMap = {
    sm: 'w-6 h-6 text-[10px]',
    md: 'w-10 h-10 text-sm',
    lg: 'w-16 h-16 text-lg',
    xl: 'w-24 h-24 text-2xl',
  };

  const imgSrc = src || fallbackSrc;

  if (imgSrc) {
    return (
      <img
        src={imgSrc}
        alt={name}
        className={`${sizeMap[size]} rounded-full object-cover border-2 border-border`}
      />
    );
  }

  return (
    <div
      className={`${sizeMap[size]} rounded-full bg-muted flex items-center justify-center text-foreground font-medium border-2 border-border`}
    >
      {name.charAt(0).toUpperCase()}
    </div>
  );
}
