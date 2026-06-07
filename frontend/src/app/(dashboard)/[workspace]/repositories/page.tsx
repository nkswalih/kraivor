import { GitBranch, Plus, MoreHorizontal, CheckCircle2, ShieldAlert, Sparkles } from 'lucide-react';

export default function RepositoriesPage() {
  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <h1 className="text-lg font-medium flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-primary" /> Repositories
        </h1>
        <button className="btn-shimmer text-primary-foreground text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5">
          <Plus className="w-3.5 h-3.5" /> Connect Repo
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="border border-border rounded-lg bg-card overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 border-b border-border bg-background text-[12px] font-medium text-muted-foreground">
            <div>Repository Name</div>
            <div>AI Status</div>
            <div>Health Score</div>
            <div></div>
          </div>

          {/* Table Rows */}
          <div className="divide-y divide-border text-[13px]">
            {[
              { name: 'kraivor-core', status: 'Analyzed', score: 'A+', color: 'text-green-500', icon: CheckCircle2 },
              { name: 'auth-service', status: 'Scanning...', score: 'B', color: 'text-primary', icon: Sparkles },
              { name: 'legacy-api', status: 'Action Needed', score: 'D', color: 'text-red-500', icon: ShieldAlert },
            ].map((repo, i) => (
              <div key={i} className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 items-center hover:bg-white/[0.02] transition-colors cursor-pointer">
                <div className="flex items-center gap-2 font-medium">
                  <GitBranch className="w-4 h-4 text-muted-foreground" />
                  {repo.name}
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <repo.icon className={`w-3.5 h-3.5 ${repo.color}`} />
                  {repo.status}
                </div>
                <div>
                  <span className="px-2 py-0.5 rounded bg-background border border-border font-mono text-[12px]">
                    {repo.score}
                  </span>
                </div>
                <div className="flex justify-end">
                  <button className="p-1 hover:bg-white/10 rounded text-muted-foreground hover:text-foreground">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}