'use client';

import { useState, useRef } from 'react';
import { Upload, X, FileText, Image, Mic, Loader2, Check } from 'lucide-react';
import { useIngestFile, useIngestText } from '@/lib/hooks/use-knowledge-dashboard';

export function KnowledgeUploadDialog({
  workspaceId,
  onClose,
}: {
  workspaceId: string;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<'file' | 'text'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ingestFile = useIngestFile(workspaceId);
  const ingestText = useIngestText(workspaceId);

  const handleFileUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      await ingestFile.mutateAsync({ file: selectedFile });
      setDone(true);
      setTimeout(onClose, 1500);
    } catch {
      setUploading(false);
    }
  };

  const handleTextUpload = async () => {
    if (!textContent.trim()) return;
    setUploading(true);
    try {
      await ingestText.mutateAsync({ text: textContent, title: textTitle || undefined });
      setDone(true);
      setTimeout(onClose, 1500);
    } catch {
      setUploading(false);
    }
  };

  const getFileIcon = (name: string) => {
    const ext = name.split('.').pop()?.toLowerCase();
    if (['pdf'].includes(ext || '')) return <FileText className="w-5 h-5 text-red-400" />;
    if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext || '')) return <Image className="w-5 h-5 text-blue-400" />;
    if (['wav', 'mp3', 'm4a', 'ogg', 'flac'].includes(ext || '')) return <Mic className="w-5 h-5 text-green-400" />;
    return <FileText className="w-5 h-5 text-muted-foreground" />;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onMouseDown={e => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-lg bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#27272A]">
          <h2 className="text-[15px] font-semibold text-[#FAFAFA] flex items-center gap-2">
            <Upload className="w-4 h-4 text-venom-yellow" /> Upload Knowledge
          </h2>
          <button onClick={onClose} className="p-1 text-text-tertiary hover:text-[#FAFAFA] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          {/* Tabs */}
          <div className="flex gap-1 mb-4">
            {(['file', 'text'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
                  tab === t
                    ? 'bg-venom-yellow/10 text-venom-yellow'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t === 'file' ? 'File Upload' : 'Paste Text'}
              </button>
            ))}
          </div>

          {done ? (
            <div className="flex flex-col items-center py-8">
              <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mb-3">
                <Check className="w-6 h-6 text-green-400" />
              </div>
              <p className="text-[13px] font-medium text-foreground">Uploaded successfully</p>
              <p className="text-[11px] text-muted-foreground mt-1">Processing your knowledge...</p>
            </div>
          ) : tab === 'file' ? (
            <div>
              {/* Drop zone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => {
                  e.preventDefault();
                  const file = e.dataTransfer.files[0];
                  if (file) setSelectedFile(file);
                }}
                className="border-2 border-dashed border-[#27272A] rounded-lg p-8 text-center cursor-pointer hover:border-venom-yellow/30 transition-colors"
              >
                {selectedFile ? (
                  <div className="flex items-center gap-3">
                    {getFileIcon(selectedFile.name)}
                    <div className="text-left min-w-0">
                      <div className="text-[13px] text-foreground truncate">{selectedFile.name}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {(selectedFile.size / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-[13px] text-muted-foreground">
                      Drop a file or click to browse
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      PDF, images, audio — up to 50MB
                    </p>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.wav,.mp3,.m4a,.ogg,.flac"
                className="hidden"
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (file) setSelectedFile(file);
                }}
              />
              <button
                onClick={handleFileUpload}
                disabled={!selectedFile || uploading}
                className="w-full mt-4 px-4 py-2 bg-venom-yellow text-black text-[13px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                {uploading ? 'Uploading...' : 'Upload File'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <input
                value={textTitle}
                onChange={e => setTextTitle(e.target.value)}
                placeholder="Title (optional)"
                className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
              />
              <textarea
                value={textContent}
                onChange={e => setTextContent(e.target.value)}
                placeholder="Paste your text content here..."
                rows={8}
                className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors resize-none"
              />
              <button
                onClick={handleTextUpload}
                disabled={!textContent.trim() || uploading}
                className="w-full px-4 py-2 bg-venom-yellow text-black text-[13px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                {uploading ? 'Processing...' : 'Ingest Text'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
