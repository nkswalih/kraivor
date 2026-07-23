import Link from 'next/link';
import Image from 'next/image';
import { TwitterLogo, GithubLogo, DiscordLogo, ArrowUpRight } from '@phosphor-icons/react/dist/ssr';

const footerLinks = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '/features' },
      { label: 'Pricing', href: '/pricing' },
      { label: 'Docs', href: '/docs' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Terms of Service', href: '#' },
      { label: 'Privacy Policy', href: '#' },
    ],
  },
];

const socialLinks = [
  { href: '#', label: 'Twitter', Icon: TwitterLogo },
  { href: '#', label: 'GitHub', Icon: GithubLogo },
  { href: '#', label: 'Discord', Icon: DiscordLogo },
];

export function MarketingFooter() {
  return (
    <footer className="border-t border-neutral-800/60">
      <div className="mx-auto max-w-5xl px-3 sm:px-4 lg:px-6 py-12 lg:py-16">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4 lg:gap-12">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="inline-block shrink-0">
              <Image src="/kraivor_text_logo.svg" alt="Kraivor" width={80} height={20} className="h-5 w-auto" />
            </Link>
            <p className="mt-3 text-sm text-neutral-500 leading-relaxed max-w-[260px]">
              AI-powered code analysis platform that helps teams ship better software, faster.
            </p>
            <div className="mt-4 flex gap-2">
              {socialLinks.map(({ href, label, Icon }) => (
                <Link
                  key={label}
                  href={href}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-800 text-neutral-500 hover:text-[var(--text-accent)] hover:border-[var(--text-accent)]/30 transition-colors"
                  aria-label={label}
                >
                  <Icon size={13} weight="fill" />
                </Link>
              ))}
            </div>
          </div>
          {footerLinks.map((group) => (
            <div key={group.title}>
              <h3 className="font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-3">
                {group.title}
              </h3>
              <ul className="space-y-2">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="inline-flex items-center gap-1 text-sm text-neutral-400 hover:text-white transition-colors group"
                    >
                      {link.label}
                      <ArrowUpRight
                        size={10}
                        className="text-neutral-600 group-hover:text-neutral-400 transition-colors"
                        weight="bold"
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 pt-6 border-t border-neutral-800/60 flex flex-col items-center gap-2 sm:flex-row sm:justify-between">
          <p className="font-mono text-[11px] tracking-wider text-neutral-600">
            &copy; {new Date().getFullYear()} Kraivor Technologies. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
