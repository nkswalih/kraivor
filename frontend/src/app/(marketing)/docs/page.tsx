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
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

/* ─── Helper Component ───────────────────────────────────────── */
function RevealSection({
  children,
  delay = '',
  className = '',
}: {
  children: React.ReactNode;
  delay?: string;
  className?: string;
}) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div
      ref={ref}
      className={`transition-all duration-1000 ${className} ${
        isVisible ? `opacity-100 translate-y-0 ${delay}` : 'opacity-0 translate-y-12'
      }`}
    >
      {children}
    </div>
  );
}

/* ─── Icons ─────────────────────────────────────────────────── */
const Icons = {
  Search: () => (
    <svg
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  Book: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
  Git: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <circle cx="18" cy="18" r="3" />
      <circle cx="6" cy="6" r="3" />
      <path d="M13 6h3a2 2 0 0 1 2 2v7" />
      <line x1="6" y1="9" x2="6" y2="21" />
    </svg>
  ),
  Bot: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
      <line x1="8" y1="16" x2="8" y2="16" />
      <line x1="16" y1="16" x2="16" y2="16" />
    </svg>
  ),
  Workflow: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  Code: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  ),
  LifeBuoy: () => (
    <svg
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="4" />
      <line x1="4.93" y1="4.93" x2="9.17" y2="9.17" />
      <line x1="14.83" y1="14.83" x2="19.07" y2="19.07" />
      <line x1="14.83" y1="9.17" x2="19.07" y2="4.93" />
      <line x1="14.83" y1="9.17" x2="18.36" y2="5.64" />
      <line x1="4.93" y1="19.07" x2="9.17" y2="14.83" />
    </svg>
  ),
  ArrowRight: () => (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  ),
};

const DOC_CATEGORIES = [
  {
    icon: Icons.Book,
    title: 'Getting Started',
    desc: 'Platform overview, authentication, and setting up your first workspace.',
  },
  {
    icon: Icons.Git,
    title: 'Repository Analyzer',
    desc: 'Connecting GitHub/GitLab, configuring rules, and understanding readiness scores.',
  },
  {
    icon: Icons.Bot,
    title: 'Agentic AI System',
    desc: 'How to prompt agents, use the Orchestrator, and manage AI context.',
  },
  {
    icon: Icons.Workflow,
    title: 'Developer Productivity',
    desc: 'Managing AI-enhanced notes, linking tasks to PRs, and organizing projects.',
  },
  {
    icon: Icons.Code,
    title: 'API Reference',
    desc: 'REST API endpoints, WebSocket events, and authentication tokens.',
  },
  {
    icon: Icons.LifeBuoy,
    title: 'Troubleshooting',
    desc: 'Common issues, observability logs, and how to read correlation IDs.',
  },
];

