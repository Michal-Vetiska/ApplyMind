import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Briefcase,
  CheckCircle2,
  Mail,
  MessageSquare,
  Send,
  Sparkles,
  UserRound,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { normalizeList, normalizePaginated } from "@/lib/normalize";
import type { Application, EmailMessage, Job } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { PageLoader } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";

interface Overview {
  jobs_found?: number;
  jobs_discovered?: number;
  jobs_relevant?: number;
  applications_ready?: number;
  applications_drafted?: number;
  applications_sent?: number;
  employer_replies?: number;
  employer_responses?: number;
  interview_invitations?: number;
  interviews?: number;
  average_match_score?: number;
  llm_cost_mtd_usd?: number;
  sample_size_note?: string;
}

const KPI_META = [
  { keys: ["jobs_found", "jobs_discovered"], label: "Nalezené nabídky", icon: Briefcase },
  { keys: ["jobs_relevant"], label: "Relevantní nabídky", icon: Sparkles },
  { keys: ["applications_ready", "applications_drafted"], label: "Připravené přihlášky", icon: CheckCircle2 },
  { keys: ["applications_sent"], label: "Odeslané přihlášky", icon: Send },
  { keys: ["employer_replies", "employer_responses"], label: "Odpovědi zaměstnavatelů", icon: MessageSquare },
  { keys: ["interview_invitations", "interviews"], label: "Pozvánky na pohovor", icon: UserRound },
] as const;

function pick(overview: Overview | undefined, keys: readonly string[]) {
  if (!overview) return 0;
  for (const key of keys) {
    const value = overview[key as keyof Overview];
    if (typeof value === "number") return value;
  }
  return 0;
}

export function DashboardPage() {
  const overviewQuery = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => apiGet<Overview>("/api/analytics/overview"),
  });

  const attentionQuery = useQuery({
    queryKey: ["applications"],
    queryFn: () => apiGet<Application[] | { items: Application[] }>("/api/applications"),
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs", "priority"],
    queryFn: () => apiGet<{ items: Job[]; total: number } | Job[]>("/api/jobs?limit=50"),
  });

  const messagesQuery = useQuery({
    queryKey: ["email", "recent"],
    queryFn: () =>
      apiGet<{ items: EmailMessage[]; total: number } | EmailMessage[]>(
        "/api/email/messages?limit=5",
      ),
  });

  if (overviewQuery.isLoading) return <PageLoader />;

  const overview = overviewQuery.data;
  const attention = normalizeList(attentionQuery.data)
    .filter((a) => ["DRAFTED", "READY_FOR_REVIEW", "PENDING_APPROVAL"].includes(a.status))
    .slice(0, 5);
  const priorityJobs = normalizePaginated(jobsQuery.data)
    .items.filter((j) => (j.match_score ?? 0) > 0 || j.match_decision === "RECOMMENDED")
    .sort((a, b) => (b.match_score ?? 0) - (a.match_score ?? 0))
    .slice(0, 5);
  const messages = normalizePaginated(messagesQuery.data).items.slice(0, 5);

  return (
    <div>
      <PageHeader
        title="Přehled"
        description="Stav vašeho AI náborového pipeline a úkoly vyžadující pozornost."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {KPI_META.map(({ keys, label, icon: Icon }, index) => (
          <Card key={label} className="animate-fade-up" style={{ animationDelay: `${index * 40}ms` }}>
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div>
                <CardDescription>{label}</CardDescription>
                <CardTitle className="mt-2 font-display text-3xl">{pick(overview, keys)}</CardTitle>
              </div>
              <div className="rounded-lg bg-primary/10 p-2 text-primary">
                <Icon className="h-4 w-4" />
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>

      {overview?.sample_size_note ? (
        <p className="mt-3 text-xs text-muted-foreground">{overview.sample_size_note}</p>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Přihlášky k vyřízení</CardTitle>
              <CardDescription>Koncepty a čekající schválení</CardDescription>
            </div>
            <Link to="/prihlasky">
              <Button variant="outline" size="sm">
                Otevřít
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {attention.length === 0 ? (
              <EmptyState
                title="Nic nečeká na akci"
                description="Žádné koncepty ani přihlášky ke schválení."
              />
            ) : (
              <ul className="space-y-3">
                {attention.map((app) => (
                  <li key={app.id} className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium">
                        {app.job_title ?? app.job?.title ?? `Přihláška ${app.id.slice(0, 8)}`}
                      </div>
                      <Badge>{statusLabel(app.status)}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {app.company_name ?? app.job?.company_name ?? "—"} ·{" "}
                      {formatDate(app.last_activity_at ?? app.sent_at, true)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Prioritní nabídky</CardTitle>
              <CardDescription>Doporučené podle match skóre</CardDescription>
            </div>
            <Link to="/nabidky">
              <Button variant="outline" size="sm">
                Všechny nabídky
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {priorityJobs.length === 0 ? (
              <EmptyState
                title="Zatím žádné nabídky"
                description="Přidejte zdroje nebo importujte nabídku URL. Data se načítají z API — žádná ukázková data."
                action={
                  <Link to="/nabidky">
                    <Button size="sm">Importovat nabídku</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="space-y-3">
                {priorityJobs.map((job) => (
                  <li key={job.id}>
                    <Link
                      to={`/nabidky/${job.id}`}
                      className="block rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5 transition hover:border-primary/40"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium">{job.title}</div>
                        <Badge variant="secondary">{Math.round(job.match_score ?? 0)}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {job.company_name ?? "—"} · {job.location ?? "Lokalita neuvedena"}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Poslední e-maily</CardTitle>
              <CardDescription>Nábory a odpovědi z připojené schránky</CardDescription>
            </div>
            <Link to="/email">
              <Button variant="outline" size="sm">
                Schránka
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {messages.length === 0 ? (
              <EmptyState
                icon={<Mail className="h-8 w-8" />}
                title="Žádné zprávy"
                description="Připojte Email.cz ve Nastavení a spusťte synchronizaci."
              />
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {messages.map((msg) => (
                  <li key={msg.id} className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5">
                    <div className="font-medium">{msg.subject || "(bez předmětu)"}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {msg.sender} · {formatDate(msg.received_at ?? msg.sent_at, true)}
                    </div>
                    <Badge variant="outline" className="mt-2">
                      {msg.classification}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    DRAFTED: "Koncept",
    READY_FOR_REVIEW: "Ke kontrole",
    PENDING_APPROVAL: "Ke schválení",
    APPROVED: "Schváleno",
    SENT: "Odesláno",
  };
  return map[status] ?? status;
}
