"use client";

import {
  ArrowDownRight,
  ArrowUpRight,
  Coins,
  Database,
  FileText,
  Layers,
  MessagesSquare,
} from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/app/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { useActiveWorkspace, useUsage } from "@/hooks/use-workspaces";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function UsagePage() {
  const active = useActiveWorkspace();
  const { data, isLoading } = useUsage(active?.id ?? null);

  if (!active) {
    return (
      <p className="text-muted-foreground">
        Select or create a workspace on the{" "}
        <Link href="/dashboard" className="text-primary underline-offset-4 hover:underline">
          dashboard
        </Link>{" "}
        first.
      </p>
    );
  }

  const maxDay = Math.max(1, ...(data?.questions_by_day.map((d) => d.count) ?? [1]));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Metering"
        title="Usage"
        description={
          <>
            Activity and quota for{" "}
            <span className="font-medium text-foreground">{active.name}</span>.
          </>
        }
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-56 rounded-lg" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Questions this month"
              icon={MessagesSquare}
              accent
              value={
                data.monthly_question_limit != null
                  ? `${data.questions_this_period} / ${data.monthly_question_limit}`
                  : String(data.questions_this_period)
              }
              hint={data.monthly_question_limit == null ? "No limit set" : "Resets monthly"}
            />
            <Stat label="Documents" icon={FileText} value={String(data.total_documents)} />
            <Stat label="Chunks" icon={Layers} value={String(data.total_chunks)} />
            <Stat label="Storage" icon={Database} value={formatBytes(data.storage_used_bytes)} />
            <Stat
              label="Tokens (prompt)"
              icon={ArrowUpRight}
              value={data.total_tokens_in.toLocaleString()}
            />
            <Stat
              label="Tokens (completion)"
              icon={ArrowDownRight}
              value={data.total_tokens_out.toLocaleString()}
            />
            <Stat
              label="Estimated cost"
              icon={Coins}
              value={`$${data.total_cost_estimate.toFixed(4)}`}
              hint="Based on configured per-token rates"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Questions / last 14 days
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.questions_by_day.length === 0 ? (
                <p className="text-sm text-muted-foreground">No questions yet.</p>
              ) : (
                <div className="flex items-end gap-2" style={{ height: 150 }}>
                  {data.questions_by_day.map((d) => (
                    <div
                      key={d.date}
                      className="group flex flex-1 flex-col items-center gap-1.5"
                    >
                      <span className="font-mono text-[10px] tabular-nums text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
                        {d.count}
                      </span>
                      <div
                        className="w-full rounded-t bg-primary/60 transition-colors group-hover:bg-primary"
                        style={{ height: `${(d.count / maxDay) * 110}px` }}
                        title={`${d.count} on ${d.date}`}
                      />
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {d.date.slice(5)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
