import { cn } from '@/lib/utils';

interface ShimmerTextProps {
  children: React.ReactNode;
  className?: string;
}

export function ShimmerText({ children, className }: ShimmerTextProps) {
  return (
    <div
      className={cn(
        'relative inline-block animate-shimmer bg-gradient-to-r from-muted-foreground/60 via-muted-foreground to-muted-foreground/60 bg-[length:200%_100%] bg-clip-text text-transparent',
        className,
      )}
    >
      {children}
    </div>
  );
}
