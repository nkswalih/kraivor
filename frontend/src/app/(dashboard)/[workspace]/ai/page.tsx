import { Sparkles, MessageSquare, Send, Paperclip } from 'lucide-react';

export default function AIWorkspacePage() {
  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Chat History Area */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        
        {/* User Message */}
        <div className="flex items-start gap-4 self-end max-w-[80%]">
          <div className="bg-card border border-border px-4 py-3 rounded-2xl rounded-tr-sm text-[13px] leading-relaxed">
            Can you analyze the security vulnerabilities in the auth-service repository?
          </div>
          <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
            <span className="text-[11px] font-bold text-primary">ME</span>
          </div>
        </div>

        {/* AI Response */}
        <div className="flex items-start gap-4 max-w-[80%]">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(217,119,6,0.3)]">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <div className="bg-background border border-border px-4 py-3 rounded-2xl rounded-tl-sm text-[13px] leading-relaxed">
            <p className="mb-2">I've analyzed the <span className="text-primary font-medium">auth-service</span> codebase. Here are the critical security findings:</p>
            <ul className="space-y-2 list-disc pl-4 text-muted-foreground">
              <li>Hardcoded JWT secrets found in <code className="bg-card border border-border px-1 rounded text-primary">auth/jwt.py</code></li>
              <li>Missing rate limiting on the login endpoint.</li>
            </ul>
          </div>
        </div>

      </div>

      {/* Input Area */}
      <div className="p-4 bg-card border-t border-border shrink-0">
        <div className="max-w-[800px] mx-auto bg-background border border-border rounded-xl flex items-end p-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all">
          <button className="p-2 text-muted-foreground hover:text-foreground shrink-0">
            <Paperclip className="w-4" />
          </button>
          <textarea 
            placeholder="Ask Kraivor AI about your codebase..."
            className="flex-1 justify-center bg-transparent border-none outline-none text-[13px] text-foreground resize-none p-2 min-h-[40px] max-h-[150px]"
            rows={1}
          />
          <button className="p-2 bg-primary hover:bg-primary-light text-primary-foreground rounded-lg m-1 shrink-0 transition-colors">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-[11px] text-muted-foreground mt-2">
          AI can make mistakes. Verify critical code architectures.
        </p>
      </div>
    </div>
  );
}