/* ─── Page Component ─────────────────────────────────────────── */
export default function DocsPage() {
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
        <div className="absolute top-[-10%] right-[10%] h-[500px] w-[500px] rounded-full bg-[hsl(var(--primary))]/10 blur-[150px] animate-float-slow" />
        <div className="absolute bottom-[20%] left-[-10%] h-[400px] w-[400px] rounded-full bg-[hsl(var(--primary-dark))]/20 blur-[120px] animate-float-medium" />
      </div>

      {/* ── Header ────────────────────────────────────────────── */}
      <header
        className={`fixed top-0 z-50 w-full transition-all duration-300 ${scrolled ? 'border-b border-white/5 bg-[#0a0a0f]/80 backdrop-blur-xl' : 'bg-transparent'}`}
      >
        <div className="container mx-auto flex h-20 items-center justify-between px-6">
          <Link
            href={ROUTES.HOME}
            className="text-2xl font-bold tracking-tight bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent"
          >
            ✦ Kraivor Docs
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href={ROUTES.LOGIN}
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Sign in
            </Link>
            <Link
              href={ROUTES.REGISTER}
              className="btn-shimmer rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10 pt-32 pb-24">
        {/* ── Hero & Search ───────────────────────────────────── */}
        <section className="container mx-auto px-6 pt-12 pb-24 text-center">
          <div className="animate-fade-up mx-auto max-w-3xl">
            <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl mb-6 text-white">
              How can we help you <br className="hidden sm:block" />
              <span className="bg-gradient-to-r from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
                build better?
              </span>
            </h1>
            <p className="text-lg text-slate-400 mb-10">
              Explore our guides, API references, and architecture overviews to get the most out of
              the Kraivor Platform.
            </p>

            {/* Search Bar */}
            <div className="relative max-w-2xl mx-auto group">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-[hsl(var(--primary-light))] transition-colors">
                <Icons.Search />
              </div>
              <input
                type="text"
                placeholder="Search documentation, API, or guides..."
                className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder-slate-500 backdrop-blur-md transition-all duration-300 focus:outline-none focus:border-[hsl(var(--primary))/50] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:bg-white/[0.06] shadow-2xl"
              />
              <div className="absolute inset-y-0 right-2 flex items-center">
                <span className="hidden sm:inline-flex items-center justify-center px-2 py-1 text-xs font-semibold text-slate-400 border border-white/10 rounded-md bg-white/5">
                  ⌘ K
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Documentation Categories ─────────────────────────── */}
        <section className="container mx-auto px-6 py-12">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {DOC_CATEGORIES.map((category, idx) => (
              <RevealSection key={idx} delay={`delay-[${idx * 100}ms]`}>
                <Link
                  href="#"
                  className="group block h-full rounded-2xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md transition-all duration-300 hover:bg-white/[0.04] hover:border-[hsl(var(--primary))/40] hover:shadow-[0_8px_32px_-10px_hsla(var(--primary),0.2)] hover:-translate-y-1"
                >
                  <div className="mb-6 flex items-center justify-between">
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary-light))] ring-1 ring-white/10 group-hover:ring-[hsl(var(--primary))/50] transition-colors">
                      <category.icon />
                    </div>
                    <div className="text-slate-600 group-hover:text-[hsl(var(--primary-light))] transition-colors group-hover:translate-x-1 duration-300">
                      <Icons.ArrowRight />
                    </div>
                  </div>
                  <h3 className="mb-3 text-xl font-bold text-white group-hover:text-[hsl(var(--primary-light))] transition-colors">
                    {category.title}
                  </h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{category.desc}</p>
                </Link>
              </RevealSection>
            ))}
          </div>
        </section>

        {/* ── Popular Articles / Quick Links ───────────────────── */}
        <section className="container mx-auto px-6 py-20">
          <RevealSection>
            <div className="rounded-3xl border border-white/10 bg-white/[0.01] p-8 md:p-12 backdrop-blur-sm">
              <h2 className="text-2xl font-bold text-white mb-8">Quick Start Guides</h2>

              <div className="grid gap-4 md:grid-cols-2">
                {[
                  'Understanding the Production Readiness Score',
                  'Invoking the Orchestrator Agent via API',
                  'Connecting GitLab self-hosted repositories',
                  'How to structure AI-enhanced architecture notes',
                  'Reading Kraivor Correlation IDs in your logs',
                  'Migrating from legacy static analyzers',
                ].map((article, i) => (
                  <Link
                    key={i}
                    href="#"
                    className="group flex items-center justify-between p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/10 transition-colors"
                  >
                    <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                      {article}
                    </span>
                    <span className="text-slate-600 group-hover:text-[hsl(var(--primary-light))] transition-colors">
                      <Icons.ArrowRight />
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </RevealSection>
        </section>

        {/* ── CTA Support ──────────────────────────────────────── */}
        <section className="container mx-auto px-6 pb-12">
          <RevealSection>
            <div className="text-center">
              <p className="text-slate-400 mb-4">Can&apos;t find what you&apos;re looking for?</p>
              <Link
                href="#"
                className="inline-flex items-center gap-2 text-[hsl(var(--primary-light))] hover:text-white transition-colors font-medium"
              >
                Contact Developer Support <Icons.ArrowRight />
              </Link>
            </div>
          </RevealSection>
        </section>
      </main>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="border-t border-white/10 bg-[#0a0a0f] py-12">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <span className="text-xl font-bold tracking-tight text-white">✦ Kraivor</span>
          <div className="flex gap-6">
            <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
              Status
            </Link>
            <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
              API Docs
            </Link>
            <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
              GitHub
            </Link>
          </div>
          <p className="text-sm text-slate-500">
            &copy; {new Date().getFullYear()} Kraivor Technologies.
          </p>
        </div>
      </footer>
    </div>
  );
}
