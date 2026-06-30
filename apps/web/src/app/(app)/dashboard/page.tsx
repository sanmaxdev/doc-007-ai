"use client";

import { useState } from "react";

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
import { useConversations } from "@/hooks/use-chat";
import { useDocuments } from "@/hooks/use-documents";
import { useCreateWorkspace, useMembers, useWorkspaces } from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-semibold">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

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
        <CardTitle>Create a workspace</CardTitle>
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

export default function DashboardPage() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const activeId = useWorkspaceStore((s) => s.activeId);
  const setActive = useWorkspaceStore((s) => s.setActive);

  const active = workspaces?.find((w) => w.id === activeId) ?? workspaces?.[0];
  const { data: members } = useMembers(active?.id ?? null);
  const { data: documents } = useDocuments(active?.id ?? null);
  const { data: conversations } = useConversations(active?.id ?? null);

  if (isLoading) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  if (!workspaces || workspaces.length === 0) {
    return (
      <div className="mx-auto max-w-lg">
        <CreateWorkspace onCreated={setActive} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{active?.name}</h1>
        <p className="text-sm text-muted-foreground">
          Your role: <span className="font-medium text-foreground">{active?.role}</span>
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Documents" value={documents ? String(documents.length) : "-"} />
        <StatCard
          label="Conversations"
          value={conversations ? String(conversations.length) : "-"}
        />
        <StatCard label="Members" value={members ? String(members.length) : "-"} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>People with access to this workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {(members ?? []).map((m) => (
            <div
              key={m.user_id}
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
            >
              <span>{m.full_name || m.email}</span>
              <span className="rounded bg-secondary px-2 py-0.5 text-xs capitalize text-muted-foreground">
                {m.role}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      <CreateWorkspace onCreated={setActive} />
    </div>
  );
}
