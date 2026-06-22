'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Share2, Check, Search, Send } from 'lucide-react';
import { toast } from 'sonner';
import { useParams } from 'next/navigation';
import { copyToClipboard } from '@/lib/utils';

interface ShareDialogProps {
  discussionId: string;
  title: string;
}

export function ShareDialog({ discussionId, title }: ShareDialogProps) {
  const [open, setOpen] = useState(false);
  const params = useParams();
  const workspace = params?.workspace as string;
  const url =
    typeof window !== 'undefined'
      ? `${window.location.origin}/${workspace}/community/${discussionId}`
      : '';

  useEffect(() => {
    if (open) {
      copyToClipboard(url).then(ok => {
        if (ok) toast.success('Link copied to clipboard');
        else toast.error('Failed to copy link');
      });
    }
  }, [open, url]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 hover:text-foreground transition-colors"
      >
        <Share2 className="w-4 h-4" /> Share
      </button>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-md mx-4 shadow-xl animate-fade-up"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-medium text-foreground">Share</h2>
          <button
            onClick={() => setOpen(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="space-y-2">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              Share via
            </p>
            <div className="grid grid-cols-4 gap-3">
              <a
                href={`https://facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <svg className="w-5 h-5 text-[#1877F2]" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                </svg>
                <span className="text-[10px] text-muted-foreground">Facebook</span>
              </a>
              <a
                href={`https://wa.me/?text=${encodeURIComponent(title + ' ' + url)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <svg className="w-5 h-5 text-[#25D366]" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                <span className="text-[10px] text-muted-foreground">WhatsApp</span>
              </a>
              <a
                href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(title + ' ' + url)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <svg className="w-5 h-5 text-foreground" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
                <span className="text-[10px] text-muted-foreground">X</span>
              </a>
              <a
                href={`mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <svg
                  className="w-5 h-5 text-muted-foreground"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
                <span className="text-[10px] text-muted-foreground">Email</span>
              </a>
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Send to team member
            </p>
            <TeamMemberSearch discussionId={discussionId} />
          </div>

          <div className="pt-2 border-t border-border">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">
              Link
            </p>
            <button
              onClick={async () => {
                const ok = await copyToClipboard(url);
                if (ok) toast.success('Link copied to clipboard');
                else toast.error('Failed to copy link');
              }}
              className="w-full flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-[12px] text-muted-foreground hover:text-foreground transition-colors overflow-hidden"
            >
              <span className="truncate flex-1 text-left font-mono">{url}</span>
              <Check className="w-3.5 h-3.5 shrink-0" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TeamMemberSearch({ discussionId }: { discussionId: string }) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<{
    id: string;
    name: string;
    avatar_url?: string;
  } | null>(null);

  const handleSend = () => {
    if (!selected) return;
    toast.success(`Link sent to ${selected.name} via DM`);
    setSelected(null);
    setQuery('');
  };

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search team members..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full bg-background border border-border rounded-md pl-8 pr-3 py-2 text-[12px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
        />
      </div>
      {selected && (
        <div className="flex items-center justify-between bg-muted/50 rounded-md px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[9px] font-medium">
              {selected.name.charAt(0)}
            </div>
            <span className="text-[12px] text-foreground">{selected.name}</span>
          </div>
          <button
            onClick={handleSend}
            className="flex items-center gap-1 text-[11px] font-medium text-primary hover:text-primary/80 transition-colors"
          >
            <Send className="w-3 h-3" /> Send
          </button>
        </div>
      )}
    </div>
  );
}
