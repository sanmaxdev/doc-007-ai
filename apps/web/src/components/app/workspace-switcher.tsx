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
    return <span className="font-mono text-xs text-muted-foreground">Loading…</span>;
  }
  if (!workspaces || workspaces.length === 0) {
    return <span className="font-mono text-xs text-muted-foreground">No workspace yet</span>;
  }

  const active = workspaces.find((w) => w.id === activeId) ?? workspaces[0];
  const initial = (active?.name ?? "?").trim().charAt(0).toUpperCase() || "?";

  return (
    <div className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-card pl-1.5 pr-1 transition-colors focus-within:ring-2 focus-within:ring-ring">
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded bg-primary/15 font-mono text-xs font-semibold text-primary">
        {initial}
      </span>
      <select
        value={activeId ?? ""}
        onChange={(e) => setActive(e.target.value)}
        className="h-full max-w-[10rem] cursor-pointer truncate border-0 bg-transparent pr-1 text-sm font-medium focus:outline-none"
        aria-label="Active workspace"
      >
        {workspaces.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
    </div>
  );
}
