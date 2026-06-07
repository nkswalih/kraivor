import { CheckSquare, SignalHigh, SignalMedium, SignalLow, Plus, Filter, CircleDot, CheckCircle2 } from 'lucide-react';

export default function TasksPage() {
  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272A] shrink-0 bg-[#0A0A0B]">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-medium flex items-center gap-2 text-[#FAFAFA]">
            <CheckSquare className="w-5 h-5 text-[#6366F1]" /> Issues
          </h1>
          <div className="h-5 w-px bg-[#27272A]" />
          <div className="flex items-center gap-2">
            <button className="text-[12px] font-medium text-[#FAFAFA] px-2 py-1 bg-[#18181B] rounded-[4px]">Active</button>
            <button className="text-[12px] font-medium text-[#A1A1AA] px-2 py-1 hover:text-[#FAFAFA] transition-colors">Backlog</button>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button className="p-1.5 border border-[#27272A] bg-[#111113] rounded-[6px] text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors">
            <Filter className="w-4 h-4" />
          </button>
          <button className="bg-[#6366F1] hover:bg-[#4F46E5] text-white text-[12px] font-medium py-1.5 px-3 rounded-[6px] flex items-center gap-1.5 transition-colors">
            <Plus className="w-3.5 h-3.5" /> New Issue
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-[#0A0A0B] p-6">
        
        {/* Status Group: In Progress */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-[13px] font-medium text-[#FAFAFA] mb-3 px-2">
            <CircleDot className="w-4 h-4 text-[#F59E0B]" /> In Progress <span className="text-[#A1A1AA] ml-1">2</span>
          </div>
          <div className="border border-[#27272A] rounded-[8px] bg-[#111113] divide-y divide-[#27272A]">
            {/* Task Row */}
            <div className="flex items-center gap-4 p-2.5 hover:bg-[#18181B] transition-colors cursor-pointer text-[13px] group">
              <span className="text-[#A1A1AA] font-mono text-[11px] w-14">KRV-42</span>
              <SignalHigh className="w-3.5 h-3.5 text-[#EF4444]" />
              <span className="flex-1 text-[#FAFAFA] group-hover:text-[#6366F1] transition-colors">Implement Multi-Agent Orchestrator</span>
              <span className="text-[11px] text-[#A1A1AA] bg-[#18181B] px-1.5 py-0.5 rounded border border-[#27272A]">Oct 12</span>
              <div className="w-5 h-5 rounded-full bg-[#6366F1] flex items-center justify-center text-[9px] text-white font-bold">AJ</div>
            </div>
            {/* Task Row */}
            <div className="flex items-center gap-4 p-2.5 hover:bg-[#18181B] transition-colors cursor-pointer text-[13px] group">
              <span className="text-[#A1A1AA] font-mono text-[11px] w-14">KRV-45</span>
              <SignalMedium className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span className="flex-1 text-[#FAFAFA] group-hover:text-[#6366F1] transition-colors">Setup PostgreSQL Database Schema</span>
              <span className="text-[11px] text-[#A1A1AA] bg-[#18181B] px-1.5 py-0.5 rounded border border-[#27272A]">Oct 14</span>
              <div className="w-5 h-5 rounded-full bg-[#22C55E] flex items-center justify-center text-[9px] text-white font-bold">SD</div>
            </div>
          </div>
        </div>

        {/* Status Group: Todo */}
        <div>
          <div className="flex items-center gap-2 text-[13px] font-medium text-[#FAFAFA] mb-3 px-2">
            <CircleDot className="w-4 h-4 text-[#A1A1AA]" /> Todo <span className="text-[#A1A1AA] ml-1">1</span>
          </div>
          <div className="border border-[#27272A] rounded-[8px] bg-[#111113] divide-y divide-[#27272A]">
             <div className="flex items-center gap-4 p-2.5 hover:bg-[#18181B] transition-colors cursor-pointer text-[13px] group">
              <span className="text-[#A1A1AA] font-mono text-[11px] w-14">KRV-48</span>
              <SignalLow className="w-3.5 h-3.5 text-[#A1A1AA]" />
              <span className="flex-1 text-[#FAFAFA] group-hover:text-[#6366F1] transition-colors">Design Landing Page for Marketing</span>
              <span className="text-[11px] text-[#A1A1AA] bg-[#18181B] px-1.5 py-0.5 rounded border border-[#27272A]">Oct 18</span>
              <div className="w-5 h-5 rounded-full border border-[#27272A] border-dashed flex items-center justify-center text-[10px] text-[#A1A1AA]">+</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}