'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeAiApi } from '@/lib/api/knowledge-ai-api';

const kKeys = {
  all: ['knowledge-ai'] as const,
  health: (wsId: string) => [...kKeys.all, 'health', wsId] as const,
  stats: (wsId: string) => [...kKeys.all, 'stats', wsId] as const,
  list: (wsId: string) => [...kKeys.all, 'list', wsId] as const,
  graph: (wsId: string) => [...kKeys.all, 'graph', wsId] as const,
  monitoring: (wsId: string) => [...kKeys.all, 'monitoring', wsId] as const,
  search: (wsId: string, q: string) => [...kKeys.all, 'search', wsId, q] as const,
  workflows: () => [...kKeys.all, 'workflows'] as const,
  templates: () => [...kKeys.all, 'templates'] as const,
};

/* ─── Health ──────────────────────────────────────────────── */

export function useKnowledgeHealth(workspaceId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: kKeys.health(workspaceId ?? ''),
    queryFn: () => knowledgeAiApi.getHealth(workspaceId!),
    enabled: !!workspaceId && enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

/* ─── Stats ───────────────────────────────────────────────── */

export function useKnowledgeStats(workspaceId: string | undefined) {
  return useQuery({
    queryKey: kKeys.stats(workspaceId ?? ''),
    queryFn: () => knowledgeAiApi.getStats(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}

/* ─── List Items ──────────────────────────────────────────── */

export function useKnowledgeItems(
  workspaceId: string | undefined,
  limit = 20,
  offset = 0,
  sourceType?: string,
) {
  return useQuery({
    queryKey: [...kKeys.list(workspaceId ?? ''), limit, offset, sourceType],
    queryFn: () => knowledgeAiApi.listItems(workspaceId!, limit, offset, sourceType),
    enabled: !!workspaceId,
    staleTime: 15_000,
  });
}

/* ─── Search ──────────────────────────────────────────────── */

export function useKnowledgeSearch(workspaceId: string | undefined, query: string) {
  return useQuery({
    queryKey: kKeys.search(workspaceId ?? '', query),
    queryFn: () => knowledgeAiApi.search(workspaceId!, query),
    enabled: !!workspaceId && query.length > 2,
    staleTime: 30_000,
  });
}

/* ─── Graph ───────────────────────────────────────────────── */

export function useKnowledgeGraph(workspaceId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: kKeys.graph(workspaceId ?? ''),
    queryFn: () => knowledgeAiApi.getGraphStats(workspaceId!),
    enabled: !!workspaceId && enabled,
    staleTime: 60_000,
  });
}

export function useKnowledgeGraphEntities(workspaceId: string | undefined) {
  return useQuery({
    queryKey: [...kKeys.graph(workspaceId ?? ''), 'entities'],
    queryFn: () => knowledgeAiApi.getGraphEntities(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

/* ─── Monitoring ──────────────────────────────────────────── */

export function useQueryStats(workspaceId: string | undefined) {
  return useQuery({
    queryKey: kKeys.monitoring(workspaceId ?? ''),
    queryFn: () => knowledgeAiApi.getQueryStats(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}

/* ─── Workflows ───────────────────────────────────────────── */

export function useWorkflowDefinitions() {
  return useQuery({
    queryKey: kKeys.workflows(),
    queryFn: () => knowledgeAiApi.getWorkflowDefinitions(),
    staleTime: 300_000,
  });
}

export function useRunWorkflow(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ workflowName, topic }: { workflowName: string; topic?: string }) =>
      knowledgeAiApi.runWorkflow(workspaceId, workflowName, topic),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kKeys.stats(workspaceId) });
    },
  });
}

/* ─── Templates ───────────────────────────────────────────── */

export function useTemplates() {
  return useQuery({
    queryKey: kKeys.templates(),
    queryFn: () => knowledgeAiApi.getTemplates(),
    staleTime: 300_000,
  });
}

export function useImportTemplate(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) => knowledgeAiApi.importTemplate(workspaceId, templateId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kKeys.stats(workspaceId) });
      qc.invalidateQueries({ queryKey: kKeys.list(workspaceId) });
    },
  });
}

/* ─── Ingest ──────────────────────────────────────────────── */

export function useIngestFile(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, language }: { file: File; language?: string }) =>
      knowledgeAiApi.ingestFile(workspaceId, file, language),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kKeys.stats(workspaceId) });
      qc.invalidateQueries({ queryKey: kKeys.list(workspaceId) });
    },
  });
}

export function useIngestText(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ text, title }: { text: string; title?: string }) =>
      knowledgeAiApi.ingestText(workspaceId, text, title),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kKeys.stats(workspaceId) });
      qc.invalidateQueries({ queryKey: kKeys.list(workspaceId) });
    },
  });
}
