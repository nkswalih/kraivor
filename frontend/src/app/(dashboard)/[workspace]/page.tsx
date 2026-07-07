'use client';

import { useParams } from 'next/navigation';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import {
  GitBranch,
  MessageSquare,
  Users,
  Layers,
  ArrowRight,
  Clock,
  Hash,
  Sparkles,
  Activity,
  BookOpen,
  Circle,
  AlertCircle,
  Plus,
  Loader2,
} from 'lucide-react';
import { useDashboard, type DashboardData } from '@/lib/hooks/use-dashboard';
import type { AnalysisJob } from '@/types/domain/analysis';
import { Badge, Skeleton } from '@/components/ui/shadcn';
import { cn, formatRelativeTime, avatarUrl } from '@/lib/utils';
import { profileEndpoints } from '@/lib/api/endpoints';

/* ─── Stat Card ──────────────────────────────────────────────────── */

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  loading,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  color: string;
  loading?: boolean;
}) {
  return (
    <div
      className="group relative bg-krait-surface1 border border-krait-border rounded-lg p-4 flex flex-col
                 animate-fade-up
                 hover:border-venom-yellow/40 hover:shadow-venom transition-all duration-[var(--duration-fast)] ease-strike"
    >
      {/* Snake band active indicator */}
      <div
        className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-transparent group-hover:bg-venom-yellow
                      transition-all duration-[var(--duration-normal)] ease-strike"
      />
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] text-text-secondary">{label}</span>
        {loading ? <Skeleton className="h-4 w-4" /> : <Icon className={`w-4 h-4 ${color}`} />}
      </div>
      {loading ? (
        <Skeleton className="h-7 w-16" />
      ) : (
        <span className="text-2xl font-medium text-text-primary">{value}</span>
      )}
    </div>
  );
}

/* ─── Chat Activity Row ─────────────────────────────────────────── */

