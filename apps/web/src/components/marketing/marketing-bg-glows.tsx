export function MarketingBackgroundGlows() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
      <div className="absolute top-[-10%] right-[-5%] h-[600px] w-[600px] rounded-full bg-[hsl(var(--primary))]/10 blur-[150px] animate-float-slow" />
      <div className="absolute bottom-[-10%] left-[-10%] h-[500px] w-[500px] rounded-full bg-[hsl(var(--primary-dark))]/20 blur-[120px] animate-float-medium" />
    </div>
  );
}
