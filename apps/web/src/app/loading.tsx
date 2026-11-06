export default function RootLoading() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-krait-void">
      <div className="flex flex-col items-center gap-4">
        <div className="krait-loader" />
        <p className="text-[13px] text-text-tertiary font-medium">Loading...</p>
      </div>
    </div>
  );
}
