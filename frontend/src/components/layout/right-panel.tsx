'use client';

import { Sparkles, X, Send } from 'lucide-react';
import { useUIStore } from '@/lib/stores';

export function RightPanel() {
  const closeRightPanel = useUIStore(state => state.closeRightPanel);

  return (
    <aside className="w-[320px] bg-[#111113] border-l border-[#27272A] h-full flex flex-col shrink-0">
      <div className="h-12 border-b border-[#27272A] flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#6366F1]" />
          <span className="font-medium text-[#FAFAFA] text-[13px]">AI Context Chat</span>
        </div>
        <button onClick={closeRightPanel} className="text-[#A1A1AA] hover:text-[#FAFAFA]">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Chat History Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="bg-[#18181B] border border-[#27272A] p-3 rounded-[6px]">
          <p className="text-[13px] text-[#A1A1AA] leading-relaxed">
            I'm analyzing the <span className="text-[#6366F1]">Authentication System</span>{' '}
            architecture you currently have open. How can I help you improve it?
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-[#27272A] bg-[#0A0A0B]">
        <div className="flex items-end bg-[#18181B] border border-[#27272A] rounded-[6px] p-1 focus-within:border-[#6366F1] transition-colors">
          <textarea
            placeholder="Ask AI about this context..."
            className="w-full bg-transparent border-none text-[13px] text-[#FAFAFA] placeholder-[#A1A1AA] resize-none focus:outline-none p-2 min-h-[40px] max-h-[120px]"
            rows={1}
          />
          <button className="p-2 text-[#FAFAFA] bg-[#6366F1] rounded-[4px] hover:bg-[#6366F1]/90 m-0.5 shrink-0">
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
