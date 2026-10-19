import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Radio, RefreshCw } from "lucide-react";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { JobSource } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageLoader } from "@/components/ui/spinner";

function healthVariant(status: string) {
  switch (status) {
    case "HEALTHY":
      return "success" as const;
    case "DEGRADED":
    case "RATE_LIMITED":
      return "warning" as const;
    case "ERROR":
    case "AUTH_REQUIRED":
      return "danger" as const;
    case "UNSUPPORTED":
      return "outline" as const;
    default:
      return "secondary" as const;
  }
}

export function SourcesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const sourcesQuery = useQuery({
    queryKey: ["sources"],
    queryFn: () => apiGet<JobSource[]>("/api/sources"),
  });

  const providersQuery = useQuery({
    queryKey: ["sources", "providers"],
    queryFn: () => apiGet<Array<{ provider?: string; name?: string; id?: string } | string>>("/api/sources/providers"),
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => apiPost(`/api/sources/${id}/sync`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: (source: JobSource) =>
      apiPatch<JobSource>(`/api/sources/${source.id}`, {
        name: source.name,
        provider: source.provider,
        source_url: source.source_url,
        configuration: source.configuration,
        enabled: !source.enabled,
        poll_interval_minutes: source.poll_interval_minutes,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      name: string;
      provider: string;
      source_url?: string;
      configuration: Record<string, unknown>;
      poll_interval_minutes: number;
    }) => apiPost<JobSource>("/api/sources", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowForm(false);
    },
  });

  if (sourcesQuery.isLoading) return <PageLoader />;

  const sources = sourcesQuery.data ?? [];
  const providers = (providersQuery.data ?? []).map((p) =>
    typeof p === "string" ? p : p.provider ?? p.id ?? p.name ?? "",
  );

  return (
    <div>
      <PageHeader
        title="Zdroje nabídek"
        description="Správa ATS boardů, RSS a dalších zdrojů. České portály bez ověřeného API jsou označené jako UNSUPPORTED."
        actions={
          <Button onClick={() => setShowForm((v) => !v)}>Přidat zdroj</Button>
        }
      />

      {showForm ? (
        <SourceForm
          providers={providers.filter(Boolean)}
          onSubmit={(p) => createMutation.mutate(p)}
          pending={createMutation.isPending}
          error={createMutation.error?.message}
        />
      ) : null}

      {sources.length === 0 ? (
        <EmptyState
          icon={<Radio className="h-10 w-10" />}
          title="Žádné zdroje"
          description="Přidejte Greenhouse/Lever/Ashby/SmartRecruiters board nebo RSS feed. Jobs.cz a podobné portály vyžadují manuální import."
        />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {sources.map((source) => (
            <Card key={source.id}>
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle>{source.name}</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">{source.provider}</p>
                </div>
                <Badge variant={healthVariant(source.health_status)}>{source.health_status}</Badge>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                  <div>Povoleno: {source.enabled ? "ano" : "ne"}</div>
                  <div>Nabídek: {source.discovered_jobs_count}</div>
                  <div>Poslední sync: {formatDate(source.last_checked_at, true)}</div>
                  <div>Úspěch: {formatDate(source.last_success_at, true)}</div>
                  <div>Interval: {source.poll_interval_minutes} min</div>
                  <div className="truncate">URL: {source.source_url ?? "—"}</div>
                </div>
                {source.last_error ? (
                  <p className="rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
                    {source.last_error}
                  </p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={syncMutation.isPending || source.health_status === "UNSUPPORTED"}
                    onClick={() => syncMutation.mutate(source.id)}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Synchronizovat
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={toggleMutation.isPending || source.health_status === "UNSUPPORTED"}
                    onClick={() => toggleMutation.mutate(source)}
                  >
                    {source.enabled ? "Vypnout" : "Zapnout"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function SourceForm({
  providers,
  onSubmit,
  pending,
  error,
}: {
  providers: string[];
  onSubmit: (payload: {
    name: string;
    provider: string;
    source_url?: string;
    configuration: Record<string, unknown>;
    poll_interval_minutes: number;
  }) => void;
  pending: boolean;
  error?: string;
}) {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState(providers[0] ?? "greenhouse");
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [interval, setInterval] = useState("180");

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>Nový zdroj</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Název</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Provider</Label>
          <Input list="providers" value={provider} onChange={(e) => setProvider(e.target.value)} />
          <datalist id="providers">
            {providers.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
        </div>
        <div className="space-y-1.5">
          <Label>URL / board</Label>
          <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="board token / slug / feed URL" />
        </div>
        <div className="space-y-1.5">
          <Label>Konfigurační token / slug</Label>
          <Input value={token} onChange={(e) => setToken(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Interval (min)</Label>
          <Input value={interval} onChange={(e) => setInterval(e.target.value)} />
        </div>
        {error ? <p className="text-sm text-destructive sm:col-span-2">{error}</p> : null}
        <div className="sm:col-span-2">
          <Button
            disabled={pending || !name || !provider}
            onClick={() =>
              onSubmit({
                name,
                provider,
                source_url: url || undefined,
                configuration: token
                  ? { board_token: token, site: token, board_name: token, companyIdentifier: token, feed_url: url }
                  : url
                    ? { feed_url: url }
                    : {},
                poll_interval_minutes: Number(interval) || 180,
              })
            }
          >
            {pending ? "Ukládám…" : "Vytvořit zdroj"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
