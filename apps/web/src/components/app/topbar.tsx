"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { ThemeToggle } from "@/components/app/theme-toggle";
import { WorkspaceSwitcher } from "@/components/app/workspace-switcher";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

export function Topbar() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

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
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4">
      <WorkspaceSwitcher />
      <div className="flex items-center gap-2">
        {user?.email && (
          <span className="hidden text-sm text-muted-foreground sm:inline">{user.email}</span>
        )}
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Log out" onClick={logout}>
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
