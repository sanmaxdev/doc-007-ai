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
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, soon: false },
  { href: "/documents", label: "Documents", icon: FileText, soon: false },
  { href: "/chat", label: "Chat", icon: MessagesSquare, soon: false },
  { href: "/debug", label: "Retrieval", icon: FlaskConical, soon: false },
  { href: "/usage", label: "Usage", icon: BarChart3, soon: false },
  { href: "/analytics", label: "Analytics", icon: LineChart, soon: false },
  { href: "/members", label: "Members", icon: Users, soon: false },
  { href: "/settings", label: "Settings", icon: Settings, soon: false },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card md:flex">
      <div className="flex h-14 items-center border-b border-border px-5 font-semibold">
        DOC<span className="text-primary">-007-</span>AI
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {NAV.map(({ href, label, icon: Icon, soon }) => {
          const active = pathname === href;
          const classes = cn(
            "flex items-center justify-between rounded-md px-3 py-2 text-sm",
            active
              ? "bg-secondary font-medium text-foreground"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            soon && "pointer-events-none opacity-50",
          );
          const inner = (
            <>
              <span className="flex items-center gap-3">
                <Icon className="h-4 w-4" />
                {label}
              </span>
              {soon && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                  soon
                </span>
              )}
            </>
          );
          return soon ? (
            <div key={href} className={classes}>
              {inner}
            </div>
          ) : (
            <Link key={href} href={href} className={classes}>
              {inner}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
