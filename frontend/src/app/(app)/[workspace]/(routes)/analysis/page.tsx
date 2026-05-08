'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/shadcn';
import { Button, Input } from '@/components/ui/shadcn';
import { GitBranch, Plus, Search } from 'lucide-react';

export default function AnalysisPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Repository Analysis</h1>
          <p className="text-muted-foreground">Connect and analyze your code repositories</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Connect Repository
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-10" placeholder="Search repositories..." />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="cursor-pointer hover:border-primary transition-colors">
          <CardHeader className="flex flex-row items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <GitBranch className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Connect a repository</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Connect your GitHub, GitLab, or Bitbucket repository to start analyzing
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}