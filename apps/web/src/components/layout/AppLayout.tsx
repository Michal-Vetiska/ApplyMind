import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Bot,
  Briefcase,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  Radio,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { to: "/", label: "Přehled", icon: LayoutDashboard, end: true },
  { to: "/nabidky", label: "Nabídky", icon: Briefcase },
  { to: "/prihlasky", label: "Přihlášky", icon: FileText },
  { to: "/email", label: "E-mail", icon: Mail },
  { to: "/znalosti", label: "Znalostní báze", icon: Sparkles },
  { to: "/analytika", label: "Analytika", icon: BarChart3 },
  { to: "/automatizace", label: "Automatizace", icon: Bot },
  { to: "/zdroje", label: "Zdroje", icon: Radio },
  { to: "/nastaveni", label: "Nastavení", icon: Settings },
] as const;

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/prihlaseni");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-[260px] border-r border-border/80 bg-card/95 backdrop-blur-md transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between gap-2 border-b border-border/60 px-5 py-5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary shadow-glow">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <div className="font-display text-lg font-semibold tracking-tight">ApplyMind</div>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  AI náborový agent
                </div>
              </div>
            </div>
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto p-3">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={"end" in item ? item.end : false}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                      isActive && "bg-accent text-accent-foreground shadow-sm",
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="border-t border-border/60 p-4">
            <div className="mb-3 truncate text-sm">
              <div className="font-medium">{user?.name}</div>
              <div className="truncate text-xs text-muted-foreground">{user?.email}</div>
            </div>
            <Button variant="outline" className="w-full" onClick={() => void handleLogout()}>
              <LogOut className="h-4 w-4" />
              Odhlásit se
            </Button>
          </div>
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          aria-label="Zavřít menu"
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border/60 bg-background/80 px-4 py-3 backdrop-blur-md lg:hidden">
          <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
            <Menu className="h-5 w-5" />
          </Button>
          <span className="font-display font-semibold">ApplyMind</span>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
