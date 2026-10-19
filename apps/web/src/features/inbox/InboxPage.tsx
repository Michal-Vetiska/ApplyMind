import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, RefreshCw } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { normalizePaginated } from "@/lib/normalize";
import type { EmailAccount, EmailMessage } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/ui/spinner";

export function InboxPage() {
  const queryClient = useQueryClient();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const accountsQuery = useQuery({
    queryKey: ["email", "accounts"],
    queryFn: () => apiGet<EmailAccount[]>("/api/email/accounts"),
  });

  const messagesQuery = useQuery({
    queryKey: ["email", "messages"],
    queryFn: () =>
      apiGet<{ items: EmailMessage[]; total: number }>("/api/email/messages?limit=100"),
  });

  const syncMutation = useMutation({
    mutationFn: async () => {
      const accounts = accountsQuery.data ?? [];
      if (accounts.length === 0) {
        throw new Error("Nejdřív připojte e-mailový účet v Nastavení.");
      }
      return apiPost(`/api/email/accounts/${accounts[0].id}/sync`);
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["email"] }),
  });

  if (messagesQuery.isLoading) return <PageLoader />;

  const messages = normalizePaginated(messagesQuery.data).items;

  const threads = useMemo(() => {
    const map = new Map<
      string,
      { key: string; subject?: string | null; classification?: string; lastAt?: string | null; messages: EmailMessage[] }
    >();
    for (const msg of messages) {
      const key = msg.thread_identifier || msg.message_id || msg.id;
      const existing = map.get(key);
      if (!existing) {
        map.set(key, {
          key,
          subject: msg.subject,
          classification: msg.classification,
          lastAt: msg.received_at ?? msg.sent_at,
          messages: [msg],
        });
      } else {
        existing.messages.push(msg);
        const at = msg.received_at ?? msg.sent_at;
        if (at && (!existing.lastAt || at > existing.lastAt)) {
          existing.lastAt = at;
          existing.subject = msg.subject ?? existing.subject;
          existing.classification = msg.classification;
        }
      }
    }
    return Array.from(map.values()).sort((a, b) => (b.lastAt ?? "").localeCompare(a.lastAt ?? ""));
  }, [messages]);

  const active = threads.find((t) => t.key === selectedKey) ?? threads[0] ?? null;

  return (
    <div>
      <PageHeader
        title="E-mail"
        description="Náborová vlákna ze synchronizované schránky Email.cz."
        actions={
          <Button
            variant="outline"
            disabled={syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
          >
            <RefreshCw className="h-4 w-4" />
            {syncMutation.isPending ? "Synchronizuji…" : "Synchronizovat"}
          </Button>
        }
      />

      {syncMutation.isError ? (
        <p className="mb-3 text-sm text-destructive">{syncMutation.error.message}</p>
      ) : null}

      {threads.length === 0 ? (
        <EmptyState
          icon={<Mail className="h-10 w-10" />}
          title="Schránka je prázdná"
          description="Připojte účet Email.cz v Nastavení a spusťte synchronizaci. Žádná mock data se nezobrazují."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Vlákna ({threads.length})</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[70vh] space-y-1 overflow-y-auto p-2">
              {threads.map((thread) => (
                <button
                  key={thread.key}
                  type="button"
                  onClick={() => setSelectedKey(thread.key)}
                  className={`w-full rounded-lg px-3 py-2.5 text-left transition ${
                    active?.key === thread.key
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted"
                  }`}
                >
                  <div className="truncate text-sm font-medium">
                    {thread.subject || "(bez předmětu)"}
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      {thread.classification ?? "UNCERTAIN"}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      {formatDate(thread.lastAt)}
                    </span>
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{active?.subject || "(bez předmětu)"}</CardTitle>
              <p className="text-sm text-muted-foreground">
                {active?.messages.length ?? 0} zpráv ve vlákně
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {(active?.messages ?? []).map((msg) => (
                <div key={msg.id} className="rounded-lg border border-border/60 bg-muted/20 p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-medium">{msg.sender}</div>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(msg.received_at ?? msg.sent_at, true)}
                    </span>
                  </div>
                  <Badge variant="secondary" className="mb-3">
                    {msg.classification}
                  </Badge>
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-secondary-foreground">
                    {msg.text_body || "(náhled textu není k dispozici)"}
                  </pre>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
