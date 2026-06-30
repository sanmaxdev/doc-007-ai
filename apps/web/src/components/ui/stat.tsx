import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * A single metric tile in the dossier style: a mono uppercase label, a large
 * tabular-figure value, and an optional hint line and corner icon. Values read
 * as instrument readouts rather than generic dashboard numbers.
 */
export function Stat({
  label,
  value,
  hint,
  icon: Icon,
  accent,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  accent?: boolean;
  className?: string;
}) {
  return (
    <Card className={cn("relative overflow-hidden p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
          {label}
        </span>
        {Icon && (
          <Icon
            className={cn("h-4 w-4", accent ? "text-primary" : "text-muted-foreground/70")}
          />
        )}
      </div>
      <p
        className={cn(
          "mt-3 font-display text-3xl font-semibold tabular-nums tracking-tight",
          accent && "text-primary",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}
