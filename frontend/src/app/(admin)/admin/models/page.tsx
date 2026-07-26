'use client';

import { useEffect, useState, useCallback } from 'react';
import { Plus, Pencil, Trash2, Loader2, Server, Route, Cpu, Zap } from 'lucide-react';
import { adminEndpoints } from '@/lib/api/endpoints/admin';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/shadcn/tabs';
import { Button } from '@/components/ui/shadcn/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/shadcn/dialog';
import { Input } from '@/components/ui/shadcn/input';
import { Label } from '@/components/ui/shadcn/label';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/shadcn/select';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/shadcn/table';
import { Checkbox } from '@/components/ui/shadcn/checkbox';
import { Badge } from '@/components/ui/shadcn/badge';
import { Spinner } from '@/components/ui/shadcn/spinner';
import { ICON_OPTIONS } from '@/components/ai/ai-model-icons';

interface Model {
  id: string;
  frontend_id: string;
  model_id: string;
  display_name: string;
  provider_name: string;
  status: string;
  tier: string;
  context_window: number;
  max_output_tokens: number;
  supports_vision: boolean;
  supports_tools: boolean;
  supports_reasoning: boolean;
  latency_display?: string;
  icon_key?: string;
}

interface Route {
  id: string;
  task_name: string;
  primary_model_id: string;
  fallback_model_id: string;
  max_tokens: number;
  timeout_seconds: number;
}

interface Provider {
  id: string;
  provider_name: string;
  display_name: string;
  base_url: string;
  is_active: boolean;
  rate_limit_rpm: number;
  rate_limit_tpm: number;
}

type Tab = 'models' | 'routes' | 'providers';

const TASK_NAMES = [
  'greeting',
  'simple_qa',
  'complex_analysis',
  'code_generation',
  'summarization',
  'translation',
  'creative_writing',
  'data_extraction',
  'tool_calling',
  'vision_analysis',
];

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-text-tertiary">
      <Icon className="w-10 h-10 mb-3 opacity-40" />
      <p className="text-[13px]">{message}</p>
    </div>
  );
}