function RecentChatActivity({
  rooms,
  loading,
}: {
  rooms: DashboardData['rooms'];
  loading: boolean;
}) {
  const recent = [...rooms]
    .filter(r => r.last_message_at)
    .sort((a, b) => new Date(b.last_message_at!).getTime() - new Date(a.last_message_at!).getTime())
    .slice(0, 5);

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3">
            <Skeleton variant="circle" className="h-8 w-8" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-32" />
              <Skeleton className="h-3 w-48" />
            </div>
            <Skeleton className="h-3 w-12" />
          </div>
        ))}
      </div>
    );
  }

  if (recent.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <MessageSquare className="w-8 h-8 text-text-tertiary mb-2" />
        <p className="text-sm text-text-secondary font-medium">No activity yet</p>
        <p className="text-xs text-text-tertiary mt-1">Start a conversation to see it here</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {recent.map((room, i) => (
        <div
          key={room.id}
          className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-krait-surface2 transition-colors cursor-pointer group animate-fade-up"
          style={{ animationDelay: `${i * 0.04}s` }}
        >
          <div className="w-8 h-8 rounded-md bg-krait-surface2 border border-krait-border flex items-center justify-center shrink-0">
            <Hash className="w-3.5 h-3.5 text-text-tertiary group-hover:text-venom-yellow transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-text-primary truncate">{room.name}</p>
            <p className="text-[12px] text-text-tertiary truncate">
              {room.topic || `${room.room_type_display} room`}
            </p>
          </div>
          <span className="text-[11px] text-text-tertiary shrink-0 font-mono">
            {room.last_message_at ? formatRelativeTime(room.last_message_at) : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Repository Row ────────────────────────────────────────────── */

function RecentRepositories({
  repos,
  loading,
}: {
  repos: DashboardData['repositories'];
  loading: boolean;
}) {
  const recent = repos.slice(0, 3);

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3">
            <Skeleton variant="rect" className="h-8 w-8" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-36" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (recent.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <GitBranch className="w-8 h-8 text-text-tertiary mb-2" />
        <p className="text-sm text-text-secondary font-medium">No repositories</p>
        <p className="text-xs text-text-tertiary mt-1">Connect a repo to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {recent.map((repo, i) => (
        <div
          key={repo.id}
          className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-krait-surface2 transition-colors cursor-pointer group animate-fade-up"
          style={{ animationDelay: `${i * 0.04}s` }}
        >
          <div className="w-8 h-8 rounded-md bg-krait-surface2 border border-krait-border flex items-center justify-center shrink-0">
            <GitBranch className="w-3.5 h-3.5 text-text-tertiary group-hover:text-venom-yellow transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-text-primary truncate">{repo.github_repo}</p>
            <p className="text-[12px] text-text-tertiary">
              {repo.language ?? 'Unknown'} · Updated {formatRelativeTime(repo.updated_at)}
            </p>
          </div>
          <Badge variant={repo.status === 'connected' ? 'success' : 'default'}>
            {repo.status === 'connected' ? 'Connected' : 'Disconnected'}
          </Badge>
        </div>
      ))}
    </div>
  );
}

/* ─── Active Members ────────────────────────────────────────────── */

function ActiveMembers({
  members,
  workspaceName,
  loading,
}: {
  members: DashboardData['members'];
  workspaceName: string;
  loading: boolean;
}) {
  const displayMembers = members.filter(m => m.status === 'active').slice(0, 6);

  const memberIds = useMemo(() => displayMembers.map(m => m.user_id), [displayMembers]);

  const { data: profilesData } = useQuery({
    queryKey: ['profiles-by-ids', memberIds],
    queryFn: () => profileEndpoints.getProfilesByIds(memberIds),
    enabled: memberIds.length > 0,
    staleTime: 60_000,
  });

  const profileMap = useMemo(() => profilesData?.profiles ?? {}, [profilesData]);

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-2">
            <Skeleton variant="circle" className="h-8 w-8" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (displayMembers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <Users className="w-8 h-8 text-text-tertiary mb-2" />
        <p className="text-sm text-text-secondary font-medium">No members yet</p>
        <p className="text-xs text-text-tertiary mt-1">Invite your team to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {displayMembers.map((member, i) => {
        const profile = profileMap[member.user_id];
        const src =
          avatarUrl(profile?.avatar_url, profile?.user_avatar_url) ||
          member.user?.avatar_url ||
          null;

        return (
          <div
            key={member.user_id}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-krait-surface2 transition-colors group animate-fade-up"
            style={{ animationDelay: `${i * 0.04}s` }}
          >
            <div className="relative shrink-0">
              {src ? (
              <img
                src={src}
                alt=""
                loading="lazy"
                className="w-8 h-8 rounded-full object-cover border border-krait-border"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-krait-surface3 border border-krait-border flex items-center justify-center text-xs font-medium text-text-primary">
                  {member.user?.name
                    ? member.user.name
                        .split(' ')
                        .map(n => n[0])
                        .join('')
                        .toUpperCase()
                        .slice(0, 2)
                    : 'U'}
                </div>
              )}
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#22c55e] border-2 border-krait-surface1" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-text-primary truncate">
                {profile?.username || profile?.display_name || member.user?.name || 'Member'}
              </p>
              <p className="text-[11px] text-text-tertiary">
                {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
              </p>
            </div>
            <Badge variant={member.role === 'owner' ? 'venom' : 'default'}>{member.role}</Badge>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Knowledge Cards ───────────────────────────────────────────── */

function KnowledgeSpaces({
  spaces,
  loading,
  workspaceSlug,
}: {
  spaces: DashboardData['knowledgeSpaces'];
  loading: boolean;
  workspaceSlug: string;
}) {
  const display = spaces.slice(0, 6);

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} variant="rect" className="h-28" />
        ))}
      </div>
    );
  }

  if (display.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <BookOpen className="w-8 h-8 text-text-tertiary mb-2" />
        <p className="text-sm text-text-secondary font-medium">No knowledge spaces</p>
        <p className="text-xs text-text-tertiary mt-1">
          Create your first space to document your architecture
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {display.map((space, i) => (
        <div
          key={space.id}
          className="animate-fade-up"
          style={{ animationDelay: `${i * 0.05}s` }}
        >
          <Link
            href={`/${workspaceSlug}/knowledge/${space.id}`}
            className="block p-4 rounded-lg bg-krait-surface1 border border-krait-border
                       hover:border-venom-yellow/30 hover:shadow-venom
                       transition-all duration-[var(--duration-normal)] ease-strike group h-full"
          >
            <div className="flex items-start justify-between mb-2">
              <Layers className="w-4 h-4 text-venom-yellow/60 group-hover:text-venom-yellow transition-colors mt-0.5" />
              <span className="text-[11px] text-text-tertiary font-mono">
                {formatRelativeTime(space.updated_at)}
              </span>
            </div>
            <p className="text-[13px] font-medium text-text-primary group-hover:text-venom-yellow transition-colors truncate">
              {space.name}
            </p>
            {space.description && (
              <p className="text-[12px] text-text-tertiary mt-1 line-clamp-2">
                {space.description}
              </p>
            )}
          </Link>
        </div>
      ))}
    </div>
  );
}

/* ─── Section Header ────────────────────────────────────────────── */

function SectionHeader({ title, href }: { title: string; href?: string }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-[13px] font-medium text-text-secondary uppercase tracking-wider">
        {title}
      </h2>
      {href && (
        <Link
          href={href}
          className="text-[12px] text-venom-yellow hover:text-venom-gold flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="w-3 h-3" />
        </Link>
      )}
    </div>
  );
}

/* ─── Page Section Wrapper ──────────────────────────────────────── */

function DashboardSection({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-krait-surface1 border border-krait-border rounded-lg p-4 ${className ?? ''}`}
    >
      {children}
    </div>
  );
}

/* ─── Error State ───────────────────────────────────────────────── */

function DashboardError({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircle className="w-10 h-10 text-color-error mb-3" />
      <p className="text-base font-medium text-text-primary mb-1">Failed to load dashboard</p>
      <p className="text-sm text-text-tertiary max-w-md">{message}</p>
    </div>
  );
}

/* ─── Greeting ──────────────────────────────────────────────────── */

function Greeting() {
  const hour = new Date().getHours();
  let timeStr = 'evening';
  if (hour < 12) timeStr = 'morning';
  else if (hour < 17) timeStr = 'afternoon';
  return `Good ${timeStr}`;
}

/* ════════════════════════════════════════════════════════════════════
   DASHBOARD PAGE
   ════════════════════════════════════════════════════════════════════ */

export default function DashboardPage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const { workspace, rooms, repositories, knowledgeSpaces, members, recentJobs, stats, isLoading, error } =
    useDashboard();

  if (error) {
    return (
      <div className="p-8 max-w-[1100px] w-full mx-auto">
        <DashboardError
          message={error instanceof Error ? error.message : 'An unexpected error occurred'}
        />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1100px] w-full mx-auto">
      {/* Page header */}
      <div className="mb-8 animate-fade-up">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-xl font-semibold text-text-primary tracking-tight">
            {isLoading ? (
              <Skeleton className="h-6 w-48 inline-block" />
            ) : (
              <>
                {Greeting()}, {workspace?.name ?? 'Developer'}.
              </>
            )}
          </h1>
          {isLoading && <Loader2 className="w-4 h-4 text-venom-yellow animate-spin" />}
        </div>
        <div className="text-sm text-text-tertiary">
          {isLoading ? (
            <Skeleton className="h-4 w-64" />
          ) : (
            `${stats.repoCount} repositories · ${stats.memberCount} members · ${stats.roomCount} rooms`
          )}
        </div>
      </div>

      {/* Row 1: Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatCard
          icon={GitBranch}
          label="Repositories"
          value={stats.repoCount}
          color="text-venom-yellow"
          loading={isLoading}
        />
        <StatCard
          icon={Users}
          label="Members"
          value={stats.memberCount}
          color="text-color-info"
          loading={isLoading}
        />
        <StatCard
          icon={MessageSquare}
          label="Active Rooms"
          value={stats.roomCount}
          color="text-color-success"
          loading={isLoading}
        />
        <StatCard
          icon={BookOpen}
          label="Knowledge Spaces"
          value={stats.knowledgeCount}
          color="text-venom-amber"
          loading={isLoading}
        />
      </div>

      {/* Recent Analysis */}
      <div className="mb-8 animate-fade-up" style={{ animationDelay: '0.06s' }}>
        <SectionHeader title="Recent Analysis" href={`/${workspaceSlug}/analysis`} />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} variant="rect" className="h-28" />
              ))
            : recentJobs.slice(0, 4).map((job: AnalysisJob) => (
                <Link
                  key={job.job_id}
                  href={`/${workspaceSlug}/analysis/jobs/${job.job_id}`}
                  className="block p-4 rounded-lg bg-krait-surface1 border border-krait-border
                             hover:border-venom-yellow/30 hover:shadow-venom
                             transition-all duration-[var(--duration-normal)] ease-strike group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <GitBranch className="w-4 h-4 text-venom-yellow/60 group-hover:text-venom-yellow transition-colors" />
                    <span className="text-[11px] text-text-tertiary font-mono">
                      {job.completed_at ? formatRelativeTime(job.completed_at) : job.status}
                    </span>
                  </div>
                  <p className="text-[13px] font-medium text-text-primary group-hover:text-venom-yellow transition-colors truncate">
                    {job.repo_url?.split('/').pop() ?? 'Untitled'}
                  </p>
                  <div className="flex items-center gap-3 mt-2">
                    {job.overall_score != null ? (
                      <span className={cn(
                        'text-lg font-semibold',
                        job.overall_score >= 75 ? 'text-color-success' :
                        job.overall_score >= 50 ? 'text-venom-amber' :
                        'text-color-error'
                      )}>
                        {job.overall_score}
                      </span>
                    ) : (
                      <span className="text-[12px] text-text-tertiary">
                        {job.status === 'completed' ? 'No score' : 'Running...'}
                      </span>
                    )}
                    {job.total_findings != null && (
                      <span className="text-[11px] text-text-tertiary">
                        {job.total_findings} finding{job.total_findings !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </Link>
              ))}
          {!isLoading && recentJobs.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-8 text-center">
              <Sparkles className="w-6 h-6 text-text-tertiary mb-2" />
              <p className="text-sm text-text-secondary font-medium">No analyses yet</p>
              <p className="text-xs text-text-tertiary mt-1">
                <Link href={`/${workspaceSlug}/analysis`} className="text-venom-yellow hover:underline">
                  Run your first analysis
                </Link>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Row 2: 3-column middle section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <DashboardSection>
          <SectionHeader title="Recent Chat Activity" href={`/${workspaceSlug}/chat`} />
          <RecentChatActivity rooms={rooms} loading={isLoading} />
        </DashboardSection>

        <DashboardSection>
          <SectionHeader title="Recent Repositories" href={`/${workspaceSlug}/repositories`} />
          <RecentRepositories repos={repositories} loading={isLoading} />
        </DashboardSection>

        <DashboardSection>
          <SectionHeader title="Active Members" />
          <ActiveMembers
            members={members}
            workspaceName={workspace?.name ?? ''}
            loading={isLoading}
          />
        </DashboardSection>
      </div>

      {/* Row 3: Knowledge Spaces */}
      <div className="animate-fade-up" style={{ animationDelay: '0.1s' }}>
        <SectionHeader title="Knowledge Spaces" href={`/${workspaceSlug}/knowledge`} />
        <KnowledgeSpaces
          spaces={knowledgeSpaces}
          loading={isLoading}
          workspaceSlug={workspaceSlug}
        />
      </div>

      {/* Quick Actions */}
      <div className="mt-8 animate-fade-up" style={{ animationDelay: '0.15s' }}>
        <SectionHeader title="Quick Actions" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Link
            href={`/${workspaceSlug}/analysis`}
            className="flex items-center gap-2.5 px-4 py-3 rounded-lg
                       btn-shimmer text-primary-foreground text-[13px] font-semibold
                       transition-all duration-[var(--duration-fast)] ease-strike active:scale-[0.98]"
          >
            <Sparkles className="w-4 h-4" />
            New AI Analysis
          </Link>
          <Link
            href={`/${workspaceSlug}/repositories`}
            className="flex items-center gap-2.5 px-4 py-3 rounded-lg
                       btn-shimmer-secondary text-text-primary text-[13px] font-medium
                       transition-all duration-[var(--duration-fast)] ease-strike active:scale-[0.98]"
          >
            <GitBranch className="w-4 h-4" />
            Connect Repository
          </Link>
          <Link
            href={`/${workspaceSlug}/knowledge`}
            className="flex items-center gap-2.5 px-4 py-3 rounded-lg
                       btn-shimmer-secondary text-text-primary text-[13px] font-medium
                       transition-all duration-[var(--duration-fast)] ease-strike active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            Create Knowledge Space
          </Link>
        </div>
      </div>
    </div>
  );
}
