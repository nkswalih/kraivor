import Link from 'next/link';
import { ROUTES } from '@/constants';
import { MarketingHeader } from '@/components/marketing/marketing-header';
import { MarketingFooter } from '@/components/marketing/marketing-footer';
import { Container } from '@/components/marketing/container';
import { RevealSection } from '@/components/marketing/reveal-section';
import { PricingTiers } from '@/components/marketing/pricing-tiers';
import { FAQSection } from '@/components/marketing/faq-section';

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#121215] text-neutral-100">
      <MarketingHeader active="pricing" />

      <main className="pt-24 pb-16">
        {/* Hero */}
        <section className="py-16 text-center">
          <Container>
            <RevealSection>
              <h1 className="font-display text-5xl sm:text-6xl font-normal tracking-tight leading-[1.05] text-neutral-100 mb-6">
                Simple, transparent pricing
              </h1>
              <p className="text-base text-neutral-500 max-w-[55ch] mx-auto">
                Choose the plan that fits your team. No hidden fees, no surprise charges.
              </p>
            </RevealSection>
          </Container>
        </section>

        {/* Tiers */}
        <section className="py-8">
          <Container>
            <PricingTiers />
          </Container>
        </section>

        {/* FAQ */}
        <section className="py-20">
          <Container>
            <RevealSection>
              <div className="border border-neutral-800 rounded-xl p-8 md:p-12">
                <h2 className="text-2xl font-normal text-neutral-100 mb-10 text-center">
                  Frequently Asked Questions
                </h2>
                <FAQSection />
              </div>
            </RevealSection>
          </Container>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
