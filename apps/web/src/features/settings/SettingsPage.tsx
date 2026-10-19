import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { AppSettings, EmailAccount, Resume, SearchProfile, UserProfile } from "@/types/api";
import { normalizeList } from "@/lib/normalize";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageLoader } from "@/components/ui/spinner";

export function SettingsPage() {
  const queryClient = useQueryClient();

  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: () => apiGet<UserProfile>("/api/profile"),
  });
  const searchQuery = useQuery({
    queryKey: ["search-profiles"],
    queryFn: () => apiGet<SearchProfile[]>("/api/search-profiles"),
  });
  const resumesQuery = useQuery({
    queryKey: ["resumes"],
    queryFn: () => apiGet<Resume[]>("/api/resumes"),
  });
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiGet<AppSettings>("/api/settings"),
  });
  const emailQuery = useQuery({
    queryKey: ["email", "accounts"],
    queryFn: () => apiGet<EmailAccount[] | { items: EmailAccount[] }>("/api/email/accounts"),
  });

  if (profileQuery.isLoading) return <PageLoader />;

  return (
    <div>
      <PageHeader
        title="Nastavení"
        description="Profil, search profily, soukromí, životopisy a připojení e-mailu."
      />
      <div className="space-y-4">
        <ProfileSection
          profile={profileQuery.data}
          onSaved={() => void queryClient.invalidateQueries({ queryKey: ["profile"] })}
        />
        <SearchProfilesSection
          profiles={searchQuery.data ?? []}
          onChanged={() => void queryClient.invalidateQueries({ queryKey: ["search-profiles"] })}
        />
        <ResumesSection
          resumes={resumesQuery.data ?? []}
          onChanged={() => void queryClient.invalidateQueries({ queryKey: ["resumes"] })}
        />
        <PrivacySection
          settings={settingsQuery.data}
          onChanged={() => void queryClient.invalidateQueries({ queryKey: ["settings"] })}
        />
        <EmailConnectSection
          accounts={normalizeList(emailQuery.data)}
          onChanged={() => void queryClient.invalidateQueries({ queryKey: ["email"] })}
        />
      </div>
    </div>
  );
}

