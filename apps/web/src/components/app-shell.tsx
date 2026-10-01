"use client";

import {
  Clapperboard,
  FolderKanban,
  Layers,
  LayoutDashboard,
  Library,
  Menu,
  Settings,
  Tags,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ApiStatus } from "@/components/api-status";
import { cn } from "@/lib/utils";
import { useUi } from "@/lib/store";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/sources", label: "Sources", icon: Library },
  { href: "/topics", label: "Topics", icon: Tags },
  { href: "/collections", label: "Collections", icon: Layers },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/studio", label: "Studio", icon: Clapperboard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUi();

  return (
    <div className="flex min-h-screen">
      <aside
        className={cn(
          "bg-sidebar text-sidebar-foreground border-sidebar-border hidden shrink-0 border-r transition-[width] md:block",
          sidebarOpen ? "w-60" : "w-16",
        )}
      >
        <div className="flex h-14 items-center gap-2 px-4 font-semibold">
          <Clapperboard className="size-5 shrink-0" />
          {sidebarOpen && <span>StoryWeaver</span>}
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1 p-2">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "hover:bg-sidebar-accent flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                  active && "bg-sidebar-accent font-medium",
                )}
              >
                <Icon className="size-4 shrink-0" />
                {sidebarOpen && label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4">
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label="Toggle sidebar"
            className="hover:bg-accent hidden rounded-md p-2 md:block"
          >
            <Menu className="size-4" />
          </button>
          <span className="text-muted-foreground text-sm md:hidden">StoryWeaver</span>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground hidden text-sm sm:inline">
              From source to story to video.
            </span>
            <ApiStatus />
          </div>
        </header>
        <nav aria-label="Mobile" className="flex gap-1 overflow-x-auto border-b p-2 md:hidden">
          {NAV.map(({ href, label }) => (
            <Link key={href} href={href} className="rounded-md px-3 py-1 text-sm whitespace-nowrap">
              {label}
            </Link>
          ))}
        </nav>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
