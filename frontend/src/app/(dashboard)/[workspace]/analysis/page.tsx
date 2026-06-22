'use client';

import { useState } from 'react';
import {
  Activity,
  Shield,
  Zap,
  Server,
  GitBranch,
  Search,
  Filter,
  MoreHorizontal,
  AlertCircle,
} from 'lucide-react';

const TABS = ['All Reports', 'Security', 'Architecture', 'Performance', 'DevOps'];

const MOCK_REPORTS = [
  {
    id: 'ANL-104',
    repo: 'auth-service',
    issue: 'Hardcoded JWT secret in environment file',
    engine: 'Security',
    severity: 'Critical',
    date: '2h ago',
  },
  {
    id: 'ANL-103',
    repo: 'kraivor-core',
    issue: 'Circular dependency detected in /modules',
    engine: 'Architecture',
    severity: 'High',
    date: '5h ago',
  },
  {
    id: 'ANL-102',
    repo: 'frontend-monorepo',
    issue: 'Unoptimized bundle size > 2MB',
    engine: 'Performance',
    severity: 'Medium',
    date: '1d ago',
  },
  {
    id: 'ANL-101',
    repo: 'payment-gateway',
    issue: 'Missing rate limiter on /charge endpoint',
    engine: 'Security',
    severity: 'High',
    date: '2d ago',
  },
  {
    id: 'ANL-100',
    repo: 'legacy-api',
    issue: 'Dockerfile missing multi-stage build',
    engine: 'DevOps',
    severity: 'Low',
    date: '3d ago',
  },
];

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState('All Reports');

  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Header & Controls */}
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <h1 className="text-lg font-medium flex items-center gap-2 mb-4 text-foreground">
          <Activity className="w-5 h-5 text-primary" /> Repository Analysis
        </h1>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Tabs */}
          <div className="flex items-center gap-1 bg-card border border-border p-1 rounded-lg w-fit">
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-[12px] font-medium rounded-md transition-all ${
                  activeTab === tab
                    ? 'bg-background border border-border text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Filters & Search */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search reports..."
                className="w-[200px] bg-card border border-border text-[12px] text-foreground rounded-md pl-8 pr-3 py-1.5 focus:border-primary focus:outline-none transition-colors"
              />
            </div>
            <button className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors">
              <Filter className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Data Table Area */}
      <div className="flex-1 overflow-y-auto bg-background p-6">
        <div className="border border-border rounded-lg bg-card overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-[80px_1.5fr_2.5fr_1fr_1fr_60px] gap-4 p-3 border-b border-border bg-background/50 text-[12px] font-medium text-muted-foreground">
            <div>ID</div>
            <div>Repository</div>
            <div>Issue Summary</div>
            <div>Category</div>
            <div>Date</div>
            <div></div>
          </div>

          {/* Table Rows */}
          <div className="divide-y divide-border">
            {MOCK_REPORTS.map(report => (
              <div
                key={report.id}
                className="grid grid-cols-[80px_1.5fr_2.5fr_1fr_1fr_60px] gap-4 p-3 items-center hover:bg-white/[0.02] transition-colors cursor-pointer text-[13px] group"
              >
                <div className="font-mono text-muted-foreground text-[12px]">{report.id}</div>
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <GitBranch className="w-3.5 h-3.5 text-muted-foreground" />
                  {report.repo}
                </div>
                <div className="text-foreground truncate pr-4">{report.issue}</div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  {report.engine === 'Security' && <Shield className="w-3.5 h-3.5 text-red-400" />}
                  {report.engine === 'Architecture' && (
                    <Server className="w-3.5 h-3.5 text-primary" />
                  )}
                  {report.engine === 'Performance' && (
                    <Zap className="w-3.5 h-3.5 text-yellow-400" />
                  )}
                  {report.engine === 'DevOps' && <Activity className="w-3.5 h-3.5 text-blue-400" />}
                  <span className="text-[12px]">{report.engine}</span>
                </div>
                <div className="text-muted-foreground text-[12px]">{report.date}</div>
                <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
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
