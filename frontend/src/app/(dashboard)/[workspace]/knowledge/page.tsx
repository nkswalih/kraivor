import { Edit3, Plus, LayoutGrid, List } from 'lucide-react';

export default function KnowledgePage() {
  return (
    <div className="p-6 h-full flex flex-col animate-fade-up">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-medium text-foreground">Knowledge Base</h1>
          <p className="text-[13px] text-muted-foreground mt-1">Architecture diagrams, documentation, and canvases.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-background border border-border p-1 rounded-md">
            <button className="p-1 bg-card rounded text-foreground shadow-sm"><LayoutGrid className="w-4 h-4" /></button>
            <button className="p-1 text-muted-foreground hover:text-foreground"><List className="w-4 h-4" /></button>
          </div>
          <button className="btn-shimmer text-primary-foreground text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" /> New Canvas
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {['System Architecture', 'Database Schema', 'Auth Flow', 'API Planning'].map((doc) => (
          <div key={doc} className="group flex flex-col bg-card border border-border rounded-lg overflow-hidden hover:border-primary/50 transition-colors cursor-pointer">
            <div className="h-32 bg-background flex items-center justify-center border-b border-border relative overflow-hidden">
              {/* Fake canvas grid pattern */}
              <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)', backgroundSize: '16px 16px' }}></div>
              <Edit3 className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors z-10" />
            </div>
            <div className="p-3">
              <h3 className="text-[13px] font-medium text-foreground">{doc}</h3>
              <p className="text-[11px] text-muted-foreground mt-1">Edited 2 days ago</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}