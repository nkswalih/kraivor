import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  AI_PROVIDERS,
  AI_PROVIDER_ORDER,
  UNKNOWN_PROVIDER_META,
  getProviderMeta,
} from '@/constants/ai-providers';

/**
 * Regression guard for the provider-metadata duplication.
 *
 * This table used to be copy-pasted into three components and had already
 * drifted (xAI was "xAI" in two files and "xAI (Grok)" in the third, and
 * docsUrl was missing from one entirely). These tests pin the invariants so a
 * future edit cannot silently reintroduce the inconsistency.
 */

describe('AI_PROVIDERS', () => {
  it('defines the expected set of providers', () => {
    expect(Object.keys(AI_PROVIDERS).sort()).toEqual([
      'anthropic',
      'deepseek',
      'google',
      'groq',
      'openai',
      'openrouter',
      'xai',
    ]);
  });

  it('gives every provider a complete metadata entry', () => {
    for (const [id, meta] of Object.entries(AI_PROVIDERS)) {
      expect(meta.name, `${id} name`).toBeTruthy();
      expect(meta.placeholder, `${id} placeholder`).toBeTruthy();
      expect(meta.color, `${id} color`).toMatch(/^#[0-9A-Fa-f]{6}$/);
      expect(meta.docsUrl, `${id} docsUrl`).toMatch(/^https:\/\//);
    }
  });

  it('uses a unique display name per provider', () => {
    const names = Object.values(AI_PROVIDERS).map(p => p.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it('orders every provider exactly once', () => {
    expect([...AI_PROVIDER_ORDER].sort()).toEqual(Object.keys(AI_PROVIDERS).sort());
  });
});

describe('getProviderMeta', () => {
  it('returns the canonical entry for a known provider', () => {
    expect(getProviderMeta('openrouter')).toEqual(AI_PROVIDERS.openrouter);
  });

  it('is case sensitive, so callers must pass the canonical id', () => {
    expect(getProviderMeta('OpenRouter')).not.toEqual(AI_PROVIDERS.openrouter);
  });

  it('falls back to the supplied name for an unknown provider', () => {
    const meta = getProviderMeta('some-new-llm');
    expect(meta.name).toBe('some-new-llm');
    expect(meta.placeholder).toBe(UNKNOWN_PROVIDER_META.placeholder);
  });

  it('never returns undefined fields that would render as "undefined"', () => {
    const meta = getProviderMeta('nope');
    for (const value of Object.values(meta)) {
      expect(value).toBeDefined();
    }
  });
});
