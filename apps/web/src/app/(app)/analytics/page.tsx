"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useActiveWorkspace, useAnalytics } from "@/hooks/use-workspaces";

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

export default function AnalyticsPage() {
  const active = useActiveWorkspace();
  const { data, isLoading } = useAnalytics(active?.id ?? null);

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

  const totalFeedback = (data?.feedback_helpful ?? 0) + (data?.feedback_not_helpful ?? 0);
  const helpfulRate = totalFeedback ? Math.round(((data!.feedback_helpful ?? 0) / totalFeedback) * 100) : null;
  const maxCites = Math.max(1, ...(data?.top_documents.map((d) => d.citations) ?? [1]));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          What people ask <span className="font-medium">{active.name}</span>, and how well it answers.
        </p>
      </div>

      {isLoading || !data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : data.total_questions === 0 ? (
        <Card>
          <CardContent className="p-12 text-center text-sm text-muted-foreground">
            No questions yet. Ask something on the Chat page and analytics will show up here.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Questions" value={String(data.total_questions)} />
            <Stat
              label="Answer rate"
              value={`${Math.round(data.answer_rate * 100)}%`}
              hint={`${data.answered} answered, ${data.unanswered} unanswered`}
            />
            <Stat
              label="Helpful rating"
              value={helpfulRate != null ? `${helpfulRate}%` : "-"}
              hint={
                totalFeedback
                  ? `${data.feedback_helpful} up, ${data.feedback_not_helpful} down`
                  : "No feedback yet"
              }
            />
            <Stat label="Knowledge gaps" value={String(data.unanswered)} hint="Questions with no answer" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Most cited documents</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.top_documents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No citations yet.</p>
                ) : (
                  data.top_documents.map((d) => (
                    <div key={`${d.document_id}-${d.filename}`} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          {d.filename}
                        </span>
                        <span className="tabular-nums text-muted-foreground">{d.citations}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-secondary">
                        <div
                          className="h-1.5 rounded-full bg-primary"
                          style={{ width: `${(d.citations / maxCites) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Knowledge gaps</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.unanswered_questions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Every question so far was answered from your documents.
                  </p>
                ) : (
                  data.unanswered_questions.map((q, i) => (
                    <div
                      key={i}
                      className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-sm"
                    >
                      {q.question}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent questions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {data.recent_questions.map((q, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <span className="truncate">{q.question}</span>
                  <span
                    className={
                      q.answered
                        ? "ml-3 shrink-0 rounded-full bg-accent/15 px-2 py-0.5 text-xs text-accent"
                        : "ml-3 shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-600"
                    }
                  >
                    {q.answered ? "answered" : "gap"}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
