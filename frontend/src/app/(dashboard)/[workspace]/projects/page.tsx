import { KanbanSquare, Plus, Activity, LayoutGrid, List } from 'lucide-react';

const MOCK_PROJECTS = [
  { id: 'PRJ-1', name: 'Developer OS Alpha', status: 'In Progress', progress: 68, lead: 'Alex', icon: '💻' },
  { id: 'PRJ-2', name: 'GitHub Integration', status: 'Planned', progress: 0, lead: 'Sarah', icon: '🐙' },
  { id: 'PRJ-3', name: 'Analysis Rule Engine v2', status: 'In Progress', progress: 34, lead: 'David', icon: '⚙️' },
  { id: 'PRJ-4', name: 'Realtime Chat Sync', status: 'Completed', progress: 100, lead: 'Alex', icon: '💬' },
];

export default function ProjectsPage() {
  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272A] shrink-0 bg-[#0A0A0B]">
        <h1 className="text-lg font-medium flex items-center gap-2 text-[#FAFAFA]">
          <KanbanSquare className="w-5 h-5 text-[#6366F1]" /> Projects
        </h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#111113] border border-[#27272A] p-1 rounded-md">
            <button className="p-1 bg-[#27272A] rounded text-[#FAFAFA]"><LayoutGrid className="w-3.5 h-3.5" /></button>
            <button className="p-1 text-[#A1A1AA] hover:text-[#FAFAFA]"><List className="w-3.5 h-3.5" /></button>
          </div>
          <button className="bg-[#6366F1] hover:bg-[#4F46E5] text-white text-[12px] font-medium py-1.5 px-3 rounded-[6px] flex items-center gap-1.5 transition-colors">
            <Plus className="w-3.5 h-3.5" /> New Project
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-[#0A0A0B]">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MOCK_PROJECTS.map((proj) => (
            <div key={proj.id} className="bg-[#111113] border border-[#27272A] rounded-[8px] p-5 hover:border-[#6366F1]/50 transition-colors cursor-pointer group">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-[6px] bg-[#18181B] border border-[#27272A] flex items-center justify-center text-lg">
                  {proj.icon}
                </div>
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${
                  proj.status === 'Completed' ? 'text-[#22C55E] bg-[#22C55E]/10 border border-[#22C55E]/20' : 
                  proj.status === 'In Progress' ? 'text-[#F59E0B] bg-[#F59E0B]/10 border border-[#F59E0B]/20' : 
                  'text-[#A1A1AA] bg-[#18181B] border border-[#27272A]'
                }`}>
                  {proj.status}
                </span>
              </div>
              
              <h3 className="text-[14px] font-medium text-[#FAFAFA] mb-1 group-hover:text-[#6366F1] transition-colors">{proj.name}</h3>
              <p className="text-[12px] text-[#A1A1AA] mb-4 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" /> Lead: {proj.lead}
              </p>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px] text-[#A1A1AA]">
                  <span>Progress</span>
                  <span>{proj.progress}%</span>
                </div>
                <div className="h-1.5 w-full bg-[#18181B] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#6366F1] rounded-full" 
                    style={{ width: `${proj.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}