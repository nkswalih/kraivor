'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, X, File, Loader2 } from 'lucide-react';

interface FileEntry {
  file: File;
  preview: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
}

export function UploadFileDialog({ open, onClose, onUpload }: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const addMoreRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((files: FileList | File[]) => {
    const newEntries: FileEntry[] = Array.from(files).map(file => ({
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
    }));
    setEntries(prev => [...prev, ...newEntries]);
  }, []);

  const removeEntry = useCallback((index: number) => {
    setEntries(prev => {
      const entry = prev[index];
      if (entry?.preview) URL.revokeObjectURL(entry.preview);
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }, [addFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
    }
    e.target.value = '';
  }, [addFiles]);

  const handleUpload = async () => {
    if (entries.length === 0) return;
    setUploading(true);
    try {
      await onUpload(entries.map(e => e.file));
      entries.forEach(e => { if (e.preview) URL.revokeObjectURL(e.preview); });
      setEntries([]);
      onClose();
    } finally {
      setUploading(false);
    }
  };

  const handleClose = useCallback(() => {
    if (uploading) return;
    entries.forEach(e => { if (e.preview) URL.revokeObjectURL(e.preview); });
    setEntries([]);
    onClose();
  }, [uploading, entries, onClose]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="w-[480px] max-h-[80vh] flex flex-col rounded-xl border border-border bg-krait-surface1 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <h2 className="text-[15px] font-medium text-foreground">Upload Files</h2>
          <button
            onClick={handleClose}
            className="p-1 text-text-tertiary hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {entries.length === 0 ? (
            <div
              className={`flex flex-col items-center gap-3 p-8 rounded-lg border-2 border-dashed cursor-pointer transition-colors ${
                dragOver
                  ? 'border-venom-yellow bg-venom-yellow/5'
                  : 'border-border hover:border-venom-yellow/50'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="w-8 h-8 text-text-tertiary" />
              <span className="text-[13px] text-text-tertiary">
                Drop files here or click to browse
              </span>
              <span className="text-[11px] text-text-tertiary">
                Any file type supported
              </span>
              <input
                ref={inputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleInputChange}
              />
            </div>
          ) : (
            <div className="space-y-2">
              {entries.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-krait-surface2"
                >
                  {entry.preview ? (
                    <img
                      src={entry.preview}
                      alt=""
                      className="w-10 h-10 rounded object-cover shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded bg-krait-surface3 flex items-center justify-center shrink-0">
                      <File className="w-5 h-5 text-text-tertiary" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] text-foreground truncate">
                      {entry.file.name}
                    </p>
                    <p className="text-[11px] text-text-tertiary">
                      {formatSize(entry.file.size)}
                    </p>
                  </div>
                  <button
                    disabled={uploading}
                    onClick={() => removeEntry(i)}
                    className="p-1 text-text-tertiary hover:text-red-400 transition-colors disabled:opacity-30"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              <div
                className="flex items-center justify-center gap-2 py-2 rounded-lg border border-dashed border-border cursor-pointer hover:border-venom-yellow/50 transition-colors text-[12px] text-text-tertiary hover:text-foreground"
                onClick={() => addMoreRef.current?.click()}
              >
                <Upload className="w-3.5 h-3.5" />
                Add more files
                <input
                  ref={addMoreRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleInputChange}
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border shrink-0">
          <button
            onClick={handleClose}
            disabled={uploading}
            className="px-4 py-2 rounded-lg border border-border text-[13px] text-foreground hover:bg-krait-surface2 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={entries.length === 0 || uploading}
            className="px-4 py-2 rounded-lg bg-venom-yellow text-black text-[13px] font-medium hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
          >
            {uploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            {uploading
              ? 'Uploading...'
              : `Upload${entries.length > 0 ? ` (${entries.length} file${entries.length > 1 ? 's' : ''})` : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
