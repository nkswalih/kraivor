import Link from 'next/link';
import { ROUTES } from '@/constants';
import { MarketingHeader } from '@/components/marketing/marketing-header';
import { MarketingFooter } from '@/components/marketing/marketing-footer';
import { Container } from '@/components/marketing/container';
import { RevealSection } from '@/components/marketing/reveal-section';
import {
  BookOpen,
  GitBranch,
  Robot,
  Kanban,
  Code,
  Lifebuoy,
  MagnifyingGlass,
  ArrowRight,
} from '@phosphor-icons/react/dist/ssr';

const DOC_CATEGORIES = [
  { icon: BookOpen, title: 'Getting Started', desc: 'Platform overview, authentication, and setting up your first workspace.' },
  { icon: GitBranch, title: 'Repository Analyzer', desc: 'Connecting GitHub/GitLab, configuring rules, and understanding readiness scores.' },
  { icon: Robot, title: 'Agentic AI System', desc: 'How to prompt agents, use the Orchestrator, and manage AI context.' },
  { icon: Kanban, title: 'Developer Productivity', desc: 'Managing AI-enhanced notes, linking tasks to PRs, and organizing projects.' },
  { icon: Code, title: 'API Reference', desc: 'REST API endpoints, WebSocket events, and authentication tokens.' },
  { icon: Lifebuoy, title: 'Troubleshooting', desc: 'Common issues, observability logs, and how to read correlation IDs.' },
];

const QUICK_ARTICLES = [
  'Understanding the Production Readiness Score',
  'Invoking the Orchestrator Agent via API',
  'Connecting GitLab self-hosted repositories',
  'How to structure AI-enhanced architecture notes',
  'Reading Kraivor Correlation IDs in your logs',
  'Migrating from legacy static analyzers',
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-[#121215] text-neutral-100">
      <MarketingHeader active="docs" />

      <main className="pt-24 pb-16">
        {/* Hero + Search */}
        <section className="py-16 text-center">
          <Container>
            <RevealSection>
              <h1 className="font-display text-5xl sm:text-6xl font-normal tracking-tight leading-[1.05] text-neutral-100 mb-4">
                How can we help you{' '}
                <span className="text-[var(--text-accent)]">build better?</span>
              </h1>
              <p className="text-neutral-500 mb-10 max-w-[55ch] mx-auto">
                Explore guides, API references, and architecture overviews to get the most out of Kraivor.
              </p>
              <div className="relative max-w-md mx-auto">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-neutral-600">
                  <MagnifyingGlass size={18} />
                </div>
                <input
                  type="text"
                  placeholder="Search documentation..."
                  className="w-full bg-neutral-900/50 border border-neutral-800 rounded-xl py-3 pl-11 pr-4 text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-[var(--text-accent)]/50 text-sm"
                />
              </div>
            </RevealSection>
          </Container>
        </section>

        {/* Categories */}
        <section className="py-8">
          <Container>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {DOC_CATEGORIES.map((category, idx) => (
              <RevealSection key={idx} delay={idx * 0.05}>
                <Link
                  href="#"
                  className="block h-full rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 transition-all hover:border-[var(--text-accent)]/30"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-neutral-900/70 border border-neutral-800 text-[var(--text-accent)] mb-4">
                    <category.icon size={18} weight="bold" />
                  </div>
                  <h3 className="text-base font-medium text-neutral-100 mb-2">{category.title}</h3>
                  <p className="text-sm text-neutral-500 leading-relaxed">{category.desc}</p>
                </Link>
              </RevealSection>
            ))}
          </div>
          </Container>
        </section>

        {/* Quick Start */}
        <section className="py-12">
          <Container>
          <RevealSection>
            <div className="border border-neutral-800 rounded-xl p-8">
              <div className="flex items-center gap-2 mb-6">
                <BookOpen size={18} weight="bold" className="text-[var(--text-accent)]" />
                <h2 className="text-lg font-medium text-neutral-100">Quick Start Guides</h2>
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {QUICK_ARTICLES.map((article, i) => (
                  <Link
                    key={i}
                    href="#"
                    className="flex items-center justify-between p-3 rounded-xl border border-neutral-800 bg-neutral-900/50 group"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[11px] text-neutral-600 w-6">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span className="text-sm text-neutral-500 group-hover:text-neutral-100 transition-colors">
                        {article}
                      </span>
                    </div>
                    <ArrowRight
                      size={12}
                      weight="bold"
                      className="text-neutral-600 group-hover:text-[var(--text-accent)] transition-colors shrink-0"
                    />
                  </Link>
                ))}
              </div>
            </div>
          </RevealSection>
          </Container>
        </section>

        {/* Support CTA */}
        <section className="py-12 text-center">
          <Container>
            <RevealSection>
              <p className="text-neutral-500 mb-4">Can&apos;t find what you&apos;re looking for?</p>
              <Link
                href="#"
                className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-5 py-2.5 text-sm font-medium text-black transition-all hover:brightness-110"
              >
                Contact Developer Support <ArrowRight size={14} weight="bold" />
              </Link>
            </RevealSection>
          </Container>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
