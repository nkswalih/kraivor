import Link from 'next/link';
import { ROUTES } from '@/constants';
import { MarketingHeader } from '@/components/marketing/marketing-header';
import { MarketingFooter } from '@/components/marketing/marketing-footer';
import { Container } from '@/components/marketing/container';
import { RevealSection } from '@/components/marketing/reveal-section';
import { Code, Robot, Kanban, Article, SquaresFour, GitBranch, ArrowRight } from '@phosphor-icons/react/dist/ssr';

const PRODUCTIVITY_FEATURES = [
  { icon: Article, title: 'AI-Enhanced Notes', desc: 'Notes indexed alongside your codebase. Ask the AI a question and it remembers why a decision was made.' },
  { icon: SquaresFour, title: 'Task Management', desc: 'Tasks linked to PRs, commits, and analysis findings. Never lose context between code and work items.' },
  { icon: Kanban, title: 'Project Organization', desc: 'Architecture diagrams, milestones, and cross-repository tracking in one unified workspace.' },
  { icon: GitBranch, title: 'Decision Log', desc: 'Every architectural decision captured and indexed. The AI uses your decision history to give better answers.' },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-[#121215] text-neutral-100">
      <MarketingHeader active="features" />

      <main className="pt-24 pb-16">
        {/* ── HERO ── */}
        <section className="py-16 text-center">
          <Container>
            <RevealSection>
              <h1 className="font-display text-5xl sm:text-6xl font-normal tracking-tight leading-[1.05] text-neutral-100 mb-6">
                One platform.{' '}
                <span className="text-[var(--text-accent)]">Three products.</span>
              </h1>
              <p className="text-base text-neutral-500 max-w-[60ch] mx-auto leading-relaxed">
                Not three tools bolted together. One platform where analysis, AI, and productivity share infrastructure, identity, and context.
              </p>
            </RevealSection>
          </Container>
        </section>

        {/* ── PRODUCT 01: ANALYZER ── */}
        <section className="border-t border-neutral-800/60">
          <Container className="py-20">
            <RevealSection>
              <div className="grid lg:grid-cols-2 gap-12 items-center">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600 mb-3">Core Product</p>
                  <h2 className="font-display text-3xl font-normal text-neutral-100 mb-4 leading-tight">Repository Analyzer</h2>
                  <p className="text-sm text-neutral-500 leading-relaxed mb-6">
                    Connect your GitHub or GitLab repository and Kraivor analyzes the entire codebase — evaluating architecture, code quality, security posture, and scalability readiness.
                  </p>
                  <p className="text-sm text-neutral-600 leading-relaxed">
                    <span className="text-neutral-300 font-medium">Key differentiator:</span> Rule-based static analysis combined with AI contextual understanding. Rules catch definite problems; AI catches architectural intent.
                  </p>
                </div>
                <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 font-mono text-sm leading-7">
                  <div className="flex items-center gap-2 mb-3 pb-3 border-b border-neutral-800">
                    <Code size={13} weight="bold" className="text-[var(--text-accent)]" />
                    <span className="text-[10px] text-neutral-600 uppercase tracking-[0.15em]">Analyzer Dashboard Preview</span>
                  </div>
                  <div className="space-y-2 text-neutral-500">
                    <p><span className="text-emerald-500">*</span> Architecture <span className="text-neutral-300">85/100</span> - <span className="text-neutral-600">clean modular layout</span></p>
                    <p><span className="text-[var(--text-accent)]">*</span> Code Quality <span className="text-neutral-300">78/100</span> - <span className="text-neutral-600">some long functions flagged</span></p>
                    <p><span className="text-rose-500">*</span> Security <span className="text-neutral-300">92/100</span> - <span className="text-neutral-600">1 outdated dependency</span></p>
                    <p><span className="text-sky-500">*</span> Readiness <span className="text-neutral-300">74/100</span> - <span className="text-neutral-600">missing CI/CD config</span></p>
                  </div>
                </div>
              </div>
            </RevealSection>
          </Container>
        </section>

        {/* ── PRODUCT 02: AI ── */}
        <section className="border-y border-neutral-800/60">
          <Container className="py-20">
            <RevealSection>
              <div className="text-center mb-12">
                <h2 className="font-display text-3xl font-normal text-neutral-100 mb-4 leading-tight">Multi-agent intelligence</h2>
                <p className="text-sm text-neutral-500 max-w-[60ch] mx-auto">
                  Not a chatbot. Not autocomplete. A system of specialized AI agents that collaborate to answer complex engineering questions.
                </p>
              </div>
            </RevealSection>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                { title: 'Orchestrator Agent', desc: 'Routes queries to the right specialized agents. Decides which tools to invoke and in what order.' },
                { title: 'Code Explorer Agent', desc: 'Searches the codebase, reads files, traces dependencies. Has read access to every repository.' },
                { title: 'Explainer Agent', desc: 'Synthesizes findings into actionable results. Turns agent collaboration into clear engineering answers.' },
              ].map((agent, i) => (
                <RevealSection key={agent.title} delay={i * 0.1}>
                  <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 h-full">
                    <div className="flex items-center gap-3 mb-3">
                      <Robot size={16} weight="fill" className="text-[var(--text-accent)]" />
                      <span className="font-mono text-[10px] text-neutral-600 uppercase tracking-wider">Agent 0{i + 1}</span>
                    </div>
                    <h3 className="text-base font-medium text-neutral-100 mb-2">{agent.title}</h3>
                    <p className="text-sm text-neutral-500 leading-relaxed">{agent.desc}</p>
                  </div>
                </RevealSection>
              ))}
            </div>

            <RevealSection>
              <p className="mt-8 text-center text-sm text-neutral-600 max-w-2xl mx-auto border-t border-neutral-800 pt-6">
                Agents have memory, can call tools, search the codebase, and collaborate autonomously.
              </p>
            </RevealSection>
          </Container>
        </section>

        {/* ── PRODUCT 03: PRODUCTIVITY ── */}
        <section className="py-20">
          <Container>
            <RevealSection>
              <div className="text-center mb-12">
                <h2 className="font-display text-3xl font-normal text-neutral-100 mb-4 leading-tight">Developer Productivity</h2>
                <p className="text-sm text-neutral-500 max-w-[55ch] mx-auto">
                  The daily driver. Replace scattered workflow with unified context that your AI understands.
                </p>
              </div>
            </RevealSection>

            <div className="grid md:grid-cols-2 gap-6">
              {PRODUCTIVITY_FEATURES.map((feature, i) => (
                <RevealSection key={feature.title} delay={i * 0.1}>
                  <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 h-full">
                    <div className="flex items-start gap-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-neutral-900/70 border border-neutral-800 text-[var(--text-accent)]">
                        <feature.icon size={18} weight="bold" />
                      </div>
                      <div>
                        <h3 className="text-base font-medium text-neutral-100 mb-1">{feature.title}</h3>
                        <p className="text-sm text-neutral-500 leading-relaxed">{feature.desc}</p>
                      </div>
                    </div>
                  </div>
                </RevealSection>
              ))}
            </div>
          </Container>
        </section>

        {/* ── CTA ── */}
        <section className="border-t border-neutral-800/60">
          <Container className="py-20">
            <RevealSection>
              <div className="rounded-xl border border-neutral-800/60 bg-neutral-900/30 p-12 md:p-16 text-center max-w-2xl mx-auto">
                <h2 className="font-display text-2xl font-normal text-neutral-100 mb-3">
                  Ready to unify your workflow?
                </h2>
                <p className="text-sm text-neutral-500 mb-8 max-w-sm mx-auto">
                  Stop context switching. Build with production-grade intelligence.
                </p>
                <Link
                  href={ROUTES.REGISTER}
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-6 py-2.5 text-sm font-medium text-black transition-all hover:brightness-110 active:scale-[0.98]"
                >
                  Start Free Trial <ArrowRight size={15} weight="bold" />
                </Link>
              </div>
            </RevealSection>
          </Container>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
