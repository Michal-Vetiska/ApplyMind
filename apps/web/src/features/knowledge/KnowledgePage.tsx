import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSearch, Sparkles, Upload } from "lucide-react";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { normalizeList } from "@/lib/normalize";
import type { KnowledgeDocument, RagDebugResult } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageLoader } from "@/components/ui/spinner";

export function KnowledgePage() {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [debugResult, setDebugResult] = useState<RagDebugResult | null>(null);

  const docsQuery = useQuery({
    queryKey: ["knowledge", "documents"],
    queryFn: () =>
      apiGet<KnowledgeDocument[] | { items: KnowledgeDocument[] }>("/api/knowledge/documents"),
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("title", file.name);
      form.append("document_type", "resume");
      form.append("scope", "PERSONAL_KNOWLEDGE");
      form.append("approved", "false");
      return apiPost<KnowledgeDocument>("/api/knowledge/upload", form);
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/api/knowledge/documents/${id}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
  });

  const reindexMutation = useMutation({
    mutationFn: (id: string) =>
      apiPost(`/api/knowledge/reindex?document_id=${encodeURIComponent(id)}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) =>
      apiPatch(`/api/knowledge/documents/${id}/approve`, { approved: true }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
  });

  const debugMutation = useMutation({
    mutationFn: async (q: string) => {
      const result = await apiPost<{
        query: string;
        chunks: RagDebugResult["chunks"];
        count: number;
        latency_ms?: number;
        generated_response?: string;
      }>("/api/knowledge/search", { query: q, top_k: 8 });
      return {
        question: result.query,
        chunks: result.chunks ?? [],
        latency_ms: result.latency_ms,
        generated_response: result.generated_response,
      } satisfies RagDebugResult;
    },
    onSuccess: (data) => setDebugResult(data),
  });

  if (docsQuery.isLoading) return <PageLoader />;

  const docs = normalizeList(docsQuery.data);

  return (
    <div>
      <PageHeader
        title="Znalostní báze"
        description="Dokumenty zkušeností a RAG debugger pro ověření retrieval pipeline."
        actions={
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              className="hidden"
              accept=".pdf,.docx,.md,.txt"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadMutation.mutate(file);
                e.target.value = "";
              }}
            />
            <span className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-glow">
              <Upload className="h-4 w-4" />
              {uploadMutation.isPending ? "Nahrávám…" : "Nahrát dokument"}
            </span>
          </label>
        }
      />

      {uploadMutation.isError ? (
        <p className="mb-3 text-sm text-destructive">{uploadMutation.error.message}</p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dokumenty</CardTitle>
            <CardDescription>Indexované soubory a jejich schválení</CardDescription>
          </CardHeader>
          <CardContent>
            {docs.length === 0 ? (
              <EmptyState
                icon={<Sparkles className="h-8 w-8" />}
                title="Zatím žádné dokumenty"
                description="Nahrajte CV, poznámky k projektům nebo schválené zkušenosti (PDF/DOCX/MD/TXT)."
              />
            ) : (
              <ul className="space-y-3">
                {docs.map((doc) => (
                  <li key={doc.id} className="rounded-lg border border-border/60 bg-muted/20 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="font-medium">{doc.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {doc.document_type} · {doc.scope} · chunků {doc.chunk_count ?? "—"} ·{" "}
                          {formatDate(doc.indexed_at ?? doc.created_at)}
                        </div>
                      </div>
                      <Badge variant={doc.approved ? "success" : "warning"}>
                        {doc.approved ? "Schváleno" : "Ke schválení"}
                      </Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {!doc.approved ? (
                        <Button size="sm" variant="secondary" onClick={() => approveMutation.mutate(doc.id)}>
                          Schválit
                        </Button>
                      ) : null}
                      <Button size="sm" variant="outline" onClick={() => reindexMutation.mutate(doc.id)}>
                        Reindex
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => deleteMutation.mutate(doc.id)}>
                        Smazat
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileSearch className="h-4 w-4" />
              RAG debugger
            </CardTitle>
            <CardDescription>
              Zadejte otázku a zobrazte retrieved chunky přes `/api/knowledge/search`.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label>Otázka</Label>
              <Textarea
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Např. Jaké React Native projekty jsem dělal?"
              />
            </div>
            <Button
              disabled={!question.trim() || debugMutation.isPending}
              onClick={() => debugMutation.mutate(question.trim())}
            >
              {debugMutation.isPending ? "Vyhledávám…" : "Spustit retrieval"}
            </Button>
            {debugMutation.isError ? (
              <p className="text-sm text-destructive">{debugMutation.error.message}</p>
            ) : null}
            {!debugResult ? (
              <EmptyState
                title="Zatím bez výsledku"
                description="Spusťte dotaz proti indexované znalostní bázi."
              />
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span>Latence: {debugResult.latency_ms ?? "—"} ms</span>
                  <span>Chunků: {debugResult.chunks?.length ?? 0}</span>
                </div>
                {(debugResult.chunks ?? []).length === 0 ? (
                  <EmptyState title="Nic nenalezeno" description="Retrieval nevrátil žádné chunky." />
                ) : (
                  debugResult.chunks.map((chunk, idx) => (
                    <div
                      key={chunk.id ?? idx}
                      className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm"
                    >
                      <div className="mb-2 flex flex-wrap gap-2">
                        <Badge variant="secondary">
                          sim {chunk.similarity ?? chunk.score ?? "—"}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {chunk.document_title ?? chunk.document_id ?? "dokument"}
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {chunk.content ?? JSON.stringify(chunk)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
