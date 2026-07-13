'use client';

import { useState } from 'react';
import { Package, Download, Loader2, Check } from 'lucide-react';
import { useTemplates, useImportTemplate } from '@/lib/hooks/use-knowledge-dashboard';

export function KnowledgeTemplates({ workspaceId }: { workspaceId: string }) {
  const [imported, setImported] = useState<string | null>(null);
  const templates = useTemplates();
  const importTemplate = useImportTemplate(workspaceId);

  const handleImport = async (templateId: string) => {
    try {
      await importTemplate.mutateAsync(templateId);
      setImported(templateId);
      setTimeout(() => setImported(null), 2000);
    } catch {
      // error handled by mutation
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {templates.isLoading ? (
          <>
            <div className="h-32 bg-card border border-border rounded-lg animate-pulse" />
            <div className="h-32 bg-card border border-border rounded-lg animate-pulse" />
          </>
        ) : (
          templates.data?.templates.map(t => (
            <div key={t.template_id} className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-venom-yellow" />
                  <span className="text-[13px] font-medium text-foreground">{t.name}</span>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 bg-accent rounded shrink-0">{t.category}</span>
              </div>
              <p className="text-[11px] text-muted-foreground line-clamp-2 mb-3">{t.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground">{t.item_count} items</span>
                  <span className="text-[10px] text-muted-foreground">by {t.author}</span>
                </div>
                <button
                  onClick={() => handleImport(t.template_id)}
                  disabled={importTemplate.isPending || imported === t.template_id}
                  className="px-3 py-1 bg-venom-yellow/10 text-venom-yellow text-[11px] font-medium rounded hover:bg-venom-yellow/20 transition-colors disabled:opacity-50 flex items-center gap-1"
                >
                  {imported === t.template_id ? (
                    <Check className="w-3 h-3" />
                  ) : importTemplate.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Download className="w-3 h-3" />
                  )}
                  {imported === t.template_id ? 'Imported' : 'Import'}
                </button>
              </div>
              {t.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {t.tags.map(tag => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-accent rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
