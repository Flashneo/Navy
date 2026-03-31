"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/jobs", label: "Jobs", icon: "💼" },
  { href: "/runs", label: "Runs", icon: "🚀" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-background">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-primary">Navy</span>
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            AI Job Search Agent
          </span>
        </h1>
      </div>
      <nav className="space-y-1 p-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              pathname === item.href
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="absolute bottom-4 left-4 right-4">
        <div className="rounded-lg bg-muted p-3 text-xs text-muted-foreground">
          <p className="font-medium">Navy v0.1.0</p>
          <p>LinkedIn Job Search AI Agent</p>
        </div>
      </div>
    </aside>
  );
}
