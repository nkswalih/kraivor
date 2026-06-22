import Link from 'next/link';

export default function MarketingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center justify-between px-6 py-4 border-b border-border">
        <Link href="/" className="text-lg font-bold text-foreground">
          Kraivor
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="/docs"
            className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Docs
          </Link>
          <Link
            href="/features"
            className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Features
          </Link>
          <Link
            href="/pricing"
            className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Pricing
          </Link>
        </nav>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
        <h1 className="text-4xl font-bold text-foreground max-w-2xl">
          Kraivor - Next-gen Code Review Platform
        </h1>
        <p className="mt-4 text-[15px] text-muted-foreground max-w-xl">
          Streamline your code reviews with AI-powered insights, collaborative discussions, and
          intelligent automation.
        </p>
        <div className="mt-8 flex items-center gap-4">
          <Link
            href="/new-workspace"
            className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2.5 text-[13px] font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            Get Started
          </Link>
          <Link
            href="/docs"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-6 py-2.5 text-[13px] font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
          >
            Read Docs
          </Link>
        </div>
      </main>

      <footer className="px-6 py-4 border-t border-border text-center text-[12px] text-muted-foreground">
        &copy; {new Date().getFullYear()} Kraivor. All rights reserved.
      </footer>
    </div>
  );
}
