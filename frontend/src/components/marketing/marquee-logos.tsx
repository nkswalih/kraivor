'use client';

import { motion, useReducedMotion } from 'framer-motion';

const LOGOS = [
  { name: 'Vercel', url: 'https://cdn.simpleicons.org/vercel/888888' },
  { name: 'Linear', url: 'https://cdn.simpleicons.org/linear/e8c547' },
  { name: 'Stripe', url: 'https://cdn.simpleicons.org/stripe/888888' },
  { name: 'Raycast', url: 'https://cdn.simpleicons.org/raycast/888888' },
  { name: 'Supabase', url: 'https://cdn.simpleicons.org/supabase/888888' },
  { name: 'Figma', url: 'https://cdn.simpleicons.org/figma/888888' },
  { name: 'Sentry', url: 'https://cdn.simpleicons.org/sentry/888888' },
  { name: 'Notion', url: 'https://cdn.simpleicons.org/notion/888888' },
];

export function MarqueeLogos() {
  const reduce = useReducedMotion();

  if (reduce) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-10">
        {LOGOS.map((logo) => (
          <img
            key={logo.name}
            src={logo.url}
            alt={logo.name}
            className="h-6 w-auto opacity-50 grayscale"
            loading="lazy"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden w-full">
      <motion.div
        className="flex gap-16 items-center"
        animate={{ x: [0, -1536] }}
        transition={{
          duration: 40,
          repeat: Infinity,
          ease: 'linear',
        }}
      >
        {[...LOGOS, ...LOGOS, ...LOGOS].map((logo, i) => (
          <img
            key={`${logo.name}-${i}`}
            src={logo.url}
            alt={logo.name}
            className="h-6 w-auto opacity-50 grayscale hover:opacity-70 transition-opacity shrink-0"
            loading="lazy"
          />
        ))}
      </motion.div>
    </div>
  );
}
