import { cn } from "@/lib/utils";

/**
 * Shimmering placeholder used while data loads. A static muted block with a
 * single highlight band that sweeps across it (wired to the `shimmer` keyframe).
 */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-muted/60",
        "after:absolute after:inset-0 after:-translate-x-full after:animate-shimmer",
        "after:bg-gradient-to-r after:from-transparent after:via-foreground/10 after:to-transparent",
        className,
      )}
      {...props}
    />
  );
}
