"use client";

import { CheckCircle2, FileText, MessagesSquare, Percent, ThumbsUp, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/app/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { useActiveWorkspace, useAnalytics } from "@/hooks/use-workspaces";

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
  const helpfulRate = totalFeedback
    ? Math.round(((data!.feedback_helpful ?? 0) / totalFeedback) * 100)
    : null;
  const maxCites = Math.max(1, ...(data?.top_documents.map((d) => d.citations) ?? [1]));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Intelligence"
        title="Analytics"
        description={
          <>
            What people ask{" "}
            <span className="font-medium text-foreground">{active.name}</span>, and how well it
            answers.
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
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-64 rounded-lg" />
            <Skeleton className="h-64 rounded-lg" />
          </div>
        </div>
      ) : data.total_questions === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl border border-border bg-secondary/60">
              <MessagesSquare className="h-5 w-5 text-primary" />
            </span>
            <p className="font-medium">No questions yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Ask something on the{" "}
              <Link href="/chat" className="text-primary hover:underline">
                Chat
              </Link>{" "}
              page and analytics will start showing up here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Questions" icon={MessagesSquare} value={String(data.total_questions)} />
            <Stat
              label="Answer rate"
              icon={Percent}
              accent
              value={`${Math.round(data.answer_rate * 100)}%`}
              hint={`${data.answered} answered, ${data.unanswered} unanswered`}
            />
            <Stat
              label="Helpful rating"
              icon={ThumbsUp}
              value={helpfulRate != null ? `${helpfulRate}%` : "-"}
              hint={
                totalFeedback
                  ? `${data.feedback_helpful} up, ${data.feedback_not_helpful} down`
                  : "No feedback yet"
              }
            />
            <Stat
              label="Knowledge gaps"
              icon={TriangleAlert}
              value={String(data.unanswered)}
              hint="Questions with no answer"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Most cited documents</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3.5">
                {data.top_documents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No citations yet.</p>
                ) : (
                  data.top_documents.map((d) => (
                    <div key={`${d.document_id}-${d.filename}`} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex min-w-0 items-center gap-2">
                          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                          <span className="truncate">{d.filename}</span>
                        </span>
                        <span className="ml-2 shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                          {d.citations}
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                        <div
                          className="h-full rounded-full bg-primary"
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
                <CardTitle className="flex items-center gap-2">
                  <TriangleAlert className="h-4 w-4 text-amber-500" />
                  Knowledge gaps
                </CardTitle>
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
                  className="flex items-center justify-between gap-3 rounded-md border border-border bg-background/40 px-3 py-2 text-sm"
                >
                  <span className="truncate">{q.question}</span>
                  {q.answered ? (
                    <Badge variant="success" className="shrink-0">
                      <CheckCircle2 className="h-3 w-3" />
                      answered
                    </Badge>
                  ) : (
                    <Badge variant="warning" className="shrink-0">
                      <TriangleAlert className="h-3 w-3" />
                      gap
                    </Badge>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
