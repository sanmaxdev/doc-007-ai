"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAcceptInvitation } from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

type Status = "accepting" | "done" | "error";

function InviteInner() {
  const params = useSearchParams();
  const token = params.get("token");
  const router = useRouter();
  const accept = useAcceptInvitation();
  const setActive = useWorkspaceStore((s) => s.setActive);

  const [status, setStatus] = useState<Status>(token ? "accepting" : "error");
  const [message, setMessage] = useState(
    token ? "Accepting your invitation…" : "This invite link is missing its token.",
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    accept
      .mutateAsync(token)
      .then((ws) => {
        if (cancelled) return;
        setActive(ws.id);
        setStatus("done");
        setMessage(`You've joined ${ws.name}.`);
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Could not accept this invitation.");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="mx-auto max-w-md pt-12">
      <Card>
        <CardContent className="space-y-4 p-8 text-center">
          <h1 className="text-xl font-semibold">Workspace invitation</h1>
          <p
            className={
              status === "error" ? "text-sm text-destructive" : "text-sm text-muted-foreground"
            }
          >
            {message}
          </p>
          {status === "done" && (
            <Button onClick={() => router.push("/dashboard")}>Go to dashboard</Button>
          )}
          {status === "error" && (
            <Button variant="outline" onClick={() => router.push("/dashboard")}>
              Back to dashboard
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <InviteInner />
    </Suspense>
  );
}
