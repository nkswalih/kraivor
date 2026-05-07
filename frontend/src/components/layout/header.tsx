'use client';

import { useAuth } from '@/lib/hooks';
import { Avatar, AvatarFallback, AvatarImage, Button, Separator } from '@/components/ui/shadcn';
import { getInitials } from '@/lib/utils';
import { LogOut, User, Bell } from 'lucide-react';

interface HeaderProps {
  workspaceName?: string;
}

export function Header({ workspaceName }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold">{workspaceName || 'Dashboard'}</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
        </Button>
        <Separator orientation="vertical" className="h-6" />
        <div className="flex items-center gap-2">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user?.avatar} alt={user?.name} />
            <AvatarFallback>{user ? getInitials(user.name) : 'U'}</AvatarFallback>
          </Avatar>
          <div className="hidden text-sm md:block">
            <p className="font-medium">{user?.name || 'User'}</p>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => logout()}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}