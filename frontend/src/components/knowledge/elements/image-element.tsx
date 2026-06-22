'use client';

import type { ImageElementData } from '@/types/knowledge';

interface Props {
  data: ImageElementData;
}

export function ImageElement({ data }: Props) {
  return (
    <div className="w-full h-full bg-krait-surface3 flex items-center justify-center overflow-hidden">
      {data.url ? (
        <img
          src={data.url}
          alt={data.alt ?? ''}
          className="w-full h-full"
          style={{ objectFit: data.objectFit ?? 'contain' }}
        />
      ) : (
        <div className="flex flex-col items-center gap-2 text-text-tertiary">
          <svg
            className="w-8 h-8"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
            />
          </svg>
          <span className="text-[12px]">Image not available</span>
        </div>
      )}
    </div>
  );
}
