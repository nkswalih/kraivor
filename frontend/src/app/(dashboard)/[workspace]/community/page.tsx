import { Globe, TrendingUp, MessageSquare, ArrowBigUp, Share2, Search, Filter } from 'lucide-react';

export default function CommunityPage() {
  return (
    <div className="flex h-full w-full animate-fade-up">
      
      {/* Main Feed Column */}
      <div className="flex-1 overflow-y-auto p-6 max-w-[850px] mx-auto border-r border-border bg-background">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-xl font-medium flex items-center gap-2 text-foreground">
              <Globe className="w-5 h-5 text-primary" /> Developer Community
            </h1>
            <p className="text-[13px] text-muted-foreground mt-1">Discover public reports, architecture patterns, and discussions.</p>
          </div>
          <button className="btn-shimmer text-primary-foreground text-[13px] font-medium px-4 py-2 rounded-md">
            New Discussion
          </button>
        </div>

        {/* Filter/Sort Tabs */}
        <div className="flex items-center justify-between border-b border-border pb-4 mb-6">
          <div className="flex items-center gap-4 text-[13px] font-medium">
            <button className="text-foreground border-b-2 border-primary pb-4 -mb-[17px]">Trending</button>
            <button className="text-muted-foreground hover:text-foreground transition-colors">Latest</button>
            <button className="text-muted-foreground hover:text-foreground transition-colors">Architecture</button>
            <button className="text-muted-foreground hover:text-foreground transition-colors">AI Prompts</button>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-1.5 text-muted-foreground hover:text-foreground rounded bg-card border border-border">
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Feed Posts */}
        <div className="space-y-4">
          {[
            {
              title: "How we reduced API latency by 40% using Redis",
              author: "DavidK",
              time: "4 hours ago",
              tags: ["Performance", "Backend"],
              upvotes: 342,
              comments: 45
            },
            {
              title: "Shared Report: Next.js 15 App Router Production Readiness",
              author: "SarahDev",
              time: "12 hours ago",
              tags: ["Analysis", "Next.js"],
              upvotes: 128,
              comments: 12,
              hasCard: true
            },
            {
              title: "Best practices for microservices authorization?",
              author: "BackendNoob",
              time: "1 day ago",
              tags: ["Security", "Discussion"],
              upvotes: 56,
              comments: 89
            }
          ].map((post, i) => (
            <div key={i} className="bg-card border border-border rounded-lg p-4 hover:border-primary/40 transition-colors cursor-pointer group">
              <div className="flex gap-4">
                {/* Vote Column */}
                <div className="flex flex-col items-center gap-1 shrink-0 text-muted-foreground">
                  <button className="hover:text-primary transition-colors hover:bg-primary/10 rounded p-1">
                    <ArrowBigUp className="w-5 h-5" />
                  </button>
                  <span className="text-[12px] font-medium text-foreground">{post.upvotes}</span>
                </div>
                
                {/* Content Column */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-1.5">
                    <span className="font-medium text-foreground hover:underline">{post.author}</span>
                    <span>•</span>
                    <span>{post.time}</span>
                  </div>
                  
                  <h3 className="text-[15px] font-medium text-foreground mb-2 group-hover:text-primary transition-colors">
                    {post.title}
                  </h3>
                  
                  <div className="flex items-center gap-2 mb-3">
                    {post.tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 rounded-full bg-background border border-border text-[11px] text-muted-foreground">
                        {tag}
                      </span>
                    ))}
                  </div>

                  {post.hasCard && (
                    <div className="mt-3 mb-3 p-3 border border-border rounded-md bg-background flex items-center gap-3 w-fit">
                      <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center border border-primary/30">
                        <TrendingUp className="w-4 h-4 text-primary" />
                      </div>
                      <div>
                        <div className="text-[12px] font-medium text-foreground">Next.js Demo App</div>
                        <div className="text-[11px] text-muted-foreground">Health Score: 98%</div>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-4 text-muted-foreground text-[12px]">
                    <div className="flex items-center gap-1.5 hover:text-foreground transition-colors">
                      <MessageSquare className="w-4 h-4" /> {post.comments} Comments
                    </div>
                    <div className="flex items-center gap-1.5 hover:text-foreground transition-colors">
                      <Share2 className="w-4 h-4" /> Share
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Sidebar (Stats & Topics) */}
      <div className="w-[300px] bg-card p-6 hidden lg:block shrink-0">
        <h3 className="text-[12px] font-semibold tracking-wider text-muted-foreground uppercase mb-4">Trending Topics</h3>
        <div className="flex flex-wrap gap-2 mb-8">
          {['#architecture', '#system-design', '#rust', '#react-server-components', '#devops'].map(tag => (
            <span key={tag} className="px-2.5 py-1 rounded bg-background border border-border text-[12px] text-muted-foreground hover:text-foreground hover:border-primary/50 cursor-pointer transition-colors">
              {tag}
            </span>
          ))}
        </div>

        <h3 className="text-[12px] font-semibold tracking-wider text-muted-foreground uppercase mb-4">Top Contributors</h3>
        <div className="space-y-3">
          {[
            { name: 'DavidK', role: 'Architect', pts: '12.4k' },
            { name: 'SarahDev', role: 'Frontend', pts: '8.2k' },
            { name: 'AlexSec', role: 'Security', pts: '6.1k' }
          ].map(user => (
            <div key={user.name} className="flex items-center justify-between group cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-muted flex items-center justify-center text-[10px] text-foreground font-medium">
                  {user.name.charAt(0)}
                </div>
                <div>
                  <div className="text-[13px] font-medium text-foreground group-hover:underline">{user.name}</div>
                  <div className="text-[11px] text-muted-foreground">{user.role}</div>
                </div>
              </div>
              <span className="text-[11px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">{user.pts}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}