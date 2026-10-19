import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, Sparkles } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate, formatSalary, formatScore } from "@/lib/utils";
import type { Application, Job } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageLoader } from "@/components/ui/spinner";

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const jobQuery = useQuery({
    queryKey: ["jobs", id],
    queryFn: () => apiGet<Job>(`/api/jobs/${id}`),
    enabled: Boolean(id),
  });

  const evaluateMutation = useMutation({
    mutationFn: () => apiPost(`/api/jobs/${id}/evaluate`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["jobs", id] }),
  });

  const generateMutation = useMutation({
    mutationFn: () => apiPost<Application>("/api/applications/generate", { job_id: id }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (jobQuery.isLoading) return <PageLoader />;
  if (jobQuery.isError || !jobQuery.data) {
    return (
      <EmptyState
        title="Nabídka nenalezena"
        description={jobQuery.error?.message ?? "Požadovaná nabídka neexistuje."}
        action={
          <Link to="/nabidky">
            <Button variant="outline">Zpět na nabídky</Button>
          </Link>
        }
      />
    );
  }

  const job = jobQuery.data;
  const matchRaw = job.matches?.[0] as
    | {
        overall_score?: number;
        decision?: string;
        explanation?: Record<string, unknown>;
        missing_skills?: string[];
        skill_score?: number;
        seniority_score?: number;
        location_score?: number;
        compensation_score?: number;
      }
    | undefined;
  const overall = job.match_score ?? matchRaw?.overall_score ?? job.match?.overall_score;
  const decision = job.match_decision ?? matchRaw?.decision ?? job.match?.decision;
  const missing = matchRaw?.missing_skills ?? job.match?.missing_skills_json ?? [];

  return (
    <div>
      <Link to="/nabidky" className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Zpět na nabídky
      </Link>
      <PageHeader
        title={job.title}
        description={`${job.company_name ?? job.company?.name ?? "Neznámá firma"} · ${job.location ?? "Lokalita neuvedena"}`}
        actions={
          <>
            <Button variant="outline" onClick={() => evaluateMutation.mutate()} disabled={evaluateMutation.isPending}>
              <Sparkles className="h-4 w-4" />
              {evaluateMutation.isPending ? "Hodnotím…" : "Vyhodnotit shodu"}
            </Button>
            <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
              {generateMutation.isPending ? "Generuji…" : "Vygenerovat přihlášku"}
            </Button>
            {job.source_url ? (
              <a href={job.source_url} target="_blank" rel="noreferrer">
                <Button variant="secondary">
                  <ExternalLink className="h-4 w-4" />
                  Originál
                </Button>
              </a>
            ) : null}
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Popis nabídky</CardTitle>
          </CardHeader>
          <CardContent>
            {job.description ? (
              <div className="prose prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed text-secondary-foreground">
                {job.description}
              </div>
            ) : (
              <EmptyState title="Popis chybí" description="Nabídka nemá uložený text popisu." />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Detaily</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Plat" value={formatSalary(job.salary_min, job.salary_max, job.currency ?? "CZK", job.salary_flag)} />
              <Row label="Remote" value={job.remote_type ?? "—"} />
              <Row label="Úvazek" value={job.employment_type ?? "—"} />
              <Row label="Seniorita" value={job.seniority ?? "—"} />
              <Row label="Způsob přihlášky" value={job.apply_method ?? "—"} />
              <Row label="Kontakt" value={job.contact_email ?? "—"} />
              <Row label="Objeveno" value={formatDate(job.discovered_at, true)} />
              <div className="flex flex-wrap gap-1.5 pt-1">
                {(job.technologies ?? []).map((t) => (
                  <Badge key={t} variant="secondary">
                    {t}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Match skóre</CardTitle>
              <CardDescription>Vysvětlitelné hodnocení shody</CardDescription>
            </CardHeader>
            <CardContent>
              {overall == null ? (
                <EmptyState
                  title="Zatím nevyhodnoceno"
                  description="Spusťte vyhodnocení shody s vaším search profilem."
                />
              ) : (
                <div className="space-y-3">
                  <div className="font-display text-4xl font-semibold text-primary">
                    {formatScore(overall)}
                  </div>
                  {decision ? <Badge>{decision}</Badge> : null}
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <div>Technologie: {formatScore(matchRaw?.skill_score ?? job.match?.skill_score)}</div>
                    <div>Seniorita: {formatScore(matchRaw?.seniority_score ?? job.match?.seniority_score)}</div>
                    <div>Lokalita: {formatScore(matchRaw?.location_score ?? job.match?.location_score)}</div>
                    <div>Kompenzace: {formatScore(matchRaw?.compensation_score ?? job.match?.compensation_score)}</div>
                  </div>
                  {missing.length > 0 ? (
                    <div>
                      <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Chybějící skill</div>
                      <div className="flex flex-wrap gap-1">
                        {missing.map((s) => (
                          <Badge key={s} variant="warning">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {generateMutation.isSuccess ? (
        <p className="mt-4 text-sm text-primary">
          Přihláška byla vytvořena.{" "}
          <Link className="underline" to="/prihlasky">
            Přejít na přihlášky
          </Link>
        </p>
      ) : null}
      {generateMutation.isError ? (
        <p className="mt-4 text-sm text-destructive">{generateMutation.error.message}</p>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
