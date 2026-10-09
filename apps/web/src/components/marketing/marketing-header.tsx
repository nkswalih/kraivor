'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useScroll, useMotionValueEvent } from 'framer-motion';
import Image from 'next/image';
import { List, X, GithubLogo } from '@phosphor-icons/react';
import { ROUTES } from '@/constants';
import { Container } from '@/components/marketing/container';
import { NavActions } from '@/components/marketing/nav-actions';

const NAV_LINKS = [
  { href: ROUTES.FEATURES, label: 'Features', key: 'features' },
  { href: ROUTES.PRICING, label: 'Pricing', key: 'pricing' },
  { href: ROUTES.DOCS, label: 'Docs', key: 'docs' },
] as const;

export function MarketingHeader({ active }: { active?: string }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, 'change', (latest) => {
    setScrolled(latest > 20);
  });

  return (
    <>
      <header
        className={`fixed top-0 z-50 w-full transition-all duration-300 h-12 ${
          scrolled
            ? 'bg-[#121215]/80 backdrop-blur-md border-b border-neutral-800/30'
            : 'bg-transparent'
        }`}
      >
        <Container className="h-full flex items-center">
          <div className="flex-1">
            <Link href={ROUTES.HOME} className="shrink-0">
              <Image src="/kraivor_text_logo.svg" alt="Kraivor" width={80} height={20} className="h-7 w-auto" />
            </Link>
          </div>
          <nav className="hidden md:flex items-center gap-6 ml-4">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.key}
                href={link.href}
                className={`text-sm transition-colors ${
                  active === link.key
                    ? 'text-neutral-300'
                    : 'text-neutral-500 hover:text-neutral-300'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex-1 flex items-center justify-end">
            <div className="hidden md:flex items-center gap-2">
              <Link
                href="https://github.com/nkswalih/kraivor"
                className="flex items-center gap-1.5 h-8 rounded-lg border border-neutral-600/30 text-neutral-500 hover:text-neutral-300 hover:border-neutral-500/50 transition-colors px-2.5"
                aria-label="GitHub"
              >
                <GithubLogo size={14} weight="fill" />
                <span className="text-[12px] font-medium">GitHub</span>
              </Link>
              <NavActions />
            </div>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-100"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            >
              {menuOpen ? <X size={16} /> : <List size={16} />}
            </button>
          </div>
        </Container>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-[60] bg-[#121215] flex flex-col items-center justify-center gap-8 md:hidden">
          <button
            onClick={() => setMenuOpen(false)}
            className="absolute top-4 right-6 w-8 h-8 rounded-lg bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-100"
            aria-label="Close menu"
          >
            <X size={16} />
          </button>
          <div className="flex flex-col items-center gap-6 text-base" onClick={() => setMenuOpen(false)}>
            <Link href={ROUTES.HOME}>
              <Image src="/kraivor_text_logo.svg" alt="Kraivor" width={80} height={20} className="h-5 w-auto" />
            </Link>
            {NAV_LINKS.map((link) => (
              <Link
                key={link.key}
                href={link.href}
                className={`text-base transition-colors ${
                  active === link.key
                    ? 'text-neutral-300'
                    : 'text-neutral-500 hover:text-neutral-300'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <div className="flex flex-col items-center gap-4 mt-4">
              <NavActions />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
