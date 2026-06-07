import { Settings, Users, Key, Shield, CreditCard } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="flex h-full w-full bg-[#0A0A0B] animate-fade-up text-[13px]">
      
      {/* Settings Navigation Sidebar */}
      <div className="w-[220px] border-r border-[#27272A] bg-[#111113] py-4 px-3 flex flex-col gap-1 shrink-0">
        <div className="px-2 mb-2 text-[11px] font-semibold tracking-wider text-[#A1A1AA] uppercase">Workspace Settings</div>
        
        <button className="flex items-center gap-2 px-2.5 py-1.5 bg-[#18181B] text-[#FAFAFA] rounded-[6px] font-medium">
          <Settings className="w-4 h-4 text-[#A1A1AA]" /> General
        </button>
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] font-medium transition-colors">
          <Users className="w-4 h-4" /> Members
        </button>
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] font-medium transition-colors">
          <CreditCard className="w-4 h-4" /> Billing
        </button>

        <div className="px-2 mt-6 mb-2 text-[11px] font-semibold tracking-wider text-[#A1A1AA] uppercase">Developer</div>
        
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] font-medium transition-colors">
          <Key className="w-4 h-4" /> API Keys
        </button>
        <button className="flex items-center gap-2 px-2.5 py-1.5 text-[#A1A1AA] hover:bg-[#18181B] hover:text-[#FAFAFA] rounded-[6px] font-medium transition-colors">
          <Shield className="w-4 h-4" /> Security
        </button>
      </div>

      {/* Settings Content Area */}
      <div className="flex-1 overflow-y-auto p-8 max-w-[800px]">
        <h1 className="text-xl font-medium text-[#FAFAFA] mb-1">General Settings</h1>
        <p className="text-[#A1A1AA] mb-8">Manage your workspace preferences and identity.</p>

        {/* Form Group */}
        <div className="space-y-6">
          <div className="space-y-3 border-b border-[#27272A] pb-6">
            <label className="block font-medium text-[#FAFAFA]">Workspace Name</label>
            <input 
              type="text" 
              defaultValue="Kraivor Inc"
              className="w-full max-w-[400px] bg-[#111113] border border-[#27272A] rounded-[6px] px-3 py-2 text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors"
            />
            <p className="text-[12px] text-[#A1A1AA]">This is your organization's display name.</p>
          </div>

          <div className="space-y-3 border-b border-[#27272A] pb-6">
            <label className="block font-medium text-[#FAFAFA]">Workspace URL</label>
            <div className="flex items-center max-w-[400px]">
              <span className="bg-[#18181B] border border-[#27272A] border-r-0 rounded-l-[6px] px-3 py-2 text-[#A1A1AA]">kraivor.com/</span>
              <input 
                type="text" 
                defaultValue="kraivor-inc"
                className="flex-1 bg-[#111113] border border-[#27272A] rounded-r-[6px] px-3 py-2 text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors"
              />
            </div>
          </div>

          <div className="pt-4">
            <button className="bg-[#6366F1] hover:bg-[#4F46E5] text-white font-medium py-2 px-4 rounded-[6px] transition-colors">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}