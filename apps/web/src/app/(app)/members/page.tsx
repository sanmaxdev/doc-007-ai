"use client";

import { Copy, Trash2, UserPlus } from "lucide-react";
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
import {
  useActiveWorkspace,
  useChangeMemberRole,
  useCreateInvitation,
  useInvitations,
  useMembers,
  useRemoveMember,
  useRevokeInvitation,
} from "@/hooks/use-workspaces";
import type { Member, Role } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

function roleVariant(role: Role): "info" | "success" | "default" {
  if (role === "owner") return "info";
  if (role === "admin") return "success";
  return "default";
}

function initialsOf(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function MembersPage() {
  const active = useActiveWorkspace();
  const me = useAuthStore((s) => s.user);
  const workspaceId = active?.id ?? null;
  const isOwner = active?.role === "owner";
  const isAdmin = active?.role === "owner" || active?.role === "admin";

  const { data: members } = useMembers(workspaceId);
  const { data: invitations } = useInvitations(workspaceId, isAdmin);
  const createInvite = useCreateInvitation(workspaceId);
  const revokeInvite = useRevokeInvitation(workspaceId);
  const changeRole = useChangeMemberRole(workspaceId);
  const removeMember = useRemoveMember(workspaceId);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.trim()) return;
    try {
      const res = await createInvite.mutateAsync({ email: email.trim(), role });
      setEmail("");
      setInviteLink(`${window.location.origin}/invite?token=${res.token}`);
      setCopied(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the invitation.");
    }
  }

  async function copyLink() {
    if (!inviteLink) return;
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
  }

  function canRemove(m: Member): boolean {
    if (!isAdmin) return false;
    if (m.role === "owner") return false;
    if (m.user_id === me?.id) return false;
    if (m.role === "admin" && !isOwner) return false;
    return true;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace access"
        title="Members"
        description={
          <>
            People with access to{" "}
            <span className="font-medium text-foreground">{active.name}</span>.
          </>
        }
      />

      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle>Invite a member</CardTitle>
            <CardDescription>
              They&apos;ll join with the role you choose once they accept the invite link.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={invite} className="flex flex-wrap items-end gap-3">
              <div className="flex-1 space-y-2" style={{ minWidth: 220 }}>
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="teammate@company.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-role">Role</Label>
                <select
                  id="invite-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                  className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <Button type="submit" disabled={createInvite.isPending || !email.trim()}>
                <UserPlus className="h-4 w-4" />
                {createInvite.isPending ? "Inviting…" : "Invite"}
              </Button>
            </form>

            {error && <p className="text-sm text-destructive">{error}</p>}

            {inviteLink && (
              <div className="rounded-md border border-primary/30 bg-primary/[0.06] p-3">
                <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-primary">
                  Invite link / shown once
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 overflow-x-auto whitespace-nowrap rounded bg-background px-2 py-1.5 text-xs">
                    {inviteLink}
                  </code>
                  <Button variant="outline" size="sm" onClick={copyLink}>
                    <Copy className="h-3.5 w-3.5" />
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Share this with the invitee. They sign in with the invited email and open
                  the link to join.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-secondary/40 text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Member</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {(members ?? []).map((m) => (
              <tr
                key={m.user_id}
                className="border-b border-border transition-colors last:border-0 hover:bg-secondary/30"
              >
                <td className="px-4 py-3">
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
                </td>
                <td className="px-4 py-3">
                  {isOwner && m.role !== "owner" ? (
                    <select
                      value={m.role}
                      onChange={(e) =>
                        changeRole.mutate({ userId: m.user_id, role: e.target.value as Role })
                      }
                      disabled={changeRole.isPending}
                      className="h-8 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <Badge variant={roleVariant(m.role)} className="capitalize">
                      {m.role}
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {canRemove(m) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Remove member"
                      title="Remove member"
                      disabled={removeMember.isPending}
                      onClick={() => removeMember.mutate(m.user_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {isAdmin && invitations && invitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Pending invitations</CardTitle>
            <CardDescription>Invites that haven&apos;t been accepted yet.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {invitations.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <span className="flex items-center gap-2">
                  {inv.email}
                  <Badge variant={roleVariant(inv.role)} className="capitalize">
                    {inv.role}
                  </Badge>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={revokeInvite.isPending}
                  onClick={() => revokeInvite.mutate(inv.id)}
                >
                  Revoke
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
