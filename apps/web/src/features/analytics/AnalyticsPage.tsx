import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet } from "@/lib/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageLoader } from "@/components/ui/spinner";

interface Overview {
  jobs_found?: number;
  jobs_relevant?: number;
  applications_ready?: number;
  applications_sent?: number;
  employer_replies?: number;
  interview_invitations?: number;
  average_match_score?: number;
  llm_cost_mtd_usd?: number;
  sample_size_note?: string;
}

export function AnalyticsPage() {
  const overviewQuery = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => apiGet<Overview>("/api/analytics/overview"),
  });

  const seriesQuery = useQuery({
    queryKey: ["analytics", "timeseries"],
    queryFn: () =>
      apiGet<{ series: Array<{ date: string; applications?: number; sent?: number; responses?: number; interviews?: number }> }>(
        "/api/analytics/timeseries",
      ),
  });

  const funnelQuery = useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: () =>
      apiGet<{ stages: Array<{ name: string; count: number }> }>("/api/analytics/funnel"),
  });

  if (overviewQuery.isLoading) return <PageLoader />;

  const overview = overviewQuery.data;
  const series = seriesQuery.data?.series ?? [];
  const funnel = (funnelQuery.data?.stages ?? []).map((s) => ({
    stage: s.name,
    count: s.count,
  }));

  const hasAny =
    (overview?.applications_sent ?? 0) +
      (overview?.jobs_found ?? 0) +
      series.length +
      funnel.reduce((sum, s) => sum + s.count, 0) >
    0;

  return (
    <div>
      <PageHeader
        title="Analytika"
        description="Metriky z reálných záznamů v databázi — bez vymyšlených čísel."
      />

      {!hasAny && !overviewQuery.isError ? (
        <EmptyState
          title="Zatím žádná data k analýze"
          description="Jakmile objevíte nabídky a odešlete přihlášky, zobrazí se funnel, časové řady a náklady LLM."
        />
      ) : null}

      <div className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Odeslané" value={overview?.applications_sent ?? 0} />
        <Metric title="Odpovědi" value={overview?.employer_replies ?? 0} />
        <Metric title="Pohovory" value={overview?.interview_invitations ?? 0} />
        <Metric
          title="Průměrné match skóre"
          value={
            overview?.average_match_score == null
              ? "—"
              : Math.round(overview.average_match_score).toString()
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Přihlášky v čase</CardTitle>
            <CardDescription>Vytvořené a odeslané přihlášky</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {series.length === 0 ? (
              <EmptyState title="Bez časové řady" description="API nevrátilo žádné body." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series}>
                  <defs>
                    <linearGradient id="apps" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(162 72% 42%)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="hsl(162 72% 42%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="hsl(220 14% 18%)" strokeDasharray="3 3" />
                  <XAxis dataKey="date" stroke="hsl(215 12% 58%)" fontSize={12} />
                  <YAxis stroke="hsl(215 12% 58%)" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(222 18% 10%)",
                      border: "1px solid hsl(220 14% 20%)",
                      borderRadius: 8,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="applications"
                    stroke="hsl(162 72% 42%)"
                    fill="url(#apps)"
                    name="Přihlášky"
                  />
                  <Area
                    type="monotone"
                    dataKey="sent"
                    stroke="hsl(200 70% 55%)"
                    fill="transparent"
                    name="Odeslané"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Náborový funnel</CardTitle>
            <CardDescription>Průchod pipeline z DB agregací</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {funnel.length === 0 ? (
              <EmptyState title="Funnel je prázdný" description="Zatím nejsou data po fázích." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnel}>
                  <CartesianGrid stroke="hsl(220 14% 18%)" strokeDasharray="3 3" />
                  <XAxis dataKey="stage" stroke="hsl(215 12% 58%)" fontSize={11} />
                  <YAxis stroke="hsl(215 12% 58%)" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(222 18% 10%)",
                      border: "1px solid hsl(220 14% 20%)",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="count" fill="hsl(162 72% 42%)" radius={[6, 6, 0, 0]} name="Počet" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Náklady AI (měsíc)</CardTitle>
            <CardDescription>Odhad z LLMUsage v overview endpointu</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <Metric
                title="Odhadované náklady MTD"
                value={`$${(overview?.llm_cost_mtd_usd ?? 0).toFixed(4)}`}
              />
              <Metric title="Připravené přihlášky" value={overview?.applications_ready ?? 0} />
            </div>
            {overview?.sample_size_note ? (
              <p className="mt-3 text-xs text-muted-foreground">{overview.sample_size_note}</p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({ title, value }: { title: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="font-display text-3xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}
