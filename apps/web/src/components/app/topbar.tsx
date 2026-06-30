"use client";

import { LogOut } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { ThemeToggle } from "@/components/app/theme-toggle";
import { WorkspaceSwitcher } from "@/components/app/workspace-switcher";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const SECTION_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  documents: "Documents",
  chat: "Chat",
  debug: "Retrieval",
  usage: "Usage",
  analytics: "Analytics",
  members: "Members",
  settings: "Settings",
};

export function Topbar() {
  const router = useRouter();
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);

  const section = SECTION_LABELS[pathname.split("/")[1] ?? ""] ?? "";

  async function logout() {
    try {
      await api.logout();
    } catch {
      /* best effort; tokens are cleared regardless */
    }
    useAuthStore.getState().clear();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md">
      <div className="flex min-w-0 items-center gap-3">
        <WorkspaceSwitcher />
        {section && (
          <span className="hidden items-center gap-3 sm:flex">
            <span className="text-muted-foreground/40">/</span>
            <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
              {section}
            </span>
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {user?.email && (
          <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
            {user.email}
          </span>
        )}
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Log out" onClick={logout}>
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
