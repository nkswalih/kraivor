export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#0a0a0f]">
      {/* ── Animated gradient orbs ───────────────────────── */}
      <div
        aria-hidden="true"
        className="animate-float-slow pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full opacity-25"
        style={{
          background: 'radial-gradient(circle, #7c3aed 0%, #4f46e5 50%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />
      <div
        aria-hidden="true"
        className="animate-float-medium pointer-events-none absolute -bottom-32 -right-32 h-[500px] w-[500px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, #6366f1 0%, #8b5cf6 50%, transparent 70%)',
          filter: 'blur(90px)',
        }}
      />
      <div
        aria-hidden="true"
        className="animate-float-fast pointer-events-none absolute top-1/2 left-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-10"
        style={{
          background: 'radial-gradient(circle, #a78bfa 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />

      {/* ── Subtle dot grid ─────────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      {/* ── Spinning ring decoration ─────────────────────── */}
      <div
        aria-hidden="true"
        className="animate-spin-slow pointer-events-none absolute top-8 right-8 h-32 w-32 rounded-full opacity-10"
        style={{
          border: '1px solid',
          borderColor: 'transparent #7c3aed transparent #4f46e5',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-12 left-12 h-20 w-20 rounded-full opacity-10"
        style={{
          border: '1px solid rgba(139, 92, 246, 0.5)',
        }}
      />

      {/* ── Page content ─────────────────────────────────── */}
      <div className="relative z-10 w-full px-4 py-8">
        {children}
      </div>
    </div>
  );
}