import Link from "next/link";

import { NavList, SystemsStatus, Wordmark } from "@/components/app/nav";

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card md:flex">
      <div className="flex h-14 items-center border-b border-border px-5">
        <Link href="/dashboard">
          <Wordmark />
        </Link>
      </div>
      <NavList />
      <div className="border-t border-border px-5 py-3">
        <SystemsStatus />
      </div>
    </aside>
  );
}
