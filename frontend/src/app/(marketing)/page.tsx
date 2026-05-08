import Link from 'next/link';
import { Button } from '@/components/ui/shadcn';
import { ROUTES } from '@/constants';

export default function MarketingPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold">Kraivor</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link href={ROUTES.FEATURES} className="text-sm font-medium hover:underline">
              Features
            </Link>
            <Link href={ROUTES.PRICING} className="text-sm font-medium hover:underline">
              Pricing
            </Link>
            <Link href={ROUTES.DOCS} className="text-sm font-medium hover:underline">
              Docs
            </Link>
            <Link href={ROUTES.LOGIN}>
              <Button variant="outline" size="sm">
                Sign in
              </Button>
            </Link>
            <Link href={ROUTES.REGISTER}>
              <Button size="sm">Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="py-24 text-center">
          <div className="container mx-auto px-4">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              Developer Intelligence Platform
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
              One platform. Three products. Production-grade from day one. Analyze your code,
              collaborate with AI, and ship faster.
            </p>
            <div className="mt-10 flex justify-center gap-4">
              <Link href={ROUTES.REGISTER}>
                <Button size="lg">Start Free Trial</Button>
              </Link>
              <Link href={ROUTES.FEATURES}>
                <Button variant="outline" size="lg">
                  Learn More
                </Button>
              </Link>
            </div>
          </div>
        </section>

        <section className="py-24 bg-muted/50">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-12">Why Kraivor?</h2>
            <div className="grid gap-8 md:grid-cols-3">
              <div className="text-center">
                <h3 className="text-xl font-semibold mb-2">Repository Analysis</h3>
                <p className="text-muted-foreground">
                  Get comprehensive insights into your codebase with AI-powered analysis
                </p>
              </div>
              <div className="text-center">
                <h3 className="text-xl font-semibold mb-2">AI Assistant</h3>
                <p className="text-muted-foreground">
                  Chat with AI to understand, refactor, and improve your code
                </p>
              </div>
              <div className="text-center">
                <h3 className="text-xl font-semibold mb-2">Project Management</h3>
                <p className="text-muted-foreground">
                  Track tasks, notes, and projects in one unified workspace
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t py-12">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} Kraivor. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}