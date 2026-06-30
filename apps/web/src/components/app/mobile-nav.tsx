"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { NavList, SystemsStatus, Wordmark } from "@/components/app/nav";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Mobile-only navigation: a hamburger that opens a slide-in drawer carrying the
 * same grouped nav as the desktop sidebar. Closes on route change, Esc, overlay
 * tap, or selecting a link. Hidden from md up, where the sidebar takes over.
 */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close whenever the route changes (e.g. browser back while the drawer is open).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync drawer visibility with the router
    setOpen(false);
  }, [pathname]);

  // Close on Escape and lock body scroll while the drawer is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  return (
    <div className="md:hidden">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Open navigation"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Overlay */}
      <div
        aria-hidden={!open}
        onClick={() => setOpen(false)}
        className={cn(
          "fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity duration-300",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      {/* Drawer */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card shadow-2xl transition-transform duration-300 ease-out",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-5">
          <Link href="/dashboard" onClick={() => setOpen(false)}>
            <Wordmark />
          </Link>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
        <NavList onNavigate={() => setOpen(false)} />
        <div className="border-t border-border px-5 py-3">
          <SystemsStatus />
        </div>
      </aside>
    </div>
  );
}
