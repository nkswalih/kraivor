'use client';

const skeletonBase = 'animate-pulse bg-[#27272A] rounded';

export function SkeletonLine({ className = '' }: { className?: string }) {
  return <div className={`${skeletonBase} h-3 ${className}`} />;
}

export function SkeletonBlock({ className = '' }: { className?: string }) {
  return <div className={`${skeletonBase} ${className}`} />;
}

export function SkeletonAvatar({ className = '' }: { className?: string }) {
  return <div className={`${skeletonBase} rounded-full shrink-0 ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="border border-[#27272A] rounded-lg p-4 space-y-3 bg-[#111113]">
      <div className="flex items-center gap-3">
        <SkeletonBlock className="w-8 h-8 rounded-lg" />
        <div className="flex-1 space-y-2">
          <SkeletonLine className="w-1/3" />
          <SkeletonLine className="w-2/3" />
        </div>
      </div>
      <SkeletonLine className="w-full" />
      <SkeletonLine className="w-3/4" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="border border-[#27272A] rounded-lg overflow-hidden">
      <div className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 border-b border-[#27272A] bg-[#1C1C1F]">
        <SkeletonLine className="w-20" />
        <SkeletonLine className="w-16" />
        <SkeletonLine className="w-16" />
        <SkeletonLine className="w-8 ml-auto" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 border-b border-[#27272A]/50">
          <SkeletonLine className="w-40" />
          <SkeletonLine className="w-20" />
          <SkeletonLine className="w-14" />
          <SkeletonBlock className="w-6 h-6 rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonMessage() {
  return (
    <div className="flex gap-3 px-4 py-2">
      <SkeletonAvatar className="w-9 h-9" />
      <div className="flex-1 space-y-2 pt-1">
        <div className="flex items-center gap-2">
          <SkeletonLine className="w-24" />
          <SkeletonLine className="w-12" />
        </div>
        <SkeletonLine className="w-3/4" />
        <SkeletonLine className="w-1/2" />
      </div>
    </div>
  );
}

export function SkeletonChatSidebar() {
  return (
    <div className="w-[240px] bg-[#111113] border-r border-[#27272A] p-3 space-y-4 shrink-0">
      <div className="space-y-1">
        <SkeletonLine className="w-16 mb-2" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2 px-2 py-1.5">
            <SkeletonBlock className="w-4 h-4 rounded" />
            <SkeletonLine className="w-28" />
          </div>
        ))}
      </div>
      <div className="space-y-1">
        <SkeletonLine className="w-24 mb-2" />
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2 px-2 py-1.5">
            <SkeletonAvatar className="w-5 h-5" />
            <SkeletonLine className="w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}
