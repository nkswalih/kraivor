'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, GitBranch, Upload, Loader2, AlertCircle, FileText, Info } from 'lucide-react';
import Link from 'next/link';
import type { Repository } from '@/types/api';
import { useQuery } from '@tanstack/react-query';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useStartAnalysis, useFileUpload } from '@/lib/hooks/use-analysis';
import type { StartAnalysisRequest } from '@/types/domain/analysis';
import { analysisService } from '@/lib/api/analysis-service';

type Mode = 'git' | 'upload';

export default function NewAnalysisPage() {
  const router = useRouter();
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>('git');
  const [repoId, setRepoId] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [deepScan, setDeepScan] = useState(false);
  const [depth, setDepth] = useState(3);
  const [showDeepInfo, setShowDeepInfo] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: repos, isLoading: reposLoading, error: reposError } = useQuery<Repository[]>({
    queryKey: ['repos', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId && mode === 'git',
  });

  const reposList = repos ?? [];

  const { data: branches, isLoading: branchesLoading, error: branchesError } = useQuery<string[]>({
    queryKey: ['branches', repoUrl],
    queryFn: () => analysisService.jobs.branches(repoUrl),
    enabled: !!repoUrl && mode === 'git',
  });

  useEffect(() => {
    if (branches && branches.length > 0) {
      setBranch(branches[0]);
    }
  }, [branches]);

  const { mutate: startAnalysis, isPending: isStartPending, error: startError } = useStartAnalysis();
  const { mutate: uploadFile, isPending: isUploadPending, error: uploadError } = useFileUpload();

  const isPending = isStartPending || isUploadPending;
  const submitError = startError || uploadError;

  const handleGitSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoId || !workspaceId) return;

    const data: StartAnalysisRequest = {
      repo_id: repoId,
      workspace_id: workspaceId,
      repo_url: repoUrl,
      branch,
      deep_scan: deepScan,
      depth: deepScan ? depth : 1,
    };

    startAnalysis(data, {
      onSuccess: (job) => {
        router.push(`/${workspaceSlug}/analysis/jobs/${job.job_id}`);
      },
    });
  };

  const handleFileUpload = () => {
    if (!selectedFile || !workspaceId) return;

    uploadFile(
      { workspaceId, file: selectedFile },
      {
        onSuccess: (job) => {
          router.push(`/${workspaceSlug}/analysis/jobs/${job.job_id}`);
        },
      },
    );
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  };

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-1">
          <Link
            href={`/${workspaceSlug}/analysis`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground">New Analysis</h1>
        </div>
        <p className="text-sm text-text-tertiary mt-1">Configure and start a repository analysis</p>

        {/* Mode Toggle */}
        <div className="flex items-center gap-1 mt-3 bg-card border border-border rounded-lg p-0.5 w-fit">
          <button
            type="button"
            onClick={() => setMode('git')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors ${
              mode === 'git' ? 'bg-white/10 text-foreground' : 'text-text-tertiary hover:text-foreground'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            Git Repository
          </button>
          <button
            type="button"
            onClick={() => setMode('upload')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors ${
              mode === 'upload' ? 'bg-white/10 text-foreground' : 'text-text-tertiary hover:text-foreground'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload File
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        {mode === 'git' ? (
          <form onSubmit={handleGitSubmit} className="space-y-6">
            {/* Repository Selection */}
            <div>
              <label className="text-[13px] font-medium text-foreground block mb-1.5">
                Repository
              </label>
              {reposLoading ? (
                <div className="flex items-center gap-2 text-text-tertiary text-[13px] p-3 border border-border rounded-md bg-card">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading repositories...
                </div>
              ) : reposError ? (
                <div className="flex items-center gap-2 text-color-error text-[13px] p-3 border border-border rounded-md bg-card">
                  <AlertCircle className="w-4 h-4" />
                  Failed to load repositories
                </div>
              ) : reposList.length === 0 ? (
                <div className="p-3 border border-border rounded-md bg-card text-text-tertiary text-[13px]">
                  No repositories found. Connect one first.
                </div>
              ) : (
                <select
                  value={repoId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setRepoId(id);
                    const r = reposList.find((r: { id: string }) => r.id === id);
                    if (r) {
                      setRepoUrl(`https://github.com/${r.github_repo}` || '');
                    }
                  }}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
                  required
                >
                  <option value="">Select a repository...</option>
                  {reposList.map((r: Repository) => (
                    <option key={r.id} value={r.id}>
                      {r.github_repo || r.id}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Branch */}
            <div>
              <label className="text-[13px] font-medium text-foreground block mb-1.5">
                Branch
              </label>
              {!repoUrl ? (
                <div className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-text-tertiary">
                  Select a repository first
                </div>
              ) : branchesLoading ? (
                <div className="flex items-center gap-2 w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-text-tertiary">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading branches...
                </div>
              ) : branchesError ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 p-2 border border-red-500/30 bg-red-500/10 rounded-md text-color-error text-[12px]">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    Failed to fetch branches. Enter manually below.
                  </div>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
                    placeholder="main"
                  />
                </div>
              ) : (
                <select
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
                >
                  {branches?.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Deep Scan Toggle with Info */}
            <div className="relative">
              <div className="flex items-center justify-between p-3 border border-border rounded-md bg-card">
                <div className="flex items-center gap-2">
                  <div>
                    <p className="text-[13px] font-medium text-foreground">Deep Scan</p>
                    <p className="text-[12px] text-text-tertiary">Analyze commit history for churn hotspots</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowDeepInfo(!showDeepInfo)}
                    className="p-0.5 rounded-full text-text-tertiary hover:text-foreground transition-colors"
                  >
                    <Info className="w-3.5 h-3.5" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setDeepScan(!deepScan)}
                  className={`relative w-10 h-5 rounded-full transition-colors ${deepScan ? 'bg-yellow-500' : 'bg-krait-surface3'}`}
                >
                  <div
                    className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${deepScan ? 'translate-x-5' : 'translate-x-0.5'}`}
                  />
                </button>
              </div>
              {showDeepInfo && (
                <div className="absolute z-10 mt-1 p-3 border border-border rounded-md bg-card shadow-lg text-[12px] text-text-secondary leading-relaxed max-w-sm">
                  <p className="mb-2">
                    <strong className="text-foreground">Deep Scan</strong> fetches additional commit history (<code className="text-venom-yellow">git clone --depth N</code>) to enable <strong className="text-foreground">code churn analysis</strong>.
                  </p>
                  <ul className="list-disc pl-4 space-y-1">
                    <li>Identifies files that change most frequently (<strong>hotspots</strong>)</li>
                    <li>Detects ownership diffusion (many authors per file)</li>
                    <li>Higher depth = more accurate churn signal</li>
                    <li>Adds <strong>quality</strong> findings to your analysis results</li>
                  </ul>
                  <button
                    type="button"
                    onClick={() => setShowDeepInfo(false)}
                    className="mt-2 text-[11px] text-text-tertiary hover:text-foreground"
                  >
                    Got it
                  </button>
                </div>
              )}
            </div>

            {/* Depth Slider (shown only when deep scan is on) */}
            {deepScan && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[13px] font-medium text-foreground">
                    Commit Depth
                  </label>
                  <span className="text-[12px] text-venom-yellow font-mono">{depth}</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={10}
                  value={depth}
                  onChange={(e) => setDepth(Number(e.target.value))}
                  className="w-full accent-venom-yellow"
                />
                <div className="flex justify-between text-[10px] text-text-tertiary mt-0.5">
                  <span>Shallow</span>
                  <span>Deep</span>
                </div>
              </div>
            )}

            {/* Error */}
            {submitError && (
              <div className="flex items-center gap-2 p-3 border border-red-500/30 bg-red-500/10 rounded-md text-color-error text-[13px]">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {submitError.message}
              </div>
            )}

            {/* Submit */}
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={isPending || !repoId || !workspaceId}
                className="flex items-center gap-2 px-5 py-2 rounded-md btn-shimmer text-primary-foreground text-[13px] font-semibold disabled:opacity-50 transition-all active:scale-[0.98]"
              >
                {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
                {isPending ? 'Starting...' : 'Start Analysis'}
              </button>
              <Link
                href={`/${workspaceSlug}/analysis`}
                className="px-5 py-2 rounded-md border border-border bg-card text-text-secondary text-[13px] font-medium hover:text-foreground transition-colors"
              >
                Cancel
              </Link>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            {/* Project Zip Upload */}
            <div>
              <label className="text-[13px] font-medium text-foreground block mb-1.5">
                Project Archive
              </label>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  dragOver ? 'border-venom-yellow bg-venom-yellow/5' : 'border-border hover:border-muted-foreground'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    if (f && !f.name.endsWith('.zip')) {
                      e.target.value = '';
                      return;
                    }
                    setSelectedFile(f);
                  }}
                />
                {selectedFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="w-8 h-8 text-venom-yellow" />
                    <p className="text-[13px] font-medium text-foreground">{selectedFile.name}</p>
                    <p className="text-[11px] text-text-tertiary">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                      className="text-[11px] text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="w-8 h-8 text-text-tertiary" />
                    <p className="text-[13px] text-text-tertiary">
                      Drag and drop a project zip here, or click to browse
                    </p>
                    <p className="text-[11px] text-text-tertiary">
                      Upload your entire project as a .zip archive for full analysis
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Error */}
            {submitError && (
              <div className="flex items-center gap-2 p-3 border border-red-500/30 bg-red-500/10 rounded-md text-color-error text-[13px]">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {submitError.message}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleFileUpload}
                disabled={isPending || !selectedFile || !workspaceId}
                className="flex items-center gap-2 px-5 py-2 rounded-md btn-shimmer text-primary-foreground text-[13px] font-semibold disabled:opacity-50 transition-all active:scale-[0.98]"
              >
                {isUploadPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {isUploadPending ? 'Uploading...' : 'Upload & Analyze'}
              </button>
              <Link
                href={`/${workspaceSlug}/analysis`}
                className="px-5 py-2 rounded-md border border-border bg-card text-text-secondary text-[13px] font-medium hover:text-foreground transition-colors"
              >
                Cancel
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
