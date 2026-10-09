import Link from 'next/link';
import { ROUTES } from '@/constants';
import { MarketingHeader } from '@/components/marketing/marketing-header';
import { MarketingFooter } from '@/components/marketing/marketing-footer';
import { Container } from '@/components/marketing/container';
import { MarqueeLogos } from '@/components/marketing/marquee-logos';
import { RevealSection } from '@/components/marketing/reveal-section';
import { ArrowRight, Code, Robot, Kanban, MagnifyingGlass } from '@phosphor-icons/react/dist/ssr';

const PRODUCTS = [
  {
    icon: Code,
    title: 'Repository Analyzer',
    desc: 'Connect any Git repo and get architecture evaluation, code quality scores, security posture, and readiness metrics in seconds.',
    stat: '500ms',
    statLabel: 'avg scan time',
  },
  {
    icon: Robot,
    title: 'Agentic AI',
    desc: 'Specialized agents collaborate to answer engineering questions - from code exploration to architecture reasoning.',
    stat: '3',
    statLabel: 'specialized agents',
  },
  {
    icon: Kanban,
    title: 'Developer Workspace',
    desc: 'AI-enhanced notes, task management, and decision logs indexed alongside your codebase for context continuity.',
    stat: '1',
    statLabel: 'unified view',
  },
];

const STATS = [
  { value: '10K+', label: 'concurrent users' },
  { value: '500ms', label: 'avg analysis time' },
  { value: '3', label: 'integrated products' },
  { value: '99.9%', label: 'platform uptime' },
];

