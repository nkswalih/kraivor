import { Activity, GitBranch, Sparkles, Edit3, ArrowRight } from 'lucide-react';

export default function DashboardHome() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto animate-fade-up">
      <h1 className="text-2xl font-semibold mb-6">Good morning, Developer.</h1>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
        {[
          { label: 'Health Score', value: '94%', icon: Activity, color: 'text-primary' },
          { label: 'Active Repos', value: '12', icon: GitBranch, color: 'text-foreground' },
          { label: 'AI Sessions', value: '4', icon: Sparkles, color: 'text-primary' },
          { label: 'Draft Notes', value: '7', icon: Edit3, color: 'text-foreground' },
        ].map((stat, i) => (
          <div key={i} className="bg-card border border-border rounded-lg p-4 flex flex-col hover:border-primary/50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[13px] text-muted-foreground">{stat.label}</span>
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
            </div>
            <span className="text-2xl font-medium">{stat.value}</span>
          </div>
        ))}
      </div>

      {/* Main Content Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Recent Repos */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-medium text-muted-foreground">Recent Repositories</h2>
            <button className="text-[12px] text-primary hover:text-primary-light flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {['kraivor-core', 'auth-service', 'frontend-monorepo'].map((repo) => (
              <div key={repo} className="flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors cursor-pointer group">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-background border border-border flex items-center justify-center">
                    <GitBranch className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <div>
                    <h3 className="text-[13px] font-medium">{repo}</h3>
                    <p className="text-[12px] text-muted-foreground">Updated 2 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 rounded bg-primary/10 text-primary text-[11px] font-medium border border-primary/20">
                    98% Health
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions (Using your btn-shimmer) */}
        <div className="space-y-4">
          <h2 className="text-[14px] font-medium text-muted-foreground">Quick Actions</h2>
          <div className="space-y-2">
            <button className="w-full btn-shimmer text-primary-foreground text-[13px] font-medium py-2.5 px-4 rounded-lg flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> New AI Analysis
            </button>
            <button className="w-full btn-shimmer-secondary text-foreground text-[13px] font-medium py-2.5 px-4 rounded-lg flex items-center gap-2">
              <GitBranch className="w-4 h-4" /> Connect Repository
            </button>
            <button className="w-full btn-shimmer-secondary text-foreground text-[13px] font-medium py-2.5 px-4 rounded-lg flex items-center gap-2">
              <Edit3 className="w-4 h-4" /> Create Canvas
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}