import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { normalizeList } from "@/lib/normalize";
import type { Application, Job } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageLoader } from "@/components/ui/spinner";

const COLUMNS: Array<{ id: string; label: string; statuses: string[] }> = [
  { id: "new", label: "Nové", statuses: ["DRAFTED", "READY_FOR_REVIEW"] },
  { id: "ready", label: "Připravené", statuses: ["APPROVED"] },
  { id: "sent", label: "Odeslané", statuses: ["SUBMISSION_IN_PROGRESS", "SENT", "SENT_UNCONFIRMED"] },
  { id: "reply", label: "Odpověď", statuses: ["RESPONSE_RECEIVED", "NEEDS_MANUAL_REVIEW"] },
  { id: "interview", label: "Pohovor", statuses: ["INTERVIEW"] },
  { id: "offer", label: "Nabídka", statuses: ["OFFER"] },
  { id: "rejected", label: "Zamítnuté", statuses: ["REJECTED", "FAILED", "WITHDRAWN"] },
];

export function ApplicationsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const appsQuery = useQuery({
    queryKey: ["applications"],
    queryFn: () => apiGet<Application[] | { items: Application[] }>("/api/applications"),
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs", "for-apps"],
    queryFn: () => apiGet<{ items: Job[] } | Job[]>("/api/jobs?limit=200"),
  });

  const apps = normalizeList(appsQuery.data);
  const jobs = normalizeList(jobsQuery.data);
  const jobsById = useMemo(() => new Map(jobs.map((j) => [j.id, j])), [jobs]);
  const selected = apps.find((a) => a.id === selectedId) ?? null;
  const selectedJob = selected ? jobsById.get(selected.job_id) : undefined;

  const approveMutation = useMutation({
    mutationFn: (payload: { id: string; subject?: string; message?: string; recipient_email?: string }) =>
      apiPost<Application>(`/api/applications/${payload.id}/approve`, {
        subject: payload.subject,
        message: payload.message,
        recipient_email: payload.recipient_email,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => apiPost<Application>(`/api/applications/${id}/submit`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiPatch<Application>(`/api/applications/${id}/status`, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (appsQuery.isLoading) return <PageLoader />;

  const byColumn = COLUMNS.map((col) => ({
    ...col,
    items: apps.filter((a) => col.statuses.includes(a.status)),
  }));

  return (
    <div>
      <PageHeader
        title="Přihlášky"
        description="Kanban přehled životního cyklu přihlášek. Přetahování = validovaný přechod stavu."
      />

      {apps.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-10 w-10" />}
          title="Zatím žádné přihlášky"
          description="Vygenerujte přihlášku z detailu nabídky. Data se načítají z API."
        />
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {byColumn.map((col) => (
            <div key={col.id} className="w-64 shrink-0">
              <div className="mb-2 flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold">{col.label}</h3>
                <Badge variant="outline">{col.items.length}</Badge>
              </div>
              <div
                className="min-h-[420px] space-y-2 rounded-xl border border-border/60 bg-muted/10 p-2"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const appId = e.dataTransfer.getData("text/app-id");
                  const targetStatus = col.statuses[0];
                  if (appId && targetStatus) {
                    statusMutation.mutate({ id: appId, status: targetStatus });
                  }
                }}
              >
                {col.items.length === 0 ? (
                  <p className="px-2 py-6 text-center text-xs text-muted-foreground">Prázdné</p>
                ) : (
                  col.items.map((app) => {
                    const job = jobsById.get(app.job_id);
                    return (
                      <button
                        key={app.id}
                        type="button"
                        draggable
                        onDragStart={(e) => e.dataTransfer.setData("text/app-id", app.id)}
                        onClick={() => setSelectedId(app.id)}
                        className="w-full rounded-lg border border-border/70 bg-card p-3 text-left transition hover:border-primary/40"
                      >
                        <div className="font-medium leading-snug">
                          {job?.title ?? `Přihláška ${app.id.slice(0, 8)}`}
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {job?.company_name ?? "—"}
                        </div>
                        <div className="mt-2 flex items-center justify-between gap-2">
                          <Badge variant="secondary" className="text-[10px]">
                            {app.status}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">
                            {formatDate(app.last_activity_at ?? app.sent_at)}
                          </span>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected ? (
        <ApplicationDetail
          app={selected}
          job={selectedJob}
          onClose={() => setSelectedId(null)}
          onApprove={(payload) => approveMutation.mutate({ id: selected.id, ...payload })}
          onSubmit={() => submitMutation.mutate(selected.id)}
          approving={approveMutation.isPending}
          submitting={submitMutation.isPending}
          error={approveMutation.error?.message ?? submitMutation.error?.message}
        />
      ) : null}
    </div>
  );
}

function ApplicationDetail({
  app,
  job,
  onClose,
  onApprove,
  onSubmit,
  approving,
  submitting,
  error,
}: {
  app: Application;
  job?: Job;
  onClose: () => void;
  onApprove: (payload: { subject?: string; message?: string; recipient_email?: string }) => void;
  onSubmit: () => void;
  approving: boolean;
  submitting: boolean;
  error?: string;
}) {
  const [subject, setSubject] = useState(app.approved_subject ?? app.generated_subject ?? "");
  const [message, setMessage] = useState(app.approved_message ?? app.generated_message ?? "");
  const [recipient, setRecipient] = useState(app.recipient_email ?? "");

  return (
    <Card className="mt-4 animate-fade-up">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>{job?.title ?? "Detail přihlášky"}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            {job?.company_name ?? "—"} · stav {app.status}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Zavřít
        </Button>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Předmět</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Zpráva</Label>
            <Textarea rows={12} value={message} onChange={(e) => setMessage(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Příjemce</Label>
            <Input value={recipient} onChange={(e) => setRecipient(e.target.value)} placeholder="hr@firma.cz" />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={approving}
              onClick={() =>
                onApprove({
                  subject,
                  message,
                  recipient_email: recipient || undefined,
                })
              }
            >
              {approving ? "Schvaluji…" : "Schválit"}
            </Button>
            <Button variant="secondary" disabled={submitting} onClick={onSubmit}>
              {submitting ? "Odesílám…" : "Odeslat / dry-run"}
            </Button>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {app.failure_reason ? (
            <p className="text-sm text-warning">Důvod: {app.failure_reason}</p>
          ) : null}
        </div>
        <div className="space-y-3">
          <h4 className="text-sm font-semibold">Evidence (citace)</h4>
          {(app.evidence ?? []).length === 0 ? (
            <EmptyState title="Bez evidence" description="Generování nepřiložilo doložené claimy." />
          ) : (
            <ul className="space-y-2">
              {app.evidence!.map((ev) => (
                <li key={ev.id} className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                  <Badge variant="outline" className="mb-2">
                    {ev.verification_status}
                  </Badge>
                  <p>{ev.claim}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
