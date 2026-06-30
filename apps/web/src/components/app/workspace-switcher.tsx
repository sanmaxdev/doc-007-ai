"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useWorkspaces } from "@/hooks/use-workspaces";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/stores/workspace";

function initialOf(name: string): string {
  return (name ?? "?").trim().charAt(0).toUpperCase() || "?";
}

export function WorkspaceSwitcher() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const activeId = useWorkspaceStore((s) => s.activeId);
  const setActive = useWorkspaceStore((s) => s.setActive);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!workspaces || workspaces.length === 0) return;
    const exists = workspaces.some((w) => w.id === activeId);
    if (!activeId || !exists) setActive(workspaces[0].id);
  }, [workspaces, activeId, setActive]);

  // Close on outside click or Escape.
  useEffect(() => {
    function onPointer(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (isLoading) {
    return <span className="font-mono text-xs text-muted-foreground">Loading…</span>;
  }
  if (!workspaces || workspaces.length === 0) {
    return <span className="font-mono text-xs text-muted-foreground">No workspace yet</span>;
  }

  const active = workspaces.find((w) => w.id === activeId) ?? workspaces[0];

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Switch workspace"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-card pl-1.5 pr-2 transition-colors hover:border-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded bg-primary/15 font-mono text-xs font-semibold text-primary">
          {initialOf(active.name)}
        </span>
        <span className="max-w-[9rem] truncate text-sm font-medium">{active.name}</span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full z-50 mt-1.5 min-w-[14rem] overflow-hidden rounded-md border border-border bg-popover p-1 shadow-xl shadow-black/30"
        >
          <p className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/70">
            Workspaces
          </p>
          {workspaces.map((w) => {
            const selected = w.id === active.id;
            return (
              <button
                key={w.id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  setActive(w.id);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-secondary",
                  selected && "bg-secondary/60",
                )}
              >
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded bg-secondary font-mono text-xs font-medium">
                  {initialOf(w.name)}
                </span>
                <span className="flex-1 truncate">{w.name}</span>
                {selected && <Check className="h-4 w-4 shrink-0 text-primary" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
