"use client";

import { useEffect } from "react";

import { useWorkspaces } from "@/hooks/use-workspaces";
import { useWorkspaceStore } from "@/stores/workspace";

export function WorkspaceSwitcher() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const activeId = useWorkspaceStore((s) => s.activeId);
  const setActive = useWorkspaceStore((s) => s.setActive);

  useEffect(() => {
    if (!workspaces || workspaces.length === 0) return;
    const exists = workspaces.some((w) => w.id === activeId);
    if (!activeId || !exists) setActive(workspaces[0].id);
  }, [workspaces, activeId, setActive]);

  if (isLoading) {
    return <span className="text-sm text-muted-foreground">Loading…</span>;
  }
  if (!workspaces || workspaces.length === 0) {
    return <span className="text-sm text-muted-foreground">No workspace yet</span>;
  }

  return (
    <select
      value={activeId ?? ""}
      onChange={(e) => setActive(e.target.value)}
      className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label="Active workspace"
    >
      {workspaces.map((w) => (
        <option key={w.id} value={w.id}>
          {w.name}
        </option>
      ))}
    </select>
  );
}