function ConfirmDeleteDialog({
  open,
  onOpenChange,
  onConfirm,
  label,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  label: string;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {label}</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this {label.toLowerCase()}? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <DialogClose asChild>
            <Button variant="outline" className="bg-krait-surface2 border-krait-border text-text-secondary hover:bg-krait-surface1 text-[13px]">
              Cancel
            </Button>
          </DialogClose>
          <Button
            variant="destructive"
            onClick={onConfirm}
            className="bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20 hover:bg-[#ef4444]/20 text-[13px]"
          >
            Delete
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Models Tab ──────────────────────────────────────────────────────────────

function ModelsTab() {
  const [models, setModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Model | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    frontend_id: '',
    model_id: '',
    display_name: '',
    provider_name: '',
    status: 'active',
    tier: 'standard',
    context_window: 0,
    max_output_tokens: 0,
    supports_vision: false,
    supports_tools: false,
    supports_reasoning: false,
    icon_key: '',
  });

  const fetchData = useCallback(async () => {
    try {
      const [modelsRes, providersRes] = await Promise.all([
        adminEndpoints.listModels(),
        adminEndpoints.listProviders(),
      ]);
      const m = modelsRes as { models?: Model[] };
      const p = providersRes as { providers?: Provider[] };
      setModels(m.models ?? []);
      setProviders(p.providers ?? []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = () => {
    setForm({
      frontend_id: '',
      model_id: '',
      display_name: '',
      provider_name: '',
      status: 'active',
      tier: 'standard',
      context_window: 0,
      max_output_tokens: 0,
      supports_vision: false,
      supports_tools: false,
      supports_reasoning: false,
      icon_key: '',
    });
    setEditingModel(null);
  };

  const openCreate = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEdit = (model: Model) => {
    setEditingModel(model);
    setForm({
      frontend_id: model.frontend_id,
      model_id: model.model_id,
      display_name: model.display_name,
      provider_name: model.provider_name,
      status: model.status,
      tier: model.tier,
      context_window: model.context_window,
      max_output_tokens: model.max_output_tokens,
      supports_vision: model.supports_vision,
      supports_tools: model.supports_tools,
      supports_reasoning: model.supports_reasoning,
      icon_key: model.icon_key || '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingModel) {
        await adminEndpoints.updateModel(editingModel.id, form);
      } else {
        await adminEndpoints.createModel(form);
      }
      await adminEndpoints.invalidateCache();
      setDialogOpen(false);
      resetForm();
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await adminEndpoints.deleteModel(deleteTarget.id);
      await adminEndpoints.invalidateCache();
      setDeleteTarget(null);
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    }
  };

  const tierColor = (tier: string) => {
    switch (tier) {
      case 'fast': return 'success';
      case 'standard': return 'default';
      case 'balanced': return 'warning';
      case 'extended': return 'venom';
      default: return 'default';
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-text-tertiary">{models.length} model{models.length !== 1 ? 's' : ''}</p>
        <Button
          onClick={openCreate}
          className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px] h-8"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          Add Model
        </Button>
      </div>

      <div className="bg-krait-obsidian border border-krait-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="md" className="text-venom-yellow" />
          </div>
        ) : models.length === 0 ? (
          <EmptyState icon={Cpu} message="No models configured yet" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-krait-border">
                <TableHead className="w-10"></TableHead>
                <TableHead>Frontend ID</TableHead>
                <TableHead>Backend Model</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {models.map((model) => (
                <TableRow key={model.id} className="border-krait-border hover:bg-krait-surface1">
                  <TableCell className="py-2.5">
                    <span className="inline-flex items-center justify-center w-5 h-5">
                      {(() => {
                        const opt = ICON_OPTIONS.find(o => o.key === model.icon_key);
                        if (opt) {
                          const IconComp = opt.component;
                          return <IconComp size={16} className="shrink-0" />;
                        }
                        return <div className="w-3.5 h-3.5 rounded-sm bg-krait-surface2" />;
                      })()}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-[12px]">{model.frontend_id}</TableCell>
                  <TableCell className="font-mono text-[12px] text-text-tertiary">{model.model_id}</TableCell>
                  <TableCell>{model.provider_name}</TableCell>
                  <TableCell>
                    <Badge variant={model.status === 'active' ? 'success' : 'outline'}>
                      {model.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={tierColor(model.tier) as 'success' | 'default' | 'warning' | 'venom'}>
                      {model.tier}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-text-primary"
                        onClick={() => openEdit(model)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-[#ef4444]"
                        onClick={() => setDeleteTarget(model)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setDialogOpen(open); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingModel ? 'Edit Model' : 'Add Model'}</DialogTitle>
            <DialogDescription>
              {editingModel ? 'Update model configuration.' : 'Configure a new LLM model.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Frontend ID</Label>
              <Input
                value={form.frontend_id}
                onChange={(e) => setForm({ ...form, frontend_id: e.target.value })}
                placeholder="e.g. groq-qwen3.6-27b, claude-fable-5"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Model ID (backend)</Label>
              <Input
                value={form.model_id}
                onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                placeholder="e.g. qwen/qwen3.6-27b, anthropic/claude-fable-5"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Display Name</Label>
              <Input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                placeholder="e.g. GPT-4o, Claude 3.5 Sonnet"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Provider</Label>
              <Select value={form.provider_name} onValueChange={(v) => setForm({ ...form, provider_name: v })}>
                <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((p) => (
                    <SelectItem key={p.id} value={p.provider_name}>
                      {p.provider_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Icon</Label>
              <div className="flex flex-wrap gap-1.5">
                {ICON_OPTIONS.map((opt) => {
                  const IconComp = opt.component;
                  const selected = form.icon_key === opt.key;
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      title={opt.label}
                      onClick={() => setForm({ ...form, icon_key: selected ? '' : opt.key })}
                      className={`flex items-center justify-center w-8 h-8 rounded-md border transition-colors ${
                        selected
                          ? 'bg-venom-yellow/15 border-venom-yellow/50 text-venom-yellow'
                          : 'bg-krait-surface2 border-krait-border text-text-tertiary hover:text-text-secondary hover:border-text-tertiary'
                      }`}
                    >
                      <span className="inline-flex items-center justify-center w-4 h-4">
                        <IconComp size={16} className="shrink-0" />
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Status</Label>
                <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                  <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Tier</Label>
                <Select value={form.tier} onValueChange={(v) => setForm({ ...form, tier: v })}>
                  <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fast">Fast</SelectItem>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="extended">Extended</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Context Window</Label>
                <Input
                  type="number"
                  value={form.context_window || ''}
                  onChange={(e) => setForm({ ...form, context_window: Number(e.target.value) })}
                  placeholder="128000"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Max Output Tokens</Label>
                <Input
                  type="number"
                  value={form.max_output_tokens || ''}
                  onChange={(e) => setForm({ ...form, max_output_tokens: Number(e.target.value) })}
                  placeholder="4096"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-[12px] text-text-secondary">Capabilities</Label>
              <div className="flex items-center gap-4">
                {(['supports_vision', 'supports_tools', 'supports_reasoning'] as const).map((key) => (
                  <label key={key} className="flex items-center gap-2 text-[13px] text-text-secondary cursor-pointer">
                    <Checkbox
                      checked={form[key]}
                      onCheckedChange={(checked) => setForm({ ...form, [key]: !!checked })}
                    />
                    {key.replace('supports_', '')}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <DialogClose asChild>
              <Button variant="outline" className="bg-krait-surface2 border-krait-border text-text-secondary hover:bg-krait-surface1 text-[13px]">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSave}
              disabled={saving || !form.frontend_id || !form.model_id || !form.display_name || !form.provider_name}
              className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px]"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />}
              {editingModel ? 'Update' : 'Create'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDeleteDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        label="Model"
      />
    </>
  );
}

// ── Routes Tab ──────────────────────────────────────────────────────────────

function RoutesTab() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<Route | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Route | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    task_name: '',
    primary_model_id: '',
    fallback_model_id: '',
    max_tokens: 0,
    timeout_seconds: 30,
  });

  const fetchData = useCallback(async () => {
    try {
      const [routesRes, modelsRes] = await Promise.all([
        adminEndpoints.listRoutes(),
        adminEndpoints.listModels(),
      ]);
      const r = routesRes as { routes?: Route[] };
      const m = modelsRes as { models?: Model[] };
      setRoutes(r.routes ?? []);
      setModels(m.models ?? []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = () => {
    setForm({ task_name: '', primary_model_id: '', fallback_model_id: '', max_tokens: 0, timeout_seconds: 30 });
    setEditingRoute(null);
  };

  const openCreate = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEdit = (route: Route) => {
    setEditingRoute(route);
    setForm({
      task_name: route.task_name,
      primary_model_id: route.primary_model_id,
      fallback_model_id: route.fallback_model_id,
      max_tokens: route.max_tokens,
      timeout_seconds: route.timeout_seconds,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingRoute) {
        await adminEndpoints.updateRoute(editingRoute.id, form);
      } else {
        await adminEndpoints.createRoute(form);
      }
      await adminEndpoints.invalidateCache();
      setDialogOpen(false);
      resetForm();
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await adminEndpoints.deleteRoute(deleteTarget.id);
      await adminEndpoints.invalidateCache();
      setDeleteTarget(null);
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-text-tertiary">{routes.length} route{routes.length !== 1 ? 's' : ''}</p>
        <Button
          onClick={openCreate}
          className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px] h-8"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          Add Route
        </Button>
      </div>

      <div className="bg-krait-obsidian border border-krait-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="md" className="text-venom-yellow" />
          </div>
        ) : routes.length === 0 ? (
          <EmptyState icon={Route} message="No routes configured yet" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-krait-border">
                <TableHead>Task Name</TableHead>
                <TableHead>Primary Model</TableHead>
                <TableHead>Fallback Model</TableHead>
                <TableHead>Max Tokens</TableHead>
                <TableHead>Timeout</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route) => (
                <TableRow key={route.id} className="border-krait-border hover:bg-krait-surface1">
                  <TableCell className="font-medium">{route.task_name}</TableCell>
                  <TableCell className="font-mono text-[12px]">{route.primary_model_id}</TableCell>
                  <TableCell className="font-mono text-[12px]">{route.fallback_model_id}</TableCell>
                  <TableCell>{route.max_tokens?.toLocaleString()}</TableCell>
                  <TableCell>{route.timeout_seconds}s</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-text-primary"
                        onClick={() => openEdit(route)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-[#ef4444]"
                        onClick={() => setDeleteTarget(route)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setDialogOpen(open); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingRoute ? 'Edit Route' : 'Add Route'}</DialogTitle>
            <DialogDescription>
              {editingRoute ? 'Update task route configuration.' : 'Route a task to specific models.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Task Name</Label>
              <Select value={form.task_name} onValueChange={(v) => setForm({ ...form, task_name: v })}>
                <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                  <SelectValue placeholder="Select task" />
                </SelectTrigger>
                <SelectContent>
                  {TASK_NAMES.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Primary Model</Label>
              <Select value={form.primary_model_id} onValueChange={(v) => setForm({ ...form, primary_model_id: v })}>
                <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                  <SelectValue placeholder="Select primary model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.id} value={m.model_id}>
                      {m.model_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Fallback Model</Label>
              <Select value={form.fallback_model_id} onValueChange={(v) => setForm({ ...form, fallback_model_id: v })}>
                <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                  <SelectValue placeholder="Select fallback model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.id} value={m.model_id}>
                      {m.model_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Max Tokens</Label>
                <Input
                  type="number"
                  value={form.max_tokens || ''}
                  onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })}
                  placeholder="4096"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Timeout (seconds)</Label>
                <Input
                  type="number"
                  value={form.timeout_seconds || ''}
                  onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })}
                  placeholder="30"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <DialogClose asChild>
              <Button variant="outline" className="bg-krait-surface2 border-krait-border text-text-secondary hover:bg-krait-surface1 text-[13px]">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSave}
              disabled={saving || !form.task_name || !form.primary_model_id}
              className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px]"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />}
              {editingRoute ? 'Update' : 'Create'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDeleteDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        label="Route"
      />
    </>
  );
}

// ── Providers Tab ───────────────────────────────────────────────────────────

function ProvidersTab() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Provider | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    provider_name: '',
    display_name: '',
    base_url: '',
    is_active: true,
    rate_limit_rpm: 0,
    rate_limit_tpm: 0,
  });

  const fetchData = useCallback(async () => {
    try {
      const res = await adminEndpoints.listProviders();
      const d = res as { providers?: Provider[] };
      setProviders(d.providers ?? []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = () => {
    setForm({ provider_name: '', display_name: '', base_url: '', is_active: true, rate_limit_rpm: 0, rate_limit_tpm: 0 });
    setEditingProvider(null);
  };

  const openCreate = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setForm({
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      base_url: provider.base_url,
      is_active: provider.is_active,
      rate_limit_rpm: provider.rate_limit_rpm,
      rate_limit_tpm: provider.rate_limit_tpm,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingProvider) {
        await adminEndpoints.updateProvider(editingProvider.id, form);
      } else {
        await adminEndpoints.createProvider(form);
      }
      await adminEndpoints.invalidateCache();
      setDialogOpen(false);
      resetForm();
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await adminEndpoints.deleteProvider(deleteTarget.id);
      await adminEndpoints.invalidateCache();
      setDeleteTarget(null);
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-text-tertiary">{providers.length} provider{providers.length !== 1 ? 's' : ''}</p>
        <Button
          onClick={openCreate}
          className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px] h-8"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          Add Provider
        </Button>
      </div>

      <div className="bg-krait-obsidian border border-krait-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="md" className="text-venom-yellow" />
          </div>
        ) : providers.length === 0 ? (
          <EmptyState icon={Server} message="No providers configured yet" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-krait-border">
                <TableHead>Provider Name</TableHead>
                <TableHead>Base URL</TableHead>
                <TableHead>Active</TableHead>
                <TableHead>Rate Limit (RPM / TPM)</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {providers.map((provider) => (
                <TableRow key={provider.id} className="border-krait-border hover:bg-krait-surface1">
                  <TableCell className="font-medium">{provider.provider_name}</TableCell>
                  <TableCell className="font-mono text-[12px] text-text-secondary max-w-[240px] truncate">
                    {provider.base_url}
                  </TableCell>
                  <TableCell>
                    <Badge variant={provider.is_active ? 'success' : 'outline'}>
                      {provider.is_active ? 'active' : 'inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {provider.rate_limit_rpm?.toLocaleString()} / {provider.rate_limit_tpm?.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-text-primary"
                        onClick={() => openEdit(provider)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-text-tertiary hover:text-[#ef4444]"
                        onClick={() => setDeleteTarget(provider)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setDialogOpen(open); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingProvider ? 'Edit Provider' : 'Add Provider'}</DialogTitle>
            <DialogDescription>
              {editingProvider ? 'Update provider configuration.' : 'Register a new LLM provider.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Provider Name</Label>
              <Input
                value={form.provider_name}
                onChange={(e) => setForm({ ...form, provider_name: e.target.value })}
                placeholder="e.g. openai, anthropic, google"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Display Name</Label>
              <Input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                placeholder="e.g. OpenAI, Anthropic, Google AI"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Base URL</Label>
              <Input
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary placeholder:text-text-tertiary"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Rate Limit (RPM)</Label>
                <Input
                  type="number"
                  value={form.rate_limit_rpm || ''}
                  onChange={(e) => setForm({ ...form, rate_limit_rpm: Number(e.target.value) })}
                  placeholder="600"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Rate Limit (TPM)</Label>
                <Input
                  type="number"
                  value={form.rate_limit_tpm || ''}
                  onChange={(e) => setForm({ ...form, rate_limit_tpm: Number(e.target.value) })}
                  placeholder="90000"
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-[13px] text-text-secondary cursor-pointer">
              <Checkbox
                checked={form.is_active}
                onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })}
              />
              Active
            </label>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <DialogClose asChild>
              <Button variant="outline" className="bg-krait-surface2 border-krait-border text-text-secondary hover:bg-krait-surface1 text-[13px]">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSave}
              disabled={saving || !form.provider_name || !form.display_name || !form.base_url}
              className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px]"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />}
              {editingProvider ? 'Update' : 'Create'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDeleteDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        label="Provider"
      />
    </>
  );
}

// ── Kraivor AI Tab ──────────────────────────────────────────────────────────

function KraivorAITab() {
  const [model, setModel] = useState<Model | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    display_name: '',
    model_id: '',
    status: 'active',
    context_window: 131072,
    max_output_tokens: 16384,
    supports_tools: true,
    supports_vision: false,
    supports_reasoning: false,
    latency_display: '0.4s',
    notes: '',
  });

  const fetchData = useCallback(async () => {
    try {
      const res = await adminEndpoints.listModels();
      const m = res as { models?: Model[] };
      const krait = (m.models ?? []).find(
        (x) => x.provider_name === 'kraivor' || x.model_id === 'openrouter/auto'
      );
      setModel(krait ?? null);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const openEdit = () => {
    if (model) {
      setForm({
        display_name: model.display_name,
        model_id: model.model_id,
        status: model.status,
        context_window: model.context_window,
        max_output_tokens: model.max_output_tokens,
        supports_tools: model.supports_tools,
        supports_vision: model.supports_vision,
        supports_reasoning: model.supports_reasoning,
        latency_display: model.latency_display || '0.4s',
        notes: (model as unknown as Record<string, string>).notes || '',
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (model) {
        await adminEndpoints.updateModel(model.id, form);
      } else {
        await adminEndpoints.createModel({
          ...form,
          provider_name: 'kraivor',
          frontend_id: 'krait-2.0',
          tier: 'standard',
        });
      }
      await adminEndpoints.invalidateCache();
      setDialogOpen(false);
      setLoading(true);
      await fetchData();
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner size="md" className="text-venom-yellow" />
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-[13px] text-text-tertiary">
          Built-in model powering the default chat experience
        </p>
        <Button
          onClick={openEdit}
          className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px] h-8"
        >
          <Pencil className="w-3.5 h-3.5 mr-1.5" />
          Configure
        </Button>
      </div>

      <div className="bg-krait-obsidian border border-krait-border rounded-xl p-6">
        {model ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-venom-yellow/10 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-venom-yellow" />
              </div>
              <div>
                <h3 className="text-[14px] font-semibold text-text-primary">{model.display_name}</h3>
                <p className="text-[12px] text-text-tertiary font-mono">{model.model_id}</p>
              </div>
              <div className="ml-auto">
                <Badge variant={model.status === 'active' ? 'success' : 'outline'}>
                  {model.status}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Context</p>
                <p className="text-[13px] text-text-primary">{model.context_window?.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Max Output</p>
                <p className="text-[13px] text-text-primary">{model.max_output_tokens?.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Latency</p>
                <p className="text-[13px] text-text-primary">
                  {model.latency_display || '—'}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Provider</p>
                <p className="text-[13px] text-text-primary">{model.provider_name}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 pt-2">
              {[
                { label: 'Tools', value: model.supports_tools },
                { label: 'Vision', value: model.supports_vision },
                { label: 'Reasoning', value: model.supports_reasoning },
              ].map((cap) => (
                <div key={cap.label} className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${cap.value ? 'bg-green-500' : 'bg-zinc-600'}`} />
                  <span className="text-[12px] text-text-secondary">{cap.label}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState icon={Zap} message="Kraivor AI model not configured yet" />
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Configure Kraivor AI</DialogTitle>
            <DialogDescription>
              Settings for the built-in default chat model.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Display Name</Label>
              <Input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Backend Model</Label>
              <Input
                value={form.model_id}
                onChange={(e) => setForm({ ...form, model_id: e.target.value })}
                placeholder="openrouter/auto"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Latency Display</Label>
              <Input
                value={form.latency_display}
                onChange={(e) => setForm({ ...form, latency_display: e.target.value })}
                placeholder="0.4s"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Status</Label>
                <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                  <SelectTrigger className="bg-krait-surface2 border-krait-border text-[13px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[12px] text-text-secondary">Max Output Tokens</Label>
                <Input
                  type="number"
                  value={form.max_output_tokens || ''}
                  onChange={(e) => setForm({ ...form, max_output_tokens: Number(e.target.value) })}
                  className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-[12px] text-text-secondary">Capabilities</Label>
              <div className="flex items-center gap-4">
                {(['supports_tools', 'supports_vision', 'supports_reasoning'] as const).map((key) => (
                  <label key={key} className="flex items-center gap-2 text-[13px] text-text-secondary cursor-pointer">
                    <Checkbox
                      checked={form[key]}
                      onCheckedChange={(checked) => setForm({ ...form, [key]: !!checked })}
                    />
                    {key.replace('supports_', '')}
                  </label>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[12px] text-text-secondary">Notes</Label>
              <Input
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Optional notes"
                className="bg-krait-surface2 border-krait-border text-[13px] text-text-primary"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <DialogClose asChild>
              <Button variant="outline" className="bg-krait-surface2 border-krait-border text-text-secondary hover:bg-krait-surface1 text-[13px]">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSave}
              disabled={saving || !form.display_name || !form.model_id}
              className="bg-venom-yellow text-black hover:bg-venom-yellow/90 font-semibold text-[13px]"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />}
              {model ? 'Update' : 'Create'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function AdminModelsPage() {
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-text-primary">Model Management</h1>
        <p className="text-[13px] text-text-tertiary mt-0.5">
          Configure LLM models, task routes, and provider connections
        </p>
      </div>

      <Tabs defaultValue="kraivor">
        <TabsList>
          <TabsTrigger value="kraivor">
            <Zap className="w-3.5 h-3.5 mr-1.5" />
            Kraivor AI
          </TabsTrigger>
          <TabsTrigger value="models">
            <Cpu className="w-3.5 h-3.5 mr-1.5" />
            Models
          </TabsTrigger>
          <TabsTrigger value="routes">
            <Route className="w-3.5 h-3.5 mr-1.5" />
            Routes
          </TabsTrigger>
          <TabsTrigger value="providers">
            <Server className="w-3.5 h-3.5 mr-1.5" />
            Providers
          </TabsTrigger>
        </TabsList>

        <TabsContent value="kraivor">
          <KraivorAITab />
        </TabsContent>

        <TabsContent value="models">
          <ModelsTab />
        </TabsContent>

        <TabsContent value="routes">
          <RoutesTab />
        </TabsContent>

        <TabsContent value="providers">
          <ProvidersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
