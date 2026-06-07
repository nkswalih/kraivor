import { Bell, Check, Inbox, MessageSquare, AlertCircle } from 'lucide-react';

export default function NotificationsPage() {
  return (
    <div className="flex h-full w-full bg-[#0A0A0B] animate-fade-up">
      
      {/* Left Sidebar - Notification Filters */}
      <div className="w-[220px] border-r border-[#27272A] bg-[#111113] p-3 flex flex-col gap-1 shrink-0">
        <button className="flex items-center justify-between px-2.5 py-1.5 bg-[#18181B] text-[#FAFAFA] rounded-[6px] text-[13px] font-medium">
          <div className="flex items-center gap-2"><Inbox className="w-4 h-4 text-[#A1A1AA]" /> Inbox</div>
          <span className="text-[10px] bg-[#6366F1] text-white px-1.5 py-0.5 rounded-full">3</span>
        </button>
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] text-[13px] font-medium transition-colors">
          <MessageSquare className="w-4 h-4" /> Mentions
        </button>
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] text-[13px] font-medium transition-colors">
          <AlertCircle className="w-4 h-4" /> System Alerts
        </button>
      </div>

      {/* Main Notification List */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 border-b border-[#27272A] flex items-center justify-between px-6 shrink-0">
          <h2 className="text-[14px] font-medium text-[#FAFAFA]">Inbox</h2>
          <button className="text-[12px] text-[#A1A1AA] hover:text-[#FAFAFA] flex items-center gap-1.5 transition-colors">
            <Check className="w-3.5 h-3.5" /> Mark all as read
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {/* Notification Item */}
          <div className="flex gap-4 p-4 bg-[#111113] border border-[#27272A] rounded-[8px] cursor-pointer hover:border-[#6366F1]/50 transition-colors">
            <div className="mt-0.5 relative">
              <img src="https://i.pravatar.cc/150?u=a042581f4e29026024d" alt="Alex" className="w-8 h-8 rounded-full border border-[#27272A]" />
              <div className="absolute -bottom-1 -right-1 bg-[#0A0A0B] rounded-full p-0.5">
                <MessageSquare className="w-3 h-3 text-[#6366F1]" />
              </div>
            </div>
            <div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-medium text-[13px] text-[#FAFAFA]">Sarah DevOps</span>
                <span className="text-[13px] text-[#A1A1AA]">mentioned you in</span>
                <span className="font-medium text-[13px] text-[#FAFAFA]">KRV-42</span>
                <span className="text-[11px] text-[#A1A1AA] ml-2">10m ago</span>
              </div>
              <p className="text-[13px] text-[#A1A1AA]">"Hey @Alex, can you review the architecture canvas for the orchestrator?"</p>
            </div>
          </div>

          {/* System Alert Item */}
          <div className="flex gap-4 p-4 bg-[#111113] border border-[#27272A] rounded-[8px] cursor-pointer hover:border-[#6366F1]/50 transition-colors">
            <div className="mt-0.5 relative">
              <div className="w-8 h-8 rounded-full bg-[#EF4444]/10 border border-[#EF4444]/20 flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-[#EF4444]" />
              </div>
            </div>
            <div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-medium text-[13px] text-[#FAFAFA]">Analysis Engine</span>
                <span className="text-[13px] text-[#A1A1AA]">reported a critical issue in</span>
                <span className="font-medium text-[13px] text-[#FAFAFA]">auth-service</span>
                <span className="text-[11px] text-[#A1A1AA] ml-2">1h ago</span>
              </div>
              <p className="text-[13px] text-[#A1A1AA]">Hardcoded JWT secret found in production build step.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}