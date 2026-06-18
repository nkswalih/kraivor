'use client';

import { useState, useCallback } from 'react';
import { Upload, X, File, Loader2 } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  onUpload: (file: File) => Promise<void>;
}

export function UploadFileDialog({ open, onClose, onUpload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    if (f.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result as string);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await onUpload(file);
      setFile(null);
      setPreview(null);
      onClose();
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-[420px] rounded-xl border border-border bg-krait-surface1 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-[15px] font-medium text-foreground">Upload File</h2>
          <button onClick={onClose} className="p-1 text-text-tertiary hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">
          {!file ? (
            <label className="flex flex-col items-center gap-3 p-8 rounded-lg border-2 border-dashed border-border hover:border-venom-yellow/50 cursor-pointer transition-colors">
              <Upload className="w-8 h-8 text-text-tertiary" />
              <span className="text-[13px] text-text-tertiary">
                Drop a file here or click to browse
              </span>
              <span className="text-[11px] text-text-tertiary">
                Images, PDFs, and code files
              </span>
              <input
                type="file"
                className="hidden"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                accept="image/*,application/pdf,.py,.js,.ts,.tsx,.jsx,.json,.md,.txt,.css,.html"
              />
            </label>
          ) : (
            <div className="space-y-4">
              {preview ? (
                <img src={preview} alt="" className="w-full h-40 object-contain rounded-lg bg-krait-void" />
              ) : (
                <div className="flex items-center justify-center h-20 rounded-lg bg-krait-surface3">
                  <File className="w-8 h-8 text-text-tertiary" />
                </div>
              )}
              <div>
                <p className="text-[13px] text-foreground font-medium">{file.name}</p>
                <p className="text-[11px] text-text-tertiary">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { setFile(null); setPreview(null); }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border text-[13px] text-foreground hover:bg-krait-surface2"
                >
                  Remove
                </button>
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="flex-1 px-4 py-2 rounded-lg bg-venom-yellow text-black text-[13px] font-medium hover:brightness-110 transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  Upload
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
