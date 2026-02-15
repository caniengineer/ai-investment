"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  BarChart3,
  TrendingUp,
  BookOpen,
  Activity,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/strategies", label: "Strategies", icon: TrendingUp },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/metrics", label: "Metrics", icon: Activity },
  { href: "/playbook", label: "Playbook", icon: Brain },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-[var(--sidebar-width)] flex-col border-r border-[var(--border)] bg-[var(--card)]">
      <div className="flex h-14 items-center gap-2 border-b border-[var(--border)] px-4">
        <TrendingUp className="h-5 w-5 text-[var(--primary)]" />
        <span className="text-lg font-semibold">AlphaAgent</span>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
