"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useActiveWorkspace, useUsage } from "@/hooks/use-workspaces";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
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
      <div>
        <h1 className="text-2xl font-semibold">Usage</h1>
        <p className="text-sm text-muted-foreground">
          Activity and quota for <span className="font-medium">{active.name}</span>.
        </p>
      </div>

      {isLoading || !data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Questions this month"
              value={
                data.monthly_question_limit != null
                  ? `${data.questions_this_period} / ${data.monthly_question_limit}`
                  : String(data.questions_this_period)
              }
              hint={data.monthly_question_limit == null ? "No limit set" : "Resets monthly"}
            />
            <Stat label="Documents" value={String(data.total_documents)} />
            <Stat label="Chunks" value={String(data.total_chunks)} />
            <Stat label="Storage" value={formatBytes(data.storage_used_bytes)} />
            <Stat
              label="Tokens (prompt)"
              value={data.total_tokens_in.toLocaleString()}
            />
            <Stat
              label="Tokens (completion)"
              value={data.total_tokens_out.toLocaleString()}
            />
            <Stat
              label="Estimated cost"
              value={`$${data.total_cost_estimate.toFixed(4)}`}
              hint="Based on configured per-token rates"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Questions (last 14 days)</CardTitle>
            </CardHeader>
            <CardContent>
              {data.questions_by_day.length === 0 ? (
                <p className="text-sm text-muted-foreground">No questions yet.</p>
              ) : (
                <div className="flex items-end gap-2" style={{ height: 140 }}>
                  {data.questions_by_day.map((d) => (
                    <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t bg-primary/70"
                        style={{ height: `${(d.count / maxDay) * 110}px` }}
                        title={`${d.count} on ${d.date}`}
                      />
                      <span className="text-[10px] text-muted-foreground">
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
