"use client";

import { FileText, MessagesSquare, Plus, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/app/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { useConversations } from "@/hooks/use-chat";
import { useDocuments } from "@/hooks/use-documents";
import { useCreateWorkspace, useMembers, useWorkspaces } from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

function CreateWorkspace({ onCreated }: { onCreated?: (id: string) => void }) {
  const [name, setName] = useState("");
  const create = useCreateWorkspace();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const ws = await create.mutateAsync({ name: name.trim() });
    setName("");
    onCreated?.(ws.id);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-4 w-4 text-primary" />
          Create a workspace
        </CardTitle>
        <CardDescription>
          A workspace holds your documents and keeps them isolated from other teams.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="flex items-end gap-3">
          <div className="flex-1 space-y-2">
            <Label htmlFor="ws-name">Workspace name</Label>
            <Input
              id="ws-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Inc"
            />
          </div>
          <Button type="submit" disabled={create.isPending || !name.trim()}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12 w-64" />
      <div className="grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-28 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-48 rounded-lg" />
    </div>
  );
}

function initialsOf(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function DashboardPage() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const activeId = useWorkspaceStore((s) => s.activeId);
  const setActive = useWorkspaceStore((s) => s.setActive);

  const active = workspaces?.find((w) => w.id === activeId) ?? workspaces?.[0];
  const { data: members } = useMembers(active?.id ?? null);
  const { data: documents } = useDocuments(active?.id ?? null);
  const { data: conversations } = useConversations(active?.id ?? null);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (!workspaces || workspaces.length === 0) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <PageHeader
          eyebrow="Get started"
          title="Create your first workspace"
          description="Everything in DOC-007-AI lives inside a workspace. Spin one up to upload documents and start asking questions."
        />
        <CreateWorkspace onCreated={setActive} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workspace overview"
        title={active?.name ?? "Workspace"}
        description="A snapshot of the knowledge base, conversations, and the team behind this workspace."
        actions={
          active?.role && (
            <Badge variant="info" className="capitalize">
              {active.role}
            </Badge>
          )
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Link href="/documents" className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Stat
            label="Documents"
            value={documents ? documents.length : "-"}
            hint="Sources in this knowledge base"
            icon={FileText}
          />
        </Link>
        <Link href="/chat" className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Stat
            label="Conversations"
            value={conversations ? conversations.length : "-"}
            hint="Question threads asked"
            icon={MessagesSquare}
          />
        </Link>
        <Link href="/members" className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Stat
            label="Members"
            value={members ? members.length : "-"}
            hint="People with access"
            icon={Users}
          />
        </Link>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle>Team</CardTitle>
            <CardDescription>People with access to this workspace.</CardDescription>
          </div>
          <Link
            href="/members"
            className="font-mono text-xs uppercase tracking-[0.14em] text-primary hover:underline"
          >
            Manage
          </Link>
        </CardHeader>
        <CardContent className="space-y-2">
          {members === undefined ? (
            <>
              <Skeleton className="h-12 rounded-md" />
              <Skeleton className="h-12 rounded-md" />
            </>
          ) : members.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No members yet.</p>
          ) : (
            members.map((m) => (
              <div
                key={m.user_id}
                className="flex items-center justify-between rounded-md border border-border bg-background/40 px-3 py-2.5 text-sm"
              >
                <span className="flex items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-secondary font-mono text-xs font-medium">
                    {initialsOf(m.full_name || m.email)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{m.full_name || m.email}</span>
                    {m.full_name && (
                      <span className="block truncate text-xs text-muted-foreground">
                        {m.email}
                      </span>
                    )}
                  </span>
                </span>
                <Badge variant={m.role === "owner" ? "info" : "default"} className="capitalize">
                  {m.role}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <CreateWorkspace onCreated={setActive} />
    </div>
  );
}
