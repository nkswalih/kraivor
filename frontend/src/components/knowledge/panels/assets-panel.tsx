'use client';

import { useState, useCallback, useEffect } from 'react';
import { Upload, File, Image, Trash2, Loader2 } from 'lucide-react';
import { knowledgeAssetApi } from '@/lib/knowledge/knowledge-api';
import type { KnowledgeAssetReference } from '@/types/knowledge';
import { UploadFileDialog } from '../dialogs/upload-file-dialog';

interface Props {
  spaceId: string;
}

export function AssetsPanel({ spaceId }: Props) {
  const [assets, setAssets] = useState<KnowledgeAssetReference[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await knowledgeAssetApi.list(spaceId);
      setAssets(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [spaceId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleUpload = useCallback(async (files: File[]) => {
    setUploading(true);
    try {
      for (const file of files) {
        await knowledgeAssetApi.upload(spaceId, file);
      }
      await load();
    } catch {
      // ignore
    } finally {
      setUploading(false);
    }
  }, [spaceId, load]);

  const handleDelete = useCallback(async (assetId: string) => {
    try {
      await knowledgeAssetApi.delete(spaceId, assetId);
      setAssets(prev => prev.filter(a => a.id !== assetId));
    } catch {
      // ignore
    }
  }, [spaceId]);

  const fileTypeIcon = (mime: string | null | undefined) => {
    if (mime?.startsWith('image/')) return <Image className="w-4 h-4" />;
    return <File className="w-4 h-4" />;
  };

  const formatSize = (bytes: number | null | undefined) => {
    if (bytes == null) return '-';
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="p-3 space-y-3 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
          Assets
        </h3>
        <button
          className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3 transition-colors disabled:opacity-50"
          onClick={() => setDialogOpen(true)}
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Upload className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 text-text-tertiary animate-spin" />
        </div>
      ) : assets.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Upload className="w-8 h-8 text-text-tertiary mb-2" />
          <p className="text-[13px] text-text-tertiary mb-1">No assets yet</p>
          <p className="text-[11px] text-text-tertiary max-w-[180px]">
            Upload images, PDFs, or files to use on the canvas
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {assets.map(asset => (
            <div
              key={asset.id}
              draggable={!!asset.url}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-krait-surface3 group cursor-grab active:cursor-grabbing"
              onDragStart={e => {
                e.dataTransfer.setData(
                  'application/json',
                  JSON.stringify({
                    type: 'asset',
                    url: asset.url,
                    mimeType: asset.mime_type,
                    fileName: asset.file_name,
                    assetId: asset.id,
                  }),
                );
                e.dataTransfer.effectAllowed = 'copy';
              }}
            >
              <span className="text-venom-yellow">
                {fileTypeIcon(asset.mime_type)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] text-foreground truncate">
                  {asset.file_name}
                </p>
                <p className="text-[10px] text-text-tertiary">
                  {formatSize(asset.file_size)}
                </p>
              </div>
              <button
                className="p-0.5 text-text-tertiary opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all"
                onClick={() => handleDelete(asset.id)}
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <UploadFileDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onUpload={handleUpload}
      />
    </div>
  );
}