function ProfileSection({ profile, onSaved }: { profile?: UserProfile; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    location: "",
    summary: "",
    portfolio_url: "",
    github_url: "",
    linkedin_url: "",
  });

  useEffect(() => {
    if (!profile) return;
    setForm({
      name: profile.name ?? "",
      email: profile.email ?? "",
      phone: profile.phone ?? "",
      location: profile.location ?? "",
      summary: profile.summary ?? "",
      portfolio_url: profile.portfolio_url ?? "",
      github_url: profile.github_url ?? "",
      linkedin_url: profile.linkedin_url ?? "",
    });
  }, [profile]);

  const mutation = useMutation({
    mutationFn: () => apiPatch<UserProfile>("/api/profile", form),
    onSuccess: onSaved,
  });

  if (!profile) {
    return (
      <Card>
        <CardContent className="p-5">
          <EmptyState title="Profil nenalezen" description="Backend nevrátil uživatelský profil." />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profil</CardTitle>
        <CardDescription>Základní údaje používané při generování přihlášek</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        {(
          [
            ["name", "Jméno"],
            ["email", "E-mail"],
            ["phone", "Telefon"],
            ["location", "Lokalita"],
            ["portfolio_url", "Portfolio URL"],
            ["github_url", "GitHub"],
            ["linkedin_url", "LinkedIn"],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className="space-y-1.5">
            <Label>{label}</Label>
            <Input value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
          </div>
        ))}
        <div className="space-y-1.5 sm:col-span-2">
          <Label>Shrnutí</Label>
          <Textarea rows={4} value={form.summary} onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))} />
        </div>
        <div className="sm:col-span-2">
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? "Ukládám…" : "Uložit profil"}
          </Button>
          {mutation.isError ? <p className="mt-2 text-sm text-destructive">{mutation.error.message}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function SearchProfilesSection({
  profiles,
  onChanged,
}: {
  profiles: SearchProfile[];
  onChanged: () => void;
}) {
  const [name, setName] = useState("");
  const createMutation = useMutation({
    mutationFn: () =>
      apiPost<SearchProfile>("/api/search-profiles", {
        name: name || "Nový search profil",
        enabled: true,
        locations: ["Praha"],
        job_titles: { high: ["React Developer"] },
        technologies: ["React", "TypeScript"],
        employment_types: ["full-time"],
        remote_preferences: ["remote", "hybrid"],
        seniority: ["junior", "medior"],
      }),
    onSuccess: () => {
      setName("");
      onChanged();
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/api/search-profiles/${id}`),
    onSuccess: onChanged,
  });
  const toggleMutation = useMutation({
    mutationFn: (profile: SearchProfile) =>
      apiPatch(`/api/search-profiles/${profile.id}`, { enabled: !profile.enabled }),
    onSuccess: onChanged,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search profily</CardTitle>
        <CardDescription>Preference pro matching a discovery</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {profiles.length === 0 ? (
          <EmptyState title="Žádný search profil" description="Vytvořte alespoň jeden profil preferencí." />
        ) : (
          profiles.map((p) => (
            <div
              key={p.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5"
            >
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-muted-foreground">
                  práh {p.matching_threshold} · auto-apply {p.auto_apply_enabled ? "ano" : "ne"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={p.enabled ? "success" : "outline"}>
                  {p.enabled ? "Aktivní" : "Vypnuto"}
                </Badge>
                <Button size="sm" variant="outline" onClick={() => toggleMutation.mutate(p)}>
                  {p.enabled ? "Vypnout" : "Zapnout"}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => deleteMutation.mutate(p.id)}>
                  Smazat
                </Button>
              </div>
            </div>
          ))
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input placeholder="Název nového profilu" value={name} onChange={(e) => setName(e.target.value)} />
          <Button disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>
            Přidat
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ResumesSection({ resumes, onChanged }: { resumes: Resume[]; onChanged: () => void }) {
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("name", file.name);
      form.append("is_default", resumes.length === 0 ? "true" : "false");
      return apiPost<Resume>("/api/resumes", form);
    },
    onSuccess: onChanged,
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/api/resumes/${id}`),
    onSuccess: onChanged,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Životopisy</CardTitle>
        <CardDescription>PDF / DOCX / MD / TXT — výběr pro přihlášky</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {resumes.length === 0 ? (
          <EmptyState title="Žádný životopis" description="Nahrajte alespoň jedno CV." />
        ) : (
          resumes.map((r) => (
            <div
              key={r.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5"
            >
              <div>
                <div className="font-medium">{r.name}</div>
                <div className="text-xs text-muted-foreground">{r.original_filename}</div>
              </div>
              <div className="flex items-center gap-2">
                {r.is_default ? <Badge>Výchozí</Badge> : null}
                <Button size="sm" variant="destructive" onClick={() => deleteMutation.mutate(r.id)}>
                  Smazat
                </Button>
              </div>
            </div>
          ))
        )}
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
          <span className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm hover:bg-muted">
            {uploadMutation.isPending ? "Nahrávám…" : "Nahrát životopis"}
          </span>
        </label>
        {uploadMutation.isError ? (
          <p className="text-sm text-destructive">{uploadMutation.error.message}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PrivacySection({
  settings,
  onChanged,
}: {
  settings?: AppSettings;
  onChanged: () => void;
}) {
  const privacy = settings?.privacy ?? {};
  const [form, setForm] = useState({
    allow_llm_email_processing: false,
    store_email_bodies: true,
    redact_pii_in_logs: true,
    allow_llm_on_historical_mail: false,
  });

  useEffect(() => {
    setForm({
      allow_llm_email_processing: Boolean(privacy.allow_llm_email_processing),
      store_email_bodies: privacy.store_email_bodies !== false,
      redact_pii_in_logs: privacy.redact_pii_in_logs !== false,
      allow_llm_on_historical_mail: Boolean(privacy.allow_llm_on_historical_mail),
    });
  }, [
    privacy.allow_llm_email_processing,
    privacy.store_email_bodies,
    privacy.redact_pii_in_logs,
    privacy.allow_llm_on_historical_mail,
  ]);

  const mutation = useMutation({
    mutationFn: () => apiPatch("/api/settings", { privacy: form }),
    onSuccess: onChanged,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Soukromí a runtime</CardTitle>
        <CardDescription>Hranice zpracování e-mailů a stav LLM / SMTP</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
          <p>LLM nakonfigurován: {settings?.runtime?.llm_configured ? "ano" : "ne"}</p>
          <p>E-mail dry-run: {settings?.runtime?.email_dry_run ? "zapnuto" : "vypnuto"}</p>
          <p>
            Reálné odesílání: {settings?.runtime?.email_sending_enabled ? "zapnuto" : "vypnuto"}
          </p>
        </div>
        {(
          [
            ["allow_llm_email_processing", "Povolit LLM zpracování e-mailů"],
            ["allow_llm_on_historical_mail", "Povolit AI na historické maily"],
            ["store_email_bodies", "Ukládat těla e-mailů"],
            ["redact_pii_in_logs", "Redigovat PII v logách"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              checked={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))}
              className="h-4 w-4 rounded border-border"
            />
            {label}
          </label>
        ))}
        <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? "Ukládám…" : "Uložit soukromí"}
        </Button>
      </CardContent>
    </Card>
  );
}

function EmailConnectSection({
  accounts,
  onChanged,
}: {
  accounts: EmailAccount[];
  onChanged: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const connectMutation = useMutation({
    mutationFn: () =>
      apiPost("/api/email/accounts", {
        email_address: email,
        password,
        provider: "email.cz",
        imap_host: "imap.seznam.cz",
        imap_port: 993,
        smtp_host: "smtp.seznam.cz",
        smtp_port: 465,
        allow_llm_processing: false,
      }),
    onSuccess: () => {
      setPassword("");
      onChanged();
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Připojení e-mailu</CardTitle>
        <CardDescription>
          Email.cz / Seznam — IMAP imap.seznam.cz:993, SMTP smtp.seznam.cz:465
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {accounts.length === 0 ? (
          <EmptyState title="Žádný účet" description="Připojte schránku aplikovaným heslem." />
        ) : (
          accounts.map((acc) => (
            <div
              key={acc.id}
              className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5"
            >
              <div>
                <div className="font-medium">{acc.email_address}</div>
                <div className="text-xs text-muted-foreground">
                  {acc.provider} · poslední sync {acc.last_sync_at ?? "nikdy"}
                </div>
              </div>
              <Badge variant={acc.connected ? "success" : "danger"}>
                {acc.connected ? "Připojeno" : "Odpojeno"}
              </Badge>
            </div>
          ))
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>E-mail</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vy@email.cz" />
          </div>
          <div className="space-y-1.5">
            <Label>Aplikační heslo</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
        </div>
        <Button
          disabled={connectMutation.isPending || !email || !password}
          onClick={() => connectMutation.mutate()}
        >
          {connectMutation.isPending ? "Připojuji…" : "Připojit Email.cz"}
        </Button>
        {connectMutation.isError ? (
          <p className="text-sm text-destructive">{connectMutation.error.message}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
