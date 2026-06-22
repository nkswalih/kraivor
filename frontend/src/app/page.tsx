'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/lib/stores/auth-store';
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

/* ─── Icons ─────────────────────────────────────────────────── */
const CodeIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="16 18 22 12 16 6"></polyline>
    <polyline points="8 6 2 12 8 18"></polyline>
  </svg>
);

const SparklesIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
  </svg>
);

const LayersIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
    <polyline points="2 17 12 22 22 17"></polyline>
    <polyline points="2 12 12 17 22 12"></polyline>
  </svg>
);

/* ─── Section Component ──────────────────────────────────────── */
function RevealSection({ children, delay = '' }: { children: React.ReactNode; delay?: string }) {
  const { ref, isVisible } = useScrollReveal();
  return (
    <div
      ref={ref}
      className={`transition-all duration-1000 ${
        isVisible ? `opacity-100 translate-y-0 ${delay}` : 'opacity-0 translate-y-12'
      }`}
    >
      {children}
    </div>
  );
}

/* ─── Main Page ──────────────────────────────────────────────── */
export default function RootPage() {
  const { isAuthenticated, workspaceSlug } = useAuthStore();
  const [scrolled, setScrolled] = useState(false);

  // Handle header blur on scroll
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0a0a0f] text-slate-200">
      {/* ── Ambient Background Glows ─────────────────────────── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-[10%] top-[-10%] h-[500px] w-[500px] rounded-full bg-[hsl(var(--primary))]/20 blur-[120px] animate-float-slow" />
        <div className="absolute right-[-10%] top-[20%] h-[400px] w-[400px] rounded-full bg-[hsl(var(--primary-light))]/10 blur-[120px] animate-float-medium" />
        <div className="absolute bottom-[-10%] left-[20%] h-[600px] w-[600px] rounded-full bg-[hsl(var(--primary-dark))]/20 blur-[150px] animate-float-fast" />
      </div>

      {/* ── Header ────────────────────────────────────────────── */}
      <header
        className={`fixed top-0 z-50 w-full transition-all duration-300 ${
          scrolled
            ? 'border-b border-white/5 bg-[#0a0a0f]/60 backdrop-blur-xl'
            : 'border-transparent bg-transparent'
        }`}
      >
        <div className="container mx-auto flex h-20 items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold tracking-tight bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
              ✦ Kraivor
            </span>
          </div>
          <nav className="hidden items-center gap-8 md:flex">
            <Link
              href={ROUTES.FEATURES}
              className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
            >
              Features
            </Link>
            <Link
              href={ROUTES.PRICING}
              className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
            >
              Pricing
            </Link>
            <Link
              href={ROUTES.DOCS}
              className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
            >
              Docs
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <Link href={`/${workspaceSlug || 'dashboard'}`} className="btn-glassy-krait">
                {/* Left Area (Icon + Text) */}
                <div className="flex items-center gap-2.5 px-4 py-2">
                  <div className="btn-glassy-icon">
                    {/* Dashboard Grid Icon */}
                    <svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="3" y="3" width="7" height="7" rx="1.5"></rect>
                      <rect x="14" y="3" width="7" height="7" rx="1.5"></rect>
                      <rect x="14" y="14" width="7" height="7" rx="1.5"></rect>
                      <rect x="3" y="14" width="7" height="7" rx="1.5"></rect>
                    </svg>
                  </div>
                  <span className="text-sm tracking-wide">Dashboard</span>
                </div>

                {/* Center Faded Divider */}
                <div className="btn-glassy-divider"></div>

                {/* Right Area (Arrow) */}
                <div className="btn-glassy-arrow">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M5 12h14"></path>
                    <path d="m12 5 7 7-7 7"></path>
                  </svg>
                </div>
              </Link>
            ) : (
              <>
                <Link
                  href={ROUTES.LOGIN}
                  className="hidden text-sm font-medium text-slate-300 transition-colors hover:text-white sm:block"
                >
                  Sign in
                </Link>

                <Link href={ROUTES.REGISTER} className="btn-glassy-krait">
                  {/* Left Area (Icon + Text) */}
                  <div className="flex items-center gap-2.5 px-4 py-2">
                    <div className="btn-glassy-icon">
                      {/* Plus Icon */}
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                      </svg>
                    </div>
                    <span className="text-sm tracking-wide">Get Started</span>
                  </div>

                  {/* Center Faded Divider */}
                  <div className="btn-glassy-divider"></div>

                  {/* Right Area (Arrow) */}
                  <div className="btn-glassy-arrow">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14"></path>
                      <path d="m12 5 7 7-7 7"></path>
                    </svg>
                  </div>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10 pt-32">
        {/* ── Hero Section ─────────────────────────────────────── */}
        <section className="relative flex min-h-[80vh] flex-col items-center justify-center py-20 text-center">
          <div className="container mx-auto px-4">
            {/* Announcement Pill */}
            <div className="animate-fade-up mx-auto mb-8 flex max-w-fit items-center justify-center space-x-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 backdrop-blur-md">
              <span className="flex h-2 w-2 rounded-full bg-[hsl(var(--primary-light))]"></span>
              <p className="text-xs font-medium text-slate-300 sm:text-sm">
                Kraivor 2.0 is now live.{' '}
                <span className="text-white hover:underline cursor-pointer">
                  Read the launch notes →
                </span>
              </p>
            </div>

            <h1 className="animate-fade-up-delay-1 mx-auto max-w-5xl text-5xl font-extrabold tracking-tight sm:text-7xl lg:text-8xl">
              <span className="text-white">Developer Intelligence </span>
              <br className="hidden md:block" />
              <span className="bg-gradient-to-r from-[hsl(var(--primary-light))] via-[hsl(var(--primary))] to-[hsl(var(--primary-dark))] bg-clip-text text-transparent">
                Platform
              </span>
            </h1>

            <p className="animate-fade-up-delay-2 mx-auto mt-8 max-w-2xl text-lg text-slate-400 sm:text-xl leading-relaxed">
              One platform. Three products. Production-grade from day one. Analyze your code,
              collaborate with AI, and ship faster than ever before.
            </p>

            <div
              className="animate-fade-up mx-auto mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row"
              style={{ animationDelay: '0.3s' }}
            >
              <Link
                href={ROUTES.REGISTER}
                className="btn-shimmer flex w-full items-center justify-center rounded-xl px-8 py-4 text-base font-semibold text-white sm:w-auto shadow-[0_0_40px_-10px_hsl(var(--primary))]"
              >
                Start Free Trial
              </Link>
              <Link
                href={ROUTES.FEATURES}
                className="btn-shimmer-secondary flex w-full items-center justify-center rounded-xl px-8 py-4 text-base font-medium text-slate-200 sm:w-auto"
              >
                Explore Features
              </Link>
            </div>
          </div>

          {/* Abstract Dashboard Mockup Graphic */}
          <div
            className="animate-fade-up mx-auto mt-20 w-full max-w-5xl px-4"
            style={{ animationDelay: '0.4s' }}
          >
            <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] shadow-2xl backdrop-blur-xl flex items-center justify-center">
              {/* This represents a stylized dashboard frame */}
              <div className="absolute top-0 w-full h-12 border-b border-white/5 flex items-center px-4 gap-2">
                <div className="h-3 w-3 rounded-full bg-red-600 hover:bg-red-700 hover:cursor-pointer z-10"></div>
                <div className="h-3 w-3 rounded-full bg-yellow-300 hover:bg-yellow-500 hover:cursor-pointer z-10"></div>
                <div className="h-3 w-3 rounded-full bg-green-500 hover:bg-green-700 hover:cursor-pointer z-10"></div>
              </div>
              <img
                src="Screenshot 2026-05-25 212539.png"
                alt="Platform Preview"
                className="w-full h-full object-cover pt-12"
              />
              {/* Inner glowing effect */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent"></div>
            </div>
          </div>
        </section>

        {/* ── Features Section ─────────────────────────────────── */}
        <section className="py-32 relative">
          <div className="container mx-auto px-4">
            <RevealSection>
              <div className="text-center mb-20">
                <h2 className="text-3xl font-bold text-white sm:text-5xl tracking-tight">
                  Why choose Kraivor?
                </h2>
                <p className="mt-4 text-lg text-slate-400">
                  Everything you need to scale your engineering team.
                </p>
              </div>
            </RevealSection>

            <div className="grid gap-8 md:grid-cols-3">
              <RevealSection delay="delay-[100ms]">
                <div className="group relative h-full rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-xl transition-all duration-300 hover:-translate-y-2 hover:bg-white/[0.04] hover:shadow-[0_0_40px_-15px_hsl(var(--primary))] hover:border-[hsl(var(--primary))/30]">
                  <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary-light))] ring-1 ring-white/10 group-hover:ring-[hsl(var(--primary))/50] transition-all">
                    <CodeIcon />
                  </div>
                  <h3 className="mb-4 text-2xl font-bold text-white">Repository Analysis</h3>
                  <p className="text-slate-400 leading-relaxed">
                    Get comprehensive insights into your codebase with AI-powered analysis. Identify
                    bottlenecks and technical debt instantly.
                  </p>
                </div>
              </RevealSection>

              <RevealSection delay="delay-[200ms]">
                <div className="group relative h-full rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-xl transition-all duration-300 hover:-translate-y-2 hover:bg-white/[0.04] hover:shadow-[0_0_40px_-15px_hsl(var(--primary))] hover:border-[hsl(var(--primary))/30]">
                  <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary-light))] ring-1 ring-white/10 group-hover:ring-[hsl(var(--primary))/50] transition-all">
                    <SparklesIcon />
                  </div>
                  <h3 className="mb-4 text-2xl font-bold text-white">AI Assistant</h3>
                  <p className="text-slate-400 leading-relaxed">
                    Chat with context-aware AI to understand legacy code, write boilerplate, and
                    refactor complex logic in seconds.
                  </p>
                </div>
              </RevealSection>

              <RevealSection delay="delay-[300ms]">
                <div className="group relative h-full rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-xl transition-all duration-300 hover:-translate-y-2 hover:bg-white/[0.04] hover:shadow-[0_0_40px_-15px_hsl(var(--primary))] hover:border-[hsl(var(--primary))/30]">
                  <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary-light))] ring-1 ring-white/10 group-hover:ring-[hsl(var(--primary))/50] transition-all">
                    <LayersIcon />
                  </div>
                  <h3 className="mb-4 text-2xl font-bold text-white">Project Management</h3>
                  <p className="text-slate-400 leading-relaxed">
                    Track tasks, document architectures, and organize projects in one unified
                    workspace built specifically for developers.
                  </p>
                </div>
              </RevealSection>
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/10 bg-white/[0.02] py-12 backdrop-blur-lg">
        <div className="container mx-auto px-6">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white">✦ Kraivor</span>
            </div>
            <p className="text-sm text-slate-500">
              &copy; {new Date().getFullYear()} Kraivor Technologies. All rights reserved.
            </p>
            <div className="flex gap-6">
              <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
                Twitter
              </Link>
              <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
                GitHub
              </Link>
              <Link href="#" className="text-sm text-slate-500 hover:text-white transition-colors">
                Discord
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
