'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { ROUTES } from '@/constants';

/* ─── Scroll Reveal Hook ─────────────────────────────────────── */
function useScrollReveal() {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -100px 0px' }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

/* ─── Helper Component ───────────────────────────────────────── */
function RevealSection({ children, delay = '', className = '' }: { children: React.ReactNode, delay?: string, className?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div
      ref={ref}
      className={`transition-all duration-1000 ${className} ${
        isVisible ? `opacity-100 translate-y-0 ${delay}` : 'opacity-0 translate-y-16'
      }`}
    >
      {children}
    </div>
  );
}

/* ─── Icons ─────────────────────────────────────────────────── */
const Icons = {
  Gateway: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>,
  Async: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Database: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  Shield: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  Eye: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  Code: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  Bot: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>,
  Workflow: () => <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
};

/* ─── Page Component ─────────────────────────────────────────── */
export default function FeaturesPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0a0a0f] text-slate-200">
      
      {/* ── Ambient Background Glows ─────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute top-[-10%] right-[-5%] h-[600px] w-[600px] rounded-full bg-[hsl(var(--primary))]/10 blur-[150px] animate-float-slow" />
        <div className="absolute bottom-[-10%] left-[-10%] h-[500px] w-[500px] rounded-full bg-[hsl(var(--primary-dark))]/20 blur-[150px] animate-float-medium" />
      </div>

      {/* ── Header ────────────────────────────────────────────── */}
      <header className={`fixed top-0 z-50 w-full transition-all duration-300 ${scrolled ? 'border-b border-white/5 bg-[#0a0a0f]/80 backdrop-blur-xl' : 'bg-transparent'}`}>
        <div className="container mx-auto flex h-20 items-center justify-between px-6">
          <Link href={ROUTES.HOME} className="text-2xl font-bold tracking-tight bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
            ✦ Kraivor
          </Link>
          <div className="flex items-center gap-4">
            <Link href={ROUTES.LOGIN} className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Sign in</Link>
            <Link href={ROUTES.REGISTER} className="btn-shimmer rounded-xl px-5 py-2.5 text-sm font-semibold text-white">Get Started</Link>
          </div>
        </div>
      </header>

      <main className="relative z-10 pt-32 pb-24">
        
        {/* ── 1. Hero & Platform Overview ─────────────────────── */}
        <section className="container mx-auto px-6 pt-12 pb-20 text-center">
          <div className="animate-fade-up mx-auto max-w-4xl">
            <h1 className="text-5xl font-extrabold tracking-tight sm:text-7xl mb-8 text-white">
              One platform.<br />
              <span className="bg-gradient-to-r from-[hsl(var(--primary-light))] via-[hsl(var(--primary))] to-[hsl(var(--primary-dark))] bg-clip-text text-transparent">
                Three products.
              </span>
            </h1>
            <p className="text-xl text-slate-400 leading-relaxed mb-12">
              Kraivor is a unified developer intelligence platform built as a microservices system. 
              It is not three separate products loosely bolted together — it is one platform where all three products 
              share infrastructure, authentication, user identity, and workspace context.
            </p>
          </div>
        </section>

        {/* ── Core Design Principles ───────────────────────────── */}
        <section className="container mx-auto px-6 py-20">
          <RevealSection>
            <div className="mb-16 text-center">
              <h2 className="text-3xl font-bold text-white sm:text-4xl">Core Design Principles</h2>
              <div className="mt-4 h-1 w-24 bg-gradient-to-r from-[hsl(var(--primary))] to-transparent mx-auto rounded-full" />
            </div>
          </RevealSection>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: Icons.Gateway, title: "Single Entry Point", desc: "All traffic — web, mobile, CLI — enters through one API Gateway. No service is ever exposed directly to the internet." },
              { icon: Icons.Async, title: "Async by Default", desc: "Any operation taking >500ms is a background job. Results are pushed via WebSocket. This allows 10,000+ concurrent users seamlessly." },
              { icon: Icons.Database, title: "Service Owns its Data", desc: "Each microservice has its own schema. Data sharing happens exclusively through APIs or events, never shared database queries." },
              { icon: Icons.Shield, title: "Fail Gracefully", desc: "If the AI service is down, the analyzer works. Each product degrades independently, never taking down the whole platform." },
              { icon: Icons.Eye, title: "Everything is Observable", desc: "Every request has a correlation ID. Every service emits structured logs. You can trace any problem through every layer." },
            ].map((principle, idx) => (
              <RevealSection key={idx} delay={`delay-[${idx * 100}ms]`}>
                <div className="group relative h-full rounded-2xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md transition-all duration-300 hover:bg-white/[0.04] hover:border-[hsl(var(--primary))/40] hover:shadow-[0_8px_32px_-10px_hsla(var(--primary),0.3)] hover:-translate-y-1">
                  <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary-light))] ring-1 ring-white/10 group-hover:ring-[hsl(var(--primary))/50] transition-colors">
                    <principle.icon />
                  </div>
                  <h3 className="mb-3 text-lg font-bold text-white group-hover:text-[hsl(var(--primary-light))] transition-colors">{principle.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{principle.desc}</p>
                </div>
              </RevealSection>
            ))}
          </div>
        </section>

        {/* ── 2. The Three Products ───────────────────────────── */}
        <section className="container mx-auto px-6 py-32 space-y-40">
          
          {/* Product 1 */}
          <RevealSection>
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 text-[hsl(var(--primary-light))] text-sm font-semibold mb-6">
                  <Icons.Code /> Product 01
                </div>
                <h2 className="text-4xl font-bold text-white mb-6">Repository Analyzer</h2>
                <p className="text-lg text-slate-400 leading-relaxed mb-6">
                  The core product. This is what makes Kraivor valuable on day one. Connect your GitHub or GitLab repository, and Kraivor analyzes the entire codebase — evaluating folder architecture, code quality patterns, DevOps maturity, security posture, and scalability readiness.
                </p>
                <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden">
                  <div className="absolute left-0 top-0 w-1 h-full bg-[hsl(var(--primary))]" />
                  <h4 className="text-white font-bold mb-2">Key Differentiator</h4>
                  <p className="text-sm text-slate-300">
                    Rule-based static analysis combined with AI-powered contextual understanding. Rules catch definite problems; the AI catches architectural intent that rules cannot.
                  </p>
                </div>
              </div>
              
              {/* Abstract Visual representation */}
              <div className="relative aspect-square md:aspect-[4/3] rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 to-transparent flex items-center justify-center overflow-hidden shadow-2xl shadow-[hsl(var(--primary))]/5">
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
                <div className="relative z-10 w-3/4 space-y-4">
                  {[85, 92, 78].map((score, i) => (
                    <div key={i} className="bg-[#0a0a0f] border border-white/10 rounded-xl p-4 flex items-center justify-between shadow-lg">
                      <div className="h-2 w-24 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-[hsl(var(--primary-light))]" style={{ width: `${score}%` }} />
                      </div>
                      <span className="text-white font-mono text-sm">{score}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </RevealSection>

          {/* Product 2 */}
          <RevealSection>
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div className="order-2 lg:order-1 relative aspect-square md:aspect-[4/3] rounded-3xl border border-white/10 bg-gradient-to-tr from-white/5 to-transparent flex items-center justify-center overflow-hidden shadow-2xl shadow-[hsl(var(--primary))]/5">
                {/* Abstract Node Network Visual */}
                <div className="relative w-full h-full">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 rounded-full border border-[hsl(var(--primary))]/50 bg-[hsl(var(--primary))]/10 flex items-center justify-center shadow-[0_0_40px_hsla(var(--primary),0.4)] z-20">
                    <Icons.Bot />
                  </div>
                  {/* Connecting lines */}
                  <svg className="absolute inset-0 w-full h-full opacity-30" stroke="hsl(var(--primary-light))" strokeWidth="1">
                    <line x1="50%" y1="50%" x2="20%" y2="30%" />
                    <line x1="50%" y1="50%" x2="80%" y2="30%" />
                    <line x1="50%" y1="50%" x2="50%" y2="80%" />
                  </svg>
                  <div className="absolute top-[30%] left-[20%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full border border-white/20 bg-[#0a0a0f] z-10" />
                  <div className="absolute top-[30%] left-[80%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full border border-white/20 bg-[#0a0a0f] z-10" />
                  <div className="absolute top-[80%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full border border-white/20 bg-[#0a0a0f] z-10" />
                </div>
              </div>

              <div className="order-1 lg:order-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 text-[hsl(var(--primary-light))] text-sm font-semibold mb-6">
                  <Icons.Bot /> Product 02
                </div>
                <h2 className="text-4xl font-bold text-white mb-6">Agentic AI System</h2>
                <p className="text-lg text-slate-400 leading-relaxed mb-6">
                  A multi-agent AI workspace where developers interact with their codebase through intelligent agents. Not a chatbot. Not a code autocomplete. A system of specialized AI agents that collaborate to answer complex engineering questions.
                </p>
                <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden">
                  <div className="absolute left-0 top-0 w-1 h-full bg-[hsl(var(--primary))]" />
                  <h4 className="text-white font-bold mb-2">Key Differentiator</h4>
                  <p className="text-sm text-slate-300">
                    2026-standard agentic behavior. Agents have memory, can call tools, search the codebase, and collaborate autonomously. The Orchestrator decides which agents to involve, and the Explainer Agent synthesizes actionable results.
                  </p>
                </div>
              </div>
            </div>
          </RevealSection>

          {/* Product 3 */}
          <RevealSection>
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[hsl(var(--primary))]/10 border border-[hsl(var(--primary))]/20 text-[hsl(var(--primary-light))] text-sm font-semibold mb-6">
                  <Icons.Workflow /> Product 03
                </div>
                <h2 className="text-4xl font-bold text-white mb-6">Developer Productivity</h2>
                <p className="text-lg text-slate-400 leading-relaxed mb-6">
                  The daily driver. Developers live in Kraivor because it replaces their scattered workflow. Notes in Notion, tasks in Linear, architecture diagrams in Miro, decisions in Slack — Kraivor unifies these with AI that knows your codebase.
                </p>
                <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden">
                  <div className="absolute left-0 top-0 w-1 h-full bg-[hsl(var(--primary))]" />
                  <h4 className="text-white font-bold mb-2">Key Differentiator</h4>
                  <p className="text-sm text-slate-300">
                    Context continuity. Every note, task, and architectural decision is indexed alongside the codebase. When you ask the AI a question, it never loses context of why a decision was made.
                  </p>
                </div>
              </div>

              {/* Abstract UI Mockup */}
              <div className="relative aspect-square md:aspect-[4/3] rounded-3xl border border-white/10 bg-white/[0.02] flex flex-col overflow-hidden shadow-2xl shadow-[hsl(var(--primary))]/5">
                <div className="h-10 border-b border-white/10 flex items-center px-4 gap-2 bg-white/5">
                  <div className="h-3 w-3 rounded-full bg-white/20" />
                  <div className="h-3 w-3 rounded-full bg-white/20" />
                </div>
                <div className="flex-1 p-6 flex flex-col gap-4">
                  <div className="w-1/3 h-6 bg-white/10 rounded-md" />
                  <div className="w-full h-24 bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col gap-2">
                    <div className="w-1/4 h-3 bg-white/20 rounded-full" />
                    <div className="w-3/4 h-3 bg-white/10 rounded-full" />
                  </div>
                  <div className="w-full h-24 bg-white/5 border border-[hsl(var(--primary))]/30 rounded-lg p-4 flex flex-col gap-2 relative overflow-hidden">
                    <div className="absolute right-0 top-0 w-12 h-12 bg-[hsl(var(--primary))]/10 blur-xl" />
                    <div className="w-1/3 h-3 bg-[hsl(var(--primary-light))] rounded-full" />
                    <div className="w-1/2 h-3 bg-white/20 rounded-full" />
                  </div>
                </div>
              </div>
            </div>
          </RevealSection>

        </section>

        {/* ── CTA ──────────────────────────────────────────────── */}
        <section className="container mx-auto px-6 py-24">
          <RevealSection>
            <div className="relative rounded-3xl border border-white/10 bg-white/[0.02] p-12 text-center backdrop-blur-xl overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-b from-[hsl(var(--primary))]/10 to-transparent opacity-50" />
              <div className="relative z-10">
                <h2 className="text-3xl font-bold text-white sm:text-5xl mb-6">Ready to unify your workflow?</h2>
                <p className="text-lg text-slate-400 mb-10 max-w-2xl mx-auto">
                  Stop context switching between fragmented tools. Join Kraivor and build with production-grade intelligence.
                </p>
                <Link href={ROUTES.REGISTER} className="btn-shimmer inline-flex items-center justify-center rounded-xl px-10 py-4 text-base font-semibold text-white shadow-[0_0_40px_-10px_hsl(var(--primary))]">
                  Start Your Free Trial →
                </Link>
              </div>
            </div>
          </RevealSection>
        </section>

      </main>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="border-t border-white/10 bg-[#0a0a0f] py-12">
        <div className="container mx-auto px-6 text-center">
          <span className="text-xl font-bold tracking-tight text-white mb-4 block">✦ Kraivor</span>
          <p className="text-sm text-slate-500">
            &copy; {new Date().getFullYear()} Kraivor Technologies. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}