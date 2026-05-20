'use client';

import React, { useState } from 'react';
import { AuthButton } from '@/components/auth/AuthButton';
import { AuthInput } from '@/components/auth/AuthInput';
import { sileo } from 'sileo';
import { Copy, Eye, EyeOff, Trash2, Key } from 'lucide-react';

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([
    { id: '1', name: 'Production API Key', key: 'kr_live_*************************', created: 'Oct 12, 2025', lastUsed: '2 mins ago' },
    { id: '2', name: 'Development Key', key: 'kr_test_*************************', created: 'Nov 05, 2025', lastUsed: 'Never' }
  ]);
  const [isCreating, setIsCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setIsCreating(true);
    setTimeout(() => {
      setKeys([{ 
        id: Date.now().toString(), 
        name: newKeyName, 
        key: 'kr_live_new_' + Math.random().toString(36).substring(7), 
        created: 'Just now', 
        lastUsed: 'Never' 
      }, ...keys]);
      setNewKeyName('');
      setIsCreating(false);
      sileo.success('API Key created successfully');
    }, 800);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    sileo.success('Copied to clipboard');
  };

  const deleteKey = (id: string) => {
    setKeys(keys.filter(k => k.id !== id));
    sileo.success('API Key revoked');
  };

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-xl font-semibold mb-1">API Keys</h2>
        <p className="text-sm text-gray-400">Manage API keys used to authenticate requests to Kraivor.</p>
      </div>

      <div className="border-t border-white/10 pt-8">
        <h3 className="text-lg font-medium mb-4">Create New Key</h3>
        <form onSubmit={handleCreate} className="flex gap-3 max-w-lg">
          <AuthInput 
            placeholder="e.g. Production App" 
            value={newKeyName} 
            onChange={(e) => setNewKeyName(e.target.value)} 
            className="flex-1"
          />
          <AuthButton type="submit" isLoading={isCreating} className="w-auto px-6 whitespace-nowrap">
            Create Key
          </AuthButton>
        </form>
      </div>

      <div className="border-t border-white/10 pt-8">
        <h3 className="text-lg font-medium mb-4">Active Keys</h3>
        <div className="space-y-4">
          {keys.map((item) => (
            <div key={item.id} className="p-5 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col sm:flex-row gap-4 sm:items-center justify-between hover:border-white/10 transition-colors">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-sm">{item.name}</h4>
                  <span className="text-[10px] text-gray-500 bg-[#151515] px-2 py-0.5 rounded border border-white/5">
                    Created {item.created}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <code className="text-sm text-primary font-mono bg-primary/10 px-2 py-1 rounded">
                    {item.key}
                  </code>
                  <button onClick={() => copyToClipboard(item.key)} className="text-gray-400 hover:text-white transition-colors" title="Copy Key">
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-3">Last used: {item.lastUsed}</p>
              </div>
              
              <button 
                onClick={() => deleteKey(item.id)}
                className="self-start sm:self-center p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                title="Revoke Key"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          {keys.length === 0 && (
            <div className="text-center py-10 border border-dashed border-white/10 rounded-xl">
              <Key className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-400">No active API keys</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

