import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, Filter, Upload } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { buildQuery, formatDate, formatSalary, formatScore } from "@/lib/utils";
import { normalizePaginated } from "@/lib/normalize";
import type { Job } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageLoader } from "@/components/ui/spinner";

interface Filters {
  q: string;
  location: string;
  remote_type: string;
  seniority: string;
  min_score: string;
  status: string;
}

const INITIAL: Filters = {
  q: "",
  location: "",
  remote_type: "",
  seniority: "",
  min_score: "",
  status: "",
};

export function JobsPage() {
  const [filters, setFilters] = useState<Filters>(INITIAL);
  const [applied, setApplied] = useState<Filters>(INITIAL);
  const [showImport, setShowImport] = useState(false);
  const queryClient = useQueryClient();

  const queryString = useMemo(
    () =>
      buildQuery({
        limit: 50,
        q: applied.q || undefined,
        location: applied.location || undefined,
        remote_type: applied.remote_type || undefined,
        seniority: applied.seniority || undefined,
        min_score: applied.min_score || undefined,
        status: applied.status || undefined,
      }),
    [applied],
  );

  const jobsQuery = useQuery({
    queryKey: ["jobs", queryString],
    queryFn: () => apiGet<Job[] | { items: Job[]; total: number }>(`/api/jobs${queryString}`),
  });

  const importMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      company_name?: string;
      description?: string;
      source_url?: string;
      location?: string;
    }) => apiPost<Job>("/api/jobs/import", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setShowImport(false);
    },
  });

  if (jobsQuery.isLoading) return <PageLoader />;

  const { items: jobs, total } = normalizePaginated(jobsQuery.data);

  return (
    <div>
      <PageHeader
        title="Nabídky"
        description="Objevené a importované pracovní nabídky z připojených zdrojů."
        actions={
          <Button onClick={() => setShowImport((v) => !v)} variant={showImport ? "secondary" : "default"}>
            <Upload className="h-4 w-4" />
            Importovat
          </Button>
        }
      />

      {showImport ? <JobImportForm onSubmit={(p) => importMutation.mutate(p)} pending={importMutation.isPending} error={importMutation.error?.message} /> : null}

      <Card className="mb-4">
        <CardHeader className="flex flex-row items-center gap-2 pb-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm">Filtry</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Field label="Hledat" value={filters.q} onChange={(v) => setFilters((f) => ({ ...f, q: v }))} placeholder="Pozice, firma…" />
            <Field label="Lokalita" value={filters.location} onChange={(v) => setFilters((f) => ({ ...f, location: v }))} placeholder="Praha" />
            <Field label="Remote" value={filters.remote_type} onChange={(v) => setFilters((f) => ({ ...f, remote_type: v }))} placeholder="remote / hybrid" />
            <Field label="Seniorita" value={filters.seniority} onChange={(v) => setFilters((f) => ({ ...f, seniority: v }))} placeholder="junior" />
            <Field label="Min. skóre" value={filters.min_score} onChange={(v) => setFilters((f) => ({ ...f, min_score: v }))} placeholder="60" />
            <Field label="Stav" value={filters.status} onChange={(v) => setFilters((f) => ({ ...f, status: v }))} placeholder="DISCOVERED" />
          </div>
          <div className="mt-3 flex gap-2">
            <Button size="sm" onClick={() => setApplied(filters)}>
              Použít filtry
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFilters(INITIAL);
                setApplied(INITIAL);
              }}
            >
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {jobsQuery.isError ? (
        <EmptyState
          title="Nepodařilo se načíst nabídky"
          description={jobsQuery.error.message}
        />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="h-10 w-10" />}
          title="Zatím žádné nabídky"
          description="Spusťte synchronizaci zdrojů nebo importujte nabídku ručně. V UI se nezobrazují mock data."
          action={
            <Button size="sm" onClick={() => setShowImport(true)}>
              Importovat nabídku
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Celkem {total} nabídek</p>
          {jobs.map((job) => {
            const score = job.match_score ?? job.match?.overall_score;
            return (
              <Link key={job.id} to={`/nabidky/${job.id}`} className="block">
                <Card className="transition hover:border-primary/40 hover:shadow-glow">
                  <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-display text-lg font-semibold">{job.title}</h3>
                        <Badge variant="outline">{job.status}</Badge>
                        {job.match_decision ? <Badge variant="secondary">{job.match_decision}</Badge> : null}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {job.company_name ?? job.company?.name ?? "Neznámá firma"} ·{" "}
                        {job.location ?? "Lokalita neuvedena"} · {job.remote_type ?? "—"}
                      </p>
                      <p className="text-sm">
                        {formatSalary(job.salary_min, job.salary_max, job.currency ?? "CZK", job.salary_flag)}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {(job.technologies ?? []).slice(0, 8).map((tech) => (
                          <Badge key={tech} variant="secondary">
                            {tech}
                          </Badge>
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Zdroj: {job.source?.name ?? job.source?.provider ?? "—"} · Objeveno{" "}
                        {formatDate(job.discovered_at)}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-display text-3xl font-semibold text-primary">{formatScore(score)}</div>
                      <div className="text-xs text-muted-foreground">match skóre</div>
                      <div className="mt-2 text-xs text-muted-foreground">{job.apply_method ?? "—"}</div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function JobImportForm({
  onSubmit,
  pending,
  error,
}: {
  onSubmit: (payload: {
    title: string;
    company_name?: string;
    description?: string;
    source_url?: string;
    location?: string;
  }) => void;
  pending: boolean;
  error?: string;
}) {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [raw, setRaw] = useState("");

  return (
    <Card className="mb-4 animate-fade-up">
      <CardHeader>
        <CardTitle>Manuální import nabídky</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Název pozice *</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label>URL nabídky</Label>
            <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
          </div>
          <div className="space-y-1.5">
            <Label>Firma</Label>
            <Input value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Lokalita</Label>
            <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Praha" />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Text nabídky (volitelné)</Label>
            <Textarea value={raw} onChange={(e) => setRaw(e.target.value)} rows={5} />
          </div>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button
          disabled={pending || !title.trim()}
          onClick={() =>
            onSubmit({
              title: title.trim(),
              source_url: url || undefined,
              company_name: company || undefined,
              description: raw || undefined,
              location: location || undefined,
            })
          }
        >
          {pending ? "Importuji…" : "Importovat do systému"}
        </Button>
      </CardContent>
    </Card>
  );
}
