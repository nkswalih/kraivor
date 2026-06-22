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
  Check: (props: React.SVGProps<SVGSVGElement>) => (
    <svg
      {...props}
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      viewBox="0 0 24 24"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  ),
  ArrowRight: (props: React.SVGProps<SVGSVGElement>) => (
    <svg
      {...props}
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

/* ─── Pricing Tiers ──────────────────────────────────────────── */
const PRICING_TIERS = [
  {
    name: 'Developer',
    description: 'For individual developers getting started.',
    price: { monthly: 999, annually: 9999 },
    features: [
      '1 Connected Repository',
      'Basic Code Analysis',
      'AI Assistant (100 Queries/month)',
      'Notes & Tasks Management',
      'Community Support',
    ],
    cta: 'Start Free Trial',
    highlight: false,
    popular: false,
  },
  {
    name: 'Team',
    description: 'For small teams and startups.',
    price: { monthly: 4999, annually: 49999 },
    features: [
      '5 Connected Repositories',
      'Advanced Code Analysis',
      'AI Assistant (1000 Queries/month)',
      'Project Management Tools',
      'Priority Email Support',
    ],
    cta: 'Start Free Trial',
    highlight: true,
    popular: true,
  },
  {
    name: 'Enterprise',
    description: 'For larger organizations and complex needs.',
    price: { monthly: 19999, annually: 199999 },
    features: [
      'Unlimited Repositories',
      'Advanced Security Audits',
      'Dedicated AI Agents',
      'Team Collaboration Features',
      '24/7 Premium Support',
      'Custom Integrations',
    ],
    cta: 'Contact Sales',
    highlight: false,
    popular: false,
  },
];

/* ─── Page Component ─────────────────────────────────────────── */
export default function PricingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [billingMode, setBillingMode] = useState<'monthly' | 'annually'>('annually');

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0a0a0f] text-slate-200">
      {/* ── Ambient Background Glows ─────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute top-[-10%] right-[-5%] h-[600px] w-[600px] rounded-full bg-[hsl(var(--primary))]/10 blur-[150px] animate-float-slow" />
        <div className="absolute bottom-[-10%] left-[-10%] h-[500px] w-[500px] rounded-full bg-[hsl(var(--primary-dark))]/20 blur-[120px] animate-float-medium" />
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
            ✦ Kraivor
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
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10 pt-32 pb-24">
        {/* ── Hero Section ─────────────────────────────────────── */}
        <section className="container mx-auto px-6 pt-12 pb-20 text-center">
          <div className="animate-fade-up mx-auto max-w-3xl">
            <h1 className="text-5xl font-extrabold tracking-tight sm:text-7xl mb-6 text-white">
              Pricing Plans
            </h1>
            <p className="text-xl text-slate-400 mb-10">
              Choose the plan that fits your team's needs. Scale your intelligence, pay for what you
              use.
            </p>

            {/* Billing Mode Toggle */}
            <div className="animate-fade-up mx-auto mb-12 flex max-w-fit items-center justify-center space-x-2 rounded-full border border-[hsl(var(--primary))]/20 bg-[hsl(var(--primary))]/5 p-2 backdrop-blur-md">
              <button
                onClick={() => setBillingMode('annually')}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${billingMode === 'annually' ? 'bg-[hsl(var(--primary))]/50 text-white shadow-lg' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
              >
                Annually <span className="text-[hsl(var(--primary-light))]">(Save 20%)</span>
              </button>
              <button
                onClick={() => setBillingMode('monthly')}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${billingMode === 'monthly' ? 'bg-[hsl(var(--primary))]/50 text-white shadow-lg' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
              >
                Monthly
              </button>
            </div>
          </div>
        </section>

        {/* ── Pricing Tiers ────────────────────────────────────── */}
        <section className="container mx-auto px-6 py-12">
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {PRICING_TIERS.map((tier, idx) => (
              <RevealSection key={idx} delay={`delay-[${idx * 100}ms]`}>
                <div
                  className={`group relative h-full rounded-3xl border p-8 backdrop-blur-xl transition-all duration-300 hover:-translate-y-2 
                  ${tier.highlight ? `border-[hsl(var(--primary))/40] bg-white/[0.04] shadow-[0_8px_32px_-10px_hsla(var(--primary),0.3)]` : 'border-white/10 bg-white/[0.02] hover:bg-white/[0.04] hover:border-[hsl(var(--primary))/30] hover:shadow-[0_0_40px_-15px_hsl(var(--primary))]'}`}
                >
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10 inline-flex items-center justify-center rounded-full bg-[hsl(var(--primary))]/80 px-4 py-1.5 text-xs font-bold text-white shadow-lg animate-pulse">
                      Most Popular
                    </div>
                  )}

                  <div className="mb-5 flex items-center justify-between">
                    <h3
                      className={`text-2xl font-bold ${tier.highlight ? 'text-[hsl(var(--primary-light))]' : 'text-white group-hover:text-[hsl(var(--primary-light))]'} transition-colors`}
                    >
                      {tier.name}
                    </h3>
                    {tier.popular && (
                      <span className="rounded-full bg-[hsl(var(--primary))]/20 px-3 py-1 text-xs font-medium text-[hsl(var(--primary-light))]">
                        Save 20%
                      </span>
                    )}
                  </div>

                  <p className="mb-8 text-sm text-slate-400">{tier.description}</p>

                  <div className="mb-8 border-b border-white/10 pb-6">
                    <p className="flex items-baseline gap-1 justify-center">
                      <span
                        className={`text-5xl font-extrabold ${tier.highlight ? 'text-[hsl(var(--primary-light))]' : 'text-white group-hover:text-[hsl(var(--primary-light))]'} transition-colors`}
                      >
                        {formatCurrency(tier.price[billingMode])}
                      </span>
                      <span className="text-sm font-medium text-slate-400">
                        /{billingMode === 'annually' ? 'year' : 'month'}
                      </span>
                    </p>
                    {billingMode === 'monthly' && (
                      <p className="text-xs text-slate-500 text-center mt-1">
                        Billed annually at {formatCurrency(tier.price.annually / 12)}/month
                      </p>
                    )}
                  </div>

                  <ul className="space-y-4 text-sm text-slate-300">
                    {tier.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        <div
                          className={`flex h-6 w-6 items-center justify-center rounded-full border transition-colors ${tier.highlight ? 'bg-[hsl(var(--primary))]/20 border-[hsl(var(--primary))/40]' : 'bg-white/5 border-white/10 group-hover:bg-white/10 group-hover:border-[hsl(var(--primary))/30]'}`}
                        >
                          <Icons.Check
                            className={`${tier.highlight ? 'text-[hsl(var(--primary-light))]' : 'text-slate-300 group-hover:text-[hsl(var(--primary-light))]'} transition-colors`}
                          />
                        </div>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    href={ROUTES.REGISTER}
                    className={`mt-10 block w-full rounded-xl px-6 py-3 text-center text-base font-semibold transition-all duration-300 
                    ${
                      tier.highlight
                        ? 'bg-[hsl(var(--primary))] text-white shadow-[0_0_40px_-10px_hsla(var(--primary),0.5)] hover:bg-[hsl(var(--primary-light))]'
                        : 'bg-white/[0.05] text-slate-200 border border-white/10 hover:bg-white/[0.1] hover:border-white/20'
                    }`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              </RevealSection>
            ))}
          </div>
        </section>

        {/* ── Feature Comparison / FAQ Section ───────────────────── */}
        <section className="container mx-auto px-6 py-24">
          <RevealSection>
            <div className="rounded-3xl border border-white/10 bg-white/[0.01] p-8 md:p-12 backdrop-blur-sm">
              <h2 className="text-3xl font-bold text-white mb-12 text-center">
                Frequently Asked Questions
              </h2>

              <div className="grid gap-6 md:grid-cols-2">
                {[
                  {
                    question: "What is Kraivor's Production Readiness Score?",
                    answer:
                      "It's an AI-driven evaluation of your codebase's scalability, security, and maintainability. It predicts potential failures before they happen in production.",
                  },
                  {
                    question: 'Can I switch plans later?',
                    answer:
                      'Yes, you can upgrade or downgrade your plan at any time. Your billing will be prorated accordingly.',
                  },
                  {
                    question: "What is included in the 'Team' plan's AI Assistant?",
                    answer:
                      'The Team plan includes 1000 AI query credits per month, allowing your team to ask extensive questions about your codebase.',
                  },
                  {
                    question: 'Do you offer custom enterprise solutions?',
                    answer:
                      "Absolutely. Contact our sales team for custom integrations, dedicated support, and tailored solutions for your organization's unique needs.",
                  },
                  {
                    question: 'How does the async processing work?',
                    answer:
                      'Any operation over 500ms is handled in the background. Results are pushed via WebSocket or polled, ensuring immediate HTTP responses and 10,000+ concurrent users without slowdowns.',
                  },
                  {
                    question: 'What is the refund policy?',
                    answer:
                      "We offer a 14-day money-back guarantee on all plans. If you're not satisfied, you can request a full refund within 14 days of your purchase.",
                  },
                ].map((faq, i) => (
                  <RevealSection key={i} delay={`delay-[${i * 100}ms]`}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5 backdrop-blur-sm">
                      <h4 className="mb-3 text-lg font-semibold text-white">{faq.question}</h4>
                      <p className="text-sm text-slate-400">{faq.answer}</p>
                    </div>
                  </RevealSection>
                ))}
              </div>
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
