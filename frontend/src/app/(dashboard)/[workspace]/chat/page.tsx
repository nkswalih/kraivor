'use client';

import { Hash, Plus, MessageSquare, Send, Smile, Paperclip, Search } from 'lucide-react';

export default function ChatPage() {
  return (
    <div className="flex h-full w-full bg-background animate-fade-up">
      
      {/* Inner Sidebar: Channels & DMs */}
      <div className="w-[220px] bg-card border-r border-border flex flex-col shrink-0">
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Jump to..." 
              className="w-full bg-background border border-border text-[12px] rounded pl-7 pr-2 py-1 focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {/* Channels Section */}
          <div className="mb-4">
            <div className="px-3 flex items-center justify-between group cursor-pointer mb-1">
              <span className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Channels</span>
              <Plus className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="space-y-0.5 px-1.5">
              {['general', 'architecture-design', 'backend-api', 'frontend-ui'].map((channel, i) => (
                <button key={channel} className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] transition-colors ${i === 1 ? 'bg-white/10 text-foreground font-medium' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'}`}>
                  <Hash className="w-3.5 h-3.5" /> {channel}
                </button>
              ))}
            </div>
          </div>

          {/* DMs Section */}
          <div>
            <div className="px-3 flex items-center justify-between group cursor-pointer mb-1">
              <span className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Direct Messages</span>
              <Plus className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="space-y-0.5 px-1.5">
              {['Alex Johnson', 'Sarah DevOps', 'Kraivor AI'].map((user, i) => (
                <button key={user} className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-muted-foreground hover:bg-white/5 hover:text-foreground transition-colors">
                  <div className="relative">
                    <div className={`w-5 h-5 rounded-full ${i === 2 ? 'bg-primary' : 'bg-muted'} flex items-center justify-center text-[10px] text-white font-bold`}>
                      {i === 2 ? <MessageSquare className="w-3 h-3" /> : user.charAt(0)}
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full border border-card"></div>
                  </div>
                  {user}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-background relative">
        {/* Chat Header */}
        <div className="h-[52px] border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/95 backdrop-blur z-10">
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-muted-foreground" />
            <h2 className="font-medium text-[14px]">architecture-design</h2>
            <span className="text-muted-foreground text-[13px] border-l border-border pl-3 ml-1">Discussing system design and Kraivor analysis reports.</span>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Message 1 */}
          <div className="flex gap-3 hover:bg-white/[0.02] p-1 -m-1 rounded">
            <div className="w-9 h-9 rounded bg-muted flex items-center justify-center text-foreground font-medium shrink-0 mt-0.5">AJ</div>
            <div>
              <div className="flex items-baseline gap-2 mb-0.5">
                <span className="font-medium text-[14px] text-foreground">Alex Johnson</span>
                <span className="text-[11px] text-muted-foreground">Today at 10:23 AM</span>
              </div>
              <p className="text-[13px] text-muted-foreground leading-relaxed">
                I just ran the Architecture rule engine on the <span className="bg-primary/20 text-primary px-1 rounded font-mono text-[12px]">auth-service</span> repo. We have a circular dependency issue between the user and token modules.
              </p>
            </div>
          </div>

          {/* Message 2 */}
          <div className="flex gap-3 hover:bg-white/[0.02] p-1 -m-1 rounded">
            <div className="w-9 h-9 rounded bg-primary flex items-center justify-center text-primary-foreground font-medium shrink-0 mt-0.5">SD</div>
            <div>
              <div className="flex items-baseline gap-2 mb-0.5">
                <span className="font-medium text-[14px] text-foreground">Sarah DevOps</span>
                <span className="text-[11px] text-muted-foreground">Today at 10:26 AM</span>
              </div>
              <p className="text-[13px] text-muted-foreground leading-relaxed mb-2">
                Good catch. I opened a canvas for this. Let's redesign the flow here before refactoring.
              </p>
              <div className="flex items-center gap-3 p-3 border border-border rounded-lg bg-card max-w-[300px] cursor-pointer hover:border-primary/50 transition-colors">
                <div className="w-8 h-8 rounded bg-background border border-border flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <div className="text-[13px] font-medium text-foreground">Auth Refactor Flow</div>
                  <div className="text-[11px] text-muted-foreground">Knowledge Canvas</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Input Box */}
        <div className="p-4 shrink-0 bg-background">
          <div className="bg-card border border-border rounded-lg px-3 py-2 flex items-end gap-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all">
            <button className="p-1.5 text-muted-foreground hover:text-foreground shrink-0 rounded-md">
              <Plus className="w-4 h-4" />
            </button>
            <textarea 
              placeholder="Message #architecture-design"
              className="flex-1 bg-transparent border-none text-[13px] text-foreground resize-none py-1.5 focus:outline-none max-h-[150px] min-h-[24px]"
              rows={1}
            />
            <div className="flex items-center gap-1 shrink-0 pb-1">
              <button className="p-1.5 text-muted-foreground hover:text-foreground rounded-md">
                <Smile className="w-4 h-4" />
              </button>
              <button className="p-1.5 text-muted-foreground hover:text-foreground rounded-md">
                <Paperclip className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}