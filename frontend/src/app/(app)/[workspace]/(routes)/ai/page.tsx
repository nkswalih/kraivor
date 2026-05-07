'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/shadcn';
import { Button, Input } from '@/components/ui/shadcn';
import { MessageSquare, Plus } from 'lucide-react';

export default function AIPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Assistant</h1>
          <p className="text-muted-foreground">Chat with AI to analyze and improve your code</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="cursor-pointer hover:border-primary transition-colors">
          <CardHeader className="flex flex-row items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <MessageSquare className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Start a conversation</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Ask questions about your code, request refactoring, or get security recommendations
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}