'use client';

import { Sparkles, X, Send } from 'lucide-react';
import { useUIStore } from '@/lib/stores';

export function RightPanel() {
  const closeRightPanel = useUIStore(state => state.closeRightPanel);

  return (
    <aside className="w-[320px] bg-krait-obsidian border-l border-krait-border h-full flex flex-col shrink-0">
      <div className="h-12 border-b border-krait-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-venom-yellow" />
          <span className="font-medium text-text-primary text-[13px]">AI Context Chat</span>
        </div>
        <button onClick={closeRightPanel} className="text-text-secondary hover:text-text-primary">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Chat History Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="bg-krait-surface1 border border-krait-border p-3 rounded-[6px]">
          <p className="text-[13px] text-text-secondary leading-relaxed">
            I&apos;m analyzing the <span className="text-venom-yellow">Authentication System</span>{' '}
            architecture you currently have open. How can I help you improve it?
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-krait-border bg-krait-void">
        <div className="flex items-end bg-krait-surface1 border border-krait-border rounded-[6px] p-1 focus-within:border-venom-yellow/50 transition-colors">
          <textarea
            placeholder="Ask AI about this context..."
            className="w-full bg-transparent border-none text-[13px] text-text-primary placeholder-text-secondary resize-none focus:outline-none p-2 min-h-[40px] max-h-[120px]"
            rows={1}
          />
          <button className="p-2 text-primary-foreground bg-primary rounded-[4px] hover:bg-primary/90 m-0.5 shrink-0">
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
