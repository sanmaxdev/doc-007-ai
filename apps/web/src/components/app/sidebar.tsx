"use client";

import {
  BarChart3,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: LucideIcon };
type NavGroup = { label: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Knowledge",
    items: [
      { href: "/documents", label: "Documents", icon: FileText },
      { href: "/chat", label: "Chat", icon: MessagesSquare },
      { href: "/debug", label: "Retrieval", icon: FlaskConical },
    ],
  },
  {
    label: "Insights",
    items: [
      { href: "/usage", label: "Usage", icon: BarChart3 },
      { href: "/analytics", label: "Analytics", icon: LineChart },
    ],
  },
  {
    label: "Workspace",
    items: [
      { href: "/members", label: "Members", icon: Users },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card md:flex">
      <div className="flex h-14 items-center border-b border-border px-5">
        <Link href="/dashboard" className="font-display text-base font-bold tracking-tight">
          DOC<span className="text-primary">-007-</span>AI
        </Link>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {NAV.map((group) => (
          <div key={group.label} className="space-y-1">
            <p className="px-3 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
              {group.label}
            </p>
            {group.items.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-secondary font-medium text-foreground"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary transition-opacity",
                      active ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <Icon
                    className={cn(
                      "h-4 w-4 shrink-0 transition-colors",
                      active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                    )}
                  />
                  {label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-5 py-3">
        <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/70">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          Systems nominal
        </span>
      </div>
    </aside>
  );
}
