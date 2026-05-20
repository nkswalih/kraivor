import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from './providers';
import { SileoToaster } from '@/components/SileoToaster';

export const metadata: Metadata = {
  title: 'Kraivor - Developer Intelligence Platform',
  description: 'One platform. Three products. Production-grade from day one.',
};

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className="dark">
      <body className={inter.className}>
        <Providers>{children}</Providers>
        <SileoToaster />
      </body>
    </html>
  );
}