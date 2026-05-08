import { Spinner } from '@/components/ui/shadcn';

export default function Loading() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}