export default function RootPage() {
  return (
    <div className="min-h-screen bg-[#121215] text-neutral-100 selection:bg-[var(--venom-yellow)]/25">
      <MarketingHeader />

      <main className="relative">
        {/* ── HERO ── */}
        <section className="pt-28 pb-20">
          <Container>
            <div className="max-w-4xl">
              <RevealSection>
                <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-normal tracking-tight leading-[1.05] text-neutral-100">
                  Your codebase.<br />
                  <span className="text-[var(--text-accent)] font-normal">Analyzed. Augmented.</span><br />
                  Accelerated.
                </h1>
              </RevealSection>
              <RevealSection delay={0.15}>
                <p className="text-base text-neutral-500 max-w-[50ch] mt-6 leading-relaxed font-normal">
                  One platform connecting repository analysis, AI agents, and developer tools into a single workflow. Production-grade from your first commit.
                </p>
              </RevealSection>
              <RevealSection delay={0.3}>
                <div className="flex flex-wrap gap-3 mt-8">
                  <Link
                    href={ROUTES.REGISTER}
                    className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-5 py-2.5 text-sm font-medium text-black transition-all hover:brightness-110 active:scale-[0.98]"
                  >
                    Start Free Trial
                    <ArrowRight size={15} weight="bold" />
                  </Link>
                  <Link
                    href={ROUTES.DOCS}
                    className="inline-flex items-center rounded-xl border border-neutral-800 px-5 py-2.5 text-sm font-medium text-neutral-400 transition-all hover:bg-neutral-900 hover:text-neutral-200 active:scale-[0.98]"
                  >
                    Read the docs
                  </Link>
                </div>
              </RevealSection>
            </div>
          </Container>
        </section>

        {/* ── PRODUCTS ── */}
        <section className="border-t border-neutral-800/60">
          <Container className="py-20">
            <RevealSection>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600 mb-3">Products</p>
              <h2 className="font-display text-2xl font-normal text-neutral-100 mb-12">
                Three products. <span className="text-[var(--text-accent)]">One workspace.</span>
              </h2>
            </RevealSection>
            <div className="grid md:grid-cols-3 gap-px bg-neutral-800/40 rounded-xl overflow-hidden">
              {PRODUCTS.map((product, i) => (
                <div key={product.title} className="bg-[#121215]">
                  <RevealSection delay={i * 0.1}>
                    <div className="p-6 md:p-8">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-900 border border-neutral-800 text-[var(--text-accent)] mb-4">
                        <product.icon size={16} weight="bold" />
                      </div>
                      <h3 className="text-base font-medium text-neutral-100 mb-2">{product.title}</h3>
                      <p className="text-sm text-neutral-500 leading-relaxed mb-5">{product.desc}</p>
                      <div className="flex items-baseline gap-1.5">
                        <span className="font-mono text-2xl font-light text-[var(--text-accent)]">{product.stat}</span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-neutral-600">{product.statLabel}</span>
                      </div>
                    </div>
                  </RevealSection>
                </div>
              ))}
            </div>
          </Container>
        </section>

        {/* ── DEEP DIVE 01: ANALYSIS ── */}
        <section className="border-t border-neutral-800/60">
          <Container className="py-20">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <RevealSection>
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600 mb-3">Analysis</p>
                  <h2 className="font-display text-3xl font-normal text-neutral-100 mb-4 leading-tight">
                    Know your codebase<br />
                    <span className="text-[var(--text-accent)] font-normal">before you merge</span>
                  </h2>
                  <p className="text-sm text-neutral-500 leading-relaxed mb-6">
                    Kraivor analyzes every PR against your architecture rules, security policies, and best practices - not just syntax. Rule-based static analysis catches definite problems; AI contextual understanding catches architectural drift.
                  </p>
                  <Link
                    href={ROUTES.FEATURES}
                    className="inline-flex items-center gap-1 text-sm font-medium text-[var(--text-accent)] transition-colors hover:opacity-80"
                  >
                    See how it works <ArrowRight size={12} weight="bold" />
                  </Link>
                </div>
              </RevealSection>
              <RevealSection>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 font-mono text-sm leading-7">
                  <div className="flex items-center gap-2 mb-3 pb-3 border-b border-neutral-800">
                    <MagnifyingGlass size={13} weight="bold" className="text-[var(--text-accent)]" />
                    <span className="text-[10px] text-neutral-600 uppercase tracking-[0.15em]">Analysis Report - api-service</span>
                  </div>
                  <div className="space-y-2 text-neutral-500">
                    <p><span className="text-emerald-500">*</span> Architecture <span className="text-neutral-300">85/100</span> - <span className="text-neutral-600">well-structured modular layout</span></p>
                    <p><span className="text-[var(--text-accent)]">*</span> Code Quality <span className="text-neutral-300">78/100</span> - <span className="text-neutral-600">some long functions flagged</span></p>
                    <p><span className="text-rose-500">*</span> Security <span className="text-neutral-300">92/100</span> - <span className="text-neutral-600">1 outdated dependency</span></p>
                    <p><span className="text-sky-500">*</span> DevOps <span className="text-neutral-300">70/100</span> - <span className="text-neutral-600">missing CI/CD pipeline config</span></p>
                  </div>
                </div>
              </RevealSection>
            </div>
          </Container>
        </section>

        {/* ── DEEP DIVE 02: AI AGENTS ── */}
        <section className="border-t border-neutral-800/60">
          <Container className="py-20">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <RevealSection>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 font-mono text-sm leading-7">
                  <div className="flex items-center gap-2 mb-3 pb-3 border-b border-neutral-800">
                    <Robot size={13} weight="bold" className="text-[var(--text-accent)]" />
                    <span className="text-[10px] text-neutral-600 uppercase tracking-[0.15em]">Agent Session - orchestrator</span>
                  </div>
                  <div className="space-y-3">
                    <p className="text-[var(--text-accent)]">Orchestrator &rarr; Code Explorer</p>
                    <p className="text-neutral-600 pl-4">Analyze the payment processing flow in the checkout module. Find rate-limiting patterns.</p>
                    <p className="text-[var(--text-accent)]">Code Explorer &rarr; Explainer</p>
                    <p className="text-neutral-600 pl-4">Found 2 rate-limit implementations using a leaky-bucket pattern. Both lack backpressure handling under peak load. Recommended fix: migrate to token-bucket with configurable burst limits.</p>
                    <p className="text-neutral-700">-</p>
                    <p className="text-emerald-500"><span className="text-neutral-300">Summary:</span> 2 findings - 1 critical - 1 recommendation</p>
                  </div>
                </div>
              </RevealSection>
              <RevealSection>
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600 mb-3">Agentic AI</p>
                  <h2 className="font-display text-3xl font-normal text-neutral-100 mb-4 leading-tight">
                    Three specialized agents.<br />
                    <span className="text-[var(--text-accent)] font-normal">One coherent answer.</span>
                  </h2>
                  <p className="text-sm text-neutral-500 leading-relaxed mb-6">
                    Not a chatbot. A multi-agent system where the Orchestrator routes queries, Code Explorer searches your entire codebase, and Explainer synthesizes findings into actionable engineering answers.
                  </p>
                  <Link
                    href={ROUTES.FEATURES}
                    className="inline-flex items-center gap-1 text-sm font-medium text-[var(--text-accent)] transition-colors hover:opacity-80"
                  >
                    Meet the agents <ArrowRight size={12} weight="bold" />
                  </Link>
                </div>
              </RevealSection>
            </div>
          </Container>
        </section>

        {/* ── STATS ── */}
        <section className="border-t border-neutral-800/60">
          <Container>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {STATS.map((stat) => (
                <RevealSection key={stat.label}>
                  <div className="text-center">
                    <p className="font-mono text-2xl font-normal text-[var(--text-accent)] mb-1">{stat.value}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-neutral-600">{stat.label}</p>
                  </div>
                </RevealSection>
              ))}
            </div>
          </Container>
        </section>

        {/* ── TRUSTED BY ── */}
        <section className="border-t border-neutral-800/60 py-16">
          <Container>
            <RevealSection>
              <p className="text-center font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600 mb-8">
                Trusted by engineering teams
              </p>
            </RevealSection>
            <RevealSection>
              <MarqueeLogos />
            </RevealSection>
          </Container>
        </section>

        {/* ── CTA ── */}
        <section className="pb-20">
          <Container>
            <RevealSection>
              <div className="rounded-xl border border-neutral-800/60 bg-neutral-900/30 p-12 md:p-16 text-center max-w-2xl mx-auto">
                <h2 className="font-display text-2xl font-normal text-neutral-100 mb-3">
                  Production-grade engineering.
                </h2>
                <p className="text-sm text-neutral-500 mb-8 max-w-sm mx-auto">
                  Start shipping with confidence. No credit card required.
                </p>
                <Link
                  href={ROUTES.REGISTER}
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-6 py-2.5 text-sm font-medium text-black transition-all hover:brightness-110 active:scale-[0.98]"
                >
                  Start Free Trial
                  <ArrowRight size={15} weight="bold" />
                </Link>
              </div>
            </RevealSection>
          </Container>
        </section>

      </main>

      <div className="fixed bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#121215] to-transparent pointer-events-none z-50" />

      <MarketingFooter />
    </div>
  );
}
