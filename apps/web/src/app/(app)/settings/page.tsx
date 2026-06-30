"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
import {
  useActiveWorkspace,
  useDeleteWorkspace,
  useUpdateWorkspace,
} from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

export default function SettingsPage() {
  const active = useActiveWorkspace();
  const router = useRouter();
  const setActive = useWorkspaceStore((s) => s.setActive);
  const workspaceId = active?.id ?? null;
  const isOwner = active?.role === "owner";
  const isAdmin = active?.role === "owner" || active?.role === "admin";

  const update = useUpdateWorkspace(workspaceId);
  const remove = useDeleteWorkspace();

  const [form, setForm] = useState({ name: "", description: "" });
  const [saved, setSaved] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (active) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync of server data into the form
      setForm({ name: active.name, description: active.description ?? "" });
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
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage this workspace.</p>
      </div>

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

      {isOwner && (
        <Card className="border-destructive/40">
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
