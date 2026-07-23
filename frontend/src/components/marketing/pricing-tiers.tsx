'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ROUTES } from '@/constants';
import { Check, ArrowRight } from '@phosphor-icons/react';

const PRICING_TIERS = [
  {
    name: 'Developer',
    description: 'For individual developers getting started.',
    price: { monthly: 999, annually: 9999 },
    features: ['1 Connected Repository', 'Basic Code Analysis', 'AI Assistant (100 Queries/month)', 'Notes & Tasks Management', 'Community Support'],
    cta: 'Start Free Trial',
    popular: false,
  },
  {
    name: 'Team',
    description: 'For small teams and startups.',
    price: { monthly: 4999, annually: 49999 },
    features: ['5 Connected Repositories', 'Advanced Code Analysis', 'AI Assistant (1000 Queries/month)', 'Project Management Tools', 'Priority Email Support'],
    cta: 'Start Free Trial',
    popular: true,
  },
  {
    name: 'Enterprise',
    description: 'For larger organizations and complex needs.',
    price: { monthly: 19999, annually: 199999 },
    features: ['Unlimited Repositories', 'Advanced Security Audits', 'Dedicated AI Agents', 'Team Collaboration Features', '24/7 Premium Support', 'Custom Integrations'],
    cta: 'Contact Sales',
    popular: false,
  },
];

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function PricingTiers() {
  const [billingMode, setBillingMode] = useState<'monthly' | 'annually'>('annually');

  return (
    <>
      <div className="flex items-center justify-center mb-10">
        <div className="inline-flex rounded-lg border border-[var(--krait-border)] overflow-hidden">
          <button
            onClick={() => setBillingMode('annually')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              billingMode === 'annually'
                ? 'bg-[var(--venom-yellow)] text-black'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Annually{' '}
            <span className="text-[10px] opacity-70">(Save 20%)</span>
          </button>
          <button
            onClick={() => setBillingMode('monthly')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              billingMode === 'monthly'
                ? 'bg-[var(--venom-yellow)] text-black'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Monthly
          </button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {PRICING_TIERS.map((tier) => (
          <div
            key={tier.name}
            className={`rounded-2xl border p-8 ${
              tier.popular
                ? 'border-[var(--text-accent)]/40 bg-[var(--krait-surface-1)]'
                : 'border-[var(--krait-border)] bg-[var(--krait-surface-1)]'
            }`}
          >
            {tier.popular && (
              <div className="inline-flex rounded-full bg-[var(--venom-yellow)] px-3 py-1 mb-4">
                <span className="font-mono text-[10px] font-bold text-black uppercase tracking-wider">
                  Most Popular
                </span>
              </div>
            )}
            <h3 className={`text-xl font-bold ${tier.popular ? 'text-[var(--text-accent)]' : 'text-[var(--text-primary)]'} mb-1`}>
              {tier.name}
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mb-6">{tier.description}</p>

            <div className="border-b border-[var(--krait-border)] pb-5 mb-5">
              <p className="flex items-baseline gap-1">
                <span className="font-mono text-4xl font-bold text-[var(--text-primary)]">
                  {formatCurrency(tier.price[billingMode])}
                </span>
                <span className="font-mono text-sm text-[var(--text-tertiary)]">
                  /{billingMode === 'annually' ? 'year' : 'month'}
                </span>
              </p>
              {billingMode === 'monthly' && (
                <p className="font-mono text-xs text-[var(--text-tertiary)] mt-1">
                  Billed annually at {formatCurrency(tier.price.annually / 12)}/month
                </p>
              )}
            </div>

            <ul className="space-y-2.5 mb-8">
              {tier.features.map((feature, i) => (
                <li key={i} className="flex items-center gap-2.5">
                  <Check size={12} weight="bold" className="text-[var(--text-accent)] shrink-0" />
                  <span className="text-sm text-[var(--text-secondary)]">{feature}</span>
                </li>
              ))}
            </ul>

            <Link
              href={ROUTES.REGISTER}
              className={`block w-full rounded-xl px-5 py-3 text-center text-sm font-semibold transition-all ${
                tier.popular
                  ? 'bg-[var(--venom-yellow)] text-black hover:brightness-110'
                  : 'border border-[var(--krait-border)] text-[var(--text-primary)] hover:bg-[var(--krait-surface-2)]'
              }`}
            >
              <span className="inline-flex items-center gap-2 justify-center">
                {tier.cta}
                <ArrowRight size={14} weight="bold" />
              </span>
            </Link>
          </div>
        ))}
      </div>
    </>
  );
}
