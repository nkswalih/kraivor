'use client';

import Link from 'next/link';
import { Sparkles, Zap, Shield, GitBranch } from 'lucide-react';

export function UpgradeCard({ show }: { show: boolean }) {
  if (!show) return null;

  return (
    <div className="mx-auto max-w-lg w-full bg-[#141416] rounded-xl border border-[#27272A] p-6 my-6">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-venom-yellow/10 border border-venom-yellow/20 flex items-center justify-center shrink-0">
          <Sparkles className="w-5 h-5 text-venom-yellow" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-[15px] font-semibold text-[#f2f2f3] mb-2">
            Upgrade to Kraivor AI Pro
          </h3>
          <ul className="space-y-1.5">
            {[
              { icon: Zap, text: '10x higher message caps on all models' },
              { icon: Shield, text: 'Priority access during peak usage' },
              { icon: GitBranch, text: 'Unlimited repository context length' },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2 text-[13px] text-[#9898a6]">
                <Icon className="w-3.5 h-3.5 text-venom-yellow/70 shrink-0" />
                {text}
              </li>
            ))}
          </ul>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-1 mt-3 text-[13px] text-venom-yellow font-medium hover:text-venom-amber transition-colors"
          >
            Learn more
            <span className="text-[15px] leading-none">&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
