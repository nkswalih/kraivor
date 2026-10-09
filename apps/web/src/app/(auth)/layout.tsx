export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-krait-void">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full opacity-10"
        style={{
          background: 'radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-32 -right-32 h-[500px] w-[500px] rounded-full opacity-10"
        style={{
          background: 'radial-gradient(circle, hsl(var(--primary-light)) 0%, transparent 70%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      <div className="relative z-10 w-full px-4 py-8">{children}</div>
    </div>
  );
}
