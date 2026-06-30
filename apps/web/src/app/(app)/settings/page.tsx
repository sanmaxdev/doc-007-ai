"use client";

import { Copy, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "@/hooks/use-apikeys";
import {
  useActiveWorkspace,
  useDeleteWorkspace,
  useUpdateWorkspace,
} from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

function ApiKeysCard({ workspaceId }: { workspaceId: string }) {
  const { data: keys } = useApiKeys(workspaceId);
  const create = useCreateApiKey(workspaceId);
  const revoke = useRevokeApiKey(workspaceId);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const res = await create.mutateAsync(name.trim());
    setName("");
    setNewKey(res.key);
    setCopied(false);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API keys</CardTitle>
        <CardDescription>
          Keys authenticate the public API (<code>/api/public/v1</code>). Treat them like
          passwords.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="flex items-end gap-3">
          <div className="flex-1 space-y-2">
            <Label htmlFor="key-name">Key name</Label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Production server"
            />
          </div>
          <Button type="submit" disabled={create.isPending || !name.trim()}>
            {create.isPending ? "Creating…" : "Create key"}
          </Button>
        </form>

        {newKey && (
          <div className="rounded-md border border-primary/30 bg-primary/[0.06] p-3">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-primary">
              New key / shown once
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto whitespace-nowrap rounded bg-background px-2 py-1.5 text-xs">
                {newKey}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  await navigator.clipboard.writeText(newKey);
                  setCopied(true);
                }}
              >
                <Copy className="h-3.5 w-3.5" />
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {(keys ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No API keys yet.</p>
          ) : (
            (keys ?? []).map((k) => (
              <div
                key={k.id}
                className="flex items-center justify-between rounded-md border border-border bg-background/40 px-3 py-2 text-sm transition-colors hover:bg-secondary/30"
              >
                <span className="flex items-center gap-2.5">
                  <span className="font-medium">{k.name}</span>
                  <code className="font-mono text-xs text-muted-foreground">{k.key_prefix}…</code>
                  {k.revoked_at && (
                    <Badge variant="danger" className="px-1.5 py-0 text-[10px]">
                      revoked
                    </Badge>
                  )}
                </span>
                {!k.revoked_at && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Revoke key"
                    title="Revoke key"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(k.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const active = useActiveWorkspace();
  const router = useRouter();
  const setActive = useWorkspaceStore((s) => s.setActive);
  const workspaceId = active?.id ?? null;
  const isOwner = active?.role === "owner";
  const isAdmin = active?.role === "owner" || active?.role === "admin";

  const update = useUpdateWorkspace(workspaceId);
  const remove = useDeleteWorkspace();

  const [form, setForm] = useState({ name: "", description: "", limit: "" });
  const [saved, setSaved] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (active) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync of server data into the form
      setForm({
        name: active.name,
        description: active.description ?? "",
        limit:
          active.monthly_question_limit != null
            ? String(active.monthly_question_limit)
            : "",
      });
    }
  }, [active]);

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

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaved(false);
    await update.mutateAsync({
      name: form.name.trim(),
      description: form.description.trim(),
      monthly_question_limit: form.limit.trim() === "" ? null : Number(form.limit),
    });
    setSaved(true);
  }

  async function confirmDelete() {
    if (!workspaceId) return;
    await remove.mutateAsync(workspaceId);
    setActive(null);
    router.push("/dashboard");
  }

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        description="Manage this workspace, its API access, and its lifecycle."
      />

      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
          <CardDescription>
            {isAdmin
              ? "Update the workspace name and description."
              : "Only owners and admins can change these settings."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ws-name">Name</Label>
              <Input
                id="ws-name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                disabled={!isAdmin}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ws-desc">Description</Label>
              <textarea
                id="ws-desc"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                disabled={!isAdmin}
                rows={3}
                placeholder="What this knowledge base is for…"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ws-limit">Monthly question limit</Label>
              <Input
                id="ws-limit"
                type="number"
                min={0}
                value={form.limit}
                onChange={(e) => setForm((f) => ({ ...f, limit: e.target.value }))}
                disabled={!isAdmin}
                placeholder="Leave blank for unlimited"
              />
              <p className="text-xs text-muted-foreground">
                Caps questions per calendar month for this workspace. Blank means unlimited.
              </p>
            </div>
            {isAdmin && (
              <div className="flex items-center gap-3">
                <Button type="submit" disabled={update.isPending || !form.name.trim()}>
                  {update.isPending ? "Saving…" : "Save changes"}
                </Button>
                {saved && <span className="text-sm text-accent">Saved.</span>}
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {isAdmin && workspaceId && <ApiKeysCard workspaceId={workspaceId} />}

      {isOwner && (
        <Card className="border-destructive/40 bg-destructive/[0.03]">
          <CardHeader>
            <CardTitle className="text-destructive">Danger zone</CardTitle>
            <CardDescription>
              Deleting a workspace permanently removes its documents, chunks, and chats.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!confirming ? (
              <Button variant="destructive" onClick={() => setConfirming(true)}>
                Delete workspace
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm">
                  Delete <span className="font-medium">{active.name}</span>? This cannot be
                  undone.
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    disabled={remove.isPending}
                    onClick={confirmDelete}
                  >
                    {remove.isPending ? "Deleting…" : "Yes, delete it"}
                  </Button>
                  <Button variant="outline" onClick={() => setConfirming(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
