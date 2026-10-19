import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Play } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { normalizeList } from "@/lib/normalize";
import type { AutomationRun } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";

const JOB_TYPES = [
  "discover_jobs",
  "evaluate_jobs",
  "sync_inbox",
  "suggest_followups",
  "refresh_source_health",
  "update_analytics",
];

function statusVariant(status: string) {
  if (status === "SUCCESS" || status === "COMPLETED") return "success" as const;
  if (status === "RUNNING") return "warning" as const;
  if (status === "FAILED" || status === "ERROR") return "danger" as const;
  return "secondary" as const;
}

export function AutomationPage() {
  const queryClient = useQueryClient();
  const [jobType, setJobType] = useState(JOB_TYPES[0]);

  const runsQuery = useQuery({
    queryKey: ["automations", "runs"],
    queryFn: () =>
      apiGet<AutomationRun[] | { items: AutomationRun[] }>("/api/automations"),
  });

  const triggerMutation = useMutation({
    mutationFn: (type: string) => apiPost("/api/automations/run", { job_type: type }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["automations"] }),
  });

  if (runsQuery.isLoading) return <PageLoader />;

  const runs = normalizeList(runsQuery.data);

  return (
    <div>
      <PageHeader
        title="Automatizace"
        description="Historie Celery běhů a manuální spuštění pipeline úloh."
      />

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Manuální spuštění</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1.5">
            <Label>Typ úlohy</Label>
            <Input list="job-types" value={jobType} onChange={(e) => setJobType(e.target.value)} />
            <datalist id="job-types">
              {JOB_TYPES.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>
          <Button
            disabled={!jobType || triggerMutation.isPending}
            onClick={() => triggerMutation.mutate(jobType)}
          >
            <Play className="h-4 w-4" />
            {triggerMutation.isPending ? "Spouštím…" : "Spustit"}
          </Button>
        </CardContent>
        {triggerMutation.isError ? (
          <p className="px-5 pb-4 text-sm text-destructive">{triggerMutation.error.message}</p>
        ) : null}
        {triggerMutation.isSuccess ? (
          <p className="px-5 pb-4 text-sm text-primary">Úloha byla zařazena ke spuštění.</p>
        ) : null}
      </Card>

      {runs.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-10 w-10" />}
          title="Žádné běhy automatizace"
          description="Spusťte úlohu ručně nebo počkejte na Celery Beat plán."
        />
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <Card key={run.id}>
              <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium">{run.job_type}</h3>
                    <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Start {formatDate(run.started_at, true)}
                    {run.completed_at ? ` · Konec ${formatDate(run.completed_at, true)}` : ""}
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Zpracováno</div>
                    <div className="font-semibold">{run.processed_count}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">OK</div>
                    <div className="font-semibold text-success">{run.success_count}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Chyby</div>
                    <div className="font-semibold text-destructive">{run.error_count}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
