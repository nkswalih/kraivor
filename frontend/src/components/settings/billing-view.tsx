'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  CreditCard,
  Check,
  ChevronRight,
  Zap,
  Sparkles,
  Shield,
  Users,
  Upload,
  FileText,
  Code,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const premiumFeatures = [
  { label: '5 teams', icon: Users },
  { label: 'Admin roles', icon: Shield },
  { label: 'Restrict new user invitations', icon: Users },
  { label: 'Unlimited file upload size', icon: Upload },
  { label: 'Coding sessions', icon: Code },
  { label: 'File upload deletion', icon: Trash2 },
];

export function BillingView() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Billing</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          Manage your subscription and view invoices.
        </p>
      </div>

      {/* ── Current Plan Card ────────────────────────────────────── */}
      <div className="rounded-xl bg-krait-surface-1 border border-krait-border p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold text-text-primary">Free plan</h3>
              <span className="text-[10px] font-medium text-text-secondary bg-muted px-2 py-0.5 rounded-full border border-krait-border-hi">
                Current
              </span>
            </div>
            <p className="text-[13px] text-text-tertiary">Free for all users</p>
          </div>
          <button className="text-[12px] font-medium text-text-secondary hover:text-text-primary transition-colors px-3 py-1.5 rounded-lg border border-krait-border">
            Manage
          </button>
        </div>
      </div>

      {/* ── Premium Upsell ───────────────────────────────────────── */}
      <div className="rounded-xl bg-gradient-to-br from-[#1a1a2e] to-[#141415] border border-[#2a2a4e] p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-text-primary">Upgrade to Basic plan</h3>
            </div>
            <p className="text-[24px] font-bold text-text-primary mt-2">
              $12<span className="text-[13px] font-normal text-text-tertiary"> /user/mo</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/pricing" className="text-[12px] font-medium text-primary hover:underline">
              View all plans
            </Link>
            <button className="bg-gradient-to-r from-primary to-primary-light hover:from-primary-dark hover:to-primary-dark text-primary-foreground font-semibold py-2.5 px-5 rounded-lg transition-all duration-150 text-[13px] active:scale-[0.98] shadow-venom">
              Upgrade now
            </button>
          </div>
        </div>

        {/* Feature Matrix */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {premiumFeatures.map(feature => {
            const Icon = feature.icon;
            return (
              <div key={feature.label} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#ffffff08] border border-[#ffffff08]">
                <Icon className="w-3.5 h-3.5 text-primary" />
                <span className="text-[12px] text-text-secondary">{feature.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── AI Usage Card ─────────────────────────────────────────── */}
      <div className="rounded-xl bg-krait-surface-1 border border-krait-border p-4 flex items-center justify-between group cursor-pointer hover:border-krait-border-hi transition-colors">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-text-secondary" />
          <div>
            <p className="text-[13px] font-medium text-text-primary">AI usage and credits</p>
            <p className="text-[12px] text-text-tertiary">$0.00 remaining</p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-text-tertiary group-hover:text-text-secondary transition-colors" />
      </div>

      {/* ── Invoices Container ────────────────────────────────────── */}
      <Section title="Recent Invoices">
        <div className="flex flex-col items-center justify-center py-12 rounded-xl bg-krait-surface-1 border border-krait-border">
          <FileText className="w-8 h-8 text-text-tertiary mb-3" />
          <p className="text-[13px] text-text-tertiary">No invoices yet</p>
          <p className="text-[11px] text-text-tertiary mt-1">Invoices will appear here after your first payment.</p>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold tracking-[0.06em] uppercase text-text-tertiary mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}
